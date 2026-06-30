"""Casos de uso de exportação de capturas (ZIP)."""

from __future__ import annotations

import logging
import zipfile
from collections.abc import Callable
from pathlib import Path

from visionflow.domain.entities.capture import Capture

_logger = logging.getLogger(__name__)


class CaptureExportService:
    """Exportação de capturas para arquivo ZIP."""

    @staticmethod
    def zip_arcname(capture: Capture) -> str:
        """Nome da entrada no ZIP (único por ``id`` para evitar sobrescrita)."""
        path = Path(capture.file_path or "")
        file_name = path.name or "captura.jpg"
        if capture.id is not None:
            return f"captura_{capture.id:06d}_{file_name}"
        return file_name

    @staticmethod
    def write_zip(
        entries: list[Capture],
        target_path: str,
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> tuple[int, int]:
        """Grava capturas em um arquivo ZIP.

        Returns:
            Tupla ``(adicionadas, ignoradas)``; ignoradas = arquivo ausente no disco.
        """
        added = 0
        skipped = 0
        total = len(entries)
        with zipfile.ZipFile(
            target_path, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for index, capture in enumerate(entries, start=1):
                source = capture.file_path or ""
                path = Path(source)
                if not path.is_file():
                    skipped += 1
                    _logger.warning("Arquivo de captura ausente no disco: %s", source)
                else:
                    archive.write(
                        path, arcname=CaptureExportService.zip_arcname(capture)
                    )
                    added += 1
                if on_progress is not None:
                    on_progress(index, total)
        return added, skipped
