"""Controles de playback para arquivo de vídeo local (``QMediaPlayer``)."""

from __future__ import annotations

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QWidget

from visionflow.presentation.widgets.video_playback_slider_bar import (
    SEEK_STEP_MS,
    VideoPlaybackSliderBar,
)


class FileVideoPlaybackControls(VideoPlaybackSliderBar):
    """Barra play/pause, seek ±5s e slider para um ``QMediaPlayer``."""

    def __init__(
        self,
        player: QMediaPlayer,
        parent: QWidget | None = None,
    ) -> None:

        super().__init__(parent)

        self._player = player

        self.play_pause_clicked.connect(self._on_play_pause_clicked)

        self.seek_back_clicked.connect(self._seek_back)

        self.seek_forward_clicked.connect(self._seek_forward)

        self.position_seeked.connect(self._player.setPosition)

        player.positionChanged.connect(self._on_position_changed)

        player.durationChanged.connect(self._on_duration_changed)

        player.playbackStateChanged.connect(self._on_playback_state_changed)

        self._sync_from_player()

    def _sync_from_player(self) -> None:

        self._on_duration_changed(self._player.duration())

        self._on_position_changed(self._player.position())

        self._on_playback_state_changed(self._player.playbackState())

    def _on_play_pause_clicked(self) -> None:

        if self._playing:
            self._player.pause()

        else:
            self._player.play()

    def _seek_back(self) -> None:

        self._seek_by_ms(-SEEK_STEP_MS)

    def _seek_forward(self) -> None:

        self._seek_by_ms(SEEK_STEP_MS)

    def _seek_by_ms(self, delta_ms: int) -> None:

        duration = max(0, self._player.duration())

        target = max(0, min(self._player.position() + delta_ms, duration))

        self._player.setPosition(target)

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:

        self.set_playing(state == QMediaPlayer.PlaybackState.PlayingState)

    def _on_duration_changed(self, duration_ms: int) -> None:

        self.set_timeline(self._player.position(), duration_ms)

    def _on_position_changed(self, position_ms: int) -> None:

        self.set_timeline(position_ms, self._player.duration())
