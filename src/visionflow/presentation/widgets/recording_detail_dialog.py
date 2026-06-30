"""Popup nativo de detalhe de uma gravação (reproduzir, baixar, excluir)."""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QShowEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from visionflow.domain.entities.recording import Recording
from visionflow.presentation.format_utils import (
    format_captured_at,
    format_file_size,
    format_time_ms,
    format_video_resolution,
)
from visionflow.presentation.icon_colors import DANGER, INFO, icon_role_color
from visionflow.presentation.icon_sizes import TOOLBAR_ICON
from visionflow.presentation.icon_utils import tinted_icon
from visionflow.presentation.preview_size_utils import (
    PreviewScaleLimits,
    scaled_preview_size,
)
from visionflow.presentation.system_dialogs import (
    apply_dialog_theme,
    save_file_path,
)
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_DANGER_OUTLINE,
    VARIANT_PRIMARY_OUTLINE,
    create_button,
)
from visionflow.presentation.widgets.file_video_playback_controls import (
    FileVideoPlaybackControls,
)
from visionflow.presentation.window_chrome import apply_native_dialog_flags

_PREVIEW_MAX_HEIGHT = 900
_PREVIEW_MAX_WIDTH = 1280
_PREVIEW_FALLBACK_W = 640
_PREVIEW_FALLBACK_H = 360
_BODY_PAD = 16
_ACTIONS_SPACING = 9
_MIN_WIDTH = 400
_MIN_HEIGHT = 360


class RecordingDetailDialog(QDialog):
    """Detalhe de gravação em janela popup nativa do Windows."""

    delete_requested = Signal(int)

    def __init__(self, recording: Recording, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recording = recording
        self._file_path = recording.file_path
        self._record_id = recording.id

        apply_native_dialog_flags(self)
        self.setObjectName("recording_detail_dialog")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setModal(True)
        self.setWindowTitle(self._header_title())

        root = QVBoxLayout(self)
        root.setContentsMargins(_BODY_PAD, _BODY_PAD, _BODY_PAD, _BODY_PAD)
        root.setSpacing(_ACTIONS_SPACING)

        subtitle = QLabel(self._header_subtitle())
        subtitle.setObjectName("recording_detail_subtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        preview = self._build_preview_widget()
        root.addWidget(preview)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(_ACTIONS_SPACING)
        actions.addStretch()

        download = create_button(
            "Salvar",
            variant=VARIANT_PRIMARY_OUTLINE,
            shape=SHAPE_PILL,
            icon=tinted_icon("icon_download.svg", icon_role_color(INFO), TOOLBAR_ICON),
        )
        download.clicked.connect(self._on_download)
        actions.addWidget(download)

        delete = create_button(
            "Excluir",
            variant=VARIANT_DANGER_OUTLINE,
            shape=SHAPE_PILL,
            icon=tinted_icon("icon_trash.svg", icon_role_color(DANGER), TOOLBAR_ICON),
        )
        delete.clicked.connect(self._on_delete)
        actions.addWidget(delete)

        root.addLayout(actions)
        self._finalize_size(subtitle, actions)
        apply_dialog_theme(self)

    def showEvent(self, event: QShowEvent) -> None:
        apply_dialog_theme(self)
        super().showEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._release_media()
        super().closeEvent(event)

    def _release_media(self) -> None:
        self._player.stop()
        self._player.setSource(QUrl())

    def _preview_dimensions(self) -> tuple[int, int]:
        return scaled_preview_size(
            self._recording.width or 0,
            self._recording.height or 0,
            PreviewScaleLimits(
                max_width=_PREVIEW_MAX_WIDTH,
                max_height=_PREVIEW_MAX_HEIGHT,
                fallback_width=_PREVIEW_FALLBACK_W,
                fallback_height=_PREVIEW_FALLBACK_H,
            ),
        )

    def _build_preview_widget(self) -> QWidget:
        preview_w, preview_h = self._preview_dimensions()
        container = QWidget()
        container.setObjectName("recording_detail_preview")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        video = QVideoWidget()
        video.setObjectName("recording_detail_video")
        video.setFixedSize(preview_w, preview_h)
        video.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        layout.addWidget(video)

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(video)
        source = Path(self._file_path)
        if source.is_file():
            self._player.setSource(QUrl.fromLocalFile(str(source.resolve())))

        self._playback_controls = FileVideoPlaybackControls(self._player, container)
        layout.addWidget(self._playback_controls)
        container.setFixedSize(
            preview_w,
            preview_h + self._playback_controls.sizeHint().height(),
        )

        if source.is_file():
            self._player.play()
        return container

    def _finalize_size(self, subtitle: QLabel, actions: QHBoxLayout) -> None:
        preview_w, preview_h = self._preview_dimensions()
        controls_h = self._playback_controls.sizeHint().height()
        layout = self.layout()
        if layout is not None:
            layout.activate()

        body_w = preview_w + 2 * _BODY_PAD
        subtitle_w = subtitle.sizeHint().width() + 2 * _BODY_PAD
        actions_w = actions.sizeHint().width() + 2 * _BODY_PAD
        body_h = (
            subtitle.sizeHint().height()
            + _ACTIONS_SPACING
            + preview_h
            + controls_h
            + _ACTIONS_SPACING
            + actions.sizeHint().height()
            + 2 * _BODY_PAD
        )
        width = max(_MIN_WIDTH, body_w, subtitle_w, actions_w)
        height = max(_MIN_HEIGHT, body_h)
        self.setFixedSize(width, height)

    def _header_title(self) -> str:
        file_name = Path(self._file_path).name
        if self._record_id is not None and file_name:
            return f"{self._record_id} - {file_name}"
        if file_name:
            return file_name
        return "Gravação"

    def _header_subtitle(self) -> str:
        parts: list[str] = []
        if self._recording.recorded_at:
            parts.append(format_captured_at(self._recording.recorded_at))
        duration = format_time_ms(self._recording.duration_ms)
        if duration:
            parts.append(f"Duração: {duration}")
        resolution = format_video_resolution(
            self._recording.width, self._recording.height
        )
        if resolution:
            parts.append(resolution)
        parts.append(format_file_size(self._recording.file_size_bytes))
        return " · ".join(parts)

    def _on_download(self) -> None:
        source = self._file_path
        if not source or not Path(source).is_file():
            return
        suffix = Path(source).suffix or ".mp4"
        suggested = Path(source).name or f"video{suffix}"
        target = save_file_path(
            self,
            "Salvar gravação",
            suggested,
            f"Vídeo (*{suffix});;Todos (*.*)",
        )
        if target:
            shutil.copyfile(source, target)

    def _on_delete(self) -> None:
        if self._record_id is None:
            return
        self._release_media()
        record_id = self._record_id
        QTimer.singleShot(0, self, lambda: self._finish_delete(record_id))

    def _finish_delete(self, record_id: int) -> None:
        self.delete_requested.emit(record_id)
        self.accept()
