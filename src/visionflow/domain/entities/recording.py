"""Entidade de gravação de vídeo (arquivo MP4 + metadados)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Recording:
    """Uma gravação persistida: arquivo de vídeo + metadados.

    ``id`` e ``recorded_at`` são preenchidos pela persistência; ao registrar uma
    gravação nova (ainda não cadastrada), ``id`` é ``None``.
    """

    file_path: str
    id: int | None = None
    recorded_at: str | None = None
    duration_ms: int | None = None
    width: int | None = None
    height: int | None = None
    file_size_bytes: int | None = None
