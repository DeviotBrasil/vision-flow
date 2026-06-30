"""Serviço de gravações: listagem, registro, detalhe e exclusão."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path

from visionflow.domain.bulk_operations import delete_many_by_id
from visionflow.domain.contracts.recording_repository import (
    RecordingRepository,
)
from visionflow.domain.contracts.thumbnail_cache import ThumbnailCache
from visionflow.domain.entities.filtered_page import FilteredPage
from visionflow.domain.entities.recording import Recording
from visionflow.domain.file_import_result import FileImportResult
from visionflow.domain.gallery_defaults import GALLERY_PAGE_SIZE
from visionflow.domain.use_cases.recording_export import RecordingExportService

_logger = logging.getLogger(__name__)

FilteredRecordings = FilteredPage[Recording]


class RecordingService:
    """Casos de uso de gravações (como :class:`CaptureService`)."""

    def __init__(
        self,
        repository: RecordingRepository,
        thumbnail_cache: ThumbnailCache | None = None,
    ) -> None:
        self._repository = repository
        self._thumbnail_cache = thumbnail_cache

    def register(self, file_path: str) -> int | None:
        """Registra no banco um vídeo recém-gravado (ou devolve id existente)."""
        return self._repository.register_file(file_path)

    def recent_today(self, limit: int) -> list[Recording]:
        """Lista as gravações mais recentes do dia corrente."""
        today = date.today()
        return self._repository.list_filtered(
            start_date=today,
            end_date=today,
            limit=limit,
        )

    def count_filtered(
        self,
        start_date: date | None,
        end_date: date | None,
    ) -> int:
        """Total de gravações no intervalo de datas informado."""
        return self._repository.count_filtered(
            start_date=start_date,
            end_date=end_date,
        )

    def list_filtered_ids(
        self,
        start_date: date | None,
        end_date: date | None,
    ) -> list[int]:
        """Lista os ``id`` de todas as gravações no intervalo (sem paginação)."""
        return self._repository.list_filtered_ids(
            start_date=start_date,
            end_date=end_date,
        )

    def list_filtered_page(
        self,
        start_date: date | None,
        end_date: date | None,
        page: int,
        page_size: int = GALLERY_PAGE_SIZE,
    ) -> FilteredRecordings:
        """Lista uma página filtrada e o total em uma única consulta."""
        page = max(page, 1)
        offset = (page - 1) * page_size
        return self._repository.list_filtered_page(
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset,
        )

    def list_page(
        self,
        start_date: date | None,
        end_date: date | None,
        page: int,
        page_size: int = GALLERY_PAGE_SIZE,
    ) -> list[Recording]:
        """Lista uma página de gravações filtradas por intervalo de datas."""
        return self.list_filtered_page(start_date, end_date, page, page_size).entries

    def list_by_ids(self, ids: Iterable[int]) -> FilteredRecordings:
        """Lista gravações pelos ``id`` informados (ordem decrescente por ``id``)."""
        id_list = list(ids)
        entries = self._repository.list_by_ids(id_list)
        return FilteredRecordings(entries=entries, total=len(entries))

    @staticmethod
    def write_zip(
        entries: list[Recording],
        target_path: str,
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> tuple[int, int]:
        """Grava gravações em um arquivo ZIP."""
        return RecordingExportService.write_zip(
            entries, target_path, on_progress=on_progress
        )

    def count(self) -> int:
        """Total de gravações registradas."""
        return self._repository.count()

    def get(self, recording_id: int) -> Recording | None:
        """Detalhe de uma gravação pelo ``id``."""
        return self._repository.get(recording_id)

    def delete(self, recording_id: int) -> bool:
        """Remove o arquivo e depois o registro da gravação."""
        recording = self._repository.get(recording_id)
        if recording is None or not recording.file_path:
            return False
        file_path = recording.file_path
        try:
            Path(file_path).unlink(missing_ok=True)
        except OSError:
            _logger.exception("Falha ao remover arquivo de gravação em %s.", file_path)
            return False
        if self._repository.delete(recording_id) is None:
            return False
        if self._thumbnail_cache is not None:
            self._thumbnail_cache.remove(file_path)
        _logger.info("Gravação removida: %s", file_path)
        return True

    def delete_many(self, ids: Iterable[int]) -> tuple[int, list[int]]:
        """Remove várias gravações; retorna contagem de sucesso e ids com falha."""
        return delete_many_by_id(self.delete, ids)

    def import_from_files(self, paths: Iterable[str]) -> FileImportResult:
        """Importa arquivos MP4 externos para o repositório local."""
        added = 0
        failed: list[str] = []
        for raw_path in paths:
            recording_id = self._repository.import_external_file(raw_path)
            if recording_id is None:
                failed.append(raw_path)
                continue
            _logger.info("Gravação importada de %s (id=%s).", raw_path, recording_id)
            added += 1
        return FileImportResult(added=added, failed=failed)
