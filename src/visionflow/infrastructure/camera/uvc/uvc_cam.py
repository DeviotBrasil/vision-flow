"""Adapter para webcams USB UVC via OpenCV (DirectShow no Windows)."""

from __future__ import annotations

import logging

import cv2

from visionflow.domain.contracts.camera import CameraError
from visionflow.domain.entities.device_info import DeviceInfo
from visionflow.domain.entities.discover_context import DiscoverContext
from visionflow.infrastructure.camera.opencv_base import OpenCvCameraBase
from visionflow.infrastructure.camera.uvc.dshow_devices import (
    DShowVideoDevice,
    list_video_input_devices,
)

_logger = logging.getLogger(__name__)

_MAX_PROBE_INDEX = 8


class UvcCameraError(CameraError):
    """Erro de operação com webcam USB UVC."""


class UvcCamera(OpenCvCameraBase):
    """Webcam USB UVC acessada via ``cv2.VideoCapture`` (DirectShow).

    Fluxo típico: :meth:`discover` → :meth:`select_device` → :meth:`connect`
    → repetidas chamadas a :meth:`grab` → :meth:`disconnect`.
    """

    _connected_guard_message = (
        "Não é possível buscar dispositivos com a câmera conectada. "
        "Desconecte antes de uma nova busca."
    )

    @property
    def _camera_error(self) -> type[CameraError]:
        return UvcCameraError

    def _discover_locked(self, context: DiscoverContext | None) -> list[DeviceInfo]:
        del context
        dshow_devices = list_video_input_devices()
        devices: list[DeviceInfo] = []
        for opencv_index in range(_MAX_PROBE_INDEX):
            if not self._probe_index(opencv_index):
                continue
            friendly_name, device_path = _resolve_uvc_device(
                opencv_index, dshow_devices
            )
            extra: dict[str, object] = {"opencv_index": opencv_index}
            if device_path:
                extra["device_path"] = device_path
            device = DeviceInfo(
                index=len(devices),
                name=friendly_name,
                model="Webcam UVC",
                serial="",
                ip="",
                mac="",
                interface="USB",
                tl_type="UVC",
                extra=extra,
            )
            devices.append(device)
        self._devices = devices
        _logger.info("Busca UVC concluída: %d webcam(s) encontrada(s).", len(devices))
        return list(devices)

    @staticmethod
    def _probe_index(opencv_index: int) -> bool:
        capture = cv2.VideoCapture(opencv_index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            return False
        try:
            ok, _frame = capture.read()
            return ok
        finally:
            capture.release()

    def _open_capture_for_device(self, device: DeviceInfo) -> cv2.VideoCapture:
        opencv_index = device.extra.get("opencv_index", device.index)
        _logger.info(
            "Conectando webcam UVC índice=%s nome=%s.",
            opencv_index,
            device.name,
        )
        capture = cv2.VideoCapture(int(opencv_index), cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            raise UvcCameraError(
                f"Não foi possível abrir a webcam no índice {opencv_index}."
            )
        ok, _frame = capture.read()
        if not ok:
            capture.release()
            raise UvcCameraError("Webcam aberta, mas não entregou frame de teste.")
        return capture


def _resolve_uvc_device(
    opencv_index: int,
    dshow_devices: list[DShowVideoDevice],
) -> tuple[str, str]:
    """Resolve nome e ``DevicePath`` pelo índice OpenCV (ordem DirectShow)."""
    if 0 <= opencv_index < len(dshow_devices):
        device = dshow_devices[opencv_index]
        return device.friendly_name, device.device_path
    return f"Webcam USB #{opencv_index}", ""
