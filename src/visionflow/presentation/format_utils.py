"""Formatação de texto compartilhada pela camada de UI."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_EMPTY = "—"
_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR = 3600


def format_time_ms(position_ms: int | float | None) -> str:
    """Formata milissegundos como ``mm:ss`` ou ``h:mm:ss``; vazio se inválido."""
    if not isinstance(position_ms, (int, float)) or position_ms < 0:
        return ""
    total_seconds = max(0, int(position_ms) // 1000)
    hours, remainder = divmod(total_seconds, _SECONDS_PER_HOUR)
    minutes, seconds = divmod(remainder, _SECONDS_PER_MINUTE)
    if hours > 0:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_video_resolution(width: Any, height: Any) -> str:
    """Formata ``largura×altura`` para metadados de vídeo; vazio se inválido."""
    if not isinstance(width, int) or not isinstance(height, int):
        return ""
    if width <= 0 or height <= 0:
        return ""
    return f"{width}×{height}"


def format_resolution(width: Any, height: Any) -> str:
    """Formata ``largura × altura``; devolve ``—`` se algum valor faltar."""
    if width and height:
        return f"{width} × {height}"
    return _EMPTY


def format_captured_short(value: str | None) -> str:
    """Formata ISO para exibição curta em cards (``dd/mm, HH:MM``)."""
    if not value:
        return _EMPTY
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%d/%m, %H:%M")
    except ValueError:
        return value


def format_file_size(size_bytes: int | None) -> str:
    """Formata tamanho de arquivo; ``—`` se inválido."""
    if size_bytes is None or size_bytes < 0:
        return _EMPTY
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_captured_at(value: str) -> str:
    """Formata ISO para exibição completa (``dd/mm/aaaa, HH:MM:SS``)."""
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%d/%m/%Y, %H:%M:%S")
    except ValueError:
        return value
