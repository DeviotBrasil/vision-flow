"""Jobs em lote na thread da UI com repintura do popup de aguarde."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtCore import QTimer

from visionflow.presentation.background_job_controller import (
    BackgroundJobController,
)
from visionflow.presentation.job_status import (
    format_loading_status,
    pump_ui_during_job,
)


def run_with_ui_pump[T, R](
    items: Iterable[T],
    process_one: Callable[[T], R],
    *,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[R]:
    """Executa ``process_one`` por item, repintando a UI entre iterações."""
    item_list = list(items)
    total = len(item_list)
    results: list[R] = []
    for index, item in enumerate(item_list, start=1):
        results.append(process_one(item))
        if on_progress is not None:
            on_progress(index, total)
        pump_ui_during_job()
    return results


class MainThreadBatchController:
    """Orquestra job síncrono na thread principal via ``QTimer.singleShot``."""

    def __init__(self, *, jobs: BackgroundJobController) -> None:
        self._jobs = jobs

    def start(
        self,
        *,
        loading_message: str,
        run: Callable[[], None],
        total: int | None = None,
    ) -> bool:
        if not self._jobs.begin(loading_message=loading_message, total=total):
            return False
        QTimer.singleShot(0, run)
        return True

    def update_progress(
        self,
        current: int,
        total: int,
        *,
        message: str | None = None,
    ) -> None:
        """Atualiza status ``X de Y`` e barra do popup de aguarde."""
        self._jobs.update_loading(
            current,
            total,
            message=message,
            status=format_loading_status(current, total),
        )

    def end_busy(self) -> None:
        self._jobs.end_busy()
