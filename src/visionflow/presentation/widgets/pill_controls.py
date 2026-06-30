"""Controles em pílula (cantos arredondados) independentes do estilo Qt."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath
from PySide6.QtWidgets import QFrame, QPushButton


def _pill_clip_path(rect: QRectF) -> QPainterPath:
    """Retorna um retângulo com semicírculos nas extremidades (formato pílula)."""
    radius = min(rect.width(), rect.height()) / 2.0
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


class PillFrame(QFrame):
    """``QFrame`` com fundo QSS recortado em pílula (badge, chips)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def paintEvent(self, event) -> None:
        path = _pill_clip_path(QRectF(self.rect()))
        with QPainter(self) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setClipPath(path)
            super().paintEvent(event)


class PillPushButton(QPushButton):
    """``QPushButton`` com aparência de pílula; cores continuam no QSS."""

    def paintEvent(self, event) -> None:
        path = _pill_clip_path(QRectF(self.rect()))
        with QPainter(self) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setClipPath(path)
            super().paintEvent(event)
