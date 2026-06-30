"""Painel inferior da Principal com abas de capturas e gravações."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)

from visionflow.domain.entities.capture import Capture
from visionflow.domain.entities.recording import Recording
from visionflow.presentation.media_thumbnail_loader import MediaThumbnailLoader
from visionflow.presentation.style_utils import set_property
from visionflow.presentation.widgets.capture_strip import CaptureStrip
from visionflow.presentation.widgets.recording_strip import RecordingStrip
from visionflow.presentation.window_constraints import (
    BOTTOM_PANEL_HEIGHT,
    STRIP_HEADER_HEIGHT,
    STRIP_HEADER_TO_BODY,
    STRIP_PAD_BOTTOM,
    STRIP_PAD_TOP,
)

TAB_CAPTURAS = "capturas"
TAB_GRAVACOES = "gravacoes"
_TAB_GAP = 16
_STRIP_PAD_H = 21


class MainRecentPanel(QFrame):
    """Painel com abas compactas alternando faixas de capturas e gravações."""

    capture_clicked = Signal(int)
    recording_clicked = Signal(int)

    def __init__(
        self,
        thumbnail_loader: MediaThumbnailLoader,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("main_recent_panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(BOTTOM_PANEL_HEIGHT)
        self._active_tab = TAB_CAPTURAS

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            _STRIP_PAD_H, STRIP_PAD_TOP, _STRIP_PAD_H, STRIP_PAD_BOTTOM
        )
        layout.setSpacing(STRIP_HEADER_TO_BODY)

        tab_row = QHBoxLayout()
        tab_row.setContentsMargins(0, 0, 0, 0)
        tab_row.setSpacing(_TAB_GAP)

        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tabs: dict[str, QPushButton] = {}

        for tab_id, label in (
            (TAB_CAPTURAS, "CAPTURAS"),
            (TAB_GRAVACOES, "GRAVAÇÕES"),
        ):
            button = QPushButton(label)
            button.setObjectName("main_recent_tab")
            button.setFixedHeight(STRIP_HEADER_HEIGHT)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFlat(True)
            button.setCheckable(True)
            button.clicked.connect(
                lambda _checked, tid=tab_id: self._on_tab_clicked(tid)
            )
            self._tab_group.addButton(button)
            self._tabs[tab_id] = button
            tab_row.addWidget(button)

        tab_row.addStretch()
        layout.addLayout(tab_row)

        self._stack = QStackedWidget()
        self._stack.setObjectName("main_recent_stack")
        layout.addWidget(self._stack)

        self._capture_strip = CaptureStrip(thumbnail_loader)
        self._capture_strip.item_clicked.connect(self.capture_clicked)
        self._stack.addWidget(self._capture_strip)

        self._recording_strip = RecordingStrip(thumbnail_loader)
        self._recording_strip.item_clicked.connect(self.recording_clicked)
        self._stack.addWidget(self._recording_strip)

        self._select_tab(TAB_CAPTURAS)

    def is_recordings_tab_active(self) -> bool:
        return self._active_tab == TAB_GRAVACOES

    def set_captures(
        self,
        captures: list[Capture],
        *,
        load_thumbnails: bool | None = None,
    ) -> None:
        if load_thumbnails is None:
            load_thumbnails = not self.is_recordings_tab_active()
        self._capture_strip.set_captures(
            captures,
            load_thumbnails=load_thumbnails,
        )

    def set_recordings(
        self,
        recordings: list[Recording],
        *,
        load_thumbnails: bool | None = None,
    ) -> None:
        if load_thumbnails is None:
            load_thumbnails = self.is_recordings_tab_active()
        self._recording_strip.set_recordings(
            recordings,
            load_thumbnails=load_thumbnails,
        )

    def _on_tab_clicked(self, tab_id: str) -> None:
        button = self._tabs[tab_id]
        if not button.isChecked():
            return
        self._select_tab(tab_id)

    def _select_tab(self, tab_id: str) -> None:
        self._active_tab = tab_id
        button = self._tabs[tab_id]
        button.blockSignals(True)
        button.setChecked(True)
        button.blockSignals(False)
        for tid, tab_button in self._tabs.items():
            set_property(tab_button, "active", tid == tab_id)
        self._stack.setCurrentIndex(0 if tab_id == TAB_CAPTURAS else 1)
        if tab_id == TAB_CAPTURAS:
            self._capture_strip.load_thumbnails()
        elif tab_id == TAB_GRAVACOES:
            self._recording_strip.load_thumbnails()
