"""Botões Capturar + Trigger compartilhados entre Principal e Câmera."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget

from visionflow.presentation.camera_controller import (
    STATE_CONNECTED,
    TRIGGER_PHASE_ACTIVE,
    TRIGGER_PHASE_DISABLING,
    TRIGGER_PHASE_ENABLING,
    TRIGGER_PHASE_IDLE,
    CameraController,
)
from visionflow.presentation.trigger_labels import (
    TRIGGER_LABEL_DISABLED,
    TRIGGER_LABEL_DISABLING,
    TRIGGER_LABEL_ENABLED,
    TRIGGER_LABEL_ENABLING,
)
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_NEUTRAL_OUTLINE,
    VARIANT_PRIMARY_OUTLINE,
    button_row,
    create_button,
)


class TriggerCaptureToolbar(QWidget):
    """Toolbar reutilizável: captura manual e toggle de trigger externo."""

    capture_clicked = Signal()
    trigger_active_changed = Signal(bool)

    def __init__(
        self,
        controller: CameraController,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller

        layout = button_row(align_left=True)
        layout.setContentsMargins(0, 0, 0, 0)

        self._capture_button = create_button(
            "Capturar",
            variant=VARIANT_PRIMARY_OUTLINE,
            shape=SHAPE_PILL,
            icon_name="icon_capture.svg",
        )
        self._capture_button.clicked.connect(self.capture_clicked.emit)
        self._capture_button.setEnabled(False)
        layout.addWidget(self._capture_button)

        self._trigger_button = create_button(
            TRIGGER_LABEL_DISABLED,
            variant=VARIANT_NEUTRAL_OUTLINE,
            shape=SHAPE_PILL,
            icon_name="icon_trigger.svg",
            checkable=True,
        )
        self._trigger_button.toggled.connect(self._on_trigger_toggled)
        self._trigger_button.setEnabled(False)
        self._trigger_button.setVisible(False)
        layout.addWidget(self._trigger_button)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(layout)

        controller.state_changed.connect(self._update_buttons)
        controller.trigger_mode_changed.connect(self._on_trigger_mode_changed)
        controller.trigger_phase_changed.connect(self._on_trigger_phase_changed)
        self._sync_from_controller()

    def reset(self) -> None:
        """Restaura botões ao estado desconectado (ex.: wizard ao voltar)."""
        self._sync_trigger_button(False)
        self._capture_button.setEnabled(False)
        self._update_buttons(self._controller.state)

    def refresh(self) -> None:
        """Sincroniza botões com o estado atual do controlador."""
        self._sync_from_controller()

    def _sync_from_controller(self) -> None:
        self._sync_trigger_button(self._controller.trigger_mode_active)
        self._on_trigger_phase_changed(self._controller.trigger_phase)
        self._update_buttons(self._controller.state)

    def _on_trigger_toggled(self, checked: bool) -> None:
        self._controller.set_trigger_mode(checked)

    def _on_trigger_mode_changed(self, active: bool) -> None:
        self._sync_trigger_button(active)
        self._update_buttons(self._controller.state)
        self.trigger_active_changed.emit(active)

    def _on_trigger_phase_changed(self, phase: str) -> None:
        if phase == TRIGGER_PHASE_ENABLING:
            self._set_trigger_text(TRIGGER_LABEL_ENABLING)
        elif phase == TRIGGER_PHASE_DISABLING:
            self._set_trigger_text(TRIGGER_LABEL_DISABLING)
        elif phase == TRIGGER_PHASE_ACTIVE:
            self._set_trigger_text(TRIGGER_LABEL_ENABLED)
        elif phase == TRIGGER_PHASE_IDLE:
            self._set_trigger_text(
                TRIGGER_LABEL_ENABLED
                if self._controller.trigger_mode_active
                else TRIGGER_LABEL_DISABLED
            )
        self._update_buttons(self._controller.state)

    def _update_buttons(self, _state: str) -> None:
        connected = self._controller.state == STATE_CONNECTED
        phase = self._controller.trigger_phase
        trigger_active = self._controller.trigger_mode_active
        busy_phase = phase in (TRIGGER_PHASE_ENABLING, TRIGGER_PHASE_DISABLING)
        capture_enabled = (
            connected and not trigger_active and phase != TRIGGER_PHASE_ENABLING
        )
        trigger_supported = self._controller.supports_trigger
        trigger_enabled = connected and not busy_phase and trigger_supported
        self._capture_button.setEnabled(capture_enabled)
        self._trigger_button.setVisible(trigger_supported)
        self._trigger_button.setEnabled(trigger_enabled)

    def _set_trigger_text(self, text: str) -> None:
        self._trigger_button.blockSignals(True)
        self._trigger_button.setText(text)
        self._trigger_button.blockSignals(False)

    def _sync_trigger_button(self, active: bool) -> None:
        self._trigger_button.blockSignals(True)
        self._trigger_button.setChecked(active)
        self._trigger_button.setText(
            TRIGGER_LABEL_ENABLED if active else TRIGGER_LABEL_DISABLED
        )
        self._trigger_button.blockSignals(False)
