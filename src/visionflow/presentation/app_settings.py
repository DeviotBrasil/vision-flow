"""Acesso centralizado a ``QSettings`` da aplicação."""

from PySide6.QtCore import QSettings

from visionflow.branding import QSETTINGS_APP, QSETTINGS_ORG


def app_settings() -> QSettings:
    """Retorna instância de configuração persistente do produto."""
    return QSettings(QSETTINGS_ORG, QSETTINGS_APP)
