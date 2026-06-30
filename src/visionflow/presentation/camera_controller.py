"""Controlador de câmera compartilhado entre as telas Principal e Câmera.

Centraliza o ciclo de vida do :class:`CameraWorker` (em uma ``QThread``), expõe
comandos de alto nível e reemite os sinais do worker. Garante uma única
instância de câmera para toda a aplicação.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import NamedTuple

from PySide6.QtCore import QMetaObject, QObject, Qt, QThread, Signal

from visionflow.domain.camera_backends import (
    BACKEND_OPT,
    BACKEND_VIDEO,
    backend_supports_trigger,
)
from visionflow.domain.contracts.camera import CameraPort
from visionflow.domain.contracts.video_recorder import VideoRecorderPort
from visionflow.domain.use_cases.camera_config import CameraConfigService
from visionflow.presentation.camera_session_state import (
    STATE_CONNECTED,
    STATE_CONNECTING,
    STATE_DISCONNECTED,
    STATE_ERROR,
    STATE_SEARCHING,
    TRIGGER_PHASE_ACTIVE,
    TRIGGER_PHASE_DISABLING,
    TRIGGER_PHASE_IDLE,
    CameraSessionState,
)
from visionflow.presentation.workers.camera_worker import CameraWorker

# Reexporta constantes para compatibilidade com telas existentes.
__all__ = [
    "STATE_CONNECTED",
    "STATE_CONNECTING",
    "STATE_DISCONNECTED",
    "STATE_ERROR",
    "STATE_SEARCHING",
    "TRIGGER_PHASE_ACTIVE",
    "TRIGGER_PHASE_DISABLING",
    "TRIGGER_PHASE_ENABLING",
    "TRIGGER_PHASE_IDLE",
    "CameraController",
]

TRIGGER_PHASE_ENABLING = "enabling"

VIDEO_SEEK_STEP_SEC = 5

_logger = logging.getLogger(__name__)


class CameraWorkerFactories(NamedTuple):
    """Fábricas injetadas na composição para o worker de câmera."""

    camera: Callable[[str], CameraPort]
    video_recorder: Callable[[], VideoRecorderPort]


class CameraController(QObject):
    """Fachada de alto nível para operar a câmera a partir das telas."""

    devices_found = Signal(object)
    connected = Signal()
    connection_failed = Signal(str)
    disconnected = Signal()
    frame_ready = Signal(object, object)
    capture_ready = Signal(object, object)
    error = Signal(str)
    state_changed = Signal(str)
    trigger_mode_changed = Signal(bool)
    trigger_phase_changed = Signal(str)
    video_position_changed = Signal(int, int)
    video_playing_changed = Signal(bool)
    recording_armed = Signal()
    recording_started = Signal(str)
    recording_stopped = Signal(str)
    recording_failed = Signal(str)

    _req_discover = Signal(str, object)
    _req_connect_index = Signal(int)
    _req_connect_saved = Signal(object)
    _req_start_live = Signal()
    _req_stop_live = Signal()
    _req_set_video_live_loop = Signal(bool)
    _req_prepare_video_preview = Signal()
    _req_video_play = Signal()
    _req_video_pause = Signal()
    _req_video_seek_by_seconds = Signal(float)
    _req_video_seek_to_ms = Signal(int)
    _req_start_trigger = Signal()
    _req_stop_trigger = Signal()
    _req_grab_once = Signal()
    _req_disconnect = Signal()
    _req_start_recording = Signal(str)
    _req_stop_recording = Signal()

    def __init__(
        self,
        factories: CameraWorkerFactories,
        config_service: CameraConfigService,
        sdk_available: Callable[[], bool],
        backend_available: Callable[[str], bool],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._session = CameraSessionState()
        self._config_service = config_service
        self._sdk_available = sdk_available
        self._backend_available = backend_available
        self._current_backend = BACKEND_OPT
        self._video_live_loop = True
        self._recording_pending = False
        self._recording_active = False

        self._thread = QThread()
        self._thread.setObjectName("CameraWorkerThread")
        self._worker = CameraWorker(factories.camera, factories.video_recorder)
        self._worker.moveToThread(self._thread)
        self._thread.finished.connect(self._worker.deleteLater)

        self._wire_worker_bridge()
        self._thread.start()
        _logger.info("CameraController iniciado (thread do worker ativa).")

    def _wire_worker_bridge(self) -> None:
        queued = Qt.ConnectionType.QueuedConnection
        self._req_discover.connect(self._worker.discover, queued)
        self._req_connect_index.connect(self._worker.connect_device, queued)
        self._req_connect_saved.connect(self._worker.connect_saved, queued)
        self._req_start_live.connect(self._worker.start_live, queued)
        self._req_stop_live.connect(self._worker.stop_live, queued)
        self._req_set_video_live_loop.connect(self._worker.set_video_live_loop, queued)
        self._req_prepare_video_preview.connect(
            self._worker.prepare_video_preview, queued
        )
        self._req_video_play.connect(self._worker.video_play, queued)
        self._req_video_pause.connect(self._worker.video_pause, queued)
        self._req_video_seek_by_seconds.connect(
            self._worker.video_seek_by_seconds, queued
        )
        self._req_video_seek_to_ms.connect(self._worker.video_seek_to_ms, queued)
        self._req_start_trigger.connect(self._worker.start_trigger_listen, queued)
        self._req_stop_trigger.connect(self._worker.stop_trigger_listen, queued)
        self._req_grab_once.connect(self._worker.grab_once, queued)
        self._req_disconnect.connect(self._worker.disconnect_device, queued)
        self._req_start_recording.connect(self._worker.start_recording, queued)
        self._req_stop_recording.connect(self._worker.stop_recording, queued)

        self._worker.devices_found.connect(self._on_devices_found)
        self._worker.connected.connect(self._on_connected)
        self._worker.connection_failed.connect(self._on_connection_failed)
        self._worker.disconnected.connect(self._on_disconnected)
        self._worker.frame_ready.connect(self.frame_ready)
        self._worker.capture_ready.connect(self.capture_ready)
        self._worker.error.connect(self._on_worker_error)
        self._worker.trigger_mode_changed.connect(self._on_trigger_mode_changed)
        self._worker.video_position_changed.connect(self.video_position_changed)
        self._worker.video_playing_changed.connect(self.video_playing_changed)
        self._worker.recording_started.connect(self._on_recording_started)
        self._worker.recording_stopped.connect(self._on_recording_stopped)
        self._worker.recording_failed.connect(self._on_recording_failed)

    def set_video_live_loop(self, enabled: bool) -> None:
        """Define preview em loop para vídeo (wizard); ``False`` na Principal."""
        self._video_live_loop = enabled
        self._req_set_video_live_loop.emit(enabled)

    @property
    def state(self) -> str:
        return self._session.connection_state

    def _set_state(self, state: str) -> None:
        if self._session.set_connection_state(state):
            _logger.debug("Estado da câmera: %s", state)
            self.state_changed.emit(state)

    def is_sdk_available(self) -> bool:
        return self._sdk_available()

    def is_backend_available(self, backend: str) -> bool:
        return self._backend_available(backend)

    @property
    def current_backend(self) -> str:
        return self._current_backend

    @property
    def is_video_backend(self) -> bool:
        return self._current_backend == BACKEND_VIDEO

    @property
    def supports_trigger(self) -> bool:
        if self._session.connection_state == STATE_CONNECTED:
            return self._session.connected_supports_trigger
        config = self._config_service.load()
        if config is not None:
            return backend_supports_trigger(config.backend)
        return backend_supports_trigger(self._current_backend)

    @property
    def trigger_mode_active(self) -> bool:
        return self._session.trigger_mode_active

    @property
    def trigger_phase(self) -> str:
        return self._session.trigger_phase

    @property
    def is_recording(self) -> bool:
        return self._recording_pending or self._recording_active

    @property
    def is_recording_active(self) -> bool:
        return self._recording_active

    def _set_trigger_phase(self, phase: str) -> None:
        if self._session.set_trigger_phase(phase):
            self.trigger_phase_changed.emit(phase)

    def discover(self, backend: str, context: object = None) -> None:
        self._current_backend = backend
        _logger.info("Solicitada busca de câmeras (backend=%s).", backend)
        self._set_state(STATE_SEARCHING)
        self._req_discover.emit(backend, context)

    def connect_index(self, index: int) -> None:
        _logger.info("Solicitada conexão pelo índice %s.", index)
        self._set_state(STATE_CONNECTING)
        self._req_connect_index.emit(index)

    def connect_saved(self) -> None:
        config = self._config_service.load()
        if config is None:
            _logger.warning("Conexão salva falhou: nenhuma configuração persistida.")
            self.connection_failed.emit(
                "Nenhuma câmera configurada. Use a tela Câmera primeiro."
            )
            self._set_state(STATE_ERROR)
            return
        self._current_backend = config.backend
        _logger.info(
            "Solicitada conexão com câmera salva (backend=%s, serial=%s, ip=%s).",
            config.backend,
            config.serial,
            config.ip,
        )
        self._set_state(STATE_CONNECTING)
        self._req_connect_saved.emit(config)

    def start_live(self) -> None:
        self._req_start_live.emit()

    def stop_live(self) -> None:
        self._req_stop_live.emit()

    def grab_once(self) -> None:
        self._req_grab_once.emit()

    def video_play(self) -> None:
        self._req_video_play.emit()

    def video_pause(self) -> None:
        self._req_video_pause.emit()

    def video_seek_back(self) -> None:
        self._req_video_seek_by_seconds.emit(-float(VIDEO_SEEK_STEP_SEC))

    def video_seek_forward(self) -> None:
        self._req_video_seek_by_seconds.emit(float(VIDEO_SEEK_STEP_SEC))

    def video_seek_to_ms(self, position_ms: int) -> None:
        self._req_video_seek_to_ms.emit(position_ms)

    def start_recording(self, output_path: str) -> None:
        if self.is_recording:
            return
        _logger.info("Solicitada gravação de vídeo: %s", output_path)
        self._recording_pending = True
        self.recording_armed.emit()
        self._req_start_recording.emit(output_path)

    def stop_recording(self) -> None:
        if not self.is_recording:
            return
        _logger.info("Solicitada parada da gravação de vídeo.")
        self._req_stop_recording.emit()

    def set_trigger_mode(self, enabled: bool) -> None:
        if enabled:
            if self._session.connection_state != STATE_CONNECTED:
                _logger.warning("Trigger ignorado: câmera não conectada.")
                self._set_trigger_phase(TRIGGER_PHASE_IDLE)
                self.trigger_mode_changed.emit(False)
                return
            if not self.supports_trigger:
                _logger.warning("Trigger ignorado: câmera não suporta trigger.")
                self._set_trigger_phase(TRIGGER_PHASE_IDLE)
                self.trigger_mode_changed.emit(False)
                self.error.emit("Esta câmera não suporta trigger externo.")
                return
            _logger.info("Solicitada ativação do modo trigger.")
            self._set_trigger_phase(TRIGGER_PHASE_ENABLING)
            self._req_start_trigger.emit()
            return
        _logger.info("Solicitada desativação do modo trigger.")
        self._set_trigger_phase(TRIGGER_PHASE_DISABLING)
        self._req_stop_trigger.emit()

    def disconnect(self) -> None:
        if self._session.connection_state == STATE_DISCONNECTED:
            return
        self._set_state(STATE_DISCONNECTED)
        self._set_trigger_phase(TRIGGER_PHASE_DISABLING)
        self._req_stop_trigger.emit()
        self._req_stop_live.emit()
        self._req_disconnect.emit()

    def shutdown(self) -> None:
        if not self._thread.isRunning():
            return
        _logger.info("Encerrando CameraController e thread do worker.")
        QMetaObject.invokeMethod(
            self._worker,
            "shutdown",
            Qt.ConnectionType.BlockingQueuedConnection,
        )
        self._thread.quit()
        if not self._thread.wait(5000):
            _logger.warning("Thread do worker não encerrou em 5 s.")

    def _on_devices_found(self, devices: object) -> None:
        count = len(devices) if devices is not None else 0
        _logger.info("Busca retornou %d dispositivo(s) à UI.", count)
        self._set_state(STATE_DISCONNECTED)
        self.devices_found.emit(devices)

    def _resume_preview(self) -> None:
        """Retoma o preview: vídeo na Principal abre tocando; live nos demais."""
        if self._current_backend == BACKEND_VIDEO and not self._video_live_loop:
            self._req_prepare_video_preview.emit()
            self._req_video_play.emit()
        else:
            self._req_start_live.emit()

    def _on_connected(self, supports_trigger: bool) -> None:
        if self._session.connection_state != STATE_CONNECTING:
            _logger.info(
                "Sinal connected ignorado (estado atual=%s); desconectando resíduo.",
                self._session.connection_state,
            )
            self._req_stop_live.emit()
            self._req_disconnect.emit()
            return
        _logger.info("Câmera conectada; iniciando preview ao vivo.")
        self._session.connected_supports_trigger = supports_trigger
        self._set_state(STATE_CONNECTED)
        self.connected.emit()
        self._resume_preview()

    def _on_worker_error(self, message: str) -> None:
        _logger.warning("Erro do worker de câmera: %s", message)
        self.error.emit(message)

    def _on_trigger_mode_changed(self, active: bool) -> None:
        self._session.trigger_mode_active = active
        self._set_trigger_phase(TRIGGER_PHASE_ACTIVE if active else TRIGGER_PHASE_IDLE)
        self.trigger_mode_changed.emit(active)
        if not active and self._session.connection_state == STATE_CONNECTED:
            self._resume_preview()

    def _on_connection_failed(self, message: str) -> None:
        _logger.warning("Falha de conexão reportada à UI: %s", message)
        self._set_state(STATE_ERROR)
        self.connection_failed.emit(message)

    def _on_disconnected(self) -> None:
        _logger.info("Câmera desconectada (sinal do worker).")
        self._session.trigger_mode_active = False
        self._set_trigger_phase(TRIGGER_PHASE_IDLE)
        self._clear_recording_state()
        self._set_state(STATE_DISCONNECTED)
        self.disconnected.emit()

    def _clear_recording_state(self) -> None:
        self._recording_pending = False
        self._recording_active = False

    def _on_recording_started(self, path: str) -> None:
        self._recording_pending = False
        self._recording_active = True
        self.recording_started.emit(path)

    def _on_recording_stopped(self, path: str) -> None:
        self._clear_recording_state()
        self.recording_stopped.emit(path)

    def _on_recording_failed(self, message: str) -> None:
        self._clear_recording_state()
        self.recording_failed.emit(message)
