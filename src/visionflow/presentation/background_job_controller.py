"""Cursor de aguarde e popup modal para jobs pesados na thread da UI."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from visionflow.presentation.widgets.loading_dialog import LoadingDialog


class BackgroundJobController:
    """Reserva um job por vez na thread principal (importar, excluir, exportar ZIP)."""

    def __init__(
        self,
        parent: QWidget,
        *,
        on_busy: Callable[[bool], None] | None = None,
    ) -> None:
        self._parent = parent
        self._on_busy = on_busy
        self._busy = False
        self._loading_dialog: LoadingDialog | None = None
        self._closing = False

    @property
    def is_running(self) -> bool:
        return self._busy

    def begin(
        self,
        *,
        loading_message: str | None = None,
        total: int | None = None,
    ) -> bool:
        """Reserva o slot de job; retorna ``False`` se já houver um ativo."""
        if self._busy or self._closing:
            return False
        if loading_message:
            parent = self._parent.window() if self._parent is not None else None
            self._loading_dialog = LoadingDialog.show_blocking(
                parent,
                loading_message,
                total=total,
            )
        self._set_busy(True)
        return True

    def update_loading(
        self,
        current: int,
        total: int,
        *,
        message: str | None = None,
        status: str | None = None,
    ) -> None:
        """Atualiza mensagem e barra do popup de aguarde."""
        dialog = self._loading_dialog
        if dialog is not None:
            dialog.apply_progress(
                current,
                total,
                message=message,
                status=status,
            )

    def end_busy(self) -> None:
        """Libera cursor, fecha popup e reabilita ações da UI."""
        self._close_loading_dialog()
        self._set_busy(False)

    def shutdown(self) -> None:
        """Libera recursos ao fechar a tela ou o app."""
        self._closing = True
        self._close_loading_dialog()
        self._set_busy(False)

    def _close_loading_dialog(self) -> None:
        dialog = self._loading_dialog
        if dialog is not None:
            dialog.close()
            dialog.deleteLater()
            self._loading_dialog = None

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()
        if self._on_busy is not None:
            self._on_busy(not busy)
