"""Mensagens de status para jobs pesados nas telas de galeria."""

from __future__ import annotations

from PySide6.QtCore import QEventLoop
from PySide6.QtWidgets import QApplication

from visionflow.presentation.widgets.loading_dialog import LoadingDialog


def format_loading_message(action: str, count: int, item_label: str) -> str:
    """Monta texto exibido no diálogo de carregamento."""
    return f"{action} {count} {item_label}…"


def format_loading_status(current: int, total: int) -> str:
    """Monta linha de status ``X de Y``."""
    return f"{current} de {total}"


GALLERY_JOB_BUSY_MESSAGE = (
    "Aguarde a conclusão da operação em andamento e tente novamente."
)


def pump_ui_during_job() -> None:
    """Repinta o popup de aguarde durante jobs longos na thread da UI."""
    QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
    LoadingDialog.repaint_visible()
