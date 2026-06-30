"""Rolagem vertical do conteúdo das telas quando a altura da janela não basta."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QFrame, QScrollArea, QSizePolicy, QWidget


class ScreenScrollArea(QScrollArea):
    """Scroll vertical da tela; limita a largura do conteúdo à do viewport."""

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        content = self.widget()
        if content is not None:
            content.setMaximumWidth(self.viewport().width())


def wrap_screen_in_scroll(screen: QWidget) -> QScrollArea:
    """Envolve a tela em ``QScrollArea`` com barra vertical sob demanda.

    A tela mantém ``Expanding`` na vertical quando há espaço; com altura mínima
    definida nas seções flexíveis, a barra aparece em vez de comprimir o layout.
    """
    scroll = ScreenScrollArea()
    scroll.setObjectName("screen_scroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    scroll.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    screen.setMinimumWidth(0)
    screen.setSizePolicy(
        QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Expanding
    )
    scroll.setWidget(screen)
    return scroll
