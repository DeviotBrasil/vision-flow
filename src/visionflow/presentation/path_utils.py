"""Utilitários de caminho para a camada de apresentação."""

from __future__ import annotations

from pathlib import Path


def normalize_media_path(file_path: str) -> str:
    """Normaliza um caminho de mídia para chave estável (cache/miniaturas)."""
    try:
        return str(Path(file_path).resolve())
    except OSError:
        return file_path
