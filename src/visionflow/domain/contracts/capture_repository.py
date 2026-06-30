"""Contrato de repositório de capturas (port de persistência)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from visionflow.domain.entities.capture import Capture
from visionflow.domain.entities.filtered_page import FilteredPage


class CaptureRepository(ABC):
    """Operações de persistência para capturas."""

    @abstractmethod
    def add(self, capture: Capture) -> int:
        """Registra uma captura e devolve o ``id`` gerado."""
        raise NotImplementedError

    @abstractmethod
    def list_recent(self, limit: int) -> list[Capture]:
        """Lista as capturas mais recentes (ordem decrescente por ``id``)."""
        raise NotImplementedError

    @abstractmethod
    def list_filtered(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        limit: int,
        offset: int = 0,
    ) -> list[Capture]:
        """Lista capturas filtradas por intervalo de datas (ordem decrescente)."""
        raise NotImplementedError

    @abstractmethod
    def count_filtered(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> int:
        """Total de capturas no intervalo de datas informado."""
        raise NotImplementedError

    @abstractmethod
    def list_filtered_page(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        limit: int,
        offset: int = 0,
    ) -> FilteredPage[Capture]:
        """Lista uma página filtrada e o total."""
        raise NotImplementedError

    @abstractmethod
    def list_filtered_ids(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> list[int]:
        """Lista ``id`` de capturas no intervalo (sem paginação)."""
        raise NotImplementedError

    @abstractmethod
    def list_by_ids(self, ids: list[int]) -> list[Capture]:
        """Lista capturas pelos ``id`` informados (ordem decrescente por ``id``)."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Retorna o total de capturas registradas."""
        raise NotImplementedError

    @abstractmethod
    def get(self, capture_id: int) -> Capture | None:
        """Retorna uma captura pelo ``id``, ou ``None`` se não existir."""
        raise NotImplementedError

    @abstractmethod
    def get_by_path(self, file_path: str) -> Capture | None:
        """Retorna uma captura pelo caminho do arquivo, ou ``None``."""
        raise NotImplementedError

    @abstractmethod
    def update_dimensions(
        self,
        capture_id: int,
        *,
        width: int,
        height: int,
    ) -> bool:
        """Atualiza ``width`` e ``height`` de uma captura existente."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, capture_id: int) -> str | None:
        """Remove o registro e devolve o ``file_path`` removido (ou ``None``)."""
        raise NotImplementedError
