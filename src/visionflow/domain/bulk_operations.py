"""Operações em lote genéricas reutilizadas pelos serviços de mídia."""

from __future__ import annotations

from collections.abc import Callable, Iterable


def delete_many_by_id(
    delete_one: Callable[[int], bool],
    ids: Iterable[int],
) -> tuple[int, list[int]]:
    """Remove vários itens; retorna contagem de sucesso e ids com falha."""
    deleted = 0
    failed: list[int] = []
    for item_id in ids:
        if delete_one(item_id):
            deleted += 1
        else:
            failed.append(item_id)
    return deleted, failed
