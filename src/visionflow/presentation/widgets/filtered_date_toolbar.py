"""Barra de filtro por data reutilizada nas telas de galeria."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from visionflow.presentation.list_screen_common import (
    FILTER_HEIGHT,
    FILTER_PAD_H,
    FOOTER_PAD_V,
    QUICK_DATE_FILTERS,
)
from visionflow.presentation.themes.theme_manager import ThemeManager
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_DANGER_OUTLINE,
    VARIANT_NEUTRAL_OUTLINE,
    VARIANT_PRIMARY_OUTLINE,
    create_button,
    refresh_button_icon_for_state,
    update_outline_action_button,
)
from visionflow.presentation.widgets.date_range_picker import DateRangePicker
from visionflow.presentation.widgets.filtered_date_toolbar_actions import (
    FilteredDateToolbarActions,
)
from visionflow.presentation.widgets.quick_date_filter_bar import (
    QuickDateFilterBar,
)

_DELETE_ICON = "icon_trash.svg"
_DOWNLOAD_ICON = "icon_download.svg"


class FilteredDateToolbar(QFrame):
    """Filtro De/Até, presets rápidos e ações de exportação/exclusão."""

    def __init__(
        self,
        *,
        screen_prefix: str,
        actions: FilteredDateToolbarActions,
        add_icon_name: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(f"{screen_prefix}_filter_bar")
        self.setFixedHeight(FILTER_HEIGHT)
        self._delete_label = "Excluir"
        self._delete_enabled = False
        self._download_enabled = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            FILTER_PAD_H, FOOTER_PAD_V, FILTER_PAD_H, FOOTER_PAD_V
        )
        layout.setSpacing(9)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        de_label = QLabel("De")
        de_label.setObjectName(f"{screen_prefix}_filter_label")
        layout.addWidget(de_label)

        self.date_picker = DateRangePicker(
            start_object_name=f"{screen_prefix}_start_date",
            end_object_name=f"{screen_prefix}_end_date",
        )
        self.date_picker.dates_changed.connect(actions.on_dates_changed)
        layout.addWidget(self.date_picker.start_date)
        layout.addWidget(QLabel("Até"))
        layout.addWidget(self.date_picker.end_date)

        self.quick_filters = QuickDateFilterBar(
            QUICK_DATE_FILTERS,
            default_preset="today",
            on_preset_clicked=actions.on_quick_filter,
        )
        layout.addWidget(self.quick_filters)
        layout.addStretch()

        self.add_button: QPushButton | None = None
        if actions.on_add is not None and add_icon_name is not None:
            self.add_button = create_button(
                "Adicionar",
                variant=VARIANT_PRIMARY_OUTLINE,
                shape=SHAPE_PILL,
                icon_name=add_icon_name,
            )
            self.add_button.clicked.connect(actions.on_add)
            layout.addWidget(self.add_button)

        self.select_all_button: QPushButton | None = None
        if actions.on_select_all is not None:
            self.select_all_button = create_button(
                "Selecionar todas",
                variant=VARIANT_NEUTRAL_OUTLINE,
                shape=SHAPE_PILL,
                icon_name="icon_check.svg",
            )
            self.select_all_button.setEnabled(False)
            self.select_all_button.clicked.connect(actions.on_select_all)
            layout.addWidget(self.select_all_button)

        self.delete_selected_button: QPushButton | None = None
        if actions.on_bulk_delete is not None:
            self.delete_selected_button = create_button(
                "Excluir",
                variant=VARIANT_DANGER_OUTLINE,
                shape=SHAPE_PILL,
                icon_name=_DELETE_ICON,
            )
            self.delete_selected_button.setEnabled(False)
            self.delete_selected_button.clicked.connect(actions.on_bulk_delete)
            layout.addWidget(self.delete_selected_button)
            self.update_delete_button(label="Excluir", enabled=False)

        self.download_button: QPushButton = create_button(
            "Salvar",
            variant=VARIANT_NEUTRAL_OUTLINE,
            shape=SHAPE_PILL,
            icon_name=_DOWNLOAD_ICON,
        )
        self.download_button.clicked.connect(actions.on_download_zip)
        layout.addWidget(self.download_button)
        self.update_download_button(enabled=False)

    def connect_theme(self) -> None:
        """Reaplica ícones dependentes de tema (ex.: botão Excluir)."""
        window = self.window()
        manager = getattr(window, "theme_manager", None)
        if isinstance(manager, ThemeManager):
            manager.theme_changed.connect(self._on_theme_changed)

    def update_delete_button(
        self,
        *,
        label: str,
        enabled: bool,
        theme: str | None = None,
    ) -> None:
        button = self.delete_selected_button
        if button is None:
            return
        self._delete_label = label
        self._delete_enabled = enabled
        button.setEnabled(enabled)
        button.setText(label)
        refresh_button_icon_for_state(
            button,
            _DELETE_ICON,
            variant=VARIANT_DANGER_OUTLINE,
            theme=theme,
        )

    def update_download_button(
        self,
        *,
        enabled: bool,
        theme: str | None = None,
    ) -> None:
        self._download_enabled = enabled
        update_outline_action_button(
            self.download_button,
            enabled=enabled,
            icon_name=_DOWNLOAD_ICON,
            enabled_variant=VARIANT_PRIMARY_OUTLINE,
            theme=theme,
        )

    def _on_theme_changed(self, theme: str) -> None:
        self.update_delete_button(
            label=self._delete_label,
            enabled=self._delete_enabled,
            theme=theme,
        )
        self.update_download_button(enabled=self._download_enabled, theme=theme)
