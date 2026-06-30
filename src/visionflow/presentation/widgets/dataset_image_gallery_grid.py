"""Grade de imagens do dataset YOLO com legenda das classes anotadas."""

from __future__ import annotations

from visionflow.domain.entities.capture import Capture
from visionflow.presentation.widgets.capture_gallery_grid import CaptureGalleryGrid
from visionflow.presentation.widgets.gallery_capture_card import GalleryCaptureCard

_EMPTY_CAPTION = "Sem anotações"
_EMPTY_TEXT = "Nenhuma imagem no dataset. Use 'Adicionar imagens'."


class DatasetImageGalleryGrid(CaptureGalleryGrid):
    """Grade de capturas que exibe, abaixo do id, as classes anotadas."""

    def __init__(self, thumbnail_loader, parent=None) -> None:
        super().__init__(thumbnail_loader, parent=parent)
        self._captions: dict[int, str] = {}
        self._empty.setText(_EMPTY_TEXT)

    def set_captions(self, captions: dict[int, str]) -> None:
        """Define a legenda (última classe) por id de imagem para os cards."""
        self._captions = captions

    def _create_card(self, item: Capture) -> GalleryCaptureCard:
        caption = self._captions.get(int(item.id or 0), _EMPTY_CAPTION)
        return GalleryCaptureCard(item, subtitle=caption)
