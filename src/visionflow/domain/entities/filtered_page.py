"""Resultado genérico de consulta paginada ou limitada."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FilteredPage[T]:
    """Entradas retornadas com total real (pode exceder o limite aplicado)."""

    entries: list[T]
    total: int

    @property
    def truncated(self) -> bool:
        return self.total > len(self.entries)
