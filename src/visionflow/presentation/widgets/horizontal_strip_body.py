"""Corpo rolável horizontal compartilhado (faixas da Principal)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from visionflow.presentation.window_constraints import (
    STRIP_SCROLLBAR_RESERVE,
    STRIP_THUMB_VIEWPORT_HEIGHT,
)

THUMB_GAP = 11
_STRIP_BODY_HEIGHT = STRIP_THUMB_VIEWPORT_HEIGHT + STRIP_SCROLLBAR_RESERVE


class HorizontalStripBody(QWidget):
    """Scroll horizontal com linha de widgets e estado vazio."""

    def __init__(self, *, strip_id: str, empty_text: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName(strip_id)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._body = QStackedWidget()
        self._body.setObjectName(f"{strip_id}_body")
        self._body.setFixedHeight(_STRIP_BODY_HEIGHT)
        layout.addWidget(self._body)

        scroll_page = QWidget()
        scroll_page.setObjectName(f"{strip_id}_scroll_page")
        scroll_layout = QVBoxLayout(scroll_page)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName(f"{strip_id}_scroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFixedHeight(STRIP_THUMB_VIEWPORT_HEIGHT)
        self._scroll.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        viewport = self._scroll.viewport()
        viewport.setObjectName(f"{strip_id}_viewport")
        viewport.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._container = QWidget()
        self._container.setObjectName(f"{strip_id}_container")
        self._container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._row = QHBoxLayout(self._container)
        self._row.setContentsMargins(0, 0, 0, 4)
        self._row.setSpacing(THUMB_GAP)
        self._row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._scroll.setWidget(self._container)
        scroll_layout.addWidget(self._scroll)
        scroll_layout.addSpacing(STRIP_SCROLLBAR_RESERVE)
        self._body.addWidget(scroll_page)

        self._empty = QLabel(empty_text)
        self._empty.setObjectName(f"{strip_id}_empty")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._body.addWidget(self._empty)

        self._body.setCurrentIndex(1)

    def clear_row(self) -> None:
        while self._row.count():
            item = self._row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def add_widget(self, widget: QWidget) -> None:
        self._row.addWidget(widget)

    def set_populated(self, has_items: bool) -> None:
        self._body.setCurrentIndex(0 if has_items else 1)
