"""Miniatura clicável de uma captura, com selo de identificação."""

from __future__ import annotations

from visionflow.domain.entities.capture import Capture
from visionflow.presentation.widgets.strip_thumbnail_frame import (
    STRIP_THUMB_HEIGHT,
    STRIP_THUMB_WIDTH,
    StripThumbnailFrame,
)


class CaptureThumbnail(StripThumbnailFrame):
    """Miniatura clicável de uma captura (frame carregado de forma assíncrona)."""

    def __init__(
        self,
        capture: Capture,
        *,
        width: int = STRIP_THUMB_WIDTH,
        height: int = STRIP_THUMB_HEIGHT,
        parent=None,
    ) -> None:
        capture_id = int(capture.id)
        super().__init__(
            object_name_prefix="capture_thumb",
            item_id=capture_id,
            size=(width, height),
            badge_text=f"#{capture_id:03d}",
            parent=parent,
        )

    def set_thumbnail(self, frame: object) -> None:
        """Aplica miniatura RGB8 carregada de forma assíncrona."""
        self.set_image_frame(frame)
