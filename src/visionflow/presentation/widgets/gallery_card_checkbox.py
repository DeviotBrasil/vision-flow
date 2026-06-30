"""Checkbox de seleção no canto dos cards da galeria."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from visionflow.presentation.icon_utils import tinted_pixmap
from visionflow.presentation.style_utils import set_property

CHECKBOX_SIZE = 22
CHECKBOX_MARGIN = 6
_CHECK_ICON_SIZE = QSize(12, 12)


class GalleryCardCheckbox(QFrame):
    """Área clicável no canto superior direito do card."""

    toggled = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("gallery_card_checkbox")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(CHECKBOX_SIZE, CHECKBOX_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._check_icon = QLabel()
        self._check_icon.setPixmap(
            tinted_pixmap("icon_check.svg", "#FFFFFF", _CHECK_ICON_SIZE)
        )
        self._check_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._check_icon.hide()
        layout.addWidget(self._check_icon)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, checked: bool) -> None:
        if self._checked == checked:
            return
        self._checked = checked
        self._check_icon.setVisible(checked)
        set_property(self, "checked", "true" if checked else "false")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_checked(not self._checked)
            self.toggled.emit(self._checked)
            event.accept()
            return
        super().mousePressEvent(event)
