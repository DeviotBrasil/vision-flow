"""Seletor de data somente por calendário popup (sem edição pelo teclado)."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QWheelEvent
from PySide6.QtWidgets import QDateEdit, QWidget

_DATE_PICKER_NAV_KEYS = frozenset(
    {
        Qt.Key.Key_Tab,
        Qt.Key.Key_Backtab,
        Qt.Key.Key_Escape,
        Qt.Key.Key_Space,
        Qt.Key.Key_Return,
        Qt.Key.Key_Enter,
    }
)


class CalendarOnlyDateEdit(QDateEdit):
    """Seletor de data via calendário popup, sem edição pelo teclado."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCalendarPopup(True)
        line_edit = self.lineEdit()
        if line_edit is not None:
            line_edit.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.lineEdit():
            if event.type() == QEvent.Type.KeyPress:
                return event.key() not in _DATE_PICKER_NAV_KEYS
            if event.type() == QEvent.Type.Wheel:
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in _DATE_PICKER_NAV_KEYS:
            super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()
