"""Conversão de payloads Qt/UI em contexto de descoberta de câmera."""

from __future__ import annotations

from visionflow.domain.entities.discover_context import DiscoverContext


def parse_discover_context(payload: object) -> DiscoverContext | None:
    """Converte payload Qt/UI em :class:`DiscoverContext`, se reconhecido."""
    if payload is None:
        return None
    if isinstance(payload, DiscoverContext):
        return payload
    if isinstance(payload, dict):
        raw_path = payload.get("video_path")
        if raw_path is None:
            return DiscoverContext()
        return DiscoverContext(video_path=str(raw_path))
    return None
