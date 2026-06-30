"""Barra de filtros rápidos por data (Hoje, Ontem, …)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget

from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_NEUTRAL_OUTLINE,
    create_button,
)


class QuickDateFilterBar(QWidget):
    """Botões de preset de data com seleção exclusiva."""

    def __init__(
        self,
        presets: tuple[tuple[str, str], ...],
        *,
        default_preset: str | None = None,
        on_preset_clicked: Callable[[str], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        self._on_preset_clicked = on_preset_clicked

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for preset_id, label in presets:
            button = create_button(
                label,
                variant=VARIANT_NEUTRAL_OUTLINE,
                shape=SHAPE_PILL,
                checkable=True,
            )
            if preset_id == default_preset:
                button.setChecked(True)
            button.clicked.connect(
                lambda _checked, preset=preset_id: self._handle_click(preset)
            )
            self._group.addButton(button)
            self._buttons[preset_id] = button
            layout.addWidget(button)

    def _handle_click(self, preset: str) -> None:
        button = self._buttons[preset]
        if not button.isChecked():
            return
        if self._on_preset_clicked is not None:
            self._on_preset_clicked(preset)

    def clear_selection(self) -> None:
        if not self._buttons:
            return
        self._group.setExclusive(False)
        for button in self._buttons.values():
            button.blockSignals(True)
            button.setChecked(False)
            button.blockSignals(False)
        self._group.setExclusive(True)
