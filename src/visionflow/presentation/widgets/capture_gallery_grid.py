"""Grade responsiva de cards de captura."""

from __future__ import annotations

from visionflow.domain.entities.capture import Capture
from visionflow.presentation.path_utils import normalize_media_path
from visionflow.presentation.widgets.gallery_capture_card import GalleryCaptureCard
from visionflow.presentation.widgets.responsive_gallery_grid import (
    GalleryGridChrome,
)
from visionflow.presentation.widgets.thumbnail_gallery_grid import (
    ThumbnailGalleryGrid,
)


class CaptureGalleryGrid(ThumbnailGalleryGrid[Capture]):
    """Scroll com grade de thumbnails ou estado vazio."""

    def __init__(self, thumbnail_loader, parent=None) -> None:
        super().__init__(
            GalleryGridChrome(
                body_object_name="captures_body",
                scroll_object_name="captures_scroll",
                grid_container_object_name="captures_grid_container",
                empty_object_name="captures_empty",
                empty_text="Nenhuma captura no período selecionado.",
            ),
            thumbnail_loader,
            parent=parent,
        )

    def set_captures(
        self,
        captures: list[Capture],
        *,
        on_card_clicked,
        columns: int | None = None,
    ) -> None:
        self.set_items(captures, on_card_clicked=on_card_clicked, columns=columns)

    def _media_path(self, item: Capture) -> str:
        return normalize_media_path(item.file_path or "")

    def _item_id(self, item: Capture) -> int:
        return int(item.id or 0)

    def _create_card(self, item: Capture) -> GalleryCaptureCard:
        return GalleryCaptureCard(item)

    def _wire_card(self, card: GalleryCaptureCard, item: Capture) -> None:
        if self._on_card_clicked is not None:
            card.clicked.connect(self._on_card_clicked)
        card.selection_toggled.connect(self._emit_selection_toggle)
