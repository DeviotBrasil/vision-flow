"""Resultado agregado de importação de arquivos externos."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FileImportResult:
    """Contagens de uma importação em lote."""

    added: int = 0
    failed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def merge(self, other: FileImportResult) -> FileImportResult:
        """Combina dois resultados parciais."""
        return FileImportResult(
            added=self.added + other.added,
            failed=[*self.failed, *other.failed],
            skipped=[*self.skipped, *other.skipped],
        )
