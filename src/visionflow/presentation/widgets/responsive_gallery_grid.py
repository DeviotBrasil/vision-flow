"""Base de grade responsiva com scroll (Capturas e Gravações)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QWidget,
)

from visionflow.presentation.widgets.gallery_card_layout import GALLERY_CARD_WIDTH

GRID_PAD = 26
GRID_GAP = 12


@dataclass(frozen=True)
class GalleryGridChrome:
    body_object_name: str
    scroll_object_name: str
    grid_container_object_name: str
    empty_object_name: str
    empty_text: str


class ResponsiveGalleryGrid(QStackedWidget):
    """Scroll com grade; subclasses implementam população dos cards."""

    def __init__(self, chrome: GalleryGridChrome, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName(chrome.body_object_name)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._grid_columns = 1

        scroll = QScrollArea()
        scroll.setObjectName(chrome.scroll_object_name)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._grid_container = QWidget()
        self._grid_container.setObjectName(chrome.grid_container_object_name)
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(GRID_PAD, GRID_PAD, GRID_PAD, GRID_PAD)
        self._grid.setHorizontalSpacing(GRID_GAP)
        self._grid.setVerticalSpacing(GRID_GAP)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self._grid_container)
        self._scroll = scroll
        self.addWidget(scroll)

        self._empty = QLabel(chrome.empty_text)
        self._empty.setObjectName(chrome.empty_object_name)
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.addWidget(self._empty)
        self.setCurrentIndex(1)
        self._on_selection_toggle: Callable[[int, bool], None] | None = None

    def set_selection_handler(
        self, handler: Callable[[int, bool], None] | None
    ) -> None:
        self._on_selection_toggle = handler

    def apply_selection(self, selected_ids: set[int]) -> None:
        raise NotImplementedError

    def _emit_selection_toggle(self, item_id: int, checked: bool) -> None:
        if self._on_selection_toggle is not None:
            self._on_selection_toggle(item_id, checked)

    def grid_column_count(self) -> int:
        viewport = self._scroll.viewport()
        available = viewport.width() - 2 * GRID_PAD
        if available <= 0:
            return 1
        return max(1, (available + GRID_GAP) // (GALLERY_CARD_WIDTH + GRID_GAP))

    def relayout_if_columns_changed(self) -> bool:
        columns = self.grid_column_count()
        if columns == self._grid_columns or not self._has_items():
            return False
        self._grid_columns = columns
        self._relayout_grid(columns)
        return True

    def _relayout_grid(self, columns: int) -> None:
        for index, widget in self._iter_card_widgets():
            row = index // columns
            col = index % columns
            self._grid.addWidget(widget, row, col)

    def _clear_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _show_empty(self) -> None:
        self.setCurrentIndex(1)

    def _show_grid(self, *, columns: int | None = None) -> int:
        self.setCurrentIndex(0)
        self._grid_columns = columns or self.grid_column_count()
        return self._grid_columns

    def _has_items(self) -> bool:
        raise NotImplementedError

    def _iter_card_widgets(self):
        raise NotImplementedError
