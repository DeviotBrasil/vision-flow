"""Etapa 3 do wizard — conexão, preview e salvar configuração."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from visionflow.presentation.icon_colors import SUCCESS, icon_role_color
from visionflow.presentation.icon_sizes import INFO_ICON
from visionflow.presentation.icon_utils import tinted_pixmap
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_PRIMARY,
    VARIANT_SECONDARY,
    button_row,
    create_button,
)
from visionflow.presentation.widgets.camera_preview import CameraPreview
from visionflow.presentation.widgets.camera_wizard.step_container import (
    build_step_container,
)
from visionflow.presentation.widgets.metadata_chips import MetadataChips


class CameraConnectionStep:
    """Etapa de conexão e teste ao vivo."""

    def __init__(self) -> None:
        page, column, _ = build_step_container(
            "Etapa 3 — Conexão e Teste",
            "Conecte-se ao dispositivo e verifique o preview ao vivo.",
        )
        self.widget = page

        connect_row = button_row(align_left=True)
        self.connect_button = create_button(
            "Conectar e Testar",
            variant=VARIANT_PRIMARY,
            shape=SHAPE_PILL,
            icon_name="icon_play.svg",
        )
        connect_row.addWidget(self.connect_button)
        column.addLayout(connect_row)

        self.success_banner = QFrame()
        self.success_banner.setObjectName("success_banner")
        banner_layout = QHBoxLayout(self.success_banner)
        banner_layout.setContentsMargins(0, 0, 0, 0)
        banner_layout.setSpacing(8)
        banner_icon = QLabel()
        banner_icon.setObjectName("success_banner_icon")
        banner_icon.setPixmap(
            tinted_pixmap("icon_check.svg", icon_role_color(SUCCESS), INFO_ICON)
        )
        banner_text = QLabel("Conexão estabelecida com sucesso.")
        banner_text.setObjectName("success_banner_text")
        banner_layout.addWidget(banner_icon)
        banner_layout.addWidget(banner_text)
        banner_layout.addStretch()
        self.success_banner.setVisible(False)
        column.addWidget(self.success_banner)

        preview_block = QFrame()
        preview_block.setObjectName("camera_preview_block")
        preview_block.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        preview_layout = QVBoxLayout(preview_block)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(10)

        self.preview = CameraPreview()
        self.preview.setMinimumHeight(320)
        self.preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        preview_layout.addWidget(self.preview)

        self.chips = MetadataChips()
        preview_layout.addWidget(self.chips)
        column.addWidget(preview_block)

        footer = button_row()
        self.back_button = create_button(
            "Voltar", variant=VARIANT_SECONDARY, shape=SHAPE_PILL
        )
        footer.addWidget(self.back_button)

        self.cancel_button = create_button(
            "Cancelar", variant=VARIANT_SECONDARY, shape=SHAPE_PILL
        )
        footer.addWidget(self.cancel_button)

        self.save_button = create_button(
            "Salvar",
            variant=VARIANT_PRIMARY,
            shape=SHAPE_PILL,
            icon_name="icon_check.svg",
        )
        self.save_button.setEnabled(False)
        footer.addWidget(self.save_button)
        column.addLayout(footer)

    def reset_ui(self) -> None:
        self.success_banner.setVisible(False)
        self.save_button.setEnabled(False)
        self.connect_button.setEnabled(True)
        self.preview.clear_frame()
        self.chips.clear()
