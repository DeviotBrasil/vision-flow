"""Campo numérico com steppers customizados (setas SVG, sem subcontroles QSS)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from visionflow.presentation.icon_colors import NEUTRAL, icon_role_color
from visionflow.presentation.icon_sizes import TOOLBAR_ICON
from visionflow.presentation.icon_utils import tinted_icon
from visionflow.presentation.themes.theme_manager import ThemeManager

_FIELD_HEIGHT = 34
_FIELD_HEIGHT_COMPACT = 28
_STEPPER_WIDTH = 22
_STEPPER_WIDTH_COMPACT = 20


class IntegerSpinField(QFrame):
    """``QSpinBox`` sem botões nativos e steppers laterais com ícones do tema."""

    valueChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None, *, compact: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("integer_spin_field")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if compact:
            self.setProperty("vfCompact", True)
            style = self.style()
            style.unpolish(self)
            style.polish(self)
        self._theme_connected = False

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self._spin = QSpinBox()
        self._spin.setObjectName("integer_spin_field_input")
        self._spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._spin.setFrame(False)
        line_edit = self._spin.lineEdit()
        if line_edit is not None:
            line_edit.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        self._spin.valueChanged.connect(self._emit_value_changed)
        row.addWidget(self._spin, 1, Qt.AlignmentFlag.AlignVCenter)

        self._stepper = QFrame()
        self._stepper.setObjectName("integer_spin_stepper")
        self._stepper.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        steps = QVBoxLayout(self._stepper)
        steps.setContentsMargins(0, 0, 0, 0)
        steps.setSpacing(0)

        self._up = QPushButton()
        self._up.setObjectName("integer_spin_step_up")
        self._up.setFlat(True)
        self._up.setCursor(Qt.CursorShape.PointingHandCursor)
        self._up.clicked.connect(self._spin.stepUp)

        self._down = QPushButton()
        self._down.setObjectName("integer_spin_step_down")
        self._down.setFlat(True)
        self._down.setCursor(Qt.CursorShape.PointingHandCursor)
        self._down.clicked.connect(self._spin.stepDown)

        steps.addWidget(self._up)
        steps.addWidget(self._down)
        row.addWidget(self._stepper, 0, Qt.AlignmentFlag.AlignVCenter)
        self._apply_size(compact)
        self._refresh_stepper_icons()

    def _apply_size(self, compact: bool) -> None:
        height = _FIELD_HEIGHT_COMPACT if compact else _FIELD_HEIGHT
        stepper_w = _STEPPER_WIDTH_COMPACT if compact else _STEPPER_WIDTH
        step_h = height // 2
        self.setFixedHeight(height)
        self._spin.setFixedHeight(height)
        self._stepper.setFixedSize(stepper_w, height)
        self._up.setFixedHeight(step_h)
        self._down.setFixedHeight(step_h)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._refresh_stepper_icons()
        self._connect_theme_manager()

    def _emit_value_changed(self, value: int) -> None:
        self.valueChanged.emit(value)

    def _theme_manager(self) -> ThemeManager | None:
        window = self.window()
        manager = getattr(window, "theme_manager", None)
        return manager if isinstance(manager, ThemeManager) else None

    def _connect_theme_manager(self) -> None:
        if self._theme_connected:
            return
        manager = self._theme_manager()
        if manager is None:
            return
        manager.theme_changed.connect(self._refresh_stepper_icons)
        self._theme_connected = True

    def _refresh_stepper_icons(self) -> None:
        icon_color = icon_role_color(NEUTRAL)
        self._up.setIcon(tinted_icon("icon_chevron_up.svg", icon_color, TOOLBAR_ICON))
        self._down.setIcon(
            tinted_icon("icon_chevron_down.svg", icon_color, TOOLBAR_ICON)
        )

    def value(self) -> int:
        return self._spin.value()

    def setValue(self, value: int) -> None:
        self._spin.setValue(value)

    def setRange(self, minimum: int, maximum: int) -> None:
        self._spin.setRange(minimum, maximum)

    def setSingleStep(self, step: int) -> None:
        self._spin.setSingleStep(step)

    def setMaximum(self, maximum: int) -> None:
        self._spin.setMaximum(maximum)

    def blockSignals(self, block: bool) -> bool:
        return self._spin.blockSignals(block)
