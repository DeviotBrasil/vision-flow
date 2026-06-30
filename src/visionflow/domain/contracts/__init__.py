"""Contratos (ports) do domínio, implementados pela infraestrutura."""

from visionflow.domain.contracts.camera import (
    CameraError,
    CameraPort,
    IncompleteFrameError,
    TriggerCapableCamera,
    TriggerWaitError,
    camera_supports_trigger,
)
from visionflow.domain.contracts.camera_config_repository import (
    CameraConfigRepository,
)
from visionflow.domain.contracts.capture_repository import CaptureRepository
from visionflow.domain.contracts.image_storage import ImageStorage
from visionflow.domain.contracts.log_repository import LogRepository

__all__ = [
    "CameraConfigRepository",
    "CameraError",
    "CameraPort",
    "CaptureRepository",
    "ImageStorage",
    "IncompleteFrameError",
    "LogRepository",
    "TriggerCapableCamera",
    "TriggerWaitError",
    "camera_supports_trigger",
]
