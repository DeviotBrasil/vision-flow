"""Entidade de captura (imagem registrada com seus metadados)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Capture:
    """Uma captura persistida: arquivo de imagem + metadados do frame.

    ``id`` e ``captured_at`` são preenchidos pela persistência; ao criar uma
    captura nova (ainda não registrada), ``id`` é ``None``.
    """

    file_path: str
    id: int | None = None
    frame_id: int | None = None
    width: int | None = None
    height: int | None = None
    pixel_format: str | None = None
    captured_at: str | None = None
