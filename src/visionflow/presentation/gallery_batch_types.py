"""Tipos compartilhados para jobs em lote nas galerias."""

from __future__ import annotations

from typing import Protocol

from visionflow.domain.file_import_result import FileImportResult


class DeleteManyFn(Protocol):
    """Remove vários itens por id e retorna contagem e falhas."""

    def __call__(self, ids: list[int]) -> tuple[int, list[int]]: ...


class ImportFilesFn(Protocol):
    """Importa arquivos externos e retorna resultado agregado."""

    def __call__(self, paths: list[str]) -> FileImportResult: ...
