"""Fábrica de adapters de câmera por backend."""

from __future__ import annotations

from collections.abc import Callable

from visionflow.domain.camera_backends import (
    BACKEND_OPT,
    BACKEND_UVC,
    BACKEND_VIDEO,
    get_backend_descriptor,
)
from visionflow.domain.contracts.camera import CameraError, CameraPort
from visionflow.infrastructure.camera.opt import OptCamera, sdk_available
from visionflow.infrastructure.camera.uvc import UvcCamera
from visionflow.infrastructure.camera.video import VideoCamera


class UnknownCameraBackendError(CameraError):
    """Backend de câmera não reconhecido."""


_CameraFactory = Callable[[], CameraPort]
_AvailabilityCheck = Callable[[], bool]

_BACKEND_FACTORIES: dict[str, tuple[_CameraFactory, _AvailabilityCheck]] = {
    BACKEND_UVC: (UvcCamera, lambda: True),
    BACKEND_OPT: (OptCamera, sdk_available),
    BACKEND_VIDEO: (VideoCamera, lambda: True),
}


def create_camera(backend: str) -> CameraPort:
    """Instancia o adapter correspondente ao ``backend`` solicitado."""
    if get_backend_descriptor(backend) is None:
        raise UnknownCameraBackendError(f"Backend de câmera desconhecido: {backend!r}")
    factory, _ = _BACKEND_FACTORIES[backend]
    return factory()


def backend_available(backend: str) -> bool:
    """Indica se o backend pode ser usado no ambiente atual."""
    if get_backend_descriptor(backend) is None:
        return False
    _, availability = _BACKEND_FACTORIES[backend]
    return availability()
