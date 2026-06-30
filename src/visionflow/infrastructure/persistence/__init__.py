"""Persistência SQLite do Vision Flow (sem ORM, sem PySide6)."""

from visionflow.infrastructure.persistence.database import connect, initialize
from visionflow.infrastructure.persistence.repositories import (
    SqliteCameraConfigRepository,
    SqliteCaptureRepository,
    SqliteLogRepository,
    SqliteRecordingRepository,
    SqliteYoloRepository,
)

__all__ = [
    "SqliteCameraConfigRepository",
    "SqliteCaptureRepository",
    "SqliteLogRepository",
    "SqliteRecordingRepository",
    "SqliteYoloRepository",
    "connect",
    "initialize",
]
