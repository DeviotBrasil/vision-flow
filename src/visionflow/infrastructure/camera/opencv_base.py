"""Base compartilhada para adapters OpenCV (UVC e arquivo de vídeo)."""

from __future__ import annotations

import logging
import threading
from abc import abstractmethod
from typing import Any, ClassVar

import cv2
import numpy as np

from visionflow.domain.contracts.camera import CameraError, CameraPort
from visionflow.domain.entities.device_info import DeviceInfo
from visionflow.domain.entities.discover_context import DiscoverContext
from visionflow.infrastructure.camera.opencv_frames import frame_to_rgb8

_logger = logging.getLogger(__name__)


class OpenCvCameraBase(CameraPort):
    """Implementação comum de câmeras baseadas em ``cv2.VideoCapture``."""

    _connected_guard_message: ClassVar[str] = (
        "Não é possível buscar dispositivos com a câmera conectada. "
        "Desconecte antes de uma nova busca."
    )

    def __init__(self) -> None:
        self._capture: cv2.VideoCapture | None = None
        self._devices: list[DeviceInfo] = []
        self._selected_index: int | None = None
        self._connected = False
        self._frame_id = 0
        self._io_lock = threading.Lock()

    @property
    @abstractmethod
    def _camera_error(self) -> type[CameraError]:
        """Subclasse de :class:`CameraError` levantada por este adapter."""

    @abstractmethod
    def _discover_locked(self, context: DiscoverContext | None) -> list[DeviceInfo]:
        """Executa descoberta já sob ``_io_lock``."""

    @abstractmethod
    def _open_capture_for_device(self, device: DeviceInfo) -> cv2.VideoCapture:
        """Abre ``VideoCapture`` para o dispositivo selecionado."""

    def discover(self, *, context: DiscoverContext | None = None) -> list[DeviceInfo]:
        with self._io_lock:
            if self._connected:
                raise self._camera_error(self._connected_guard_message)
            return self._discover_locked(context)

    def select_device(self, index: int) -> None:
        if not 0 <= index < len(self._devices):
            raise self._camera_error("Índice de dispositivo inválido.")
        self._selected_index = index

    def connect(self) -> None:
        with self._io_lock:
            self._connect_locked()

    def _connect_locked(self) -> None:
        if self._selected_index is None or not 0 <= self._selected_index < len(
            self._devices
        ):
            raise self._camera_error("Nenhum dispositivo selecionado para conexão.")

        device = self._devices[self._selected_index]
        capture = self._open_capture_for_device(device)
        self._capture = capture
        self._connected = True
        self._frame_id = 0

    def disconnect(self) -> None:
        with self._io_lock:
            if self._capture is not None:
                self._capture.release()
                self._capture = None
            self._connected = False
            _logger.info("%s desconectado.", self.__class__.__name__)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def grab(self, *, single: bool = False) -> tuple[np.ndarray, dict[str, Any]]:
        del single
        with self._io_lock:
            return self._grab_locked()

    def _grab_locked(self) -> tuple[np.ndarray, dict[str, Any]]:
        if self._capture is None or not self._connected:
            raise self._camera_error("Câmera não conectada.")

        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise self._camera_error("Falha ao ler frame.")

        self._frame_id += 1
        return frame_to_rgb8(frame, frame_id=self._frame_id)
