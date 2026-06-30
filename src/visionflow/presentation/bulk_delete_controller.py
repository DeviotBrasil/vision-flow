"""Orquestra exclusão em lote na thread da UI (SQLite não roda em worker)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from visionflow.presentation.background_job_controller import (
    BackgroundJobController,
)
from visionflow.presentation.gallery_batch_types import DeleteManyFn
from visionflow.presentation.job_status import format_loading_message
from visionflow.presentation.main_thread_batch import (
    MainThreadBatchController,
    run_with_ui_pump,
)

_logger = logging.getLogger(__name__)

_BUSY_MESSAGE = "Aguarde a conclusão da operação em andamento e tente novamente."


@dataclass(frozen=True)
class BulkDeleteBindings:
    """Callbacks da exclusão em lote."""

    delete_many: DeleteManyFn
    item_label: str
    on_finished: Callable[[int, list[int]], None]
    on_failed: Callable[[], None] | None = None
    on_busy: Callable[[], None] | None = None


class BulkDeleteController:
    """Exclusão em lote com popup modal; processa na thread principal."""

    def __init__(
        self,
        *,
        jobs: BackgroundJobController,
        bindings: BulkDeleteBindings,
    ) -> None:
        self._batch = MainThreadBatchController(jobs=jobs)
        self._bindings = bindings
        self._pending_ids: list[int] = []

    def start_delete(self, ids: list[int]) -> bool:
        if not ids:
            return False
        self._pending_ids = list(ids)
        if not self._batch.start(
            loading_message=format_loading_message(
                "Excluindo",
                len(ids),
                self._bindings.item_label,
            ),
            total=len(ids),
            run=self._run_delete,
        ):
            if self._bindings.on_busy is not None:
                self._bindings.on_busy()
            return False
        return True

    def _run_delete(self) -> None:
        deleted = 0
        failed_ids: list[int] = []
        try:

            def process_one(item_id: int) -> None:
                nonlocal deleted, failed_ids
                batch_deleted, batch_failed = self._bindings.delete_many([item_id])
                deleted += batch_deleted
                failed_ids.extend(batch_failed)

            run_with_ui_pump(
                self._pending_ids,
                process_one,
                on_progress=self._batch.update_progress,
            )
        except Exception:
            _logger.exception("Falha na exclusão em lote.")
            self._batch.end_busy()
            if self._bindings.on_failed is not None:
                self._bindings.on_failed()
            return
        self._batch.end_busy()
        self._bindings.on_finished(deleted, failed_ids)
