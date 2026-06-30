"""Contrato de repositório de logs (port de persistência)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from visionflow.domain.entities.log_entry import LogEntry


class LogRepository(ABC):
    """Operações de persistência para registros de log."""

    @abstractmethod
    def add(self, entry: LogEntry) -> int:
        """Registra um log e devolve o ``id`` gerado."""
        raise NotImplementedError

    @abstractmethod
    def list_filtered(
        self,
        *,
        day: date | None,
        text: str | None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[LogEntry]:
        """Lista logs filtrados por dia e texto (ordem decrescente por ``id``)."""
        raise NotImplementedError

    @abstractmethod
    def count_filtered(
        self,
        *,
        day: date | None,
        text: str | None,
    ) -> int:
        """Total de logs que atendem aos filtros informados."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Retorna o total de logs registrados."""
        raise NotImplementedError

    @abstractmethod
    def delete_older_than_days(self, days: int) -> int:
        """Remove logs anteriores ao período informado; devolve linhas excluídas."""
        raise NotImplementedError

    @abstractmethod
    def delete_all(self) -> int:
        """Remove todos os registros de log; devolve linhas excluídas."""
        raise NotImplementedError
