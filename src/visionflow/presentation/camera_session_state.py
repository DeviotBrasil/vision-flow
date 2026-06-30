"""Estados e fases da sessão de câmera expostos à UI."""

from __future__ import annotations

STATE_DISCONNECTED = "disconnected"
STATE_SEARCHING = "searching"
STATE_CONNECTING = "connecting"
STATE_CONNECTED = "connected"
STATE_ERROR = "error"

TRIGGER_PHASE_IDLE = "idle"
TRIGGER_PHASE_ENABLING = "enabling"
TRIGGER_PHASE_ACTIVE = "active"
TRIGGER_PHASE_DISABLING = "disabling"


class CameraSessionState:
    """Máquina de estados de alto nível da câmera."""

    def __init__(self) -> None:
        self.connection_state = STATE_DISCONNECTED
        self.trigger_mode_active = False
        self.trigger_phase = TRIGGER_PHASE_IDLE
        self.connected_supports_trigger = True

    def set_connection_state(self, state: str) -> bool:
        if state == self.connection_state:
            return False
        self.connection_state = state
        return True

    def set_trigger_phase(self, phase: str) -> bool:
        if phase == self.trigger_phase:
            return False
        self.trigger_phase = phase
        return True
