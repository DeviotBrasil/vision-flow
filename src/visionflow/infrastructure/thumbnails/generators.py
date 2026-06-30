"""Geração de frames RGB8 para miniaturas (OpenCV; seguro em worker threads)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from visionflow.infrastructure.video.video_metadata import read_thumbnail_frame

_JPEG_QUALITY = 80
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
_VIDEO_SUFFIXES = {".mp4", ".avi", ".mkv", ".mov", ".wmv"}


def is_image_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in _IMAGE_SUFFIXES


def is_video_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in _VIDEO_SUFFIXES


def _resize_rgb_frame(
    frame: np.ndarray,
    *,
    max_width: int,
    max_height: int,
) -> np.ndarray:
    height, width = frame.shape[:2]
    if width <= max_width and height <= max_height:
        return frame
    scale = min(max_width / width, max_height / height)
    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)


def _bgr_to_rgb(frame: np.ndarray) -> np.ndarray:
    if frame.ndim == 2:
        return frame
    if frame.shape[2] == 4:
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def generate_image_thumbnail(
    source_path: str,
    *,
    max_width: int,
    max_height: int,
) -> np.ndarray | None:
    """Lê imagem do disco e devolve RGB8 redimensionado para miniatura."""
    path = Path(source_path)
    if not path.is_file():
        return None
    frame = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if frame is None:
        return None
    rgb = _bgr_to_rgb(frame)
    return _resize_rgb_frame(rgb, max_width=max_width, max_height=max_height)


def generate_video_thumbnail(
    source_path: str,
    *,
    max_width: int,
    max_height: int,
) -> np.ndarray | None:
    """Extrai frame representativo do vídeo e redimensiona para miniatura."""
    frame = read_thumbnail_frame(source_path)
    if frame is None:
        return None
    return _resize_rgb_frame(frame, max_width=max_width, max_height=max_height)


def write_rgb_jpeg(path: Path, frame: np.ndarray) -> bool:
    """Grava frame RGB8 como JPEG (converte para BGR internamente)."""
    bgr = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    path.parent.mkdir(parents=True, exist_ok=True)
    return bool(
        cv2.imwrite(
            str(path),
            bgr,
            [int(cv2.IMWRITE_JPEG_QUALITY), _JPEG_QUALITY],
        )
    )


def read_rgb_jpeg(path: Path) -> np.ndarray | None:
    """Lê JPEG do cache e devolve RGB8."""
    frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if frame is None:
        return None
    return _bgr_to_rgb(frame)
