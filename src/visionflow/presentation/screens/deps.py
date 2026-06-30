"""Tipos de dependências injetadas nas telas (composição em ``factory``)."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from visionflow.presentation.media_thumbnail_loader import MediaThumbnailLoader


class MainScreenDeps(NamedTuple):
    """Dependências extras da tela Principal."""

    data_dirs: tuple[Path, Path]
    thumbnail_loader: MediaThumbnailLoader
