"""Orquestra exportação ZIP das galerias (thread principal; igual importar/excluir)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from visionflow.presentation.background_job_controller import (
    BackgroundJobController,
)
from visionflow.presentation.job_status import (
    GALLERY_JOB_BUSY_MESSAGE,
    format_loading_message,
    pump_ui_during_job,
)
from visionflow.presentation.main_thread_batch import MainThreadBatchController
from visionflow.presentation.system_dialogs import save_file_path

_logger = logging.getLogger(__name__)

_BUSY_MESSAGE = GALLERY_JOB_BUSY_MESSAGE


@dataclass(frozen=True)
class GalleryZipExportBindings:
    """Callbacks e textos da exportação ZIP."""

    list_by_ids: Callable[[list[int]], object]
    write_zip: Callable[..., tuple[int, int]]
    save_dialog_title: str
    empty_selection_message: str
    skipped_file_label: str
    zero_added_message: str


class GalleryZipExportController:
    """Resolve ids e compacta ZIP na thread principal (SQLite + I/O)."""

    def __init__(
        self,
        parent,
        *,
        jobs: BackgroundJobController,
        bindings: GalleryZipExportBindings,
        on_finished: Callable[[str | None], None],
    ) -> None:
        self._parent = parent
        self._batch = MainThreadBatchController(jobs=jobs)
        self._bindings = bindings
        self._on_finished = on_finished
        self._export_path: Path | None = None
        self._pending_ids: list[int] = []

    def start_export(
        self,
        ids: list[int],
        *,
        suggested_basename: str,
    ) -> bool:
        if not ids:
            self._on_finished(self._bindings.empty_selection_message)
            return False

        suggested = f"{suggested_basename}.zip"
        target = save_file_path(
            self._parent,
            self._bindings.save_dialog_title,
            suggested,
            "ZIP (*.zip);;Todos (*.*)",
        )
        if not target:
            return False

        path = Path(target)
        if path.suffix.lower() != ".zip":
            path = path.with_suffix(".zip")

        self._export_path = path
        self._pending_ids = list(ids)
        if not self._batch.start(
            loading_message=format_loading_message(
                "Gerando ZIP com",
                len(ids),
                self._bindings.skipped_file_label,
            ),
            total=len(ids),
            run=self._run_export,
        ):
            self._on_finished(_BUSY_MESSAGE)
            return False
        return True

    def _run_export(self) -> None:
        path = self._export_path
        if path is None:
            self._batch.end_busy()
            return

        try:
            pending_total = len(self._pending_ids)
            self._batch.update_progress(
                0,
                pending_total,
                message="Consultando itens no banco…",
            )
            pump_ui_during_job()

            page = self._bindings.list_by_ids(self._pending_ids)
            entries = list(getattr(page, "entries", page))

            total = len(entries)
            self._batch.update_progress(
                0,
                total,
                message="Compactando arquivo ZIP…",
            )
            pump_ui_during_job()

            added, skipped = self._bindings.write_zip(
                entries,
                str(path),
                on_progress=self._report_zip_progress,
            )
        except Exception:
            _logger.exception("Falha ao exportar ZIP em %s.", path)
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
            self._on_finished(self._bindings.zero_added_message)
            return

        message = self._format_success_message(added, skipped)
        self._on_finished(message)

    def _report_zip_progress(self, current: int, total: int) -> None:
        self._batch.update_progress(current, total)
        pump_ui_during_job()

    def _format_success_message(self, added: int, skipped: int) -> str | None:
        if skipped <= 0:
            return None
        label = self._bindings.skipped_file_label
        return f"ZIP salvo; {skipped} {label} não encontrado(s) no disco."
