"""Controles de playback de vídeo na tela Principal."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from visionflow.presentation.camera_controller import (
    STATE_CONNECTED,
    CameraController,
)
from visionflow.presentation.widgets.video_playback_slider_bar import (
    VideoPlaybackSliderBar,
)


class VideoPlaybackControls(VideoPlaybackSliderBar):
    """Barra play/pause, seek ±5s e slider de progresso."""

    def __init__(
        self,
        controller: CameraController,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller

        self.play_pause_clicked.connect(self._on_play_pause_clicked)
        self.seek_back_clicked.connect(controller.video_seek_back)
        self.seek_forward_clicked.connect(controller.video_seek_forward)
        self.position_seeked.connect(controller.video_seek_to_ms)

        controller.state_changed.connect(self._on_state_changed)
        controller.video_position_changed.connect(self._on_position_changed)
        controller.video_playing_changed.connect(self._on_playing_changed)

        self.setVisible(False)
        self.reset()

    def reset(self) -> None:
        """Restaura controles ao estado inicial."""
        super().reset()

    def _on_state_changed(self, state: str) -> None:
        visible = state == STATE_CONNECTED and self._controller.is_video_backend
        self.setVisible(visible)
        if not visible:
            self.reset()
            return
        self.set_controls_enabled(True)

    def _on_play_pause_clicked(self) -> None:
        if self._playing:
            self._controller.video_pause()
        else:
            self._controller.video_play()

    def _on_playing_changed(self, playing: bool) -> None:
        self.set_playing(playing)

    def _on_position_changed(self, position_ms: int, duration_ms: int) -> None:
        self.set_timeline(position_ms, duration_ms)
