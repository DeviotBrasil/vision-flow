"""Telas da aplicação."""

from PySide6.QtWidgets import QWidget

from visionflow.presentation.screens.camera_screen import CameraScreen
from visionflow.presentation.screens.captures_screen import CapturesScreen
from visionflow.presentation.screens.datasets_screen import DatasetsScreen
from visionflow.presentation.screens.logs_screen import LogsScreen
from visionflow.presentation.screens.main_screen import MainScreen
from visionflow.presentation.screens.recordings_screen import RecordingsScreen

SCREENS: tuple[type[QWidget], ...] = (
    MainScreen,
    CapturesScreen,
    RecordingsScreen,
    DatasetsScreen,
    CameraScreen,
    LogsScreen,
)

SCREEN_BY_ID: dict[str, type[QWidget]] = {screen.PAGE_ID: screen for screen in SCREENS}

__all__ = [
    "SCREENS",
    "SCREEN_BY_ID",
    "CameraScreen",
    "CapturesScreen",
    "DatasetsScreen",
    "LogsScreen",
    "MainScreen",
    "RecordingsScreen",
]
