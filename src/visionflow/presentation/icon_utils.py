"""Utilitários para carregar e colorir ícones SVG na UI.

O QSS não recolore SVGs rasterizados; quando um mesmo ícone precisa aparecer em
cores diferentes (texto do botão, estados), tingimos o pixmap em tempo de
execução preservando o canal alfa do traçado.
"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from visionflow.presentation.paths import ICONS_DIR


def tinted_pixmap(icon_name: str, color: str, size: QSize) -> QPixmap:
    """Carrega o ícone SVG e o pinta com ``color`` (via ``ICONS_DIR``)."""
    path = ICONS_DIR / icon_name
    pixmap = QIcon(str(path)).pixmap(size)
    if not pixmap.isNull():
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color))
        painter.end()
    return pixmap


def tinted_icon(icon_name: str, color: str, size: QSize) -> QIcon:
    """Versão de :func:`tinted_pixmap` que devolve um ``QIcon``."""
    return QIcon(tinted_pixmap(icon_name, color, size))
