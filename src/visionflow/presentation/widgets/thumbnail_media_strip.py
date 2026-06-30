"""Faixa horizontal com miniaturas assíncronas (Capturas e Gravações)."""

from __future__ import annotations

from abc import abstractmethod

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from visionflow.presentation.media_thumbnail_loader import MediaThumbnailLoader
from visionflow.presentation.path_utils import normalize_media_path
from visionflow.presentation.widgets.horizontal_strip_body import (
    HorizontalStripBody,
)
from visionflow.presentation.widgets.strip_thumbnail_frame import (
    STRIP_THUMB_HEIGHT,
    STRIP_THUMB_WIDTH,
    StripThumbnailFrame,
)


class ThumbnailMediaStrip[T](QWidget):
    """Base rolável com cache em memória e loader compartilhado."""

    item_clicked = Signal(int)

    def __init__(
        self,
        *,
        strip_id: str,
        empty_text: str,
        thumbnail_loader: MediaThumbnailLoader,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._thumbnail_loader = thumbnail_loader
        self._thumbnail_loader.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._thumbs_by_path: dict[str, StripThumbnailFrame] = {}
        self._thumbnail_cache: dict[str, object] = {}
        self._paths_pending: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._body = HorizontalStripBody(
            strip_id=strip_id,
            empty_text=empty_text,
        )
        layout.addWidget(self._body)

    def load_thumbnails(self) -> None:
        """Enfileira leitura de miniaturas pendentes (sob demanda)."""
        if not self._paths_pending:
            return
        paths = list(self._paths_pending)
        self._paths_pending.clear()
        self._thumbnail_loader.load(paths)

    def set_items(
        self,
        items: list[T],
        *,
        load_thumbnails: bool = False,
    ) -> None:
        """Recria as miniaturas; carrega frames só se ``load_thumbnails`` for True."""
        self._body.clear_row()
        self._thumbs_by_path.clear()
        self._paths_pending.clear()

        active_keys = {self._media_path(item) for item in items}
        self._thumbnail_cache = {
            key: frame
            for key, frame in self._thumbnail_cache.items()
            if key in active_keys
        }

        paths_to_load: list[str] = []
        for item in items:
            thumb = self._create_thumb(item)
            thumb.clicked.connect(self.item_clicked)
            self._body.add_widget(thumb)
            key = self._media_path(item)
            self._thumbs_by_path[key] = thumb
            cached = self._thumbnail_cache.get(key)
            if cached is not None:
                thumb.set_thumbnail(cached)
            elif key:
                paths_to_load.append(key)

        self._paths_pending = paths_to_load
        if load_thumbnails:
            self.load_thumbnails()

        self._body.set_populated(bool(items))

    def _on_thumbnail_ready(self, file_path: str, frame: object) -> None:
        key = normalize_media_path(file_path)
        self._thumbnail_cache[key] = frame
        thumb = self._thumbs_by_path.get(key)
        if thumb is not None:
            thumb.set_thumbnail(frame)

    @abstractmethod
    def _media_path(self, item: T) -> str:
        raise NotImplementedError

    @abstractmethod
    def _create_thumb(self, item: T) -> StripThumbnailFrame:
        raise NotImplementedError


DEFAULT_STRIP_THUMB_WIDTH = STRIP_THUMB_WIDTH
DEFAULT_STRIP_THUMB_HEIGHT = STRIP_THUMB_HEIGHT
