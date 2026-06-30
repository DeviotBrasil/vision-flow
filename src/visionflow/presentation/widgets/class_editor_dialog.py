"""Diálogo temático para criar/editar uma classe (nome + cor)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QShowEvent
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from visionflow.presentation.preview_size_utils import (
    DIALOG_ACTIONS_SPACING,
    DIALOG_BODY_PAD,
)
from visionflow.presentation.system_dialogs import apply_dialog_theme
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_NEUTRAL_OUTLINE,
    VARIANT_PRIMARY,
    create_button,
)
from visionflow.presentation.window_chrome import apply_native_dialog_flags

_DIALOG_MIN_WIDTH = 420
_DEFAULT_COLOR = "#0066CC"
_MID_LIGHTNESS = 128


class ClassEditorDialog(QDialog):
    """Coleta nome e cor de uma classe do dataset."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        name: str = "",
        color: str = _DEFAULT_COLOR,
    ) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        apply_native_dialog_flags(self)
        self.setObjectName("class_editor_dialog")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setMinimumWidth(_DIALOG_MIN_WIDTH)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            DIALOG_BODY_PAD, DIALOG_BODY_PAD, DIALOG_BODY_PAD, DIALOG_BODY_PAD
        )
        root.setSpacing(DIALOG_ACTIONS_SPACING)

        name_label = QLabel("Nome da classe")
        name_label.setObjectName("capture_edit_field_label")
        root.addWidget(name_label)
        self._name_field = QLineEdit(name)
        self._name_field.setObjectName("text_input_field")
        self._name_field.returnPressed.connect(self.accept)
        root.addWidget(self._name_field)

        color_label = QLabel("Cor")
        color_label.setObjectName("capture_edit_field_label")
        root.addWidget(color_label)
        self._color_button = QPushButton("Escolher cor…")
        self._color_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color_button.clicked.connect(self._on_pick_color)
        root.addWidget(self._color_button)
        self._apply_color_button_style()

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(DIALOG_ACTIONS_SPACING)
        cancel = create_button(
            "Cancelar", variant=VARIANT_NEUTRAL_OUTLINE, shape=SHAPE_PILL
        )
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        actions.addStretch()
        confirm = create_button("Salvar", variant=VARIANT_PRIMARY, shape=SHAPE_PILL)
        confirm.clicked.connect(self.accept)
        actions.addWidget(confirm)
        root.addLayout(actions)

    def class_name(self) -> str:
        return self._name_field.text().strip()

    def color_hex(self) -> str:
        return self._color.name()

    def showEvent(self, event: QShowEvent) -> None:
        apply_dialog_theme(self)
        self._apply_color_button_style()
        super().showEvent(event)

    def _on_pick_color(self) -> None:
        chosen = QColorDialog.getColor(self._color, self, "Cor da classe")
        if chosen.isValid():
            self._color = chosen
            self._apply_color_button_style()

    def _apply_color_button_style(self) -> None:
        hex_color = self._color.name()
        light = self._color.lightness() >= _MID_LIGHTNESS
        text_color = "#1D1D1F" if light else "#FFFFFF"
        self._color_button.setStyleSheet(
            f"background-color: {hex_color}; color: {text_color};"
            "border: none; border-radius: 6px; padding: 6px;"
        )
        self._color_button.setText(f"Escolher cor…  ({hex_color})")
