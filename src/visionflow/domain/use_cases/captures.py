"""Serviço de capturas: orquestra armazenamento de imagem + registro no banco.

Depende apenas dos contratos :class:`CaptureRepository` e :class:`ImageStorage`;
não conhece SQL, Qt nem caminhos de arquivo.
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import date, datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any

import numpy as np

from visionflow.domain.bulk_operations import delete_many_by_id
from visionflow.domain.contracts.capture_repository import CaptureRepository
from visionflow.domain.contracts.image_file_importer import ImageFileImporter
from visionflow.domain.contracts.image_storage import ImageStorage
from visionflow.domain.contracts.thumbnail_cache import ThumbnailCache
from visionflow.domain.entities.capture import Capture
from visionflow.domain.entities.filtered_page import FilteredPage
from visionflow.domain.exceptions import PersistenceError
from visionflow.domain.file_import_result import FileImportResult
from visionflow.domain.gallery_defaults import GALLERY_PAGE_SIZE
from visionflow.domain.use_cases.capture_export import CaptureExportService

_logger = logging.getLogger(__name__)

EDITED_PIXEL_FORMAT = "JPEG"

FilteredCaptures = FilteredPage[Capture]


class _ImportOutcome(Enum):
    ADDED = auto()
    SKIPPED = auto()
    FAILED = auto()


class CaptureService:
    """Casos de uso de captura (salvar, listar, contar, detalhar e excluir)."""

    def __init__(
        self,
        repository: CaptureRepository,
        storage: ImageStorage,
        file_importer: ImageFileImporter,
        thumbnail_cache: ThumbnailCache | None = None,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._file_importer = file_importer
        self._thumbnail_cache = thumbnail_cache

    def save(self, frame: np.ndarray, meta: dict[str, Any]) -> Capture | None:
        """Grava o frame e registra a captura.

        Returns:
            A :class:`Capture` criada (com ``id``), ou ``None`` se a gravação
            do arquivo falhar.
        """
        try:
            file_path = self._storage.save(frame)
        except OSError:
            _logger.exception("Falha ao gravar imagem da captura.")
            return None
        meta = meta or {}
        capture = Capture(
            file_path=file_path,
            frame_id=meta.get("frame_id"),
            width=meta.get("width"),
            height=meta.get("height"),
            pixel_format=meta.get("pixel_format"),
        )
        try:
            capture_id = self._repository.add(capture)
        except PersistenceError:
            _logger.exception(
                "Falha ao registrar captura no banco; removendo arquivo %s.",
                file_path,
            )
            self._storage.delete(file_path)
            return None
        _logger.info("Captura salva em %s.", file_path)
        return replace(capture, id=capture_id)

    def recent(self, limit: int) -> list[Capture]:
        """Lista as capturas mais recentes."""
        return self._repository.list_recent(limit)

    def recent_today(self, limit: int) -> list[Capture]:
        """Lista as capturas mais recentes do dia corrente."""
        today = date.today()
        return self._repository.list_filtered(
            start_date=today,
            end_date=today,
            limit=limit,
        )

    def count_today(self) -> int:
        """Total de capturas registradas hoje."""
        today = date.today()
        return self._repository.count_filtered(start_date=today, end_date=today)

    def count_filtered(
        self,
        start_date: date | None,
        end_date: date | None,
    ) -> int:
        """Total de capturas no intervalo de datas informado."""
        return self._repository.count_filtered(
            start_date=start_date,
            end_date=end_date,
        )

    def list_filtered_ids(
        self,
        start_date: date | None,
        end_date: date | None,
    ) -> list[int]:
        """Lista os ``id`` de todas as capturas no intervalo (sem paginação)."""
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
    ) -> FilteredCaptures:
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
    ) -> list[Capture]:
        """Lista uma página de capturas filtradas por intervalo de datas."""
        return self.list_filtered_page(start_date, end_date, page, page_size).entries

    def list_by_ids(self, ids: Iterable[int]) -> FilteredCaptures:
        """Lista capturas pelos ``id`` informados (ordem decrescente por ``id``)."""
        id_list = list(ids)
        entries = self._repository.list_by_ids(id_list)
        return FilteredCaptures(entries=entries, total=len(entries))

    @staticmethod
    def zip_arcname(capture: Capture) -> str:
        """Nome da entrada no ZIP (único por ``id`` para evitar sobrescrita)."""
        return CaptureExportService.zip_arcname(capture)

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
        return CaptureExportService.write_zip(
            entries, target_path, on_progress=on_progress
        )

    def count(self) -> int:
        """Total de capturas registradas."""
        return self._repository.count()

    def get(self, capture_id: int) -> Capture | None:
        """Detalhe de uma captura pelo ``id``."""
        return self._repository.get(capture_id)

    def save_edited_from_source(
        self, source: Capture, frame: np.ndarray
    ) -> Capture | None:
        """Registra uma nova captura derivada de ``source`` com dimensões do frame."""
        height, width = frame.shape[:2]
        meta = {
            "frame_id": source.frame_id,
            "width": width,
            "height": height,
            "pixel_format": EDITED_PIXEL_FORMAT,
        }
        return self.save(frame, meta)

    def replace_image(self, capture_id: int, frame: np.ndarray) -> Capture | None:
        """Sobrescreve o arquivo JPEG e atualiza dimensões da captura existente.

        Preserva ``id``, ``captured_at``, ``frame_id`` e ``pixel_format``.
        """
        capture = self._repository.get(capture_id)
        if capture is None or not capture.file_path:
            return None
        file_path = capture.file_path
        path = Path(file_path)
        if not path.is_file():
            _logger.error("Arquivo de captura ausente: %s.", file_path)
            return None
        backup_path = path.with_suffix(path.suffix + ".bak")
        try:
            shutil.copy2(path, backup_path)
        except OSError:
            _logger.exception("Falha ao criar backup da captura em %s.", file_path)
            return None
        try:
            updated = self._overwrite_and_update_dimensions(
                capture,
                capture_id,
                frame,
                backup_path,
            )
        finally:
            backup_path.unlink(missing_ok=True)
        if updated is None:
            return None
        _logger.info("Captura id=%s atualizada em %s.", capture_id, file_path)
        return updated

    def _overwrite_and_update_dimensions(
        self,
        capture: Capture,
        capture_id: int,
        frame: np.ndarray,
        backup_path: Path,
    ) -> Capture | None:
        file_path = capture.file_path or ""
        path = Path(file_path)
        height, width = frame.shape[:2]
        try:
            self._storage.overwrite(file_path, frame)
        except OSError:
            _logger.exception(
                "Falha ao sobrescrever imagem da captura em %s.", file_path
            )
            return None
        try:
            if not self._repository.update_dimensions(
                capture_id,
                width=width,
                height=height,
            ):
                _logger.error(
                    "Falha ao atualizar dimensões da captura id=%s.",
                    capture_id,
                )
                shutil.copy2(backup_path, path)
                return None
        except PersistenceError:
            _logger.exception(
                "Falha ao atualizar dimensões da captura id=%s.", capture_id
            )
            shutil.copy2(backup_path, path)
            return None
        return replace(capture, width=width, height=height)

    def delete(self, capture_id: int) -> bool:
        """Remove o arquivo e depois o registro da captura."""
        capture = self._repository.get(capture_id)
        if capture is None or not capture.file_path:
            return False
        file_path = capture.file_path
        try:
            self._storage.delete(file_path)
        except OSError:
            _logger.exception("Falha ao remover arquivo de captura em %s.", file_path)
            return False
        if self._repository.delete(capture_id) is None:
            return False
        if self._thumbnail_cache is not None:
            self._thumbnail_cache.remove(file_path)
        _logger.info("Captura removida: %s", file_path)
        return True

    def delete_many(self, ids: Iterable[int]) -> tuple[int, list[int]]:
        """Remove várias capturas; retorna contagem de sucesso e ids com falha."""
        return delete_many_by_id(self.delete, ids)

    def import_from_files(self, paths: Iterable[str]) -> FileImportResult:
        """Importa arquivos de imagem externos para o repositório local."""
        added = 0
        failed: list[str] = []
        skipped: list[str] = []
        for raw_path in paths:
            outcome = self._import_one_file(raw_path)
            if outcome == _ImportOutcome.ADDED:
                added += 1
            elif outcome == _ImportOutcome.SKIPPED:
                skipped.append(raw_path)
            else:
                failed.append(raw_path)
        return FileImportResult(added=added, failed=failed, skipped=skipped)

    def _import_one_file(self, raw_path: str) -> _ImportOutcome:
        source = Path(raw_path)
        if not source.is_file():
            return _ImportOutcome.FAILED
        try:
            imported = self._file_importer.import_file(str(source))
        except OSError:
            _logger.exception("Falha ao importar imagem %s.", raw_path)
            return _ImportOutcome.FAILED
        dest = Path(imported.file_path)
        if self._repository.get_by_path(str(dest.resolve())) is not None:
            return _ImportOutcome.SKIPPED
        copied = dest.resolve() != source.resolve()
        capture = Capture(
            file_path=str(dest.resolve()),
            width=imported.width,
            height=imported.height,
            pixel_format=EDITED_PIXEL_FORMAT,
            captured_at=datetime.now().isoformat(timespec="seconds"),
        )
        try:
            self._repository.add(capture)
        except PersistenceError:
            _logger.exception(
                "Falha ao registrar captura importada em %s.", imported.file_path
            )
            if copied:
                self._storage.delete(imported.file_path)
            return _ImportOutcome.FAILED
        _logger.info("Captura importada de %s.", raw_path)
        return _ImportOutcome.ADDED
