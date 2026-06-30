"""Barra de controles play/pause, seek e slider compartilhada entre players."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSlider

from visionflow.presentation.format_utils import format_time_ms
from visionflow.presentation.icon_sizes import TOOLBAR_ICON
from visionflow.presentation.icon_utils import tinted_icon
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_NEUTRAL_OUTLINE,
    icon_color,
)

SEEK_STEP_MS = 5000


class VideoPlaybackSliderBar(QFrame):
    """Chrome de playback; emite ações e recebe posição/duração via métodos."""

    play_pause_clicked = Signal()
    seek_back_clicked = Signal()
    seek_forward_clicked = Signal()
    position_seeked = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("video_playback_controls")
        self._playing = False
        self._duration_ms = 0
        self._slider_dragging = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(21, 8, 21, 8)
        layout.setSpacing(10)

        self._play_pause_button = self._make_icon_button("icon_play.svg", "Reproduzir")
        self._play_pause_button.clicked.connect(self.play_pause_clicked.emit)
        layout.addWidget(self._play_pause_button)

        self._rewind_button = self._make_icon_button(
            "icon_rewind.svg", "Voltar 5 segundos"
        )
        self._rewind_button.clicked.connect(self.seek_back_clicked.emit)
        layout.addWidget(self._rewind_button)

        self._forward_button = self._make_icon_button(
            "icon_forward.svg", "Avançar 5 segundos"
        )
        self._forward_button.clicked.connect(self.seek_forward_clicked.emit)
        layout.addWidget(self._forward_button)

        self._position_label = QLabel("00:00")
        self._position_label.setObjectName("video_playback_time")
        layout.addWidget(self._position_label)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setObjectName("video_playback_slider")
        self._slider.setRange(0, 0)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderReleased.connect(self._on_slider_released)
        layout.addWidget(self._slider, 1)

        self._duration_label = QLabel("00:00")
        self._duration_label.setObjectName("video_playback_time")
        layout.addWidget(self._duration_label)

    def _make_icon_button(self, icon_name: str, tooltip: str) -> QPushButton:
        button = QPushButton()
        button.setObjectName("video_playback_button")
        button.setFixedSize(33, 33)
        button.setToolTip(tooltip)
        button.setProperty("vfVariant", VARIANT_NEUTRAL_OUTLINE)
        button.setProperty("vfShape", SHAPE_PILL)
        button.setIcon(self._tinted_icon(icon_name))
        button.setIconSize(TOOLBAR_ICON)
        return button

    @staticmethod
    def _tinted_icon(icon_name: str) -> QIcon:
        return tinted_icon(
            icon_name,
            icon_color(VARIANT_NEUTRAL_OUTLINE),
            TOOLBAR_ICON,
        )

    def set_controls_enabled(self, enabled: bool) -> None:
        self._play_pause_button.setEnabled(enabled)
        self._rewind_button.setEnabled(enabled)
        self._forward_button.setEnabled(enabled)
        self._slider.setEnabled(enabled)

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        icon_name = "icon_pause.svg" if playing else "icon_play.svg"
        tooltip = "Pausar" if playing else "Reproduzir"
        self._play_pause_button.setToolTip(tooltip)
        self._play_pause_button.setIcon(self._tinted_icon(icon_name))

    def set_timeline(self, position_ms: int, duration_ms: int) -> None:
        self._duration_ms = max(0, duration_ms)
        if not self._slider_dragging:
            self._slider.blockSignals(True)
            self._slider.setRange(0, self._duration_ms)
            self._slider.setValue(min(position_ms, self._duration_ms))
            self._slider.blockSignals(False)
        self._position_label.setText(format_time_ms(position_ms))
        self._duration_label.setText(format_time_ms(self._duration_ms))

    def reset(self) -> None:
        self._playing = False
        self._duration_ms = 0
        self._slider_dragging = False
        self._slider.blockSignals(True)
        self._slider.setRange(0, 0)
        self._slider.setValue(0)
        self._slider.blockSignals(False)
        self._position_label.setText("00:00")
        self._duration_label.setText("00:00")
        self.set_playing(False)
        self.set_controls_enabled(False)

    def _on_slider_pressed(self) -> None:
        self._slider_dragging = True

    def _on_slider_released(self) -> None:
        self._slider_dragging = False
        self.position_seeked.emit(self._slider.value())
