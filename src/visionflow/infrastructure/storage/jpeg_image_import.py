"""Importação de arquivos de imagem para JPEG (OpenCV; seguro em worker threads)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2

from visionflow.domain.contracts.image_file_importer import ImportedImage

_JPEG_QUALITY = 95


def import_image_file(source_path: str, captures_dir: Path) -> ImportedImage:
    """Copia ou converte uma imagem para o diretório de capturas."""
    source = Path(source_path)
    if not source.is_file():
        raise OSError(f"Arquivo de imagem ausente: {source_path}.")

    frame = cv2.imread(str(source), cv2.IMREAD_UNCHANGED)
    if frame is None:
        raise OSError(f"Formato de imagem não suportado: {source_path}.")

    height, width = frame.shape[:2]
    resolved = source.resolve()
    captures_resolved = captures_dir.resolve()
    if resolved.parent == captures_resolved:
        return ImportedImage(str(resolved), width, height)

    captures_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest = captures_dir / f"{stamp}.jpg"
    while dest.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        dest = captures_dir / f"{stamp}.jpg"
    if not cv2.imwrite(
        str(dest),
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), _JPEG_QUALITY],
    ):
        raise OSError(f"Falha ao salvar imagem JPEG importada em {dest}.")
    return ImportedImage(str(dest.resolve()), width, height)
