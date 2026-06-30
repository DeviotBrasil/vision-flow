"""Seletor de intervalo de datas com locale PT-BR."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, QLocale, Signal
from PySide6.QtWidgets import QWidget

from visionflow.presentation.widgets.calendar_date_edit import (
    CalendarOnlyDateEdit,
)

_PT_BR_LOCALE = QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil)
_DATE_FILTER_HEIGHT = 28


class DateRangePicker(QWidget):
    """Par De/Até com sinal unificado de mudança."""

    dates_changed = Signal()

    def __init__(
        self,
        *,
        start_object_name: str,
        end_object_name: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._syncing = False
        self.start_date = self._create_picker(start_object_name)
        self.end_date = self._create_picker(end_object_name)

    def _create_picker(self, object_name: str) -> CalendarOnlyDateEdit:
        picker = CalendarOnlyDateEdit()
        picker.setObjectName(object_name)
        picker.setFixedHeight(_DATE_FILTER_HEIGHT)
        picker.setDisplayFormat("dd/MM/yyyy")
        picker.setLocale(_PT_BR_LOCALE)
        picker.setDate(QDate.currentDate())
        picker.dateChanged.connect(self._on_date_changed)
        return picker

    def _on_date_changed(self) -> None:
        if self._syncing:
            return
        self.dates_changed.emit()

    def selected_dates(self) -> tuple[date, date]:
        start = self.start_date.date().toPython()
        end = self.end_date.date().toPython()
        if start > end:
            start, end = end, start
            self._syncing = True
            try:
                self.start_date.setDate(QDate(start.year, start.month, start.day))
                self.end_date.setDate(QDate(end.year, end.month, end.day))
            finally:
                self._syncing = False
        return start, end

    def apply_range(self, start: date, end: date) -> None:
        self._syncing = True
        try:
            self.start_date.setDate(QDate(start.year, start.month, start.day))
            self.end_date.setDate(QDate(end.year, end.month, end.day))
        finally:
            self._syncing = False
