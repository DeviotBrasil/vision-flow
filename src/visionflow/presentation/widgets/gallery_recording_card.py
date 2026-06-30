"""Card de gravação para a galeria (layout alinhado ao card de captura)."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from visionflow.domain.entities.recording import Recording
from visionflow.presentation.format_utils import format_captured_short
from visionflow.presentation.image_utils import ndarray_to_qpixmap, rounded_pixmap
from visionflow.presentation.style_utils import set_property
from visionflow.presentation.widgets.gallery_card_layout import (
    GALLERY_CARD_HEIGHT,
    GALLERY_CARD_IMAGE_INSET,
    GALLERY_CARD_IMAGE_RADIUS,
    GALLERY_CARD_OVERLAY_HEIGHT,
    GALLERY_CARD_WIDTH,
)
from visionflow.presentation.widgets.gallery_selectable_card_mixin import (
    GallerySelectableCardMixin,
)


class GalleryRecordingCard(GallerySelectableCardMixin, QFrame):
    """Miniatura da galeria com overlay de metadados."""

    clicked = Signal(int)
    selection_toggled = Signal(int, bool)

    def __init__(self, recording: Recording, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("gallery_recording_card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(GALLERY_CARD_WIDTH, GALLERY_CARD_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        recording_id = int(recording.id or 0)
        self._file_path = recording.file_path
        image_width = GALLERY_CARD_WIDTH - 2 * GALLERY_CARD_IMAGE_INSET
        image_height = GALLERY_CARD_HEIGHT - 2 * GALLERY_CARD_IMAGE_INSET

        self._image = QLabel(self)
        self._image.setObjectName("gallery_recording_card_image")
        self._image.setGeometry(
            GALLERY_CARD_IMAGE_INSET,
            GALLERY_CARD_IMAGE_INSET,
            image_width,
            image_height,
        )
        self._image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_width = image_width
        self._image_height = image_height

        self._hover_overlay = QFrame(self)
        self._hover_overlay.setObjectName("gallery_recording_card_hover")
        self._hover_overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._hover_overlay.setGeometry(
            GALLERY_CARD_IMAGE_INSET,
            GALLERY_CARD_IMAGE_INSET,
            image_width,
            image_height,
        )
        self._hover_overlay.hide()

        overlay = QFrame(self)
        overlay.setObjectName("gallery_recording_card_overlay")
        overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        overlay_top = (
            GALLERY_CARD_HEIGHT - GALLERY_CARD_OVERLAY_HEIGHT - GALLERY_CARD_IMAGE_INSET
        )
        overlay.setGeometry(
            GALLERY_CARD_IMAGE_INSET,
            overlay_top,
            GALLERY_CARD_WIDTH - 2 * GALLERY_CARD_IMAGE_INSET,
            GALLERY_CARD_OVERLAY_HEIGHT,
        )

        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(8, 6, 8, 6)
        overlay_layout.setSpacing(0)

        if recording.id is not None:
            id_label = QLabel(f"#{recording.id:03d}")
            id_label.setObjectName("gallery_recording_card_filename")
            overlay_layout.addWidget(id_label)

        date_label = QLabel(format_captured_short(recording.recorded_at))
        date_label.setObjectName("gallery_recording_card_datetime")
        overlay_layout.addWidget(date_label)

        if recording_id > 0:
            self._init_gallery_selection_ui(
                item_id=recording_id,
                card_width=GALLERY_CARD_WIDTH,
            )
        else:
            self._item_id = 0

        self._hover_overlay.raise_()
        overlay.raise_()
        if recording_id > 0:
            self._raise_selection_checkbox()

    def _emit_selection_toggled(self, checked: bool) -> None:
        self.selection_toggled.emit(self._item_id, checked)

    def has_thumbnail(self) -> bool:
        pixmap = self._image.pixmap()
        return pixmap is not None and not pixmap.isNull()

    def set_thumbnail(self, frame: object) -> None:
        """Aplica miniatura RGB8 carregada de forma assíncrona."""
        if not hasattr(frame, "shape"):
            return
        pixmap = ndarray_to_qpixmap(frame)
        if pixmap.isNull():
            return
        self._image.setPixmap(
            rounded_pixmap(
                pixmap,
                width=self._image_width,
                height=self._image_height,
                radius=GALLERY_CARD_IMAGE_RADIUS,
            )
        )

    def enterEvent(self, event: QEvent) -> None:
        set_property(self, "hovered", True)
        self._hover_overlay.show()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        set_property(self, "hovered", False)
        self._hover_overlay.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._item_id > 0:
            self.clicked.emit(self._item_id)
        super().mousePressEvent(event)
