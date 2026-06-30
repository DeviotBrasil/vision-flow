"""Entidade de registro de log persistido no banco."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LogEntry:
    """Um evento de log gravado na tabela ``app_logs``.

    ``id`` e ``logged_at`` são preenchidos pela persistência; ao criar um
    registro novo (ainda não gravado), ``id`` é ``None``.
    """

    level: str
    logger_name: str
    message: str
    id: int | None = None
    logged_at: str | None = None
    exception_text: str | None = None
