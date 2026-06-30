"""Utilitários compartilhados para repositórios SQLite."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterable
from datetime import date
from typing import Any

from visionflow.infrastructure.persistence.database import connect

SQLITE_IN_BATCH_SIZE = 500


class SqliteRepositoryBase:
    """Operações comuns de leitura/escrita no SQLite."""

    @staticmethod
    def fetch_one(query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with connect() as connection:
            return connection.execute(query, params).fetchone()

    @staticmethod
    def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with connect() as connection:
            return connection.execute(query, params).fetchall()

    @staticmethod
    def execute(query: str, params: tuple[Any, ...] = ()) -> int:
        with connect() as connection:
            cursor = connection.execute(query, params)
            return int(cursor.lastrowid or 0)


def build_date_range_clause(
    *,
    start_date: date | None,
    end_date: date | None,
    column: str = "captured_at",
) -> tuple[str, tuple[str, ...]]:
    """Monta cláusula ``WHERE`` para intervalo de datas em coluna ISO."""
    clauses: list[str] = []
    params: list[str] = []
    if start_date is not None:
        clauses.append(f"date({column}) >= date(?)")
        params.append(start_date.isoformat())
    if end_date is not None:
        clauses.append(f"date({column}) <= date(?)")
        params.append(end_date.isoformat())
    if not clauses:
        return "", ()
    return f"WHERE {' AND '.join(clauses)}", tuple(params)


def fetch_entities_by_id_batches[T](
    ids: Iterable[int],
    fetch_batch: Callable[[list[int]], list[T]],
    *,
    batch_size: int = SQLITE_IN_BATCH_SIZE,
) -> list[T]:
    """Consulta ``IN (?)`` em lotes para respeitar o limite de variáveis SQLite."""
    id_list = list(ids)
    if not id_list:
        return []
    results: list[T] = []
    for offset in range(0, len(id_list), batch_size):
        results.extend(fetch_batch(id_list[offset : offset + batch_size]))
    return results
