"""Tela Principal — captura ao vivo e gerenciamento de capturas."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from visionflow.domain.use_cases.captures import CaptureService
from visionflow.domain.use_cases.recordings import RecordingService
from visionflow.presentation.camera_controller import (
    STATE_CONNECTED,
    STATE_CONNECTING,
    STATE_DISCONNECTED,
    STATE_ERROR,
    STATE_SEARCHING,
    TRIGGER_PHASE_ENABLING,
    CameraController,
)
from visionflow.presentation.camera_feedback import (
    apply_live_frame,
    log_camera_issue,
    show_preview_error,
)
from visionflow.presentation.icon_colors import (
    DISABLED,
    INFO,
    NEUTRAL,
    SUCCESS,
    icon_role_color,
)
from visionflow.presentation.icon_sizes import TOOLBAR_ICON, TOOLBAR_SMALL_ICON
from visionflow.presentation.icon_utils import tinted_pixmap
from visionflow.presentation.screens.deps import MainScreenDeps
from visionflow.presentation.shell_utils import open_folder_in_explorer
from visionflow.presentation.style_utils import set_property
from visionflow.presentation.system_dialogs import show_info_message
from visionflow.presentation.trigger_labels import TRIGGER_PLACEHOLDER
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_DANGER,
    VARIANT_DANGER_OUTLINE,
    VARIANT_PRIMARY,
    create_button,
    set_variant,
)
from visionflow.presentation.widgets.camera_preview import CameraPreview
from visionflow.presentation.widgets.capture_actions import show_capture_detail
from visionflow.presentation.widgets.capture_strip import STRIP_PREVIEW_LIMIT
from visionflow.presentation.widgets.main_recent_panel import MainRecentPanel
from visionflow.presentation.widgets.pill_controls import PillFrame
from visionflow.presentation.widgets.recording_actions import show_recording_detail
from visionflow.presentation.widgets.trigger_capture_toolbar import (
    TriggerCaptureToolbar,
)
from visionflow.presentation.widgets.video_playback_controls import (
    VideoPlaybackControls,
)
from visionflow.presentation.window_constraints import SCREEN_PREVIEW_MIN_HEIGHT

_CONTENT_MARGIN_H = 21
_CONTENT_MARGIN_V = 21
_TOOLBAR_PAD_H = 21
_TOOLBAR_PAD_V = 13
_TOOLBAR_SPACING = 9
_BADGE_PAD_H = 14
_BADGE_PAD_V = 7
_BADGE_GAP = 9
_CHIP_PAD_H = 14
_CHIP_PAD_V = 7
_CHIP_GAP = 6
_PATH_LABEL_MAX_WIDTH = 220

_STATUS_TEXT = {
    STATE_DISCONNECTED: "Desconectada",
    STATE_SEARCHING: "Buscando...",
    STATE_CONNECTING: "Conectando...",
    STATE_CONNECTED: "Conectada",
    STATE_ERROR: "Erro",
}

_logger = logging.getLogger(__name__)


class _CapturesPathChip(PillFrame):
    """Chip clicável que abre a pasta de capturas no Windows Explorer."""

    def __init__(self, folder: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._folder = Path(folder)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Abrir pasta de capturas no Explorer\n{self._folder}")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            open_folder_in_explorer(self._folder)
        super().mousePressEvent(event)


class MainScreen(QWidget):
    """Principal: toolbar, preview ao vivo e painel de capturas/gravações recentes."""

    PAGE_ID: ClassVar[str] = "principal"
    TITLE: ClassVar[str] = "Principal"

    def __init__(
        self,
        controller: CameraController,
        captures: CaptureService,
        recordings: RecordingService,
        deps: MainScreenDeps,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(f"{self.PAGE_ID}_screen")
        self._controller = controller
        self._captures = captures
        self._recordings = recordings
        captures_dir, recordings_dir = deps.data_dirs
        self._captures_dir = Path(captures_dir)
        self._recordings_dir = Path(recordings_dir)
        self._last_frame: np.ndarray | None = None
        self._last_meta: dict[str, Any] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())

        preview_block = QFrame()
        preview_block.setObjectName("preview_container")
        preview_block.setMinimumHeight(SCREEN_PREVIEW_MIN_HEIGHT)
        preview_row = QHBoxLayout(preview_block)
        preview_row.setContentsMargins(
            _CONTENT_MARGIN_H,
            _CONTENT_MARGIN_V,
            0,
            _CONTENT_MARGIN_V,
        )
        preview_row.setSpacing(0)
        preview_column = QVBoxLayout()
        preview_column.setContentsMargins(0, 0, 0, 0)
        preview_column.setSpacing(0)
        self._preview = CameraPreview()
        self._preview.setMinimumHeight(SCREEN_PREVIEW_MIN_HEIGHT)
        preview_column.addWidget(self._preview, 1)
        self._video_controls = VideoPlaybackControls(self._controller)
        preview_column.addWidget(self._video_controls)
        preview_row.addLayout(preview_column, 1)
        preview_row.addSpacing(_CONTENT_MARGIN_H)
        root.addWidget(preview_block, 1)

        self._recent_panel = MainRecentPanel(deps.thumbnail_loader)
        self._recent_panel.capture_clicked.connect(self._on_capture_clicked)
        self._recent_panel.recording_clicked.connect(self._on_recording_clicked)
        root.addWidget(self._recent_panel)

        self._connect_controller()
        self.refresh_recent_media()
        self._apply_state(self._controller.state)

    def shutdown(self) -> None:
        """Recursos compartilhados são encerrados em ``MainApplication.closeEvent``."""

    # -- Toolbar --------------------------------------------------------------

    def _build_toolbar(self) -> QFrame:
        toolbar = QFrame()
        toolbar.setObjectName("principal_toolbar")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(_TOOLBAR_PAD_H, _TOOLBAR_PAD_V, 0, _TOOLBAR_PAD_V)
        layout.setSpacing(_TOOLBAR_SPACING)

        layout.addWidget(self._build_status_badge())

        separator = QFrame()
        separator.setObjectName("toolbar_separator")
        layout.addWidget(separator)

        self._primary_button = create_button(
            "Iniciar",
            variant=VARIANT_PRIMARY,
            shape=SHAPE_PILL,
            icon_name="icon_play.svg",
        )
        self._primary_button.clicked.connect(self._on_primary_clicked)
        layout.addWidget(self._primary_button)

        self._trigger_capture = TriggerCaptureToolbar(self._controller)
        self._trigger_capture.capture_clicked.connect(self._on_capture_clicked_now)
        self._trigger_capture.trigger_active_changed.connect(
            self._on_trigger_active_changed
        )
        layout.addWidget(self._trigger_capture)

        self._record_button = create_button(
            "Gravar",
            variant=VARIANT_DANGER_OUTLINE,
            shape=SHAPE_PILL,
            icon_name="icon_record.svg",
        )
        self._record_button.clicked.connect(self._on_record_clicked)
        self._record_button.setEnabled(False)
        layout.addWidget(self._record_button)

        layout.addStretch()

        layout.addWidget(self._build_counter_chip())
        layout.addWidget(self._build_path_chip())
        layout.addSpacing(_TOOLBAR_PAD_H)
        return toolbar

    def _build_status_badge(self) -> PillFrame:
        badge = PillFrame()
        badge.setObjectName("status_badge")
        layout = QHBoxLayout(badge)
        layout.setContentsMargins(
            _BADGE_PAD_H, _BADGE_PAD_V, _BADGE_PAD_H, _BADGE_PAD_V
        )
        layout.setSpacing(_BADGE_GAP)

        self._status_icon = QLabel()
        self._status_icon.setObjectName("status_badge_icon")
        self._status_icon.setFixedSize(TOOLBAR_ICON)
        self._status_icon.setPixmap(
            tinted_pixmap("icon_wifi.svg", icon_role_color(SUCCESS), TOOLBAR_ICON)
        )
        self._status_icon.setScaledContents(True)
        layout.addWidget(self._status_icon)

        self._status_text = QLabel("Desconectada")
        self._status_text.setObjectName("status_badge_text")
        layout.addWidget(self._status_text)
        return badge

    def _build_counter_chip(self) -> PillFrame:
        chip = PillFrame()
        chip.setObjectName("toolbar_chip_counter")
        layout = QHBoxLayout(chip)
        layout.setContentsMargins(_CHIP_PAD_H, _CHIP_PAD_V, _CHIP_PAD_H, _CHIP_PAD_V)
        layout.setSpacing(_CHIP_GAP)

        icon = QLabel()
        icon.setPixmap(
            tinted_pixmap("icon_image.svg", icon_role_color(INFO), TOOLBAR_SMALL_ICON)
        )
        layout.addWidget(icon)

        self._counter_value = QLabel("0")
        self._counter_value.setObjectName("toolbar_chip_value")
        layout.addWidget(self._counter_value)

        caption = QLabel("capturas")
        caption.setObjectName("toolbar_chip_caption")
        layout.addWidget(caption)
        return chip

    def _build_path_chip(self) -> PillFrame:
        chip = _CapturesPathChip(self._captures_dir)
        chip.setObjectName("toolbar_chip_path")
        layout = QHBoxLayout(chip)
        layout.setContentsMargins(_CHIP_PAD_H, _CHIP_PAD_V, _CHIP_PAD_H, _CHIP_PAD_V)
        layout.setSpacing(_CHIP_GAP)

        icon = QLabel()
        icon.setPixmap(
            tinted_pixmap(
                "icon_folder.svg", icon_role_color(NEUTRAL), TOOLBAR_SMALL_ICON
            )
        )
        layout.addWidget(icon)

        path_text = str(self._captures_dir)
        path_label = QLabel()
        path_label.setObjectName("toolbar_chip_path_text")
        path_label.setMaximumWidth(_PATH_LABEL_MAX_WIDTH)
        path_label.setToolTip(chip.toolTip())
        metrics = QFontMetrics(path_label.font())
        path_label.setText(
            metrics.elidedText(
                path_text, Qt.TextElideMode.ElideRight, _PATH_LABEL_MAX_WIDTH
            )
        )
        layout.addWidget(path_label)
        return chip

    # -- Estado ---------------------------------------------------------------

    def _apply_state(self, state: str) -> None:
        self._status_text.setText(_STATUS_TEXT.get(state, "Desconectada"))
        set_property(self._status_text, "state", state)
        set_property(self._status_icon, "state", state)

        connected = state == STATE_CONNECTED
        busy = state in (STATE_SEARCHING, STATE_CONNECTING)

        if connected:
            self._primary_button.setText("Parar")
            set_variant(
                self._primary_button,
                VARIANT_DANGER,
                icon_name="icon_stop.svg",
            )
            self._status_icon.setPixmap(
                tinted_pixmap("icon_wifi.svg", icon_role_color(SUCCESS), TOOLBAR_ICON)
            )
        else:
            self._primary_button.setText("Iniciar")
            set_variant(
                self._primary_button,
                VARIANT_PRIMARY,
                icon_name="icon_play.svg",
            )
            if state in (STATE_SEARCHING, STATE_CONNECTING):
                wifi_color = icon_role_color(INFO)
            else:
                wifi_color = icon_role_color(DISABLED)
            self._status_icon.setPixmap(
                tinted_pixmap("icon_wifi.svg", wifi_color, TOOLBAR_ICON)
            )

        self._primary_button.setEnabled(not busy)
        set_property(self._primary_button, "state", state)

        if not connected:
            self._trigger_capture.reset()
        elif connected:
            self._trigger_capture.refresh()

        if not connected and not busy:
            self._preview.clear_frame()
            self._video_controls.reset()
        elif busy:
            self._preview.show_placeholder("Conectando...")

        if not connected and self._controller.is_recording:
            self._controller.stop_recording()
        self._update_record_button(state)

    def _update_record_button(self, state: str | None = None) -> None:
        current_state = state if state is not None else self._controller.state
        connected = current_state == STATE_CONNECTED
        trigger_active = self._controller.trigger_mode_active
        busy_phase = self._controller.trigger_phase == TRIGGER_PHASE_ENABLING
        recording = self._controller.is_recording
        recording_active = self._controller.is_recording_active

        if recording:
            label = "Parar gravação" if recording_active else "Preparando gravação…"
            self._record_button.setText(label)
            set_variant(
                self._record_button,
                VARIANT_DANGER,
                icon_name="icon_stop.svg",
            )
            self._record_button.setEnabled(True)
            return

        self._record_button.setText("Gravar")
        set_variant(
            self._record_button,
            VARIANT_DANGER_OUTLINE,
            icon_name="icon_record.svg",
        )
        record_enabled = connected and not trigger_active and not busy_phase
        self._record_button.setEnabled(record_enabled)

    # -- Ações ----------------------------------------------------------------

    def _on_primary_clicked(self) -> None:
        if self._controller.state == STATE_CONNECTED:
            self._controller.disconnect()
        else:
            self._controller.set_video_live_loop(False)
            self._controller.connect_saved()

    def _on_capture_clicked_now(self) -> None:
        if self._last_frame is not None:
            self._save_capture(self._last_frame, self._last_meta)

    def _on_record_clicked(self) -> None:
        if self._controller.is_recording:
            self._controller.stop_recording()
            return
        self._recordings_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(self._recordings_dir / f"{stamp}.mp4")
        self._controller.start_recording(output_path)

    def _on_trigger_active_changed(self, active: bool) -> None:
        if not active:
            return
        self._last_frame = None
        self._last_meta = None
        if self.isVisible():
            self._preview.show_placeholder(TRIGGER_PLACEHOLDER)
        self._update_record_button()

    def _save_capture(self, frame: np.ndarray, meta: dict[str, Any]) -> None:
        if self._captures.save(frame, meta) is not None:
            self.refresh_recent_media()

    def refresh_recent_media(self) -> None:
        """Atualiza faixas e contador (capturas e gravações do dia)."""
        captures = self._captures.recent_today(limit=STRIP_PREVIEW_LIMIT)
        self._recent_panel.set_captures(captures)
        self._counter_value.setText(str(self._captures.count_today()))
        self._refresh_recordings()

    def refresh_captures(self) -> None:
        """Alias de ``refresh_recent_media`` (compatível com ``DefaultLayout``)."""
        self.refresh_recent_media()

    def _refresh_recordings(self) -> None:
        recordings = self._recordings.recent_today(limit=STRIP_PREVIEW_LIMIT)
        self._recent_panel.set_recordings(recordings)

    def _on_capture_clicked(self, capture_id: int) -> None:
        show_capture_detail(
            self,
            self._captures,
            capture_id,
            on_deleted=self.refresh_recent_media,
            on_edited=self.refresh_recent_media,
        )

    def _on_recording_clicked(self, recording_id: int) -> None:
        show_recording_detail(
            self,
            self._recordings,
            recording_id,
            on_deleted=self._refresh_recordings,
        )

    # -- Sinais do controlador ------------------------------------------------

    def _connect_controller(self) -> None:
        self._controller.state_changed.connect(self._apply_state)
        self._controller.frame_ready.connect(self._on_frame_ready)
        self._controller.capture_ready.connect(self._on_capture_ready)
        self._controller.connection_failed.connect(self._on_connection_failed)
        self._controller.error.connect(self._on_error)
        self._controller.trigger_mode_changed.connect(
            lambda _active: self._update_record_button()
        )
        self._controller.trigger_phase_changed.connect(
            lambda _phase: self._update_record_button()
        )
        self._controller.recording_armed.connect(self._update_record_button)
        self._controller.recording_started.connect(
            lambda _path: self._update_record_button()
        )
        self._controller.recording_stopped.connect(self._on_recording_stopped)
        self._controller.recording_failed.connect(self._on_recording_failed)

    def _on_frame_ready(self, frame: object, meta: object) -> None:
        self._last_frame = frame
        self._last_meta = meta
        if self.isVisible():
            apply_live_frame(self._preview, frame, meta)

    def _on_capture_ready(self, frame: object, meta: object) -> None:
        if not self.isVisible():
            return
        self._save_capture(frame, meta)

    def _on_connection_failed(self, message: str) -> None:
        log_camera_issue(_logger, "Principal", message, event="falha de conexão")
        show_preview_error(self._preview, message)

    def _on_error(self, message: str) -> None:
        log_camera_issue(_logger, "Principal", message)
        show_preview_error(self._preview, message)

    def _on_recording_stopped(self, path: str) -> None:
        self._update_record_button()
        if self._recordings.register(path) is None:
            show_info_message(
                self,
                "Gravação",
                "O vídeo foi salvo no disco, mas não foi possível cadastrá-lo "
                "no banco. Verifique os logs do aplicativo.",
            )
        else:
            self._refresh_recordings()

    def _on_recording_failed(self, message: str) -> None:
        self._update_record_button()
        show_info_message(
            self,
            "Gravação",
            message,
        )
