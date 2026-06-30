"""Base visual compartilhada das miniaturas da faixa da Principal."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QFrame, QLabel

from visionflow.presentation.image_utils import ndarray_to_qpixmap, rounded_pixmap
from visionflow.presentation.style_utils import set_property

STRIP_THUMB_WIDTH = 84
STRIP_THUMB_HEIGHT = 54
THUMB_BADGE_HEIGHT = 16
IMAGE_INSET = 1
IMAGE_RADIUS = 5


class StripThumbnailFrame(QFrame):
    """Miniatura clicável com imagem, overlay de hover e selo opcional."""

    clicked = Signal(int)

    def __init__(
        self,
        *,
        object_name_prefix: str,
        item_id: int,
        size: tuple[int, int] = (STRIP_THUMB_WIDTH, STRIP_THUMB_HEIGHT),
        badge_text: str | None = None,
        parent=None,
    ) -> None:
        width, height = size
        super().__init__(parent)
        self.setObjectName(object_name_prefix)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(width, height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._item_id = item_id
        image_width = width - 2 * IMAGE_INSET
        image_height = height - 2 * IMAGE_INSET
        self._image_width = image_width
        self._image_height = image_height

        self._image = QLabel(self)
        self._image.setObjectName(f"{object_name_prefix}_image")
        self._image.setGeometry(IMAGE_INSET, IMAGE_INSET, image_width, image_height)
        self._image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._hover_overlay = QFrame(self)
        self._hover_overlay.setObjectName(f"{object_name_prefix}_hover")
        self._hover_overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._hover_overlay.setGeometry(
            IMAGE_INSET,
            IMAGE_INSET,
            image_width,
            image_height,
        )
        self._hover_overlay.hide()

        if badge_text:
            badge = QLabel(badge_text, self)
            badge.setObjectName(f"{object_name_prefix}_badge")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setGeometry(
                IMAGE_INSET,
                height - THUMB_BADGE_HEIGHT - IMAGE_INSET,
                image_width,
                THUMB_BADGE_HEIGHT,
            )
            badge.raise_()

        self._hover_overlay.raise_()

    def set_image_pixmap(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        self._image.setPixmap(
            rounded_pixmap(
                pixmap,
                width=self._image_width,
                height=self._image_height,
                radius=IMAGE_RADIUS,
            )
        )

    def set_image_frame(self, frame: object) -> None:
        if not hasattr(frame, "shape"):
            return
        pixmap = ndarray_to_qpixmap(frame)
        self.set_image_pixmap(pixmap)

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
