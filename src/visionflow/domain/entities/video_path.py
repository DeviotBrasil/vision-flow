"""Normalização de caminhos de arquivo de vídeo (domínio puro)."""

from __future__ import annotations

from pathlib import Path


def normalize_video_path(path: str) -> str:
    """Resolve ``path`` para caminho absoluto normalizado."""
    return str(Path(path).expanduser().resolve())
