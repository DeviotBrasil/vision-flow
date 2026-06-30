"""Casos de uso de exportação de gravações (ZIP)."""

from __future__ import annotations

import logging
import zipfile
from collections.abc import Callable
from pathlib import Path

from visionflow.domain.entities.recording import Recording

_logger = logging.getLogger(__name__)


class RecordingExportService:
    """Exportação de gravações para arquivo ZIP."""

    @staticmethod
    def zip_arcname(recording: Recording, *, index: int = 0) -> str:
        """Nome da entrada no ZIP (único por índice para evitar sobrescrita)."""
        path = Path(recording.file_path or "")
        file_name = path.name or "gravacao.mp4"
        if index > 0:
            stem = path.stem or "gravacao"
            suffix = path.suffix or ".mp4"
            return f"{stem}_{index:03d}{suffix}"
        return file_name

    @staticmethod
    def write_zip(
        entries: list[Recording],
        target_path: str,
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> tuple[int, int]:
        """Grava gravações em um arquivo ZIP.

        Returns:
            Tupla ``(adicionadas, ignoradas)``; ignoradas = arquivo ausente no disco.
        """
        added = 0
        skipped = 0
        total = len(entries)
        used_names: set[str] = set()
        with zipfile.ZipFile(
            target_path, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for entry_index, recording in enumerate(entries):
                source = recording.file_path or ""
                path = Path(source)
                if not path.is_file():
                    skipped += 1
                    _logger.warning("Arquivo de gravação ausente no disco: %s", source)
                else:
                    suffix_index = entry_index
                    arcname = RecordingExportService.zip_arcname(
                        recording, index=suffix_index
                    )
                    while arcname in used_names:
                        suffix_index += 1
                        arcname = RecordingExportService.zip_arcname(
                            recording, index=suffix_index
                        )
                    used_names.add(arcname)
                    archive.write(path, arcname=arcname)
                    added += 1
                if on_progress is not None:
                    on_progress(entry_index + 1, total)
        return added, skipped
