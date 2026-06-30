"""Protocolo compartilhado dos cards com miniatura na galeria."""

from __future__ import annotations

from typing import Protocol


class GalleryThumbnailCard(Protocol):
    """Contrato usado por ``ThumbnailGalleryGrid`` para cards de captura/gravação."""

    def has_thumbnail(self) -> bool:
        """Indica se a miniatura já foi aplicada ao card."""
        ...

    def set_thumbnail(self, frame: object) -> None:
        """Aplica frame RGB8 (numpy) ou equivalente ao card."""
        ...

    def set_selected(self, selected: bool) -> None:
        """Atualiza estado visual de seleção."""
        ...
