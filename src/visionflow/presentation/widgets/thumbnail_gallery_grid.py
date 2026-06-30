"""Grade responsiva com miniaturas assíncronas (Capturas e Gravações)."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget

from visionflow.presentation.media_thumbnail_loader import MediaThumbnailLoader
from visionflow.presentation.path_utils import normalize_media_path
from visionflow.presentation.widgets.gallery_thumbnail_card import (
    GalleryThumbnailCard,
)
from visionflow.presentation.widgets.responsive_gallery_grid import (
    GalleryGridChrome,
    ResponsiveGalleryGrid,
)


class ThumbnailGalleryGrid[T](ResponsiveGalleryGrid):
    """Base com cache em memória, retry e loader compartilhado."""

    def __init__(
        self,
        chrome: GalleryGridChrome,
        thumbnail_loader: MediaThumbnailLoader,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(chrome, parent=parent)
        self._thumbnail_loader = thumbnail_loader
        self._current_items: list[T] = []
        self._on_card_clicked: Callable[[int], None] | None = None
        self._cards_by_path: dict[str, GalleryThumbnailCard] = {}
        self._thumbnail_cache: dict[str, object] = {}
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.setInterval(400)
        self._retry_timer.timeout.connect(self._retry_missing_thumbnails)
        thumbnail_loader.thumbnail_ready.connect(self._on_thumbnail_ready)

    def apply_selection(self, selected_ids: set[int]) -> None:
        for item in self._current_items:
            item_id = self._item_id(item)
            key = self._media_path(item)
            card = self._cards_by_path.get(key)
            if card is not None and item_id > 0:
                card.set_selected(item_id in selected_ids)

    def set_items(
        self,
        items: list[T],
        *,
        on_card_clicked: Callable[[int], None],
        columns: int | None = None,
    ) -> None:
        self._current_items = items
        self._on_card_clicked = on_card_clicked
        self._populate(items, columns=columns)

    def _has_items(self) -> bool:
        return bool(self._current_items)

    def _iter_card_widgets(self):
        for index, item in enumerate(self._current_items):
            key = self._media_path(item)
            card = self._cards_by_path.get(key)
            if card is not None:
                yield index, card

    def _on_thumbnail_ready(self, file_path: str, frame: object) -> None:
        key = normalize_media_path(file_path)
        self._thumbnail_cache[key] = frame
        card = self._cards_by_path.get(key)
        if card is not None:
            card.set_thumbnail(frame)

    def _populate(
        self,
        items: list[T],
        *,
        columns: int | None = None,
    ) -> None:
        self._retry_timer.stop()
        self._clear_grid()
        self._cards_by_path.clear()
        active_keys = {self._media_path(item) for item in items}
        self._thumbnail_cache = {
            key: frame
            for key, frame in self._thumbnail_cache.items()
            if key in active_keys
        }

        if not items:
            self._show_empty()
            return

        grid_columns = self._show_grid(columns=columns)
        paths_to_load: list[str] = []

        for index, item in enumerate(items):
            row = index // grid_columns
            col = index % grid_columns
            card = self._create_card(item)
            key = self._media_path(item)
            self._cards_by_path[key] = card

            cached = self._thumbnail_cache.get(key)
            if cached is not None:
                card.set_thumbnail(cached)
            elif key:
                paths_to_load.append(key)

            self._wire_card(card, item)
            self._grid.addWidget(card, row, col)

        if paths_to_load:
            self._thumbnail_loader.load(paths_to_load)
        self._schedule_thumbnail_retry()

    def _schedule_thumbnail_retry(self) -> None:
        self._retry_timer.start()

    def _retry_missing_thumbnails(self) -> None:
        missing = [
            path
            for path, card in self._cards_by_path.items()
            if not card.has_thumbnail()
        ]
        if missing:
            self._thumbnail_loader.load(missing)

    @abstractmethod
    def _media_path(self, item: T) -> str:
        raise NotImplementedError

    @abstractmethod
    def _item_id(self, item: T) -> int:
        raise NotImplementedError

    @abstractmethod
    def _create_card(self, item: T) -> GalleryThumbnailCard:
        raise NotImplementedError

    @abstractmethod
    def _wire_card(self, card: GalleryThumbnailCard, item: T) -> None:
        raise NotImplementedError
