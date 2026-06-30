"""Utilitários de estilo QSS compartilhados pela camada de UI.

Centraliza o padrão de reaplicar o estilo (``unpolish``/``polish``) após mudar
uma propriedade dinâmica usada em seletores QSS, evitando repetir esse trecho
em cada widget.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget


def repolish(widget: QWidget) -> None:
    """Reaplica o QSS do widget após mudança de estado/propriedade dinâmica."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


def set_property(widget: QWidget, name: str, value: object) -> None:
    """Define uma propriedade dinâmica e repolish (refletir no seletor QSS)."""
    widget.setProperty(name, value)
    repolish(widget)
