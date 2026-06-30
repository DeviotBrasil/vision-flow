"""Miniatura clicável de uma gravação para a faixa da Principal."""

from __future__ import annotations

from visionflow.domain.entities.recording import Recording
from visionflow.presentation.widgets.strip_thumbnail_frame import (
    STRIP_THUMB_HEIGHT,
    STRIP_THUMB_WIDTH,
    StripThumbnailFrame,
)


class RecordingThumbnail(StripThumbnailFrame):
    """Miniatura clicável de uma gravação (frame carregado de forma assíncrona)."""

    def __init__(
        self,
        recording: Recording,
        *,
        width: int = STRIP_THUMB_WIDTH,
        height: int = STRIP_THUMB_HEIGHT,
        parent=None,
    ) -> None:
        recording_id = int(recording.id or 0)
        badge_text = f"#{recording_id:03d}" if recording_id > 0 else None
        super().__init__(
            object_name_prefix="recording_thumb",
            item_id=recording_id,
            size=(width, height),
            badge_text=badge_text,
            parent=parent,
        )

    def set_thumbnail(self, frame: object) -> None:
        """Aplica miniatura RGB8 carregada de forma assíncrona."""
        self.set_image_frame(frame)
