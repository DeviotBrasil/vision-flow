"""Diálogo temático simples para entrada de uma linha de texto."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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


class _TextInputDialog(QDialog):
    """Coleta uma linha de texto com OK/Cancelar e tema aplicado."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        label: str,
        initial: str,
    ) -> None:
        super().__init__(parent)
        apply_native_dialog_flags(self)
        self.setObjectName("text_input_dialog")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setMinimumWidth(_DIALOG_MIN_WIDTH)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            DIALOG_BODY_PAD, DIALOG_BODY_PAD, DIALOG_BODY_PAD, DIALOG_BODY_PAD
        )
        root.setSpacing(DIALOG_ACTIONS_SPACING)

        prompt = QLabel(label)
        prompt.setObjectName("capture_edit_field_label")
        prompt.setWordWrap(True)
        root.addWidget(prompt)

        self._field = QLineEdit(initial)
        self._field.setObjectName("text_input_field")
        self._field.selectAll()
        self._field.returnPressed.connect(self.accept)
        root.addWidget(self._field)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(DIALOG_ACTIONS_SPACING)
        cancel = create_button(
            "Cancelar", variant=VARIANT_NEUTRAL_OUTLINE, shape=SHAPE_PILL
        )
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        actions.addStretch()
        confirm = create_button("OK", variant=VARIANT_PRIMARY, shape=SHAPE_PILL)
        confirm.clicked.connect(self.accept)
        actions.addWidget(confirm)
        root.addLayout(actions)

    def value(self) -> str:
        return self._field.text().strip()

    def showEvent(self, event: QShowEvent) -> None:
        apply_dialog_theme(self)
        super().showEvent(event)


def prompt_text(
    parent: QWidget | None,
    *,
    title: str,
    label: str,
    initial: str = "",
) -> str | None:
    """Exibe o diálogo e devolve o texto informado, ou ``None`` se cancelado."""
    dialog = _TextInputDialog(parent, title=title, label=label, initial=initial)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    value = dialog.value()
    return value or None
