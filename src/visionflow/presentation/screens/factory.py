"""Fábricas de telas com dependências injetadas na raiz de composição."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from PySide6.QtWidgets import QWidget

from visionflow.domain.use_cases.camera_config import CameraConfigService
from visionflow.domain.use_cases.captures import CaptureService
from visionflow.domain.use_cases.logs import LogService
from visionflow.domain.use_cases.recordings import RecordingService
from visionflow.domain.use_cases.yolo_dataset import YoloDatasetService
from visionflow.presentation.camera_controller import CameraController
from visionflow.presentation.media_thumbnail_loader import MediaThumbnailLoader
from visionflow.presentation.screens.camera_screen import CameraScreen
from visionflow.presentation.screens.captures_screen import CapturesScreen
from visionflow.presentation.screens.datasets_screen import DatasetsScreen
from visionflow.presentation.screens.deps import MainScreenDeps
from visionflow.presentation.screens.logs_screen import LogsScreen
from visionflow.presentation.screens.main_screen import MainScreen
from visionflow.presentation.screens.recordings_screen import RecordingsScreen

ScreenFactory = Callable[[], QWidget]


class DataDirs(NamedTuple):
    """Diretórios de dados injetados na composição da UI."""

    captures: Path
    recordings: Path


class ScreenServices(NamedTuple):
    """Serviços de domínio injetados nas telas."""

    captures: CaptureService
    recordings: RecordingService
    config: CameraConfigService
    logs: LogService
    yolo: YoloDatasetService


# Telas que exigem fábrica dedicada (dependências além do construtor padrão).
FACTORY_SCREEN_IDS: frozenset[str] = frozenset(
    {"principal", "captures", "recordings", "datasets", "camera", "logs"}
)


def build_screen_factories(
    controller: CameraController,
    services: ScreenServices,
    data_dirs: DataDirs,
    *,
    thumbnail_loader: MediaThumbnailLoader,
) -> dict[str, ScreenFactory]:
    """Monta o mapa page_id → factory para telas com injeção de dependências."""
    return {
        "principal": lambda: MainScreen(
            controller,
            services.captures,
            services.recordings,
            MainScreenDeps(
                data_dirs=(data_dirs.captures, data_dirs.recordings),
                thumbnail_loader=thumbnail_loader,
            ),
        ),
        "captures": lambda: CapturesScreen(
            services.captures,
            thumbnail_loader,
        ),
        "recordings": lambda: RecordingsScreen(
            services.recordings,
            thumbnail_loader,
        ),
        "datasets": lambda: DatasetsScreen(
            services.yolo,
            services.captures,
            thumbnail_loader,
        ),
        "camera": lambda: CameraScreen(controller, services.config),
        "logs": lambda: LogsScreen(services.logs),
    }
