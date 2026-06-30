"""Configuração central de logging do Vision Flow.

Grava no banco SQLite (via :func:`attach_db_log_handler`) e no console. Nível
padrão INFO; use a variável de ambiente ``VISIONFLOW_LOG_LEVEL`` (DEBUG,
INFO, …) para diagnóstico. Exceções não tratadas e falhas em threads são
registradas automaticamente.

Exemplo::

    export VISIONFLOW_LOG_LEVEL=DEBUG
    visionflow
"""

from __future__ import annotations

import logging
import os
import sys
import threading

from visionflow.branding import ENV_LOG_LEVEL
from visionflow.domain.contracts.log_repository import LogRepository
from visionflow.infrastructure.db_log_handler import SqliteLogHandler

_CONFIGURED = False
_DB_HANDLER_ATTACHED = False
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _resolve_level() -> int:
    raw = os.environ.get(ENV_LOG_LEVEL, "INFO").strip().upper()
    return getattr(logging, raw, logging.INFO)


def configure_logging() -> None:
    """Configura handlers de console, formato e hooks de exceção (idempotente)."""
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return
    _CONFIGURED = True

    level = _resolve_level()
    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATE_FORMAT)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    logging.getLogger(__name__).info(
        "Logging iniciado (nível=%s).",
        logging.getLevelName(level),
    )

    sys.excepthook = _log_unhandled_exception
    threading.excepthook = _log_thread_exception


def attach_db_log_handler(repository: LogRepository) -> None:
    """Registra o handler que persiste logs no SQLite (idempotente)."""
    global _DB_HANDLER_ATTACHED  # noqa: PLW0603
    if _DB_HANDLER_ATTACHED:
        return
    _DB_HANDLER_ATTACHED = True

    db_handler = SqliteLogHandler(repository)
    db_handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(db_handler)

    logging.getLogger(__name__).info("Handler de logs no banco registrado.")


def _log_unhandled_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: object,
) -> None:
    logging.getLogger("visionflow").critical(
        "Exceção não tratada no thread principal.",
        exc_info=(exc_type, exc_value, exc_tb),
    )
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def _log_thread_exception(args: threading.ExceptHookArgs) -> None:
    logging.getLogger("visionflow").critical(
        "Exceção não tratada na thread %s.",
        args.thread.name if args.thread else "?",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
