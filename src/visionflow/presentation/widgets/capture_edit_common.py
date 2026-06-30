"""Utilitários compartilhados pelos diálogos de edição de captura."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QShowEvent
from PySide6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QVBoxLayout

from visionflow.domain.entities.capture import Capture
from visionflow.domain.use_cases.captures import CaptureService
from visionflow.presentation.image_utils import qimage_to_ndarray
from visionflow.presentation.preview_size_utils import (
    DIALOG_ACTIONS_SPACING,
    DIALOG_BODY_PAD,
)
from visionflow.presentation.system_dialogs import (
    apply_dialog_theme,
    confirm_replace_capture,
    show_info_message,
)
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_NEUTRAL_OUTLINE,
    VARIANT_PRIMARY,
    VARIANT_PRIMARY_OUTLINE,
    create_button,
)
from visionflow.presentation.window_chrome import apply_native_dialog_flags

EDIT_DIALOG_BODY_PAD = DIALOG_BODY_PAD
EDIT_DIALOG_SPACING = DIALOG_ACTIONS_SPACING
EDIT_DIALOG_MIN_WIDTH = 560
EDIT_DIALOG_MIN_HEIGHT = 520


class CaptureEditDialogBase(QDialog):
    """Base modal para diálogos de recorte e redimensionamento."""

    def showEvent(self, event: QShowEvent) -> None:
        apply_dialog_theme(self)
        super().showEvent(event)


def build_edit_dialog_root() -> QVBoxLayout:
    root = QVBoxLayout()
    root.setContentsMargins(
        EDIT_DIALOG_BODY_PAD,
        EDIT_DIALOG_BODY_PAD,
        EDIT_DIALOG_BODY_PAD,
        EDIT_DIALOG_BODY_PAD,
    )
    root.setSpacing(EDIT_DIALOG_SPACING)
    return root


def edit_subtitle_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("capture_edit_subtitle")
    label.setWordWrap(True)
    return label


def configure_edit_form(form: QFormLayout) -> None:
    """Alinha rótulos e campos ao centro vertical de cada linha."""
    form.setContentsMargins(0, 0, 0, 0)
    form.setHorizontalSpacing(12)
    form.setVerticalSpacing(6)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)


def edit_form_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("capture_edit_field_label")
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return label


def load_capture_image(capture: Capture) -> QImage:
    source = capture.file_path or ""
    if not source or not Path(source).is_file():
        return QImage()
    image = QImage(str(source))
    return image if not image.isNull() else QImage()


def dimensions_subtitle(image: QImage) -> str:
    if image.isNull():
        return "Imagem indisponível para edição."
    return f"Dimensões atuais: {image.width()} × {image.height()} px"


def frame_from_qimage(image: QImage) -> np.ndarray | None:
    if image.isNull():
        return None
    try:
        return qimage_to_ndarray(image)
    except ValueError:
        return None


def replace_capture(
    dialog: QDialog,
    capture_service: CaptureService,
    capture: Capture,
    frame: np.ndarray,
) -> bool:
    capture_id = int(capture.id or 0)
    if not confirm_replace_capture(dialog):
        return False
    result = capture_service.replace_image(capture_id, frame)
    if result is None:
        show_info_message(
            dialog,
            "Editar captura",
            "Não foi possível atualizar a captura. Verifique os logs.",
        )
        return False
    return True


def save_capture_as_new(
    dialog: QDialog,
    capture_service: CaptureService,
    capture: Capture,
    frame: np.ndarray,
) -> bool:
    result = capture_service.save_edited_from_source(capture, frame)
    if result is None:
        show_info_message(
            dialog,
            "Editar captura",
            "Não foi possível salvar a nova captura. Verifique os logs.",
        )
        return False
    return True


def accept_if_saved(
    dialog: QDialog,
    *,
    title: str,
    frame: np.ndarray | None,
    unavailable_message: str,
    save: Callable[[np.ndarray], bool],
) -> None:
    """Valida o frame editado e fecha o diálogo se o salvamento for bem-sucedido."""
    if frame is None:
        show_info_message(dialog, title, unavailable_message)
        return
    if save(frame):
        dialog.accept()


def build_save_actions(
    dialog: QDialog,
    *,
    on_replace: Callable[[], None],
    on_save_new: Callable[[], None],
) -> QHBoxLayout:
    actions = QHBoxLayout()
    actions.setContentsMargins(0, 0, 0, 0)
    actions.setSpacing(EDIT_DIALOG_SPACING)

    cancel = create_button(
        "Cancelar",
        variant=VARIANT_NEUTRAL_OUTLINE,
        shape=SHAPE_PILL,
    )
    cancel.clicked.connect(dialog.reject)
    actions.addWidget(cancel)
    actions.addStretch()

    replace_btn = create_button(
        "Atualizar captura",
        variant=VARIANT_PRIMARY,
        shape=SHAPE_PILL,
    )
    replace_btn.clicked.connect(on_replace)
    actions.addWidget(replace_btn)

    save_new = create_button(
        "Gerar nova captura",
        variant=VARIANT_PRIMARY_OUTLINE,
        shape=SHAPE_PILL,
    )
    save_new.clicked.connect(on_save_new)
    actions.addWidget(save_new)
    return actions


def apply_dialog_shell(
    dialog: QDialog,
    *,
    object_name: str,
    title: str,
    min_width: int,
    min_height: int,
) -> None:
    apply_native_dialog_flags(dialog)
    dialog.setObjectName(object_name)
    dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    dialog.setModal(True)
    dialog.setWindowTitle(title)
    dialog.setMinimumSize(min_width, min_height)
