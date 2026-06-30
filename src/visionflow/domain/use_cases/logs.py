"""Serviço de logs: consultas filtradas sobre registros persistidos."""

from __future__ import annotations

import csv
import io
from datetime import date

from visionflow.domain.contracts.log_repository import LogRepository
from visionflow.domain.entities.filtered_page import FilteredPage
from visionflow.domain.entities.log_entry import LogEntry

_CSV_HEADERS = ("logged_at", "level", "logger_name", "message", "exception_text")
LOG_DISPLAY_LIMIT = 5000
LOG_EXPORT_LIMIT = 100_000
LOG_RETENTION_DAYS = 90

FilteredLogs = FilteredPage[LogEntry]


class LogService:
    """Casos de uso de visualização de logs (listar, contar e exportar)."""

    def __init__(self, repository: LogRepository) -> None:
        self._repository = repository

    def count(self) -> int:
        """Total de logs registrados."""
        return self._repository.count()

    def count_filtered(
        self,
        day: date | None,
        text: str | None,
    ) -> int:
        """Total de logs no dia e termo de busca informados."""
        return self._repository.count_filtered(day=day, text=text)

    def filter_logs(
        self,
        day: date | None,
        text: str | None,
        *,
        limit: int = LOG_DISPLAY_LIMIT,
    ) -> FilteredLogs:
        """Lista logs filtrados com limite de exibição (ordem decrescente)."""
        total = self._repository.count_filtered(day=day, text=text)
        entries = self._repository.list_filtered(
            day=day,
            text=text,
            limit=limit,
        )
        return FilteredLogs(entries=entries, total=total)

    def list_for_export(
        self,
        day: date | None,
        text: str | None,
    ) -> FilteredLogs:
        """Lista logs para exportação CSV (limite maior que a tela)."""
        return self.filter_logs(day, text, limit=LOG_EXPORT_LIMIT)

    def prune_old_logs(self, retention_days: int = LOG_RETENTION_DAYS) -> int:
        """Remove registros mais antigos que o período de retenção."""
        return self._repository.delete_older_than_days(retention_days)

    def clear_all_logs(self) -> int:
        """Remove todos os registros de log; devolve linhas excluídas."""
        return self._repository.delete_all()

    @staticmethod
    def format_csv(entries: list[LogEntry]) -> str:
        """Serializa registros de log em texto CSV (cabeçalho + linhas)."""
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerow(_CSV_HEADERS)
        for entry in entries:
            writer.writerow(
                [
                    entry.logged_at or "",
                    entry.level,
                    entry.logger_name,
                    entry.message,
                    entry.exception_text or "",
                ]
            )
        return buffer.getvalue()
