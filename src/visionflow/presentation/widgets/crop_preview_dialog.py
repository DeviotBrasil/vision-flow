"""Popup de visualização do resultado de um recorte antes de salvar."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QShowEvent
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QWidget

from visionflow.presentation.preview_size_utils import (
    DIALOG_ACTIONS_SPACING,
    DIALOG_MIN_HEIGHT,
    DIALOG_MIN_WIDTH,
    build_fixed_preview_label,
    build_preview_dialog_root,
    finalize_preview_dialog_size,
)
from visionflow.presentation.system_dialogs import apply_dialog_theme
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_NEUTRAL_OUTLINE,
    create_button,
)
from visionflow.presentation.widgets.capture_edit_common import apply_dialog_shell


class CropPreviewDialog(QDialog):
    """Exibe a imagem recortada em popup modal antes de confirmar o salvamento."""

    def __init__(
        self,
        image: QImage,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._image = image
        self._preview_pixmap = QPixmap.fromImage(image)

        apply_dialog_shell(
            self,
            object_name="capture_edit_preview_dialog",
            title="Visualizar recorte",
            min_width=DIALOG_MIN_WIDTH,
            min_height=DIALOG_MIN_HEIGHT,
        )

        root = build_preview_dialog_root()
        self.setLayout(root)

        subtitle = QLabel(self._subtitle_text())
        subtitle.setObjectName("capture_edit_subtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        preview, content_size = build_fixed_preview_label(
            self._preview_pixmap,
            object_name="capture_edit_preview",
        )
        root.addWidget(preview, alignment=Qt.AlignmentFlag.AlignCenter)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(DIALOG_ACTIONS_SPACING)
        actions.addStretch()
        close_btn = create_button(
            "Fechar",
            variant=VARIANT_NEUTRAL_OUTLINE,
            shape=SHAPE_PILL,
        )
        close_btn.clicked.connect(self.accept)
        actions.addWidget(close_btn)
        root.addLayout(actions)

        finalize_preview_dialog_size(self, subtitle, content_size, actions)
        apply_dialog_theme(self)

    def showEvent(self, event: QShowEvent) -> None:
        apply_dialog_theme(self)
        super().showEvent(event)

    def _subtitle_text(self) -> str:
        w = self._image.width()
        h = self._image.height()
        return f"Resultado do recorte: {w} × {h} px"
