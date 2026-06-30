"""Contrato de cache de miniaturas em disco (port)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

ThumbnailReader = Callable[[str], object | None]


class ThumbnailCache(ABC):
    """Persistência lazy de miniaturas; leitura via ``as_reader()`` na composição."""

    @abstractmethod
    def remove(self, source_path: str) -> None:
        """Apaga a miniatura (e metadados) do ``source_path``, se existirem."""
        raise NotImplementedError

    @abstractmethod
    def as_reader(self) -> ThumbnailReader:
        """Retorna leitor lazy de frames RGB8 (sem acoplar numpy no port)."""
        raise NotImplementedError
