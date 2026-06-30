"""Conversão de frames OpenCV para RGB8 independente."""

from __future__ import annotations

from typing import Any

import numpy as np


def frame_to_rgb8(
    frame: np.ndarray, *, frame_id: int
) -> tuple[np.ndarray, dict[str, Any]]:
    """Converte frame BGR/mono do OpenCV em RGB8 com metadados de captura."""
    if frame.ndim == 2:
        rgb = np.stack([frame, frame, frame], axis=-1)
        channels = 1
        pixel_format = "Mono8"
    else:
        rgb = frame[:, :, ::-1].copy()
        channels = 3
        pixel_format = "RGB8"

    height, width = rgb.shape[:2]
    meta = {
        "frame_id": frame_id,
        "timestamp": None,
        "width": width,
        "height": height,
        "pixel_format": pixel_format,
        "channels": channels,
    }
    return rgb, meta
