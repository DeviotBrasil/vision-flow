"""Decoração de janelas modais nativas do Windows."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog


def apply_native_dialog_flags(dialog: QDialog) -> None:
    """Modal com barra de título e botões nativos do Windows."""
    dialog.setWindowFlags(
        Qt.WindowType.Dialog
        | Qt.WindowType.WindowTitleHint
        | Qt.WindowType.WindowCloseButtonHint
        | Qt.WindowType.WindowSystemMenuHint
    )
