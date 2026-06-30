"""Encaminha mensagens internas do Qt para o logging do Vision Flow.

Fica na camada de UI (e não em ``core/``) porque depende do PySide6: registra um
``qInstallMessageHandler`` que envia os avisos do Qt para o logger
``visionflow.qt``. Deve ser chamado uma vez, após ``configure_logging``.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

_logger = logging.getLogger("visionflow.qt")

_LEVEL_MAP = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg: logging.CRITICAL,
}


def _handler(msg_type: QtMsgType, context: object, message: str) -> None:
    level = _LEVEL_MAP.get(msg_type, logging.INFO)
    location = ""
    if context is not None and getattr(context, "file", None):
        location = f" ({context.file}:{getattr(context, 'line', '?')})"
    _logger.log(level, "%s%s", message, location)


def install_qt_message_handler() -> None:
    """Instala o handler que roteia mensagens do Qt para o logging."""
    qInstallMessageHandler(_handler)
