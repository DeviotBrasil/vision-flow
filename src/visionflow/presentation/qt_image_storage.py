"""Implementação Qt do contrato :class:`ImageStorage` (grava JPEG via QImage).

Vive na presentation porque depende do Qt para converter/gravar a imagem.
O diretório de captura é injetado na construção (pela raiz de composição), de
modo que a presentation não precise importar caminhos da infraestrutura.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import numpy as np

from visionflow.domain.contracts.image_storage import ImageStorage
from visionflow.presentation.image_utils import ndarray_to_qimage

_logger = logging.getLogger(__name__)

_JPEG_QUALITY = 95


class QtImageStorage(ImageStorage):
    """Grava frames como JPEG em um diretório, usando ``QImage`` do Qt."""

    def __init__(self, captures_dir: Path) -> None:
        self._captures_dir = Path(captures_dir)

    def save(self, frame: np.ndarray) -> str:
        self._captures_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        file_path = self._captures_dir / f"{stamp}.jpg"
        image = ndarray_to_qimage(frame)
        if not image.save(str(file_path), "JPEG", _JPEG_QUALITY):
            raise OSError(f"Falha ao salvar imagem JPEG em {file_path}.")
        return str(file_path)

    def overwrite(self, file_path: str, frame: np.ndarray) -> None:
        path = Path(file_path)
        image = ndarray_to_qimage(frame)
        if not image.save(str(path), "JPEG", _JPEG_QUALITY):
            raise OSError(f"Falha ao sobrescrever imagem JPEG em {path}.")

    def delete(self, file_path: str) -> None:
        Path(file_path).unlink(missing_ok=True)
