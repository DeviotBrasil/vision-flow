"""Tela Câmera — assistente (wizard) de configuração em 3 etapas."""

from __future__ import annotations

import logging
from typing import ClassVar

from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from visionflow.domain.camera_backends import BACKEND_OPT, BACKEND_VIDEO
from visionflow.domain.entities.device_info import DeviceInfo
from visionflow.domain.entities.discover_context import DiscoverContext
from visionflow.domain.use_cases.camera_config import CameraConfigService
from visionflow.presentation.camera_controller import (
    STATE_CONNECTED,
    STATE_CONNECTING,
    CameraController,
)
from visionflow.presentation.camera_feedback import (
    WizardErrorContext,
    apply_live_frame,
    report_wizard_camera_error,
)
from visionflow.presentation.system_dialogs import open_video_file_path
from visionflow.presentation.widgets.camera_wizard.camera_connection_step import (
    CameraConnectionStep,
)
from visionflow.presentation.widgets.camera_wizard.camera_devices_step import (
    STATUS_IDLE,
    CameraDevicesStep,
)
from visionflow.presentation.widgets.camera_wizard.camera_model_step import (
    CameraModelStep,
)
from visionflow.presentation.widgets.content_header import ContentHeader
from visionflow.presentation.widgets.stepper import Stepper
from visionflow.presentation.window_constraints import (
    SCREEN_WIZARD_STACK_MIN_HEIGHT,
)

_STEP_MODEL = 0
_STEP_DEVICES = 1
_STEP_CONNECTION = 2

_OPT_SDK_UNAVAILABLE = (
    "SDK OPT indisponível. Execute: python scripts/sync_opt_runtime.py"
)

_logger = logging.getLogger(__name__)


class CameraScreen(QWidget):
    """Wizard de configuração da câmera (Modelo → Dispositivos → Conexão)."""

    PAGE_ID: ClassVar[str] = "camera"
    TITLE: ClassVar[str] = "Câmera"

    def __init__(
        self,
        controller: CameraController,
        config_service: CameraConfigService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(f"{self.PAGE_ID}_screen")
        self._controller = controller
        self._config_service = config_service
        self._selected_device: DeviceInfo | None = None
        self._last_model_backend: str | None = None

        self._model_step = CameraModelStep()
        self._devices_step = CameraDevicesStep()
        self._connection_step = CameraConnectionStep()

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(24)

        root.addWidget(
            ContentHeader(
                "Configuração de Câmera",
                "Assistente de configuração de dispositivo de captura",
            )
        )

        self._stepper = Stepper(["Modelo", "Dispositivos", "Conexão"])
        root.addWidget(self._stepper)

        self._stack = QStackedWidget()
        self._stack.setObjectName("wizard_body")
        self._stack.addWidget(self._model_step)
        self._stack.addWidget(self._devices_step.widget)
        self._stack.addWidget(self._connection_step.widget)
        self._stack.setMinimumHeight(SCREEN_WIZARD_STACK_MIN_HEIGHT)
        root.addWidget(self._stack, 1)

        self._wire_wizard()
        self._connect_controller()

    def _wire_wizard(self) -> None:
        self._model_step.model_combo.currentIndexChanged.connect(self._on_model_changed)
        self._model_step.model_next.clicked.connect(
            lambda: self._go_to_step(_STEP_DEVICES)
        )
        self._devices_step.search_button.clicked.connect(
            self._on_devices_action_clicked
        )
        self._devices_step.device_table.selection_changed.connect(
            self._on_device_selected
        )
        self._devices_step.back_button.clicked.connect(self._on_back_to_model)
        self._devices_step.next_button.clicked.connect(
            lambda: self._go_to_step(_STEP_CONNECTION)
        )
        self._connection_step.connect_button.clicked.connect(self._on_connect_clicked)
        self._connection_step.back_button.clicked.connect(self._on_back_from_connection)
        self._connection_step.cancel_button.clicked.connect(self._on_cancel)
        self._connection_step.save_button.clicked.connect(self._on_save)

    def reset_wizard_entry(self) -> None:
        """Reinicia o assistente na etapa 1 (ao abrir a tela Câmera)."""
        if self._controller.state in (STATE_CONNECTED, STATE_CONNECTING):
            self._controller.stop_live()
            self._controller.disconnect()
        self._selected_device = None
        self._last_model_backend = None
        self._devices_step.next_button.setEnabled(False)
        self._devices_step.device_table.set_devices([])
        self._devices_step.status_label.setText(STATUS_IDLE)
        self._connection_step.reset_ui()
        self._go_to_step(_STEP_MODEL)

    def _selected_backend(self) -> str:
        return self._model_step.selected_backend()

    def _on_model_changed(self, index: int) -> None:
        if index < 0:
            self._model_step.model_next.setEnabled(False)
            self._last_model_backend = None
            return

        backend = self._selected_backend()
        if self._last_model_backend is not None and backend != self._last_model_backend:
            if self._controller.state in (STATE_CONNECTED, STATE_CONNECTING):
                self._controller.stop_live()
                self._controller.disconnect()
            self._clear_devices_step()

        self._last_model_backend = backend
        self._model_step.update_info_card(
            backend,
            backend_available=self._controller.is_backend_available(backend),
        )
        self._refresh_model_step_actions()
        self._devices_step.apply_backend_descriptor(backend)

    def _refresh_model_step_actions(self) -> None:
        backend = self._selected_backend()
        self._model_step.model_next.setEnabled(
            self._controller.is_backend_available(backend)
        )

    def _clear_devices_step(self) -> None:
        self._selected_device = None
        self._devices_step.next_button.setEnabled(False)
        self._devices_step.device_table.set_devices([])
        self._devices_step.status_label.setText(STATUS_IDLE)

    def _refresh_devices_step_actions(self) -> None:
        backend = self._selected_backend()
        descriptor = self._model_step.descriptor_for_selected()
        if descriptor is not None and descriptor.discover_mode == "file_picker":
            self._devices_step.search_button.setEnabled(True)
            return
        available = self._controller.is_backend_available(backend)
        self._devices_step.search_button.setEnabled(available)
        if not available:
            self._devices_step.status_label.setText(
                _OPT_SDK_UNAVAILABLE if backend == BACKEND_OPT else STATUS_IDLE
            )

    def _go_to_step(self, step: int) -> None:
        self._stack.setCurrentIndex(step)
        self._stepper.set_current(step)
        if step == _STEP_DEVICES:
            self._devices_step.apply_backend_descriptor(self._selected_backend())
            self._refresh_devices_step_actions()

    def _on_back_to_model(self) -> None:
        self._clear_devices_step()
        self._go_to_step(_STEP_MODEL)

    def _on_back_from_connection(self) -> None:
        self._go_to_step(_STEP_DEVICES)
        self._connection_step.reset_ui()
        self._controller.stop_live()
        self._controller.disconnect()

    def _on_cancel(self) -> None:
        self._go_to_step(_STEP_MODEL)
        self._connection_step.reset_ui()
        self._controller.stop_live()
        self._controller.disconnect()
        self._selected_device = None
        self._devices_step.next_button.setEnabled(False)
        self._devices_step.device_table.set_devices([])
        self._devices_step.status_label.setText(STATUS_IDLE)

    def _on_devices_action_clicked(self) -> None:
        descriptor = self._model_step.descriptor_for_selected()
        if descriptor is not None and descriptor.discover_mode == "file_picker":
            self._on_import_video_clicked()
            return
        self._on_search_clicked()

    def _on_import_video_clicked(self) -> None:
        path = open_video_file_path(self)
        if not path:
            return
        self._devices_step.status_label.setText("Importando vídeo...")
        self._devices_step.device_table.set_devices([])
        self._devices_step.next_button.setEnabled(False)
        self._controller.discover(
            BACKEND_VIDEO,
            DiscoverContext(video_path=path),
        )

    def _on_search_clicked(self) -> None:
        self._devices_step.status_label.setText("Buscando câmeras...")
        self._devices_step.device_table.set_devices([])
        self._devices_step.next_button.setEnabled(False)
        self._controller.discover(self._selected_backend())

    def _on_device_selected(self) -> None:
        self._selected_device = self._devices_step.device_table.selected_device()
        self._devices_step.next_button.setEnabled(self._selected_device is not None)

    def _on_connect_clicked(self) -> None:
        if self._selected_device is None:
            return
        self._controller.set_video_live_loop(True)
        self._connection_step.connect_button.setEnabled(False)
        self._connection_step.success_banner.setVisible(False)
        self._connection_step.preview.show_placeholder("Conectando...")
        self._controller.connect_index(self._selected_device.index)

    def _on_save(self) -> None:
        if self._selected_device is None:
            return
        try:
            self._config_service.save_from_device(
                self._selected_device,
                backend=self._controller.current_backend,
            )
        except ValueError as exc:
            report_wizard_camera_error(
                _logger,
                str(exc),
                self._wizard_error_context(_STEP_CONNECTION),
                event="falha ao salvar",
            )
            return
        self._controller.disconnect()
        self._connection_step.reset_ui()
        self._devices_step.status_label.setText("Configurações salvas com sucesso.")

    def _connect_controller(self) -> None:
        self._controller.devices_found.connect(self._on_devices_found)
        self._controller.connected.connect(self._on_connected)
        self._controller.connection_failed.connect(self._on_connection_failed)
        self._controller.frame_ready.connect(self._on_frame_ready)
        self._controller.error.connect(self._on_error)

    def _on_devices_found(self, devices: object) -> None:
        device_list = list(devices)
        self._devices_step.device_table.set_devices(device_list)
        descriptor = self._model_step.descriptor_for_selected()
        is_video = descriptor is not None and descriptor.discover_mode == "file_picker"
        if device_list:
            if is_video:
                self._devices_step.device_table.selectRow(0)
                self._selected_device = device_list[0]
                self._devices_step.next_button.setEnabled(True)
                self._devices_step.status_label.setText(
                    descriptor.devices_found_status_template
                    if descriptor is not None
                    else "Vídeo importado com sucesso."
                )
            else:
                self._selected_device = (
                    self._devices_step.device_table.selected_device()
                )
                self._devices_step.next_button.setEnabled(
                    self._selected_device is not None
                )
                if descriptor is not None:
                    self._devices_step.status_label.setText(
                        descriptor.devices_found_status_template.format(
                            count=len(device_list)
                        )
                    )
                else:
                    self._devices_step.status_label.setText(
                        f"{len(device_list)} câmera(s) encontrada(s)."
                    )
        else:
            self._selected_device = None
            self._devices_step.next_button.setEnabled(False)
            if descriptor is not None:
                self._devices_step.status_label.setText(
                    descriptor.devices_empty_status_template
                )
            elif is_video:
                self._devices_step.status_label.setText("Nenhum vídeo importado.")
            else:
                self._devices_step.status_label.setText("Nenhuma câmera encontrada.")

    def _on_connected(self) -> None:
        if self._stack.currentIndex() != _STEP_CONNECTION:
            return
        self._stepper.set_current(_STEP_CONNECTION, mark_current_done=True)
        self._connection_step.success_banner.setVisible(True)
        self._connection_step.save_button.setEnabled(True)
        self._connection_step.connect_button.setEnabled(True)

    def _on_connection_failed(self, message: str) -> None:
        if self._stack.currentIndex() != _STEP_CONNECTION:
            return
        report_wizard_camera_error(
            _logger,
            message,
            self._wizard_error_context(_STEP_CONNECTION),
            event="falha de conexão",
        )

    def _on_frame_ready(self, frame: object, meta: object) -> None:
        if self._stack.currentIndex() != _STEP_CONNECTION or not self.isVisible():
            return
        apply_live_frame(
            self._connection_step.preview,
            frame,
            meta,
            chips=self._connection_step.chips,
        )

    def _on_error(self, message: str) -> None:
        report_wizard_camera_error(
            _logger,
            message,
            self._wizard_error_context(self._stack.currentIndex()),
        )

    def _wizard_error_context(self, wizard_step: int) -> WizardErrorContext:
        return WizardErrorContext(
            screen_label="Câmera (wizard)",
            wizard_step=wizard_step,
            step_devices=_STEP_DEVICES,
            step_connection=_STEP_CONNECTION,
            devices_status=self._devices_step.status_label,
            connect_button=self._connection_step.connect_button,
            preview=self._connection_step.preview,
        )
