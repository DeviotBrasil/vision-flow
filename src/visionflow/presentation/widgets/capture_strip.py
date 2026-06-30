"""Faixa horizontal de miniaturas das últimas capturas."""

from __future__ import annotations

from visionflow.domain.entities.capture import Capture
from visionflow.presentation.path_utils import normalize_media_path
from visionflow.presentation.widgets.capture_thumbnail import CaptureThumbnail
from visionflow.presentation.widgets.thumbnail_media_strip import (
    DEFAULT_STRIP_THUMB_HEIGHT,
    DEFAULT_STRIP_THUMB_WIDTH,
    ThumbnailMediaStrip,
)

STRIP_PREVIEW_LIMIT = 10


class CaptureStrip(ThumbnailMediaStrip[Capture]):
    """Corpo rolável da faixa de capturas (sem cabeçalho; em ``MainRecentPanel``)."""

    def __init__(self, thumbnail_loader, parent=None) -> None:
        super().__init__(
            strip_id="capture_strip",
            empty_text="Nenhuma captura hoje.",
            thumbnail_loader=thumbnail_loader,
            parent=parent,
        )

    def set_captures(
        self,
        captures: list[Capture],
        *,
        load_thumbnails: bool = False,
    ) -> None:
        self.set_items(captures, load_thumbnails=load_thumbnails)

    def _media_path(self, item: Capture) -> str:
        return normalize_media_path(item.file_path or "")

    def _create_thumb(self, item: Capture) -> CaptureThumbnail:
        return CaptureThumbnail(
            item,
            width=DEFAULT_STRIP_THUMB_WIDTH,
            height=DEFAULT_STRIP_THUMB_HEIGHT,
        )
