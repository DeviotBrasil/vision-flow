"""Importação de imagens via OpenCV (seguro em worker threads)."""

from __future__ import annotations

from pathlib import Path

from visionflow.domain.contracts.image_file_importer import (
    ImageFileImporter,
    ImportedImage,
)
from visionflow.infrastructure.storage.jpeg_image_import import import_image_file


class CvImageFileImporter(ImageFileImporter):
    """Implementação :class:`ImageFileImporter` com ``cv2``."""

    def __init__(self, captures_dir: Path) -> None:
        self._captures_dir = Path(captures_dir)

    def import_file(self, source_path: str) -> ImportedImage:
        return import_image_file(source_path, self._captures_dir)
