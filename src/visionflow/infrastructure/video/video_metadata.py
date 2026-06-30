"""Metadados de arquivos de vídeo (parse de nome, propriedades OpenCV)."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

_logger = logging.getLogger(__name__)

_RECORDING_NAME_RE = re.compile(
    r"^(?:gravacao_)?(\d{8})_(\d{6})\.mp4$",
    re.IGNORECASE,
)


def parse_recorded_at(path: str | Path) -> datetime | None:
    """Extrai data/hora do nome ``YYYYMMDD_HHMMSS.mp4`` (ou legado com prefixo)."""
    file_path = Path(path)
    match = _RECORDING_NAME_RE.match(file_path.name)
    if match:
        date_part, time_part = match.groups()
        try:
            return datetime.strptime(f"{date_part}{time_part}", "%Y%m%d%H%M%S")
        except ValueError:
            _logger.debug("Nome de gravação inválido: %s", file_path.name)
    try:
        stamp = file_path.stat().st_mtime
        return datetime.fromtimestamp(stamp)
    except OSError:
        return None


def recorded_at_iso(path: str | Path) -> str | None:
    """Devolve ``recorded_at`` em ISO local ou ``None``."""
    parsed = parse_recorded_at(path)
    if parsed is None:
        return None
    return parsed.isoformat(timespec="seconds")


def read_video_properties(
    path: str | Path,
) -> tuple[int | None, int | None, int | None]:
    """Lê duração (ms), largura e altura via ``cv2.VideoCapture``."""
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return None, None, None
    try:
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_ms: int | None = None
        if fps > 0 and frame_count > 0:
            duration_ms = int((frame_count / fps) * 1000)
        safe_width = width if width > 0 else None
        safe_height = height if height > 0 else None
        return duration_ms, safe_width, safe_height
    finally:
        capture.release()


def read_first_frame(path: str | Path) -> np.ndarray | None:
    """Lê o primeiro frame do vídeo em RGB8, ou ``None`` se indisponível."""
    return _read_frame_rgb(path, frame_index=0)


def read_thumbnail_frame(path: str | Path) -> np.ndarray | None:
    """Lê um frame representativo para miniatura (varre frames iniciais)."""
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return None
    try:
        best_frame: np.ndarray | None = None
        best_score = -1.0
        max_samples = 24
        for index in range(max_samples):
            ok, frame = capture.read()
            if not ok or frame is None:
                break
            score = float(frame.mean())
            if score > best_score:
                best_score = score
                best_frame = frame
            if index >= 2 and score >= 12.0:
                break
        if best_frame is None:
            return None
        return _bgr_to_rgb(best_frame)
    finally:
        capture.release()


def _read_frame_rgb(path: str | Path, *, frame_index: int) -> np.ndarray | None:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return None
    try:
        if frame_index > 0:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok or frame is None:
            return None
        return _bgr_to_rgb(frame)
    finally:
        capture.release()


def _bgr_to_rgb(frame: np.ndarray) -> np.ndarray:
    if frame.ndim == 2:
        return np.stack([frame, frame, frame], axis=-1)
    return frame[:, :, ::-1].copy()
