"""Ações compartilhadas de captura (popup de detalhe e edição)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QDialog, QWidget

from visionflow.domain.entities.capture import Capture
from visionflow.domain.use_cases.captures import CaptureService
from visionflow.presentation.widgets.capture_crop_dialog import CaptureCropDialog
from visionflow.presentation.widgets.capture_detail_dialog import (
    CaptureDetailDialog,
)
from visionflow.presentation.widgets.capture_resize_dialog import (
    CaptureResizeDialog,
)


def show_capture_crop(
    parent: QWidget,
    capture_service: CaptureService,
    capture: Capture,
) -> bool:
    """Abre o diálogo de recorte. Retorna ``True`` se a edição foi salva."""
    dialog = CaptureCropDialog(capture, capture_service, parent)
    return dialog.exec() == QDialog.DialogCode.Accepted


def show_capture_resize(
    parent: QWidget,
    capture_service: CaptureService,
    capture: Capture,
) -> bool:
    """Abre o diálogo de redimensionamento. Retorna ``True`` se a edição foi salva."""
    dialog = CaptureResizeDialog(capture, capture_service, parent)
    return dialog.exec() == QDialog.DialogCode.Accepted


def show_capture_detail(
    parent: QWidget,
    capture_service: CaptureService,
    capture_id: int,
    on_deleted: Callable[[], None] | None = None,
    on_edited: Callable[[], None] | None = None,
) -> None:
    """Abre o popup de detalhe; exclui ou edita via serviço."""
    capture = capture_service.get(capture_id)
    if capture is None:
        return
    dialog = CaptureDetailDialog(capture, parent)

    def handle_delete(cid: int) -> None:
        if capture_service.delete(cid) and on_deleted is not None:
            on_deleted()

    def handle_crop(_cid: int) -> None:
        if show_capture_crop(parent, capture_service, capture):
            if on_edited is not None:
                on_edited()
            dialog.accept()

    def handle_resize(_cid: int) -> None:
        if show_capture_resize(parent, capture_service, capture):
            if on_edited is not None:
                on_edited()
            dialog.accept()

    dialog.delete_requested.connect(handle_delete)
    dialog.crop_requested.connect(handle_crop)
    dialog.resize_requested.connect(handle_resize)
    dialog.exec()
