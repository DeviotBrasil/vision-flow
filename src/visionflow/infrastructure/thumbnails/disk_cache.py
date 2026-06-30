"""Cache lazy de miniaturas em disco com invalidação por mtime."""

from __future__ import annotations

import hashlib
import logging
import threading
from collections.abc import Callable
from pathlib import Path

import numpy as np

from visionflow.domain.contracts.thumbnail_cache import (
    ThumbnailCache,
    ThumbnailReader,
)
from visionflow.domain.gallery_defaults import (
    THUMBNAIL_MAX_HEIGHT,
    THUMBNAIL_MAX_WIDTH,
)
from visionflow.infrastructure.thumbnails.generators import (
    generate_image_thumbnail,
    generate_video_thumbnail,
    is_image_path,
    is_video_path,
    read_rgb_jpeg,
    write_rgb_jpeg,
)

_logger = logging.getLogger(__name__)


def _normalize_source_path(source_path: str) -> str:
    try:
        return str(Path(source_path).resolve())
    except OSError:
        return source_path


def _digest(source_path: str) -> str:
    return hashlib.sha256(_normalize_source_path(source_path).encode()).hexdigest()


class DiskThumbnailCache(ThumbnailCache):
    """Persiste miniaturas JPEG sob demanda em ``thumbs_dir``."""

    def __init__(self, thumbs_dir: Path) -> None:
        self._thumbs_dir = Path(thumbs_dir)
        self._thumbs_dir.mkdir(parents=True, exist_ok=True)
        self._cache_lock = threading.RLock()

    def as_reader(self) -> ThumbnailReader:
        """Devolve callable compatível com ``MediaThumbnailLoader``."""
        return self.read_thumbnail

    def thumb_path_for(self, source_path: str) -> Path:
        return self._thumbs_dir / f"{_digest(source_path)}.jpg"

    def meta_path_for(self, source_path: str) -> Path:
        return self._thumbs_dir / f"{_digest(source_path)}.meta"

    def remove(self, source_path: str) -> None:
        with self._cache_lock:
            for path in (
                self.thumb_path_for(source_path),
                self.meta_path_for(source_path),
            ):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    _logger.exception("Falha ao remover miniatura em cache: %s.", path)

    def get_or_create(
        self,
        source_path: str,
        generator: Callable[[str], np.ndarray | None],
    ) -> Path | None:
        source = Path(source_path)
        if not source.is_file():
            return None

        digest = _digest(source_path)
        with self._cache_lock:
            mtime_ns = source.stat().st_mtime_ns
            thumb_path = self._thumbs_dir / f"{digest}.jpg"
            meta_path = self._thumbs_dir / f"{digest}.meta"

            if self._is_valid(thumb_path, meta_path, mtime_ns):
                return thumb_path

            self._clear_cached_files(thumb_path, meta_path)
            frame = self._generate_frame(source_path, generator)
            if frame is None:
                return None
            return self._persist_frame(thumb_path, meta_path, frame, mtime_ns)

    @staticmethod
    def _clear_cached_files(thumb_path: Path, meta_path: Path) -> None:
        thumb_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)

    def _generate_frame(
        self,
        source_path: str,
        generator: Callable[[str], np.ndarray | None],
    ) -> np.ndarray | None:
        try:
            return generator(source_path)
        except Exception:
            _logger.exception("Falha ao gerar miniatura de %s.", source_path)
            return None

    def _persist_frame(
        self,
        thumb_path: Path,
        meta_path: Path,
        frame: np.ndarray,
        mtime_ns: int,
    ) -> Path | None:
        if not write_rgb_jpeg(thumb_path, frame):
            _logger.error("Falha ao gravar miniatura em cache: %s.", thumb_path)
            return None
        try:
            meta_path.write_text(str(mtime_ns), encoding="ascii")
        except OSError:
            _logger.exception("Falha ao gravar metadados de miniatura: %s.", meta_path)
            thumb_path.unlink(missing_ok=True)
            return None
        return thumb_path

    def read_thumbnail(self, source_path: str) -> np.ndarray | None:
        """Obtém RGB8 da miniatura cacheada ou gera sob demanda."""
        generator = self._generator_for(source_path)
        if generator is None:
            return None
        thumb_path = self.get_or_create(source_path, generator)
        if thumb_path is None:
            return None
        return read_rgb_jpeg(thumb_path)

    def _generator_for(
        self, source_path: str
    ) -> Callable[[str], np.ndarray | None] | None:
        if is_image_path(source_path):
            return lambda path: generate_image_thumbnail(
                path,
                max_width=THUMBNAIL_MAX_WIDTH,
                max_height=THUMBNAIL_MAX_HEIGHT,
            )
        if is_video_path(source_path):
            return lambda path: generate_video_thumbnail(
                path,
                max_width=THUMBNAIL_MAX_WIDTH,
                max_height=THUMBNAIL_MAX_HEIGHT,
            )
        return None

    @staticmethod
    def _is_valid(thumb_path: Path, meta_path: Path, mtime_ns: int) -> bool:
        if not thumb_path.is_file() or not meta_path.is_file():
            return False
        try:
            cached_mtime = int(meta_path.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            return False
        return cached_mtime == mtime_ns
