"""Carrega miniaturas de mídia fora da thread da GUI."""

from __future__ import annotations

import logging
from collections.abc import Callable

import numpy as np
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot

_logger = logging.getLogger(__name__)


class _MediaThumbnailWorker(QObject):
    """Executa leitura de miniaturas em thread dedicada (única por loader)."""

    load_requested = Signal(list)
    thumbnail_ready = Signal(str, object)
    batch_done = Signal()

    def __init__(self, frame_reader: Callable[[str], object | None]) -> None:
        super().__init__()
        self._frame_reader = frame_reader
        self._paths: list[str] = []
        self._processing = False
        self.load_requested.connect(
            self.enqueue,
            Qt.ConnectionType.QueuedConnection,
        )

    @Slot(list)
    def enqueue(self, paths: list[str]) -> None:
        for path in paths:
            if path not in self._paths:
                self._paths.append(path)
        if not self._processing:
            self._process_next()

    @Slot()
    def _process_next(self) -> None:
        if not self._paths:
            self._processing = False
            self.batch_done.emit()
            return

        self._processing = True
        path = self._paths.pop(0)
        try:
            frame = self._frame_reader(path)
        except Exception:
            _logger.exception("Falha ao ler miniatura de %s.", path)
            frame = None
        if frame is not None:
            safe = np.ascontiguousarray(frame)
            self.thumbnail_ready.emit(path, safe)
        if self._paths:
            QTimer.singleShot(0, self, self._process_next)
            return
        self._processing = False
        self.batch_done.emit()


class MediaThumbnailLoader(QObject):
    """Orquestra worker de miniaturas e reemite resultados para a UI."""

    thumbnail_ready = Signal(str, object)

    def __init__(
        self,
        frame_reader: Callable[[str], object | None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._thread = QThread(self)
        self._worker = _MediaThumbnailWorker(frame_reader)
        self._worker.moveToThread(self._thread)
        self._worker.thumbnail_ready.connect(
            self._on_thumbnail_ready,
            Qt.ConnectionType.QueuedConnection,
        )
        self._worker.batch_done.connect(
            self._on_batch_done,
            Qt.ConnectionType.QueuedConnection,
        )
        self._thread.start()
        self._pending: list[str] = []
        self._awaiting_worker = False

    def load(self, paths: list[str]) -> None:
        """Enfileira caminhos; o worker processa um por vez sem cancelar leitura."""
        for path in paths:
            if path not in self._pending:
                self._pending.append(path)
        self._dispatch()

    def shutdown(self) -> None:
        self._pending.clear()
        if self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)

    def _dispatch(self) -> None:
        if self._awaiting_worker or not self._pending:
            return
        batch = list(self._pending)
        self._pending.clear()
        self._awaiting_worker = True
        self._worker.load_requested.emit(batch)

    def _on_thumbnail_ready(self, file_path: str, frame: object) -> None:
        self.thumbnail_ready.emit(file_path, frame)

    def _on_batch_done(self) -> None:
        self._awaiting_worker = False
        self._dispatch()


RecordingThumbnailLoader = MediaThumbnailLoader
