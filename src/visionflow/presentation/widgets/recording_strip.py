"""Faixa horizontal de miniaturas das últimas gravações."""

from __future__ import annotations

from visionflow.domain.entities.recording import Recording
from visionflow.presentation.path_utils import normalize_media_path
from visionflow.presentation.widgets.recording_thumbnail import RecordingThumbnail
from visionflow.presentation.widgets.thumbnail_media_strip import (
    DEFAULT_STRIP_THUMB_HEIGHT,
    DEFAULT_STRIP_THUMB_WIDTH,
    ThumbnailMediaStrip,
)


class RecordingStrip(ThumbnailMediaStrip[Recording]):
    """Corpo rolável da faixa de gravações (sem cabeçalho; em ``MainRecentPanel``)."""

    def __init__(self, thumbnail_loader, parent=None) -> None:
        super().__init__(
            strip_id="recording_strip",
            empty_text="Nenhuma gravação hoje.",
            thumbnail_loader=thumbnail_loader,
            parent=parent,
        )

    def set_recordings(
        self,
        recordings: list[Recording],
        *,
        load_thumbnails: bool = False,
    ) -> None:
        self.set_items(recordings, load_thumbnails=load_thumbnails)

    def _media_path(self, item: Recording) -> str:
        return normalize_media_path(item.file_path or "")

    def _create_thumb(self, item: Recording) -> RecordingThumbnail:
        return RecordingThumbnail(
            item,
            width=DEFAULT_STRIP_THUMB_WIDTH,
            height=DEFAULT_STRIP_THUMB_HEIGHT,
        )
