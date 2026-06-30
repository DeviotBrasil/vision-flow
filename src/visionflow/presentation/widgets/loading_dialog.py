"""Diálogo modal de carregamento (bloqueia interação durante jobs pesados)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from visionflow.presentation.system_dialogs import apply_dialog_theme


class LoadingDialog(QDialog):
    """Popup modal sem botão fechar; barra de progresso indeterminada ou por etapas."""

    def __init__(
        self,
        parent: QWidget | None,
        message: str,
        *,
        total: int | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("visionflow_loading_dialog")
        self.setWindowTitle("Aguarde")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.CustomizeWindowHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        self._message_label = QLabel(message)
        self._message_label.setObjectName("loading_dialog_message")
        self._message_label.setWordWrap(True)
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._message_label)

        self._status_label = QLabel()
        self._status_label.setObjectName("loading_dialog_status")
        self._status_label.setWordWrap(True)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.hide()
        layout.addWidget(self._status_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("loading_dialog_progress")
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        layout.addWidget(self._progress_bar)

        self.setFixedWidth(420)
        apply_dialog_theme(self)

        if total is not None and total > 0:
            self.set_progress(0, total)
            self.set_status(f"0 de {total}")
        else:
            self._progress_bar.setRange(0, 0)

    def set_message(self, message: str) -> None:
        self._message_label.setText(message)

    def set_status(self, status: str) -> None:
        if status:
            self._status_label.setText(status)
            self._status_label.show()
        else:
            self._status_label.hide()

    def set_progress(self, current: int, total: int) -> None:
        if total <= 0:
            self._progress_bar.setRange(0, 0)
            return
        self._progress_bar.setRange(0, total)
        self._progress_bar.setValue(min(current, total))

    def apply_progress(
        self,
        current: int,
        total: int,
        *,
        message: str | None = None,
        status: str | None = None,
    ) -> None:
        if message is not None:
            self.set_message(message)
        if status is not None:
            self.set_status(status)
        self.set_progress(current, total)

    @classmethod
    def show_blocking(
        cls,
        parent: QWidget | None,
        message: str,
        *,
        total: int | None = None,
    ) -> LoadingDialog:
        """Exibe o diálogo e repinta a UI antes do job iniciar."""
        dialog = cls(parent, message, total=total)
        dialog.show()
        QApplication.processEvents()
        return dialog

    @classmethod
    def repaint_visible(cls) -> None:
        """Repinta diálogos de carregamento abertos (durante jobs na UI thread)."""
        app = QApplication.instance()
        if app is None:
            return
        for widget in app.topLevelWidgets():
            if isinstance(widget, LoadingDialog) and widget.isVisible():
                widget.repaint()
