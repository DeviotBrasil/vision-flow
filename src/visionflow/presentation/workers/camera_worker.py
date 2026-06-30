"""Worker de câmera executado em uma ``QThread`` dedicada.

Mantém a thread da GUI livre: descoberta de dispositivos, conexão e captura de
frames (operações nativas potencialmente lentas) rodam aqui. A comunicação com
a UI é feita exclusivamente por sinais/slots. O adapter devolve ``numpy.ndarray``
independente por frame (cópia na infrastructure), seguro para cruzar threads.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from visionflow.domain.camera_backends import BACKEND_OPT
from visionflow.domain.contracts.camera import (
    CameraError,
    CameraPort,
    IncompleteFrameError,
    TriggerCapableCamera,
    TriggerWaitError,
    VideoPlaybackPort,
    camera_supports_trigger,
    camera_supports_video_playback,
)
from visionflow.domain.contracts.video_recorder import VideoRecorderPort
from visionflow.domain.entities.camera_config import CameraConfig
from visionflow.domain.use_cases.connect_saved import (
    SavedConnectionFailure,
    resolve_saved_device,
)
from visionflow.presentation.discover_context_parser import (
    parse_discover_context,
)
from visionflow.presentation.workers.recording_session import RecordingSession

# Intervalo do preview ao vivo (~30 fps).
_LIVE_INTERVAL_MS = 33
_MIN_LIVE_INTERVAL_MS = 16

_logger = logging.getLogger(__name__)


class CameraWorker(QObject):
    """Opera um :class:`CameraPort` e expõe operações assíncronas via slots.

    A câmera concreta é criada por um ``camera_factory`` injetado, mantendo a
    criação preguiçosa na própria thread do worker (sem acoplar a presentation
    a um adapter específico).
    """

    devices_found = Signal(object)  # list[DeviceInfo]
    connected = Signal(bool)  # supports_trigger
    connection_failed = Signal(str)
    disconnected = Signal()
    frame_ready = Signal(object, object)  # (ndarray, meta)
    capture_ready = Signal(object, object)  # (ndarray, meta) de captura única
    error = Signal(str)
    trigger_mode_changed = Signal(bool)
    video_position_changed = Signal(int, int)
    video_playing_changed = Signal(bool)
    recording_started = Signal(str)
    recording_stopped = Signal(str)
    recording_failed = Signal(str)

    def __init__(
        self,
        camera_factory: Callable[[str], CameraPort],
        video_recorder_factory: Callable[[], VideoRecorderPort],
    ) -> None:
        super().__init__()
        self._camera_factory = camera_factory
        self._video_recorder_factory = video_recorder_factory
        self._backend = BACKEND_OPT
        self._camera: CameraPort | None = None
        self._live_timer: QTimer | None = None
        self._live_busy = False
        self._trigger_listen = False
        self._trigger_busy = False
        self._session = 0
        self._disconnecting = False
        self._video_live_loop = True
        self._recording = RecordingSession(video_recorder_factory)

    def set_video_live_loop(self, enabled: bool) -> None:
        self._video_live_loop = enabled

    def _reset_camera_if_backend_changed(self, backend: str) -> None:
        if backend == self._backend and self._camera is not None:
            return
        if self._camera is not None:
            if self._camera.is_connected:
                try:
                    self._camera.disconnect()
                except (CameraError, OSError) as exc:
                    _logger.warning(
                        "Falha ao desconectar ao trocar backend (%s): %s",
                        self._backend,
                        exc,
                    )
            self._camera = None
        self._backend = backend

    def _ensure_camera(self) -> CameraPort:
        if self._camera is None:
            try:
                self._camera = self._camera_factory(self._backend)
            except CameraError as exc:
                _logger.warning("Falha ao criar adapter de câmera: %s", exc)
                raise
        return self._camera

    def _ensure_timer(self) -> QTimer:
        if self._live_timer is None:
            timer = QTimer(self)
            timer.timeout.connect(self._on_live_tick)
            self._live_timer = timer
        return self._live_timer

    def _live_interval_for_camera(self, camera: CameraPort) -> int:
        if camera_supports_video_playback(camera):
            return max(int(1000 / camera.fps), _MIN_LIVE_INTERVAL_MS)
        return _LIVE_INTERVAL_MS

    def _emit_video_position(self, camera: CameraPort) -> None:
        if not camera_supports_video_playback(camera):
            return
        self.video_position_changed.emit(camera.position_ms, camera.duration_ms)

    def _video_playback_camera(self) -> VideoPlaybackPort | None:
        camera = self._camera
        if camera is None or not camera.is_connected:
            return None
        if not isinstance(camera, VideoPlaybackPort):
            return None
        return camera

    def _seek_and_emit(self, seek: Callable[[VideoPlaybackPort], None]) -> None:
        camera = self._video_playback_camera()
        if camera is None:
            return
        try:
            seek(camera)
            frame, meta = camera.grab()
        except CameraError as exc:
            _logger.warning("Seek de vídeo falhou: %s", exc)
            self.error.emit(str(exc))
            return
        self.frame_ready.emit(frame, meta)
        self._emit_video_position(camera)

    def _cancel_session(self) -> int:
        """Invalida conexões/grabs em andamento (ex.: usuário clicou em Voltar)."""
        self._session += 1
        return self._session

    def _session_valid(self, token: int) -> bool:
        return token == self._session

    def _connect_index(self, index: int, token: int) -> None:
        """Seleciona e conecta o dispositivo, emitindo sinais de resultado."""
        camera = self._ensure_camera()
        try:
            camera.select_device(index)
            camera.connect()
        except CameraError as exc:
            _logger.warning("Conexão falhou (índice=%s): %s", index, exc)
            self.connection_failed.emit(str(exc))
            return
        if not self._session_valid(token):
            _logger.info("Conexão índice=%s descartada (sessão cancelada).", index)
            with contextlib.suppress(CameraError):
                camera.disconnect()
            return
        _logger.info("Conexão estabelecida (índice=%s).", index)
        self.connected.emit(camera_supports_trigger(camera))

    def _stop_trigger_listen(self, *, emit_signal: bool) -> None:
        """Interrompe o loop de escuta de trigger."""
        was_active = self._trigger_listen
        self._trigger_listen = False
        if emit_signal and was_active:
            self.trigger_mode_changed.emit(False)

    def _disable_trigger_on_camera(self) -> None:
        camera = self._camera
        if camera is None or not camera.is_connected:
            return
        if not isinstance(camera, TriggerCapableCamera):
            return
        with contextlib.suppress(CameraError):
            camera.set_trigger_mode(False)

    def _schedule_trigger_grab(self) -> None:
        if self._trigger_listen and not self._disconnecting:
            QTimer.singleShot(0, self, self._on_trigger_grab)

    def _fail_trigger_listen(self, message: str) -> None:
        _logger.warning("Modo trigger interrompido: %s", message)
        self._stop_trigger_listen(emit_signal=True)
        self._disable_trigger_on_camera()
        self.error.emit(message)

    @property
    def is_recording(self) -> bool:
        return self._recording.is_active

    def _write_recording_frame(self, frame: object, _meta: object) -> None:
        result = self._recording.handle_frame(frame)
        if result.failed_message is not None:
            self.recording_failed.emit(result.failed_message)
        elif result.started_path is not None:
            self.recording_started.emit(result.started_path)

    def _finalize_recording(self, *, empty_message: str | None = None) -> None:
        result = self._recording.finalize(empty_message=empty_message)
        if result.kind == "stopped" and result.path is not None:
            self.recording_stopped.emit(result.path)
        elif result.kind == "failed" and result.message is not None:
            self.recording_failed.emit(result.message)

    # -- Slots ----------------------------------------------------------------

    @Slot(str, object)
    def discover(self, backend: str, context: object = None) -> None:
        """Busca câmeras do backend indicado e emite :attr:`devices_found`."""
        self._reset_camera_if_backend_changed(backend)
        discover_context = parse_discover_context(context)
        try:
            devices = self._ensure_camera().discover(context=discover_context)
        except CameraError as exc:
            _logger.warning("Busca de câmeras falhou: %s", exc)
            self.error.emit(str(exc))
            return
        _logger.debug("Busca emitida com %d dispositivo(s).", len(devices))
        self.devices_found.emit(devices)

    @Slot(int)
    def connect_device(self, index: int) -> None:
        """Seleciona e conecta o dispositivo de índice ``index``."""
        self._connect_index(index, self._session)

    @Slot(object)
    def connect_saved(self, config: CameraConfig) -> None:
        """Busca e conecta a câmera salva, casando por série, IP, nome ou índice."""
        token = self._session
        self._reset_camera_if_backend_changed(config.backend)
        camera = self._ensure_camera()
        result = resolve_saved_device(camera, config)
        if isinstance(result, SavedConnectionFailure):
            _logger.warning("Conexão salva falhou: %s", result.message)
            self.connection_failed.emit(result.message)
            return
        if not self._session_valid(token):
            return
        self._connect_index(result.device_index, token)

    @Slot()
    def start_live(self) -> None:
        """Inicia o preview contínuo."""
        if self._disconnecting:
            return
        self._stop_trigger_listen(emit_signal=True)
        self._disable_trigger_on_camera()
        if self._camera is None or not self._camera.is_connected:
            _logger.warning("Preview ao vivo ignorado: câmera não conectada.")
            self.error.emit("Câmera não conectada para iniciar o preview.")
            return
        camera = self._camera
        if camera_supports_video_playback(camera):
            camera.set_loop_on_end(self._video_live_loop)
            if self._video_live_loop:
                camera.play()
            else:
                camera.pause()
        _logger.debug("Preview ao vivo iniciado.")
        timer = self._ensure_timer()
        timer.setInterval(self._live_interval_for_camera(camera))
        if camera_supports_video_playback(camera) and not camera.is_playing:
            return
        timer.start()

    @Slot()
    def stop_live(self) -> None:
        """Interrompe o preview contínuo."""
        if self._live_timer is not None:
            self._live_timer.stop()
            _logger.debug("Preview ao vivo interrompido.")

    @Slot()
    def prepare_video_preview(self) -> None:
        """Exibe o primeiro frame pausado (playback controlado na Principal)."""
        camera = self._video_playback_camera()
        if camera is None:
            return
        self.stop_live()
        camera.set_loop_on_end(False)
        camera.pause()
        try:
            frame, meta = camera.grab()
        except CameraError as exc:
            _logger.warning("Preview de vídeo falhou: %s", exc)
            self.error.emit(str(exc))
            return
        self.frame_ready.emit(frame, meta)
        self._emit_video_position(camera)
        self.video_playing_changed.emit(False)

    @Slot()
    def video_play(self) -> None:
        camera = self._video_playback_camera()
        if camera is None:
            return
        camera.play()
        timer = self._ensure_timer()
        timer.setInterval(self._live_interval_for_camera(camera))
        timer.start()
        self.video_playing_changed.emit(True)

    @Slot()
    def video_pause(self) -> None:
        camera = self._video_playback_camera()
        if camera is None:
            return
        camera.pause()
        self.stop_live()
        self.video_playing_changed.emit(False)

    @Slot(float)
    def video_seek_by_seconds(self, delta: float) -> None:
        self._seek_and_emit(lambda camera: camera.seek_by_seconds(delta))

    @Slot(int)
    def video_seek_to_ms(self, position_ms: int) -> None:
        self._seek_and_emit(lambda camera: camera.seek_to_ms(position_ms))

    @Slot()
    def start_trigger_listen(self) -> None:
        """Ativa escuta de trigger externo (para o live e aguarda eventos)."""
        if self._disconnecting:
            return
        if self._trigger_listen:
            _logger.debug("Modo trigger já ativo; ignorando nova ativação.")
            return
        camera = self._camera
        if camera is None or not camera.is_connected:
            _logger.warning("Modo trigger ignorado: câmera não conectada.")
            self.error.emit("Câmera não conectada para ativar o trigger.")
            self.trigger_mode_changed.emit(False)
            return
        if not isinstance(camera, TriggerCapableCamera) or not camera.supports_trigger:
            _logger.warning("Modo trigger ignorado: câmera não suporta trigger.")
            self.error.emit("Esta câmera não suporta trigger externo.")
            self.trigger_mode_changed.emit(False)
            return
        self._finalize_recording()
        self.stop_live()
        try:
            camera.set_trigger_mode(True)
        except CameraError as exc:
            _logger.warning("Falha ao ativar TriggerMode: %s", exc)
            self.error.emit(str(exc))
            self.trigger_mode_changed.emit(False)
            return
        self._trigger_listen = True
        self.trigger_mode_changed.emit(True)
        _logger.info("Modo trigger ativado; aguardando eventos.")
        # Pequeno atraso evita corrida com o último grab do preview ao vivo.
        QTimer.singleShot(50, self, self._schedule_trigger_grab)

    @Slot()
    def stop_trigger_listen(self) -> None:
        """Desativa escuta de trigger e restaura TriggerMode=Off."""
        self._stop_trigger_listen(emit_signal=True)
        self._disable_trigger_on_camera()
        _logger.info("Modo trigger desativado.")

    @Slot()
    def grab_once(self) -> None:
        """Captura um único frame e emite :attr:`capture_ready`."""
        if self._trigger_listen:
            _logger.warning("Captura única ignorada: modo trigger ativo.")
            self.error.emit("Desative o trigger para capturar manualmente.")
            return
        if self._camera is None or not self._camera.is_connected:
            _logger.warning("Captura única ignorada: câmera não conectada.")
            self.error.emit("Câmera não conectada para capturar.")
            return
        try:
            frame, meta = self._camera.grab(single=True)
        except CameraError as exc:
            _logger.warning("Captura única falhou: %s", exc)
            self.error.emit(str(exc))
            return
        _logger.debug("Captura única concluída (frame_id=%s).", meta.get("frame_id"))
        self.capture_ready.emit(frame, meta)

    @Slot(str)
    def start_recording(self, output_path: str) -> None:
        """Arma gravação; mede a taxa real do preview antes de abrir o arquivo."""
        if self.is_recording:
            _logger.debug("Gravação já ativa; ignorando nova solicitação.")
            return
        if self._trigger_listen:
            _logger.warning("Gravação ignorada: modo trigger ativo.")
            self.recording_failed.emit("Desative o trigger para gravar.")
            return
        if self._camera is None or not self._camera.is_connected:
            _logger.warning("Gravação ignorada: câmera não conectada.")
            self.recording_failed.emit("Câmera não conectada para gravar.")
            return
        self._recording.arm(output_path)

    @Slot()
    def stop_recording(self) -> None:
        """Finaliza a gravação em andamento."""
        self._finalize_recording(empty_message="Nenhum frame foi gravado.")

    @Slot()
    def disconnect_device(self) -> None:
        """Para o preview e desconecta a câmera."""
        self._cancel_session()
        self._disconnecting = True
        try:
            self._stop_trigger_listen(emit_signal=True)
            self._finalize_recording()
            self.stop_live()
            if self._camera is not None:
                try:
                    self._camera.disconnect()
                except CameraError as exc:
                    _logger.warning("Erro ao desconectar câmera: %s", exc)
                except Exception:
                    _logger.exception("Falha inesperada ao desconectar câmera.")
        finally:
            self._disconnecting = False
        _logger.info("Worker: câmera desconectada.")
        self.disconnected.emit()

    @Slot()
    def shutdown(self) -> None:
        """Encerra recursos da câmera (chamado no fim de vida da thread)."""
        _logger.info("Worker: encerrando recursos da câmera.")
        self._cancel_session()
        self._disconnecting = True
        try:
            self._stop_trigger_listen(emit_signal=False)
            self._finalize_recording()
            self.stop_live()
        finally:
            self._disconnecting = False
        if self._camera is not None:
            try:
                self._camera.disconnect()
            except CameraError as exc:
                _logger.warning("Erro ao desconectar câmera no shutdown: %s", exc)
            except Exception:
                _logger.exception("Falha inesperada ao desconectar câmera no shutdown.")

    # -- Loop de preview ------------------------------------------------------

    def _on_live_tick(self) -> None:
        if self._disconnecting or self._trigger_listen:
            self.stop_live()
            return
        if self._live_busy:
            return
        camera = self._camera
        if camera is None or not camera.is_connected:
            self.stop_live()
            return
        self._live_busy = True
        try:
            if self._disconnecting:
                return
            if camera_supports_video_playback(camera) and not camera.is_playing:
                self.stop_live()
                self.video_playing_changed.emit(False)
                return
            frame, meta = camera.grab()
            self._write_recording_frame(frame, meta)
            self.frame_ready.emit(frame, meta)
            if camera_supports_video_playback(camera):
                self._emit_video_position(camera)
                if not camera.is_playing:
                    self.stop_live()
                    self.video_playing_changed.emit(False)
        except IncompleteFrameError as exc:
            _logger.debug("Preview: frame incompleto ignorado (%s).", exc)
        except CameraError as exc:
            _logger.warning("Preview ao vivo interrompido por erro: %s", exc)
            self.stop_live()
            self.error.emit(str(exc))
        except Exception:
            _logger.exception("Preview: falha inesperada no grab.")
        finally:
            self._live_busy = False

    # -- Loop de trigger ------------------------------------------------------

    def _on_trigger_grab(self) -> None:
        if not self._trigger_listen or self._disconnecting:
            return
        if self._trigger_busy:
            return
        camera = self._camera
        if camera is None or not camera.is_connected:
            self._fail_trigger_listen("Câmera desconectada durante escuta de trigger.")
            return
        self._trigger_busy = True
        try:
            if not self._trigger_listen or self._disconnecting:
                return
            frame, meta = camera.grab(single=True)
            _logger.debug(
                "Trigger recebido (frame_id=%s); salvando captura.",
                meta.get("frame_id"),
            )
            self.frame_ready.emit(frame, meta)
            self.capture_ready.emit(frame, meta)
        except TriggerWaitError as exc:
            _logger.debug("Trigger: ainda aguardando evento (%s).", exc)
        except IncompleteFrameError as exc:
            _logger.debug("Trigger: frame incompleto ignorado (%s).", exc)
        except CameraError as exc:
            self._fail_trigger_listen(str(exc))
            return
        except Exception:
            _logger.exception("Trigger: falha inesperada no grab.")
            self._fail_trigger_listen("Falha inesperada no modo trigger.")
            return
        finally:
            self._trigger_busy = False
        self._schedule_trigger_grab()
