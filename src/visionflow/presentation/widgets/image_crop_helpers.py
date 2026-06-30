"""Geometria de alças e lógica de interação do editor de recorte."""

from __future__ import annotations

from enum import IntEnum

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QPen

_MIN_CROP_SIZE = 1
_HANDLE_SIZE = 8
_HANDLE_HIT_PAD = 4
_SMALL_SELECTION_PX = _HANDLE_SIZE * 2


class CropHandle(IntEnum):
    NONE = 0
    TOP_LEFT = 1
    TOP = 2
    TOP_RIGHT = 3
    RIGHT = 4
    BOTTOM_RIGHT = 5
    BOTTOM = 6
    BOTTOM_LEFT = 7
    LEFT = 8


HANDLE_CURSORS: dict[CropHandle, Qt.CursorShape] = {
    CropHandle.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
    CropHandle.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
    CropHandle.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
    CropHandle.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
    CropHandle.TOP: Qt.CursorShape.SizeVerCursor,
    CropHandle.BOTTOM: Qt.CursorShape.SizeVerCursor,
    CropHandle.LEFT: Qt.CursorShape.SizeHorCursor,
    CropHandle.RIGHT: Qt.CursorShape.SizeHorCursor,
}


class CropHandleLayout:
    """Posicionamento, hit-test e desenho das alças de redimensionamento."""

    def rects(self, selection: QRect) -> dict[CropHandle, QRect]:
        half = _HANDLE_SIZE // 2
        cx = selection.center().x()
        cy = selection.center().y()

        def centered_at(x: int, y: int) -> QRect:
            return QRect(x - half, y - half, _HANDLE_SIZE, _HANDLE_SIZE)

        return {
            CropHandle.TOP_LEFT: centered_at(selection.left(), selection.top()),
            CropHandle.TOP: centered_at(cx, selection.top()),
            CropHandle.TOP_RIGHT: centered_at(selection.right(), selection.top()),
            CropHandle.RIGHT: centered_at(selection.right(), cy),
            CropHandle.BOTTOM_RIGHT: centered_at(selection.right(), selection.bottom()),
            CropHandle.BOTTOM: centered_at(cx, selection.bottom()),
            CropHandle.BOTTOM_LEFT: centered_at(selection.left(), selection.bottom()),
            CropHandle.LEFT: centered_at(selection.left(), cy),
        }

    def hit_test(self, point: QPoint, selection: QRect) -> CropHandle:
        if not selection.isValid() or selection.width() <= 0 or selection.height() <= 0:
            return CropHandle.NONE

        rects = self.rects(selection)
        small = (
            selection.width() < _SMALL_SELECTION_PX
            or selection.height() < _SMALL_SELECTION_PX
        )
        if small:
            return self._closest_handle(point, rects)

        hit_pad = _HANDLE_HIT_PAD
        for handle, rect in rects.items():
            hit = rect.adjusted(-hit_pad, -hit_pad, hit_pad, hit_pad)
            if hit.contains(point):
                return handle
        return CropHandle.NONE

    def paint_handles(
        self,
        painter: QPainter,
        handle_rects: dict[CropHandle, QRect],
        *,
        border_color,
        fill_color,
    ) -> None:
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(fill_color)
        for rect in handle_rects.values():
            painter.drawRect(rect)

    @staticmethod
    def _closest_handle(
        point: QPoint,
        rects: dict[CropHandle, QRect],
    ) -> CropHandle:
        best = CropHandle.NONE
        best_dist = float("inf")
        max_dist = (_HANDLE_SIZE // 2 + _HANDLE_HIT_PAD) ** 2
        for handle, rect in rects.items():
            center = rect.center()
            dist = (point.x() - center.x()) ** 2 + (point.y() - center.y()) ** 2
            if dist <= max_dist and dist < best_dist:
                best_dist = dist
                best = handle
        return best


class CropInteractionController:
    """Calcula retângulos de recorte para arraste, movimento e redimensionamento."""

    @staticmethod
    def new_selection(origin: QPoint, current: QPoint) -> tuple[int, int, int, int]:
        x1 = min(origin.x(), current.x())
        y1 = min(origin.y(), current.y())
        x2 = max(origin.x(), current.x())
        y2 = max(origin.y(), current.y())
        width = max(_MIN_CROP_SIZE, x2 - x1 + 1)
        height = max(_MIN_CROP_SIZE, y2 - y1 + 1)
        return x1, y1, width, height

    @staticmethod
    def move_selection(
        start_rect: tuple[int, int, int, int],
        origin: QPoint,
        current: QPoint,
        img_w: int,
        img_h: int,
    ) -> tuple[int, int, int, int]:
        start_x, start_y, crop_w, crop_h = start_rect
        delta_x = current.x() - origin.x()
        delta_y = current.y() - origin.y()
        new_x = max(0, min(start_x + delta_x, img_w - crop_w))
        new_y = max(0, min(start_y + delta_y, img_h - crop_h))
        return new_x, new_y, crop_w, crop_h

    @staticmethod
    def resize_selection(
        start_rect: tuple[int, int, int, int],
        handle: CropHandle,
        current: QPoint,
        img_w: int,
        img_h: int,
    ) -> tuple[int, int, int, int]:
        start_x, start_y, start_w, start_h = start_rect
        drag_x = current.x()
        drag_y = current.y()

        left = start_x
        top = start_y
        right = start_x + start_w - 1
        bottom = start_y + start_h - 1

        if handle in (CropHandle.TOP_LEFT, CropHandle.TOP, CropHandle.TOP_RIGHT):
            top = max(0, min(drag_y, bottom - _MIN_CROP_SIZE + 1))
        if handle in (
            CropHandle.BOTTOM_LEFT,
            CropHandle.BOTTOM,
            CropHandle.BOTTOM_RIGHT,
        ):
            bottom = min(img_h - 1, max(drag_y, top + _MIN_CROP_SIZE - 1))
        if handle in (CropHandle.TOP_LEFT, CropHandle.LEFT, CropHandle.BOTTOM_LEFT):
            left = max(0, min(drag_x, right - _MIN_CROP_SIZE + 1))
        if handle in (
            CropHandle.TOP_RIGHT,
            CropHandle.RIGHT,
            CropHandle.BOTTOM_RIGHT,
        ):
            right = min(img_w - 1, max(drag_x, left + _MIN_CROP_SIZE - 1))

        return left, top, right - left + 1, bottom - top + 1
