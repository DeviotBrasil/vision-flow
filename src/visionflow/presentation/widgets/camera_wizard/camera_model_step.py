"""Etapa 1 do wizard — seleção de modelo/backend."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout

from visionflow.domain.camera_backends import (
    BACKEND_OPT,
    BACKEND_ORDER,
    BACKEND_REGISTRY,
    BackendDescriptor,
    get_backend_descriptor,
)
from visionflow.presentation.icon_colors import INFO, icon_role_color
from visionflow.presentation.icon_sizes import INFO_ICON
from visionflow.presentation.icon_utils import tinted_pixmap
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_PRIMARY,
    button_row,
    create_button,
)
from visionflow.presentation.widgets.camera_wizard.step_container import (
    build_step_container,
)

_OPT_SDK_UNAVAILABLE = (
    "SDK OPT indisponível. Execute: python scripts/sync_opt_runtime.py"
)


class CameraModelStep(QFrame):
    """Combo de backend, card informativo e botão Próximo."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        page, column, _ = build_step_container(
            "Etapa 1 — Seleção de Modelo",
            "Selecione o fabricante e modelo da câmera industrial.",
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(page)

        field_label = QLabel("MODELO DE CÂMERA")
        field_label.setObjectName("field_label")
        column.addWidget(field_label)

        self.model_combo = QComboBox()
        self.model_combo.setObjectName("model_combo")
        self.model_combo.setPlaceholderText("Selecione um modelo...")
        for index, backend_id in enumerate(BACKEND_ORDER):
            descriptor = BACKEND_REGISTRY[backend_id]
            self.model_combo.addItem(descriptor.label)
            self.model_combo.setItemData(index, backend_id, Qt.ItemDataRole.UserRole)
        self.model_combo.setCurrentIndex(-1)
        column.addWidget(self.model_combo)

        self.info_card = self._build_info_card()
        column.addWidget(self.info_card)

        footer = button_row()
        self.model_next = create_button(
            "Próximo",
            variant=VARIANT_PRIMARY,
            shape=SHAPE_PILL,
            icon_name="icon_chevron_right.svg",
        )
        self.model_next.setEnabled(False)
        footer.addWidget(self.model_next)
        column.addLayout(footer)

    def _build_info_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("info_card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        icon = QLabel()
        icon.setObjectName("info_card_icon")
        icon.setPixmap(tinted_pixmap("icon_info.svg", icon_role_color(INFO), INFO_ICON))
        icon.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(icon)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(4)
        self.info_card_title = QLabel("OPT Machine Vision")
        self.info_card_title.setObjectName("info_card_title")
        self.info_card_desc = QLabel(
            "Suporte a câmeras GigE Vision e USB3 Vision. SDK compatível com GenICam."
        )
        self.info_card_desc.setObjectName("info_card_desc")
        self.info_card_desc.setWordWrap(True)
        text_column.addWidget(self.info_card_title)
        text_column.addWidget(self.info_card_desc)
        layout.addLayout(text_column, 1)
        return card

    def selected_backend(self) -> str:
        index = self.model_combo.currentIndex()
        if index < 0:
            return BACKEND_OPT
        backend = self.model_combo.itemData(index, Qt.ItemDataRole.UserRole)
        return str(backend) if backend else BACKEND_OPT

    def update_info_card(self, backend: str, *, backend_available: bool) -> None:
        descriptor = get_backend_descriptor(backend)
        if descriptor is None:
            descriptor = BACKEND_REGISTRY[BACKEND_OPT]
        title = descriptor.wizard_info_title
        desc = descriptor.wizard_info_description
        if backend == BACKEND_OPT and not backend_available:
            desc = _OPT_SDK_UNAVAILABLE
        self.info_card_title.setText(title)
        self.info_card_desc.setText(desc)

    def descriptor_for_selected(self) -> BackendDescriptor | None:
        return get_backend_descriptor(self.selected_backend())
