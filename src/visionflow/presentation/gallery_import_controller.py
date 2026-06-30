"""Orquestra importação de arquivos na thread da UI (SQLite não roda em worker)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from visionflow.domain.file_import_result import FileImportResult
from visionflow.presentation.background_job_controller import (
    BackgroundJobController,
)
from visionflow.presentation.gallery_batch_types import ImportFilesFn
from visionflow.presentation.import_feedback import format_import_feedback
from visionflow.presentation.job_status import (
    GALLERY_JOB_BUSY_MESSAGE,
    format_loading_message,
)
from visionflow.presentation.main_thread_batch import (
    MainThreadBatchController,
    run_with_ui_pump,
)
from visionflow.presentation.system_dialogs import dialog_parent

_logger = logging.getLogger(__name__)

PickPathsFn = Callable[[object], list[str]]

_BUSY_MESSAGE = GALLERY_JOB_BUSY_MESSAGE


@dataclass(frozen=True)
class GalleryImportBindings:
    """Callbacks e rótulos da importação em lote."""

    pick_paths: PickPathsFn
    import_files: ImportFilesFn
    item_label: str


class GalleryImportController:
    """Importação com popup modal; processa na thread principal."""

    def __init__(
        self,
        parent,
        *,
        jobs: BackgroundJobController,
        bindings: GalleryImportBindings,
        on_finished: Callable[[str | None], None],
    ) -> None:
        self._parent = parent
        self._batch = MainThreadBatchController(jobs=jobs)
        self._bindings = bindings
        self._on_finished = on_finished
        self._pending_paths: list[str] = []

    def start_import(self) -> bool:
        paths = self._bindings.pick_paths(dialog_parent(self._parent))
        if not paths:
            return False

        self._pending_paths = list(paths)
        if not self._batch.start(
            loading_message=format_loading_message(
                "Importando",
                len(paths),
                self._bindings.item_label,
            ),
            total=len(paths),
            run=self._run_import,
        ):
            self._on_finished(_BUSY_MESSAGE)
            return False
        return True

    def _run_import(self) -> None:
        total = len(self._pending_paths)
        result = FileImportResult()
        try:

            def process_one(path: str) -> FileImportResult:
                return self._bindings.import_files([path])

            for partial in run_with_ui_pump(
                self._pending_paths,
                process_one,
                on_progress=self._batch.update_progress,
            ):
                result = result.merge(partial)
        except Exception:
            _logger.exception("Falha na importação em lote.")
            self._batch.end_busy()
            self._on_finished("Não foi possível importar os arquivos selecionados.")
            return

        self._batch.end_busy()
        self._on_finished(
            format_import_feedback(
                added=result.added,
                failed_count=len(result.failed),
                skipped_count=len(result.skipped),
                total=total,
                item_label=self._bindings.item_label,
            )
        )
