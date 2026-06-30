"""Widget de preview com seleção interativa de região para recorte."""

from __future__ import annotations

from enum import IntEnum

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QCursor,
    QImage,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QShowEvent,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from visionflow.presentation.crop_editor_style import (
    crop_handle_fill_color,
    crop_overlay_color,
    crop_selection_color,
)
from visionflow.presentation.themes.theme_manager import ThemeManager
from visionflow.presentation.widgets.image_crop_helpers import (
    HANDLE_CURSORS,
    CropHandle,
    CropHandleLayout,
    CropInteractionController,
)

_MIN_CROP_SIZE = 1
_PREVIEW_MIN_WIDTH = 480
_PREVIEW_MIN_HEIGHT = 320


class _CropInteraction(IntEnum):
    NONE = 0
    NEW = 1
    MOVE = 2
    RESIZE = 3


class ImageCropWidget(QWidget):
    """Exibe a imagem escalada e permite definir um retângulo de recorte."""

    crop_rect_changed = Signal(int, int, int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("capture_edit_preview")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumSize(_PREVIEW_MIN_WIDTH, _PREVIEW_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self._handle_layout = CropHandleLayout()
        self._interaction_ctrl = CropInteractionController()
        self._theme_connected = False
        self._selection_color = crop_selection_color()
        self._handle_fill_color = crop_handle_fill_color()
        self._overlay_color = crop_overlay_color()
        self._image = QImage()
        self._display_pixmap = QPixmap()
        self._crop_x = 0
        self._crop_y = 0
        self._crop_w = 0
        self._crop_h = 0
        self._interaction = _CropInteraction.NONE
        self._active_handle = CropHandle.NONE
        self._drag_origin = QPoint()
        self._drag_current = QPoint()
        self._drag_start_rect = (0, 0, 0, 0)

    def set_image(self, image: QImage) -> None:
        self._image = image.copy() if not image.isNull() else QImage()
        if self._image.isNull():
            self._display_pixmap = QPixmap()
            self._crop_x = 0
            self._crop_y = 0
            self._crop_w = 0
            self._crop_h = 0
        else:
            self._crop_x = 0
            self._crop_y = 0
            self._crop_w = self._image.width()
            self._crop_h = self._image.height()
        self._rebuild_display_pixmap()
        self.update()
        self._emit_crop_rect()

    def crop_rect(self) -> tuple[int, int, int, int]:
        return self._crop_x, self._crop_y, self._crop_w, self._crop_h

    def set_crop_rect(self, x: int, y: int, width: int, height: int) -> None:
        self._apply_crop_rect(x, y, width, height, emit=True)

    def showEvent(self, event: QShowEvent) -> None:
        self._connect_theme()
        self._refresh_theme_colors()
        super().showEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._rebuild_display_pixmap()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        if self._display_pixmap.isNull():
            painter.end()
            return

        scale, offset_x, offset_y, _, _ = self._layout_metrics()
        painter.drawPixmap(offset_x, offset_y, self._display_pixmap)

        sel = self._selection_rect_widget(scale, offset_x, offset_y)
        if sel.isValid() and sel.width() > 0 and sel.height() > 0:
            overlay = self._overlay_color
            full = self.rect()
            painter.fillRect(0, 0, full.width(), sel.top(), overlay)
            painter.fillRect(
                0,
                sel.bottom() + 1,
                full.width(),
                full.height() - sel.bottom() - 1,
                overlay,
            )
            painter.fillRect(
                0,
                sel.top(),
                sel.left(),
                sel.height(),
                overlay,
            )
            painter.fillRect(
                sel.right() + 1,
                sel.top(),
                full.width() - sel.right() - 1,
                sel.height(),
                overlay,
            )

            pen = QPen(self._selection_color, 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(sel)

            handle_rects = self._handle_layout.rects(sel)
            self._handle_layout.paint_handles(
                painter,
                handle_rects,
                border_color=self._selection_color,
                fill_color=self._handle_fill_color,
            )
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._image.isNull():
            return
        widget_point = event.position().toPoint()
        scale, offset_x, offset_y, _, _ = self._layout_metrics()
        selection = self._selection_rect_widget(scale, offset_x, offset_y)
        handle = self._handle_layout.hit_test(widget_point, selection)
        image_point = self._widget_to_image(widget_point)
        if image_point is None:
            return

        self._drag_origin = QPoint(*image_point)
        self._drag_current = self._drag_origin
        self._drag_start_rect = self.crop_rect()

        if handle != CropHandle.NONE:
            self._interaction = _CropInteraction.RESIZE
            self._active_handle = handle
        elif self._should_move_selection(image_point[0], image_point[1]):
            self._interaction = _CropInteraction.MOVE
            self._active_handle = CropHandle.NONE
        else:
            self._interaction = _CropInteraction.NEW
            self._active_handle = CropHandle.NONE
            self._apply_new_selection(emit=False)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        widget_point = event.position().toPoint()
        if self._image.isNull():
            return

        if self._interaction == _CropInteraction.NONE:
            self._update_hover_cursor(widget_point)
            return

        image_point = self._widget_to_image(widget_point, clamp=True)
        if image_point is None:
            return
        self._drag_current = QPoint(*image_point)

        if self._interaction == _CropInteraction.NEW:
            self._apply_new_selection(emit=False)
        elif self._interaction == _CropInteraction.MOVE:
            self._apply_move_selection(emit=False)
        elif self._interaction == _CropInteraction.RESIZE:
            self._apply_resize_selection(emit=False)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            had_interaction = self._interaction != _CropInteraction.NONE
            self._interaction = _CropInteraction.NONE
            self._active_handle = CropHandle.NONE
            if had_interaction:
                self._emit_crop_rect()
            self._update_hover_cursor(event.position().toPoint())
        event.accept()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.unsetCursor()

    def _connect_theme(self) -> None:
        if self._theme_connected:
            return
        manager = self._theme_manager()
        if manager is None:
            return
        manager.theme_changed.connect(self._on_theme_changed)
        self._theme_connected = True

    def _theme_manager(self) -> ThemeManager | None:
        window = self.window()
        manager = getattr(window, "theme_manager", None)
        return manager if isinstance(manager, ThemeManager) else None

    def _on_theme_changed(self, _theme_name: str) -> None:
        self._refresh_theme_colors()

    def _refresh_theme_colors(self) -> None:
        self._selection_color = crop_selection_color()
        self._handle_fill_color = crop_handle_fill_color()
        self.update()

    def _apply_crop_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        *,
        emit: bool,
    ) -> None:
        if self._image.isNull():
            return
        img_w = self._image.width()
        img_h = self._image.height()
        x = max(0, min(x, img_w - 1))
        y = max(0, min(y, img_h - 1))
        width = max(_MIN_CROP_SIZE, min(width, img_w - x))
        height = max(_MIN_CROP_SIZE, min(height, img_h - y))
        if (x, y, width, height) == (
            self._crop_x,
            self._crop_y,
            self._crop_w,
            self._crop_h,
        ):
            return
        self._crop_x = x
        self._crop_y = y
        self._crop_w = width
        self._crop_h = height
        self.update()
        if emit:
            self._emit_crop_rect()

    def _apply_new_selection(self, *, emit: bool) -> None:
        rect = self._interaction_ctrl.new_selection(
            self._drag_origin,
            self._drag_current,
        )
        self._apply_crop_rect(*rect, emit=emit)

    def _apply_move_selection(self, *, emit: bool) -> None:
        rect = self._interaction_ctrl.move_selection(
            self._drag_start_rect,
            self._drag_origin,
            self._drag_current,
            self._image.width(),
            self._image.height(),
        )
        self._apply_crop_rect(*rect, emit=emit)

    def _apply_resize_selection(self, *, emit: bool) -> None:
        rect = self._interaction_ctrl.resize_selection(
            self._drag_start_rect,
            self._active_handle,
            self._drag_current,
            self._image.width(),
            self._image.height(),
        )
        self._apply_crop_rect(*rect, emit=emit)

    def _is_full_image_crop(self) -> bool:
        if self._image.isNull():
            return False
        return (
            self._crop_x == 0
            and self._crop_y == 0
            and self._crop_w == self._image.width()
            and self._crop_h == self._image.height()
        )

    def _should_move_selection(self, x: int, y: int) -> bool:
        return self._point_in_crop(x, y) and not self._is_full_image_crop()

    def _point_in_crop(self, x: int, y: int) -> bool:
        return (
            self._crop_x <= x <= self._crop_x + self._crop_w - 1
            and self._crop_y <= y <= self._crop_y + self._crop_h - 1
        )

    def _update_hover_cursor(self, widget_point: QPoint) -> None:
        scale, offset_x, offset_y, _, _ = self._layout_metrics()
        selection = self._selection_rect_widget(scale, offset_x, offset_y)
        handle = self._handle_layout.hit_test(widget_point, selection)
        if handle != CropHandle.NONE:
            self.setCursor(QCursor(HANDLE_CURSORS[handle]))
            return

        image_point = self._widget_to_image(widget_point)
        if image_point is not None and self._should_move_selection(*image_point):
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
            return

        if image_point is not None:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        else:
            self.unsetCursor()

    def _emit_crop_rect(self) -> None:
        self.crop_rect_changed.emit(
            self._crop_x,
            self._crop_y,
            self._crop_w,
            self._crop_h,
        )

    def _rebuild_display_pixmap(self) -> None:
        if self._image.isNull():
            self._display_pixmap = QPixmap()
            return
        _scale, _, _, disp_w, disp_h = self._layout_metrics()
        if disp_w <= 0 or disp_h <= 0:
            self._display_pixmap = QPixmap()
            return
        self._display_pixmap = QPixmap.fromImage(
            self._image.scaled(
                disp_w,
                disp_h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _layout_metrics(self) -> tuple[float, int, int, int, int]:
        if self._image.isNull():
            return 1.0, 0, 0, 0, 0
        widget_w = max(self.width(), 1)
        widget_h = max(self.height(), 1)
        img_w = self._image.width()
        img_h = self._image.height()
        scale = min(widget_w / img_w, widget_h / img_h)
        disp_w = max(1, int(img_w * scale))
        disp_h = max(1, int(img_h * scale))
        offset_x = (widget_w - disp_w) // 2
        offset_y = (widget_h - disp_h) // 2
        return scale, offset_x, offset_y, disp_w, disp_h

    def _widget_to_image(
        self,
        point: QPoint,
        *,
        clamp: bool = False,
    ) -> tuple[int, int] | None:
        if self._image.isNull():
            return None
        scale, offset_x, offset_y, disp_w, disp_h = self._layout_metrics()
        image_rect = QRect(offset_x, offset_y, disp_w, disp_h)
        if not image_rect.contains(point):
            if not clamp:
                return None
            x = max(offset_x, min(point.x(), offset_x + disp_w - 1))
            y = max(offset_y, min(point.y(), offset_y + disp_h - 1))
            point = QPoint(x, y)
        img_x = int((point.x() - offset_x) / scale)
        img_y = int((point.y() - offset_y) / scale)
        img_x = max(0, min(img_x, self._image.width() - 1))
        img_y = max(0, min(img_y, self._image.height() - 1))
        return img_x, img_y

    def _selection_rect_widget(
        self,
        scale: float,
        offset_x: int,
        offset_y: int,
    ) -> QRect:
        left = offset_x + int(self._crop_x * scale)
        top = offset_y + int(self._crop_y * scale)
        width = max(1, int(self._crop_w * scale))
        height = max(1, int(self._crop_h * scale))
        return QRect(left, top, width, height)
