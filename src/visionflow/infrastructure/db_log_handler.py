"""Handler de logging que persiste registros no SQLite."""

from __future__ import annotations

import logging
import traceback
from datetime import datetime

from visionflow.domain.contracts.log_repository import LogRepository
from visionflow.domain.entities.log_entry import LogEntry
from visionflow.domain.exceptions import PersistenceError

_MAX_MESSAGE_CHARS = 16_384
_MAX_EXCEPTION_CHARS = 32_768
_SKIP_LOGGER_PREFIXES = (
    "visionflow.infrastructure.persistence",
    "visionflow.infrastructure.db_log_handler",
)


class SqliteLogHandler(logging.Handler):
    """Grava cada ``LogRecord`` na tabela ``app_logs`` via :class:`LogRepository`."""

    def __init__(self, repository: LogRepository) -> None:
        super().__init__()
        self._repository = repository

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith(_SKIP_LOGGER_PREFIXES):
            return
        try:
            message = record.getMessage()[:_MAX_MESSAGE_CHARS]
            exception_text = self._format_exception(record)
            if exception_text is not None:
                exception_text = exception_text[:_MAX_EXCEPTION_CHARS]
            entry = LogEntry(
                level=record.levelname,
                logger_name=record.name,
                message=message,
                logged_at=datetime.fromtimestamp(record.created).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                exception_text=exception_text,
            )
            self._repository.add(entry)
        except PersistenceError:
            self.handleError(record)
        except Exception:
            self.handleError(record)

    @staticmethod
    def _format_exception(record: logging.LogRecord) -> str | None:
        if record.exc_info:
            return "".join(traceback.format_exception(*record.exc_info)).strip()
        if record.exc_text:
            return record.exc_text.strip()
        return None
