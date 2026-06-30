"""Entidades de domínio do Vision Flow."""

from visionflow.domain.entities.camera_config import CameraConfig
from visionflow.domain.entities.capture import Capture
from visionflow.domain.entities.device_info import DeviceInfo
from visionflow.domain.entities.discover_context import DiscoverContext
from visionflow.domain.entities.filtered_page import FilteredPage
from visionflow.domain.entities.log_entry import LogEntry

__all__ = [
    "CameraConfig",
    "Capture",
    "DeviceInfo",
    "DiscoverContext",
    "FilteredPage",
    "LogEntry",
]
