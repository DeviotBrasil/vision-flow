"""Orquestra a exportação ZIP de um dataset YOLO (thread principal)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from visionflow.domain.use_cases.yolo_dataset import YoloDatasetService
from visionflow.domain.use_cases.yolo_export import YoloExportService
from visionflow.domain.yolo_export_format import (
    DEFAULT_YOLO_EXPORT_FORMAT,
    YoloExportFormat,
)
from visionflow.presentation.background_job_controller import (
    BackgroundJobController,
)
from visionflow.presentation.job_status import (
    GALLERY_JOB_BUSY_MESSAGE,
    pump_ui_during_job,
)
from visionflow.presentation.main_thread_batch import MainThreadBatchController
from visionflow.presentation.system_dialogs import save_file_path

_logger = logging.getLogger(__name__)


class YoloExportController:
    """Monta o payload do dataset e compacta o ZIP YOLO na thread da UI."""

    def __init__(
        self,
        parent,
        *,
        jobs: BackgroundJobController,
        service: YoloDatasetService,
        on_finished: Callable[[str | None], None],
    ) -> None:
        self._parent = parent
        self._batch = MainThreadBatchController(jobs=jobs)
        self._service = service
        self._on_finished = on_finished
        self._export_path: Path | None = None
        self._dataset_id: int | None = None
        self._export_format = DEFAULT_YOLO_EXPORT_FORMAT

    def start_export(
        self,
        dataset_id: int,
        *,
        suggested_basename: str,
        export_format: YoloExportFormat = DEFAULT_YOLO_EXPORT_FORMAT,
    ) -> bool:
        target = save_file_path(
            self._parent,
            "Salvar dataset YOLO",
            f"{suggested_basename}.zip",
            "ZIP (*.zip);;Todos (*.*)",
        )
        if not target:
            return False
        path = Path(target)
        if path.suffix.lower() != ".zip":
            path = path.with_suffix(".zip")
        self._export_path = path
        self._dataset_id = dataset_id
        self._export_format = export_format
        if not self._batch.start(
            loading_message="Gerando dataset YOLO…",
            total=None,
            run=self._run_export,
        ):
            self._on_finished(GALLERY_JOB_BUSY_MESSAGE)
            return False
        return True

    def _run_export(self) -> None:
        path = self._export_path
        dataset_id = self._dataset_id
        if path is None or dataset_id is None:
            self._batch.end_busy()
            return
        try:
            self._batch.update_progress(0, 1, message="Consultando dataset…")
            pump_ui_during_job()
            payload = self._service.build_export_payload(dataset_id)
            if payload is None:
                self._batch.end_busy()
                self._on_finished("Dataset indisponível para exportação.")
                return
            self._batch.update_progress(
                0, len(payload.images), message="Compactando arquivo ZIP…"
            )
            pump_ui_during_job()
            added, skipped = YoloExportService.write_zip(
                payload,
                str(path),
                export_format=self._export_format,
                on_progress=self._report_progress,
            )
        except Exception:
            _logger.exception("Falha ao exportar dataset YOLO em %s.", path)
            self._batch.end_busy()
            self._on_finished(
                "Não foi possível salvar o arquivo. Verifique permissões do destino."
            )
            return

        self._batch.end_busy()
        if added == 0:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                _logger.exception("Falha ao remover ZIP vazio em %s.", path)
            self._on_finished("Nenhuma imagem encontrada no disco para exportar.")
            return
        self._on_finished(self._success_message(added, skipped))

    def _report_progress(self, current: int, total: int) -> None:
        self._batch.update_progress(current, total)
        pump_ui_during_job()

    @staticmethod
    def _success_message(added: int, skipped: int) -> str | None:
        if skipped <= 0:
            return None
        return f"ZIP salvo; {skipped} imagem(ns) não encontrada(s) no disco."
