"""Contrato de repositório de gravações (port de persistência)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from visionflow.domain.entities.filtered_page import FilteredPage
from visionflow.domain.entities.recording import Recording


class RecordingRepository(ABC):
    """Operações de persistência para gravações (como capturas)."""

    @abstractmethod
    def add(self, recording: Recording) -> int:
        """Registra uma gravação e devolve o ``id`` gerado."""
        raise NotImplementedError

    @abstractmethod
    def register_file(self, file_path: str) -> int | None:
        """Cadastra um MP4 no disco e devolve o ``id`` (ou existente)."""
        raise NotImplementedError

    @abstractmethod
    def import_external_file(self, source_path: str) -> int | None:
        """Copia MP4 externo para o diretório gerenciado e registra."""
        raise NotImplementedError

    @abstractmethod
    def list_filtered(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        limit: int,
        offset: int = 0,
    ) -> list[Recording]:
        """Lista gravações filtradas por intervalo de datas (ordem decrescente)."""
        raise NotImplementedError

    @abstractmethod
    def count_filtered(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> int:
        """Total de gravações no intervalo de datas informado."""
        raise NotImplementedError

    @abstractmethod
    def list_filtered_page(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        limit: int,
        offset: int = 0,
    ) -> FilteredPage[Recording]:
        """Lista uma página filtrada e o total."""
        raise NotImplementedError

    @abstractmethod
    def list_filtered_ids(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> list[int]:
        """Lista ``id`` de gravações no intervalo (sem paginação)."""
        raise NotImplementedError

    @abstractmethod
    def list_by_ids(self, ids: list[int]) -> list[Recording]:
        """Lista gravações pelos ``id`` informados (ordem decrescente por ``id``)."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Retorna o total de gravações registradas."""
        raise NotImplementedError

    @abstractmethod
    def get(self, recording_id: int) -> Recording | None:
        """Retorna uma gravação pelo ``id``, ou ``None`` se não existir."""
        raise NotImplementedError

    @abstractmethod
    def get_by_path(self, file_path: str) -> Recording | None:
        """Retorna uma gravação pelo caminho do arquivo, ou ``None``."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, recording_id: int) -> str | None:
        """Remove o registro e devolve o ``file_path`` removido (ou ``None``)."""
        raise NotImplementedError
