"""Adapter para reprodução de arquivo de vídeo via OpenCV."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from visionflow.domain.contracts.camera import CameraError, VideoPlaybackPort
from visionflow.domain.entities.device_info import DeviceInfo
from visionflow.domain.entities.discover_context import DiscoverContext
from visionflow.domain.entities.video_path import normalize_video_path
from visionflow.infrastructure.camera.opencv_base import OpenCvCameraBase
from visionflow.infrastructure.camera.opencv_frames import frame_to_rgb8

_logger = logging.getLogger(__name__)

_DEFAULT_FPS = 30.0


class VideoCameraError(CameraError):
    """Erro de operação com arquivo de vídeo."""


class VideoCamera(OpenCvCameraBase, VideoPlaybackPort):
    """Arquivo de vídeo acessado via ``cv2.VideoCapture``.

    Fluxo típico: :meth:`discover` (com ``DiscoverContext.video_path``) →
    :meth:`select_device` → :meth:`connect` → repetidas chamadas a
    :meth:`grab` → :meth:`disconnect`.

    Na tela Principal o playback é controlado (pausar/seek); no wizard de
    Câmera pode operar em loop contínuo via :meth:`set_loop_on_end`.
    """

    _connected_guard_message = (
        "Não é possível importar vídeo com a fonte conectada. "
        "Desconecte antes de uma nova importação."
    )

    def __init__(self) -> None:
        super().__init__()
        self._source_path: Path | None = None
        self._playing = False
        self._loop_on_end = False
        self._fps = _DEFAULT_FPS
        self._duration_ms = 0
        self._cached_frame: np.ndarray | None = None

    @property
    def _camera_error(self) -> type[CameraError]:
        return VideoCameraError

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def position_ms(self) -> int:
        with self._io_lock:
            return self._current_position_ms()

    @property
    def duration_ms(self) -> int:
        return self._duration_ms

    @property
    def fps(self) -> float:
        return self._fps

    def play(self) -> None:
        with self._io_lock:
            self._ensure_ready_for_playback()
            if self._at_end_locked():
                self._seek_to_ms_locked(0)
            self._playing = True

    def pause(self) -> None:
        with self._io_lock:
            self._playing = False

    def seek_by_seconds(self, delta: float) -> None:
        with self._io_lock:
            self._ensure_ready_for_playback()
            target = self._current_position_ms() + int(delta * 1000)
            self._seek_to_ms_locked(target)

    def seek_to_ms(self, position_ms: int) -> None:
        with self._io_lock:
            self._ensure_ready_for_playback()
            self._seek_to_ms_locked(position_ms)

    def set_loop_on_end(self, enabled: bool) -> None:
        with self._io_lock:
            self._loop_on_end = enabled

    def _discover_locked(self, context: DiscoverContext | None) -> list[DeviceInfo]:
        raw_path = context.video_path if context is not None else None
        if not raw_path:
            self._devices = []
            _logger.info("Busca de vídeo concluída: nenhum caminho informado.")
            return []

        path = Path(normalize_video_path(raw_path))
        if not path.is_file():
            raise VideoCameraError(f"Arquivo de vídeo não encontrado: {path}")

        metadata = _probe_video_metadata(path)
        device = DeviceInfo(
            index=0,
            name=path.name,
            model="Arquivo de vídeo",
            serial="",
            ip="",
            mac="",
            interface="Arquivo",
            tl_type="VIDEO",
            extra={"video_path": str(path), **metadata},
        )
        self._devices = [device]
        _logger.info("Vídeo importado para descoberta: %s", path)
        return list(self._devices)

    def _open_capture_for_device(self, device: DeviceInfo) -> cv2.VideoCapture:
        video_path = str(device.extra.get("video_path", ""))
        if not video_path:
            raise VideoCameraError(
                "Caminho do vídeo ausente no dispositivo selecionado."
            )
        path = Path(normalize_video_path(video_path))
        if not path.is_file():
            raise VideoCameraError(f"Arquivo de vídeo não encontrado: {path}")
        _logger.info("Conectando arquivo de vídeo: %s", path)
        self._source_path = path
        return self._open_capture(path)

    def _open_capture(self, path: Path) -> cv2.VideoCapture:
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            capture.release()
            raise VideoCameraError(f"Não foi possível abrir o vídeo: {path}")
        ok, _frame = capture.read()
        if not ok:
            capture.release()
            raise VideoCameraError("Vídeo aberto, mas não entregou frame de teste.")
        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        return capture

    def _connect_locked(self) -> None:
        super()._connect_locked()
        assert self._capture is not None
        metadata = _read_capture_metadata(self._capture)
        self._fps = float(metadata.get("fps", _DEFAULT_FPS))
        self._duration_ms = int(metadata.get("duration_ms", 0))
        self._playing = False
        self._loop_on_end = False
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self._cached_frame = self._read_frame_at_current_position()

    def disconnect(self) -> None:
        super().disconnect()
        with self._io_lock:
            self._source_path = None
            self._playing = False
            self._loop_on_end = False
            self._cached_frame = None
            self._duration_ms = 0
            self._fps = _DEFAULT_FPS

    def grab(self, *, single: bool = False) -> tuple[np.ndarray, dict[str, Any]]:
        del single
        with self._io_lock:
            self._ensure_ready_for_playback()
            if self._playing:
                frame = self._read_next_frame()
            else:
                frame = self._require_cached_frame()
            self._frame_id += 1
            rgb, meta = frame_to_rgb8(frame, frame_id=self._frame_id)
            meta["position_ms"] = self._current_position_ms()
            meta["duration_ms"] = self._duration_ms
            return rgb, meta

    def _ensure_ready_for_playback(self) -> None:
        if self._capture is None or not self._connected or self._source_path is None:
            raise VideoCameraError("Vídeo não conectado.")

    def _require_cached_frame(self) -> np.ndarray:
        if self._cached_frame is None:
            raise VideoCameraError("Nenhum frame disponível no vídeo.")
        return self._cached_frame

    def _at_end_locked(self) -> bool:
        if self._duration_ms <= 0:
            return False
        frame_ms = 1000.0 / self._fps if self._fps > 0 else 0.0
        return self._current_position_ms() >= self._duration_ms - frame_ms - 1

    def _current_position_ms(self) -> int:
        assert self._capture is not None
        pos = self._capture.get(cv2.CAP_PROP_POS_MSEC)
        if pos is None or pos < 0:
            return 0
        return min(int(pos), self._duration_ms)

    def _seek_to_ms_locked(self, position_ms: int) -> None:
        assert self._capture is not None
        clamped = max(0, min(position_ms, self._duration_ms))
        self._capture.set(cv2.CAP_PROP_POS_MSEC, clamped)
        frame = self._read_frame_at_current_position()
        if frame is not None:
            self._cached_frame = frame

    def _read_frame_at_current_position(self) -> np.ndarray | None:
        assert self._capture is not None
        ok, frame = self._capture.read()
        if ok and frame is not None:
            return frame.copy()
        return None

    def _read_next_frame(self) -> np.ndarray:
        assert self._capture is not None
        assert self._source_path is not None

        ok, frame = self._capture.read()
        if ok and frame is not None:
            self._cached_frame = frame.copy()
            return self._cached_frame

        if self._loop_on_end:
            return self._loop_to_start()

        self._playing = False
        self._seek_to_end_locked()
        return self._require_cached_frame()

    def _loop_to_start(self) -> np.ndarray:
        assert self._capture is not None
        assert self._source_path is not None

        self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = self._capture.read()
        if ok and frame is not None:
            self._cached_frame = frame.copy()
            return self._cached_frame

        _logger.debug("Seek ao início falhou; reabrindo vídeo: %s", self._source_path)
        self._capture.release()
        self._capture = self._open_capture(self._source_path)
        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise VideoCameraError("Falha ao ler frame do vídeo.")
        self._cached_frame = frame.copy()
        return self._cached_frame

    def _seek_to_end_locked(self) -> None:
        assert self._capture is not None
        if self._duration_ms > 0:
            self._capture.set(cv2.CAP_PROP_POS_MSEC, max(0, self._duration_ms - 1))
        frame = self._read_frame_at_current_position()
        if frame is not None:
            self._cached_frame = frame


def _read_capture_metadata(capture: cv2.VideoCapture) -> dict[str, int | float]:
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    if fps <= 0:
        fps = _DEFAULT_FPS
    frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_ms = 0
    if frame_count > 0:
        duration_ms = max(0, int(frame_count / fps * 1000))
    return {
        "width": width,
        "height": height,
        "fps": fps,
        "duration_ms": duration_ms,
    }


def _probe_video_metadata(path: Path) -> dict[str, int | float]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        return {}
    try:
        return _read_capture_metadata(capture)
    finally:
        capture.release()
