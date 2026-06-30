"""Contexto opcional para descoberta de dispositivos de câmera."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoverContext:
    """Parâmetros extras por backend na operação ``discover``.

    Atualmente usado pelo backend ``video`` (``video_path``); demais backends
    ignoram os campos.
    """

    video_path: str | None = None
