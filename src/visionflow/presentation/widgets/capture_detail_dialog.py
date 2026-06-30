"""Popup nativo de detalhe de uma captura (visualizar, baixar, editar, excluir)."""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from visionflow.domain.entities.capture import Capture
from visionflow.presentation.format_utils import format_captured_at
from visionflow.presentation.icon_colors import DANGER, INFO, icon_role_color
from visionflow.presentation.icon_sizes import TOOLBAR_ICON
from visionflow.presentation.icon_utils import tinted_icon
from visionflow.presentation.preview_size_utils import (
    DIALOG_ACTIONS_SPACING,
    DIALOG_BODY_PAD,
    STANDARD_PREVIEW_LIMITS,
    PreviewDialogLayout,
    build_fixed_preview_label,
    build_preview_dialog_root,
    finalize_preview_dialog_size,
    load_scaled_preview_pixmap,
)
from visionflow.presentation.system_dialogs import (
    apply_dialog_theme,
    save_file_path,
)
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_DANGER_OUTLINE,
    VARIANT_PRIMARY_OUTLINE,
    create_button,
)
from visionflow.presentation.window_chrome import apply_native_dialog_flags


class CaptureDetailDialog(QDialog):
    """Detalhe de captura em janela popup nativa do Windows."""

    delete_requested = Signal(int)
    crop_requested = Signal(int)
    resize_requested = Signal(int)

    def __init__(self, capture: Capture, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._capture = capture
        self._capture_id = int(capture.id)
        self._preview_pixmap = load_scaled_preview_pixmap(
            str(capture.file_path or ""),
            STANDARD_PREVIEW_LIMITS,
        )

        apply_native_dialog_flags(self)
        self.setObjectName("capture_detail_dialog")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setModal(True)
        self.setWindowTitle(self._header_title())

        root = build_preview_dialog_root(
            body_pad=DIALOG_BODY_PAD,
            actions_spacing=DIALOG_ACTIONS_SPACING,
        )
        self.setLayout(root)

        subtitle = QLabel(self._header_subtitle())
        subtitle.setObjectName("capture_detail_subtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        preview, content_size = build_fixed_preview_label(
            self._preview_pixmap,
            object_name="capture_detail_preview",
        )
        root.addWidget(preview, alignment=Qt.AlignmentFlag.AlignCenter)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(DIALOG_ACTIONS_SPACING)
        actions.addStretch()

        edit_enabled = not self._preview_pixmap.isNull()

        crop = create_button(
            "Recortar",
            variant=VARIANT_PRIMARY_OUTLINE,
            shape=SHAPE_PILL,
            icon=tinted_icon("icon_crop.svg", icon_role_color(INFO), TOOLBAR_ICON),
        )
        crop.setEnabled(edit_enabled)
        crop.clicked.connect(self._on_crop)
        actions.addWidget(crop)

        resize = create_button(
            "Redimensionar",
            variant=VARIANT_PRIMARY_OUTLINE,
            shape=SHAPE_PILL,
            icon=tinted_icon("icon_resize.svg", icon_role_color(INFO), TOOLBAR_ICON),
        )
        resize.setEnabled(edit_enabled)
        resize.clicked.connect(self._on_resize)
        actions.addWidget(resize)

        download = create_button(
            "Salvar",
            variant=VARIANT_PRIMARY_OUTLINE,
            shape=SHAPE_PILL,
            icon=tinted_icon("icon_download.svg", icon_role_color(INFO), TOOLBAR_ICON),
        )
        download.clicked.connect(self._on_download)
        actions.addWidget(download)

        delete = create_button(
            "Excluir",
            variant=VARIANT_DANGER_OUTLINE,
            shape=SHAPE_PILL,
            icon=tinted_icon("icon_trash.svg", icon_role_color(DANGER), TOOLBAR_ICON),
        )
        delete.clicked.connect(self._on_delete)
        actions.addWidget(delete)

        root.addLayout(actions)
        finalize_preview_dialog_size(
            self,
            subtitle,
            content_size,
            actions,
            PreviewDialogLayout(
                body_pad=DIALOG_BODY_PAD,
                actions_spacing=DIALOG_ACTIONS_SPACING,
            ),
        )
        apply_dialog_theme(self)

    def showEvent(self, event: QShowEvent) -> None:
        apply_dialog_theme(self)
        super().showEvent(event)

    def _header_title(self) -> str:
        file_name = Path(self._capture.file_path or "").name
        if file_name:
            return f"{self._capture_id} - {file_name}"
        return str(self._capture_id)

    def _header_subtitle(self) -> str:
        captured_at = self._capture.captured_at or ""
        if not captured_at:
            return ""
        return format_captured_at(str(captured_at)) or str(captured_at)

    def _on_download(self) -> None:
        source = self._capture.file_path or ""
        if not source or not Path(source).is_file():
            return
        suffix = Path(source).suffix or ".jpg"
        suggested = f"captura_{self._capture_id:03d}{suffix}"
        target = save_file_path(
            self,
            "Salvar captura",
            suggested,
            f"Imagem (*{suffix});;Todos (*.*)",
        )
        if target:
            shutil.copyfile(source, target)

    def _on_crop(self) -> None:
        self.crop_requested.emit(self._capture_id)

    def _on_resize(self) -> None:
        self.resize_requested.emit(self._capture_id)

    def _on_delete(self) -> None:
        self.delete_requested.emit(self._capture_id)
        self.accept()
