"""Grade responsiva de cards de gravação."""

from __future__ import annotations

from visionflow.domain.entities.recording import Recording
from visionflow.presentation.path_utils import normalize_media_path
from visionflow.presentation.widgets.gallery_recording_card import (
    GalleryRecordingCard,
)
from visionflow.presentation.widgets.responsive_gallery_grid import (
    GalleryGridChrome,
)
from visionflow.presentation.widgets.thumbnail_gallery_grid import (
    ThumbnailGalleryGrid,
)


class RecordingGalleryGrid(ThumbnailGalleryGrid[Recording]):
    """Scroll com grade de thumbnails ou estado vazio."""

    def __init__(self, thumbnail_loader, parent=None) -> None:
        super().__init__(
            GalleryGridChrome(
                body_object_name="recordings_body",
                scroll_object_name="recordings_scroll",
                grid_container_object_name="recordings_grid_container",
                empty_object_name="recordings_empty",
                empty_text="Nenhuma gravação no período selecionado.",
            ),
            thumbnail_loader,
            parent=parent,
        )

    def set_recordings(
        self,
        recordings: list[Recording],
        *,
        on_card_clicked,
        columns: int | None = None,
    ) -> None:
        self.set_items(recordings, on_card_clicked=on_card_clicked, columns=columns)

    def _media_path(self, item: Recording) -> str:
        return normalize_media_path(item.file_path or "")

    def _item_id(self, item: Recording) -> int:
        return int(item.id or 0)

    def _create_card(self, item: Recording) -> GalleryRecordingCard:
        return GalleryRecordingCard(item)

    def _wire_card(self, card: GalleryRecordingCard, item: Recording) -> None:
        if self._on_card_clicked is not None:
            card.clicked.connect(self._on_card_clicked)
        if item.id is not None:
            card.selection_toggled.connect(self._emit_selection_toggle)
