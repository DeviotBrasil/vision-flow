"""Etapa 2 do wizard — busca/importação de dispositivos."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy

from visionflow.domain.camera_backends import get_backend_descriptor
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_PRIMARY,
    VARIANT_SECONDARY,
    button_row,
    create_button,
    set_variant,
)
from visionflow.presentation.widgets.camera_wizard.step_container import (
    build_step_container,
)
from visionflow.presentation.widgets.device_table import DeviceTable

STATUS_IDLE = "Nenhuma busca realizada ainda."


class CameraDevicesStep:
    """Etapa de dispositivos (retorna o widget raiz e expõe controles)."""

    def __init__(self) -> None:
        page, column, self.subtitle = build_step_container(
            "Etapa 2 — Dispositivos",
            "Busque câmeras disponíveis e selecione um dispositivo.",
            full_width=True,
        )
        self.widget = page

        self.search_button = create_button(
            "Buscar Câmeras",
            variant=VARIANT_PRIMARY,
            shape=SHAPE_PILL,
            icon_name="icon_search.svg",
        )
        self.search_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(0)
        search_row.addWidget(self.search_button, 1)
        column.addLayout(search_row)

        self.device_table = DeviceTable()
        self.device_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        column.addWidget(self.device_table, 1)

        self.status_label = QLabel(STATUS_IDLE)
        self.status_label.setObjectName("wizard_status")
        column.addWidget(self.status_label)

        footer = button_row()
        self.back_button = create_button(
            "Voltar", variant=VARIANT_SECONDARY, shape=SHAPE_PILL
        )
        footer.addWidget(self.back_button)

        self.next_button = create_button(
            "Próximo",
            variant=VARIANT_PRIMARY,
            shape=SHAPE_PILL,
            icon_name="icon_chevron_right.svg",
        )
        self.next_button.setEnabled(False)
        footer.addWidget(self.next_button)
        column.addLayout(footer)

    def apply_backend_descriptor(self, backend: str) -> None:
        descriptor = get_backend_descriptor(backend)
        if descriptor is None:
            return
        self.subtitle.setText(descriptor.wizard_devices_subtitle)
        self.search_button.setText(descriptor.wizard_search_button_label)
        self.device_table.set_column_profile(descriptor.device_table_columns)
        icon = (
            "icon_folder.svg"
            if descriptor.discover_mode == "file_picker"
            else "icon_search.svg"
        )
        set_variant(self.search_button, VARIANT_PRIMARY, icon_name=icon)
