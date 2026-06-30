"""Tela Logs — histórico com filtro por dia e busca por texto."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import ClassVar

from PySide6.QtCore import QDate, QLocale, Qt, QTimer
from PySide6.QtGui import QColor, QResizeEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from visionflow.domain.entities.log_entry import LogEntry
from visionflow.domain.exceptions import PersistenceError
from visionflow.domain.use_cases.logs import (
    LOG_DISPLAY_LIMIT,
    FilteredLogs,
    LogService,
)
from visionflow.presentation.system_dialogs import (
    confirm_clear_all_logs,
    save_file_path,
)
from visionflow.presentation.themes.theme_manager import ThemeManager
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_DANGER_OUTLINE,
    VARIANT_NEUTRAL_OUTLINE,
    create_button,
    refresh_button_icon_for_state,
)
from visionflow.presentation.widgets.calendar_date_edit import (
    CalendarOnlyDateEdit,
)
from visionflow.presentation.widgets.date_filter_utils import quick_filter_day
from visionflow.presentation.widgets.feedback_banner import FeedbackBanner
from visionflow.presentation.widgets.list_screen_header import ListScreenHeader
from visionflow.presentation.widgets.quick_date_filter_bar import (
    QuickDateFilterBar,
)

_FILTER_PAD_H = 34
_FILTER_PAD_V = 13
_FILTER_HEIGHT = 61
_DATE_FILTER_HEIGHT = 28
_SEARCH_DEBOUNCE_MS = 300
_PT_BR_LOCALE = QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil)
_LOG_QUICK_FILTERS: tuple[tuple[str, str], ...] = (("today", "Hoje"),)
_COLUMNS = ("Horário", "Nível", "Origem", "Mensagem")
_ROW_HEIGHT = 24
_MESSAGE_COLUMN = 3
_logger = logging.getLogger(__name__)

_LEVEL_COLORS = {
    "DEBUG": QColor("#8E8E93"),
    "INFO": QColor("#0066CC"),
    "WARNING": QColor("#FF9500"),
    "ERROR": QColor("#FF3B30"),
    "CRITICAL": QColor("#AF52DE"),
}


class LogsScreen(QWidget):
    """Lista completa de logs com filtro por dia e busca por texto."""

    PAGE_ID: ClassVar[str] = "logs"
    TITLE: ClassVar[str] = "Logs"
    USES_OUTER_SCROLL: ClassVar[bool] = False

    def __init__(
        self,
        log_service: LogService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(f"{self.PAGE_ID}_screen")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._logs = log_service
        self._last_result = FilteredLogs(entries=[], total=0)
        self._syncing_date = False
        self._truncation_feedback_active = False
        self._feedback_message: str | None = None

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(_SEARCH_DEBOUNCE_MS)
        self._search_timer.timeout.connect(self._reload)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = ListScreenHeader(
            object_name="logs_header",
            title=self.TITLE,
            title_object_name="logs_header_title",
            subtitle_object_name="logs_header_subtitle",
        )
        root.addWidget(self._header)
        root.addWidget(self._build_filter_bar())
        root.addWidget(self._build_feedback_banner())
        root.addWidget(self._build_body(), 1)

        self._connect_theme()
        self.refresh()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._body.currentIndex() == 0 and self._table.rowCount() > 0:
            QTimer.singleShot(0, self._adjust_table_columns)

    def refresh(self) -> None:
        """Recarrega os logs conforme filtros ativos."""
        self._reload()

    def _build_filter_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("logs_filter_bar")
        bar.setFixedHeight(_FILTER_HEIGHT)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(
            _FILTER_PAD_H, _FILTER_PAD_V, _FILTER_PAD_H, _FILTER_PAD_V
        )
        layout.setSpacing(9)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        dia_label = QLabel("Dia")
        dia_label.setObjectName("logs_filter_label")
        layout.addWidget(dia_label)

        self._day_date = self._create_date_picker("logs_day_date")
        layout.addWidget(self._day_date)

        self._quick_filters = QuickDateFilterBar(
            _LOG_QUICK_FILTERS,
            default_preset="today",
            on_preset_clicked=self._on_quick_filter_clicked,
        )
        layout.addWidget(self._quick_filters)
        layout.addSpacing(12)

        self._search_input = QLineEdit()
        self._search_input.setObjectName("logs_search_input")
        self._search_input.setPlaceholderText("Buscar no texto...")
        self._search_input.setFixedHeight(_DATE_FILTER_HEIGHT)
        self._search_input.setClearButtonEnabled(True)
        self._search_input.returnPressed.connect(self._on_search_triggered)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self._search_input, 1)

        self._download_button = create_button(
            "Salvar",
            variant=VARIANT_NEUTRAL_OUTLINE,
            shape=SHAPE_PILL,
            icon_name="icon_download.svg",
        )
        self._download_button.clicked.connect(self._on_download_csv)
        layout.addWidget(self._download_button)

        self._clear_button = create_button(
            "Limpar logs",
            variant=VARIANT_DANGER_OUTLINE,
            shape=SHAPE_PILL,
            icon_name="icon_trash.svg",
        )
        self._clear_button.setEnabled(False)
        self._clear_button.clicked.connect(self._on_clear_all_logs)
        layout.addWidget(self._clear_button)
        return bar

    def _build_feedback_banner(self) -> FeedbackBanner:
        self._feedback_banner = FeedbackBanner(
            banner_object_name="logs_error_banner",
            text_object_name="logs_error_banner_text",
            horizontal_padding=_FILTER_PAD_H,
        )
        return self._feedback_banner

    def _show_feedback(self, message: str, *, truncation: bool = False) -> None:
        self._feedback_message = message
        self._truncation_feedback_active = truncation
        self._feedback_banner.show_message(message)

    def _hide_feedback(self) -> None:
        self._feedback_message = None
        self._truncation_feedback_active = False
        self._feedback_banner.hide_message()

    def _connect_theme(self) -> None:
        window = self.window()
        manager = getattr(window, "theme_manager", None)
        if isinstance(manager, ThemeManager):
            manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme: str) -> None:
        self._refresh_action_button_icons(theme=theme)

    def _refresh_action_button_icons(self, theme: str | None = None) -> None:
        refresh_button_icon_for_state(
            self._clear_button,
            "icon_trash.svg",
            variant=VARIANT_DANGER_OUTLINE,
            theme=theme,
        )
        refresh_button_icon_for_state(
            self._download_button,
            "icon_download.svg",
            variant=VARIANT_NEUTRAL_OUTLINE,
            theme=theme,
        )

    def _update_clear_button(self, *, enabled: bool, theme: str | None = None) -> None:
        self._clear_button.setEnabled(enabled)
        self._refresh_action_button_icons(theme=theme)

    def _create_date_picker(self, object_name: str) -> CalendarOnlyDateEdit:
        picker = CalendarOnlyDateEdit()
        picker.setObjectName(object_name)
        picker.setFixedHeight(_DATE_FILTER_HEIGHT)
        picker.setDisplayFormat("dd/MM/yyyy")
        picker.setLocale(_PT_BR_LOCALE)
        picker.setDate(QDate.currentDate())
        picker.dateChanged.connect(self._on_day_changed)
        return picker

    def _build_body(self) -> QStackedWidget:
        self._body = QStackedWidget()
        self._body.setObjectName("logs_body")
        self._body.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setObjectName("logs_table")
        self._table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(True)
        self._table.setGridStyle(Qt.PenStyle.SolidLine)
        self._table.setAlternatingRowColors(False)
        self._table.setWordWrap(False)
        self._table.setCornerButtonEnabled(False)
        self._table.verticalHeader().setDefaultSectionSize(_ROW_HEIGHT)
        for column, label in enumerate(_COLUMNS):
            header_item = QTableWidgetItem(label)
            header_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            self._table.setHorizontalHeaderItem(column, header_item)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_MESSAGE_COLUMN, QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setHighlightSections(False)

        self._body.addWidget(self._table)

        self._empty = QLabel("Nenhum log encontrado para o dia selecionado.")
        self._empty.setObjectName("logs_empty")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._body.addWidget(self._empty)

        self._body.setCurrentIndex(1)
        return self._body

    def _on_day_changed(self) -> None:
        if self._syncing_date:
            return
        self._quick_filters.clear_selection()
        self._reload()

    def _on_quick_filter_clicked(self, preset: str) -> None:
        self._apply_day(quick_filter_day(preset))

    def _apply_day(self, day: date) -> None:
        self._syncing_date = True
        try:
            self._day_date.setDate(QDate(day.year, day.month, day.day))
        finally:
            self._syncing_date = False
        self._reload()

    def _on_search_text_changed(self, _text: str) -> None:
        self._search_timer.start()

    def _on_search_triggered(self) -> None:
        self._search_timer.stop()
        self._reload()

    def _on_download_csv(self) -> None:
        day = self._selected_day()
        text = self._search_input.text().strip() or None
        result = self._logs.list_for_export(day, text)
        if not result.entries:
            self._show_feedback("Nenhum log para exportar no período selecionado.")
            return
        csv_content = LogService.format_csv(result.entries)
        suggested = f"logs_{day.strftime('%Y%m%d')}.csv"
        target = save_file_path(
            self,
            "Salvar logs",
            suggested,
            "CSV (*.csv);;Todos (*.*)",
        )
        if not target:
            return
        path = Path(target)
        if path.suffix.lower() != ".csv":
            path = path.with_suffix(".csv")
        try:
            path.write_text(csv_content, encoding="utf-8-sig", newline="")
        except OSError:
            _logger.exception("Falha ao salvar CSV de logs em %s.", path)
            self._show_feedback(
                "Não foi possível salvar o arquivo. Verifique permissões do destino."
            )
            return
        if result.truncated:
            self._show_feedback(
                "CSV salvo com os "
                f"{len(result.entries):,} registros mais recentes "
                f"(total filtrado: {result.total:,}).".replace(",", ".")
            )
        else:
            self._hide_feedback()

    def _on_clear_all_logs(self) -> None:
        total = self._logs.count()
        if total == 0:
            self._show_feedback("Não há logs para excluir.")
            return
        if not confirm_clear_all_logs(self, count=total):
            return
        try:
            deleted = self._logs.clear_all_logs()
        except PersistenceError:
            _logger.exception("Falha ao limpar todos os logs.")
            self._show_feedback("Não foi possível limpar os logs. Tente novamente.")
            return
        if deleted > 0:
            self._hide_feedback()
        self._reload()

    @staticmethod
    def _count_label(count: int, *, singular: str, plural: str) -> str:
        if count == 1:
            return f"1 {singular}"
        return f"{count} {plural}"

    @staticmethod
    def _format_thousands(value: int) -> str:
        return f"{value:,}".replace(",", ".")

    def _format_subtitle(self, result: FilteredLogs, db_total: int) -> str:
        if result.truncated:
            return (
                f"{self._format_thousands(len(result.entries))} de "
                f"{self._format_thousands(result.total)} registros "
                f"(limite de {self._format_thousands(LOG_DISPLAY_LIMIT)})"
            )
        filtered = self._count_label(
            result.total,
            singular="registro encontrado",
            plural="registros encontrados",
        )
        if result.total != db_total:
            bank = self._count_label(
                db_total,
                singular="registro no banco",
                plural="registros no banco",
            )
            return f"{filtered} · {bank}"
        return filtered

    def _sync_truncation_banner(self, result: FilteredLogs) -> None:
        if result.truncated:
            message = (
                "A tabela exibe apenas os "
                f"{self._format_thousands(len(result.entries))} registros mais "
                f"recentes de {self._format_thousands(result.total)} filtrados."
            )
            stale = (
                not self._truncation_feedback_active
                or self._feedback_message != message
            )
            if stale:
                self._show_feedback(message, truncation=True)
            return
        if self._truncation_feedback_active:
            self._hide_feedback()

    def _update_summary_labels(self, result: FilteredLogs) -> None:
        db_total = self._logs.count()
        self._update_clear_button(enabled=db_total > 0)
        self._header.subtitle_label.setText(self._format_subtitle(result, db_total))
        self._sync_truncation_banner(result)

    def _reload(self) -> None:
        day = self._selected_day()
        text = self._search_input.text().strip() or None
        self._last_result = self._logs.filter_logs(day, text)
        self._update_summary_labels(self._last_result)
        self._populate_table(self._last_result.entries)

    def _populate_table(self, entries: list[LogEntry]) -> None:
        self._table.setRowCount(0)
        if not entries:
            self._body.setCurrentIndex(1)
            return

        self._body.setCurrentIndex(0)
        self._table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            message = entry.message
            if entry.exception_text:
                message = f"{message} — {entry.exception_text}"

            values = (
                entry.logged_at or "",
                entry.level,
                entry.logger_name,
                message,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                if column == 1:
                    level_key = entry.level.upper()
                    color = _LEVEL_COLORS.get(level_key, _LEVEL_COLORS["INFO"])
                    item.setForeground(color)
                self._table.setItem(row, column, item)

        self._adjust_table_columns()

    def _adjust_table_columns(self) -> None:
        header = self._table.horizontalHeader()
        for column in range(_MESSAGE_COLUMN):
            self._table.resizeColumnToContents(column)

        fixed_width = sum(
            self._table.columnWidth(column) for column in range(_MESSAGE_COLUMN)
        )
        available = self._table.viewport().width() - fixed_width

        header.setSectionResizeMode(
            _MESSAGE_COLUMN, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.resizeColumnToContents(_MESSAGE_COLUMN)
        content_width = self._table.columnWidth(_MESSAGE_COLUMN)
        header.setSectionResizeMode(_MESSAGE_COLUMN, QHeaderView.ResizeMode.Interactive)

        message_width = max(available, content_width, 0)
        self._table.setColumnWidth(_MESSAGE_COLUMN, message_width)

    def _selected_day(self) -> date:
        return self._day_date.date().toPython()
