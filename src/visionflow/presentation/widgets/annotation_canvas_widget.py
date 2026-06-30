"""Canvas de anotação: desenha retângulos e polígonos sobre uma imagem.

Coordenadas internas das formas são em pixels da imagem (não do widget); o
mapeamento imagem↔widget usa *letterbox* (igual ao editor de recorte). A
conversão para normalizado (0..1) é responsabilidade de quem consome o sinal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QPolygon,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from visionflow.domain.entities.yolo import (
    ANNOTATION_KIND_POLYGON,
    ANNOTATION_KIND_RECT,
)

_PREVIEW_MIN_WIDTH = 480
_PREVIEW_MIN_HEIGHT = 360
_MIN_RECT_SIZE = 3
_FILL_ALPHA = 60
_VERTEX_RADIUS = 4
_HANDLE_HALF = 5
_HANDLE_HIT = 10

# Ferramentas suportadas pelo canvas.
TOOL_RECT = ANNOTATION_KIND_RECT
TOOL_POLYGON = ANNOTATION_KIND_POLYGON
TOOL_SELECT = "select"

# Modos de arraste durante a edição da forma selecionada.
_EDIT_MOVE = "move"
_EDIT_VERTEX = "vertex"
_EDIT_CORNER = "corner"


@dataclass
class AnnotationShape:
    """Forma desenhada (em coordenadas de pixel da imagem)."""

    kind: str
    points: list[tuple[int, int]]
    color: str
    selected: bool = field(default=False)


@dataclass
class _EditDrag:
    """Estado de um arraste de edição da forma selecionada.

    ``index`` é a posição da forma em ``_shapes``; ``mode`` é um dos modos
    ``_EDIT_*``. Conforme o modo: ``vertex`` (índice do vértice movido),
    ``anchor`` (canto fixo oposto no redimensionamento) e ``last`` (último
    ponto de imagem durante o movimento).
    """

    index: int
    mode: str
    vertex: int = 0
    anchor: tuple[int, int] = (0, 0)
    last: tuple[int, int] = (0, 0)


class AnnotationCanvasWidget(QWidget):
    """Exibe a imagem e captura desenho de retângulos e polígonos."""

    shape_completed = Signal(str, object)
    shape_edited = Signal(int, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("capture_edit_preview")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumSize(_PREVIEW_MIN_WIDTH, _PREVIEW_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._image = QImage()
        self._display_pixmap = QPixmap()
        self._shapes: list[AnnotationShape] = []
        self._tool = TOOL_RECT
        self._active_color = "#0066CC"

        self._drawing_rect = False
        self._rect_origin = QPoint()
        self._rect_current = QPoint()
        self._polygon_points: list[tuple[int, int]] = []
        self._cursor_image_point: tuple[int, int] | None = None
        self._edit_drag: _EditDrag | None = None

    def set_image(self, image: QImage) -> None:
        self._image = image.copy() if not image.isNull() else QImage()
        self._reset_in_progress()
        self._rebuild_display_pixmap()
        self.update()

    def set_shapes(self, shapes: list[AnnotationShape]) -> None:
        self._shapes = shapes
        self.update()

    def set_tool(self, tool: str) -> None:
        if tool == self._tool:
            return
        self._tool = tool
        self._reset_in_progress()
        self.update()

    def set_active_color(self, color: str) -> None:
        self._active_color = color or "#0066CC"

    def clear_in_progress(self) -> None:
        self._reset_in_progress()
        self.update()

    def undo_last_point(self) -> None:
        if self._polygon_points:
            self._polygon_points.pop()
            self.update()

    def finish_polygon(self) -> None:
        if self._tool != TOOL_POLYGON:
            return
        points = self._dedupe(self._polygon_points)
        if len(points) >= 3:
            self.shape_completed.emit(TOOL_POLYGON, points)
        self._reset_in_progress()
        self.update()

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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale, offset_x, offset_y, _, _ = self._layout_metrics()
        painter.drawPixmap(offset_x, offset_y, self._display_pixmap)

        for shape in self._shapes:
            self._paint_shape(painter, shape, scale, offset_x, offset_y)
        self._paint_in_progress(painter, scale, offset_x, offset_y)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._image.isNull():
            return
        if self._tool == TOOL_SELECT:
            if self._begin_edit(event.position().toPoint()):
                event.accept()
            return
        image_point = self._widget_to_image(event.position().toPoint())
        if image_point is None:
            return
        if self._tool == TOOL_RECT:
            self._drawing_rect = True
            self._rect_origin = QPoint(*image_point)
            self._rect_current = QPoint(*image_point)
        else:
            self._polygon_points.append(image_point)
        self.update()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._image.isNull():
            return
        image_point = self._widget_to_image(event.position().toPoint(), clamp=True)
        if image_point is None:
            return
        self._cursor_image_point = image_point
        if self._edit_drag is not None:
            self._apply_edit(image_point)
            self.update()
            event.accept()
            return
        if self._drawing_rect:
            self._rect_current = QPoint(*image_point)
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._edit_drag is not None:
            index = self._edit_drag.index
            self._edit_drag = None
            if 0 <= index < len(self._shapes):
                self.shape_edited.emit(index, list(self._shapes[index].points))
            self.update()
            event.accept()
            return
        if self._tool == TOOL_RECT and self._drawing_rect:
            self._drawing_rect = False
            origin = self._rect_origin
            current = self._rect_current
            left, top = min(origin.x(), current.x()), min(origin.y(), current.y())
            right, bottom = max(origin.x(), current.x()), max(origin.y(), current.y())
            if right - left >= _MIN_RECT_SIZE and bottom - top >= _MIN_RECT_SIZE:
                self.shape_completed.emit(TOOL_RECT, [(left, top), (right, bottom)])
            self.update()
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self._tool == TOOL_POLYGON:
            self.finish_polygon()
            event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.finish_polygon()
        elif key == Qt.Key.Key_Escape:
            self.clear_in_progress()
        elif key == Qt.Key.Key_Backspace:
            self.undo_last_point()
        else:
            super().keyPressEvent(event)

    def _paint_shape(
        self,
        painter: QPainter,
        shape: AnnotationShape,
        scale: float,
        offset_x: int,
        offset_y: int,
    ) -> None:
        if not shape.points:
            return
        color = QColor(shape.color)
        fill = QColor(color)
        fill.setAlpha(_FILL_ALPHA)
        width = 3 if shape.selected else 2
        painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine))
        painter.setBrush(fill)
        widget_points = [
            self._image_to_widget(x, y, scale, offset_x, offset_y)
            for x, y in shape.points
        ]
        if shape.kind == ANNOTATION_KIND_RECT and len(widget_points) == 2:
            painter.drawRect(QRect(widget_points[0], widget_points[1]).normalized())
        else:
            painter.drawPolygon(QPolygon(widget_points))
        if shape.selected:
            self._paint_handles(painter, shape, scale, offset_x, offset_y)

    def _paint_handles(
        self,
        painter: QPainter,
        shape: AnnotationShape,
        scale: float,
        offset_x: int,
        offset_y: int,
    ) -> None:
        painter.setPen(QPen(QColor(shape.color), 1, Qt.PenStyle.SolidLine))
        painter.setBrush(QColor("#FFFFFF"))
        for x, y in self._handle_points(shape):
            center = self._image_to_widget(x, y, scale, offset_x, offset_y)
            painter.drawRect(
                center.x() - _HANDLE_HALF,
                center.y() - _HANDLE_HALF,
                2 * _HANDLE_HALF,
                2 * _HANDLE_HALF,
            )

    def _paint_in_progress(
        self,
        painter: QPainter,
        scale: float,
        offset_x: int,
        offset_y: int,
    ) -> None:
        color = QColor(self._active_color)
        fill = QColor(color)
        fill.setAlpha(_FILL_ALPHA)
        painter.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self._tool == TOOL_RECT and self._drawing_rect:
            start = self._image_to_widget(
                self._rect_origin.x(), self._rect_origin.y(), scale, offset_x, offset_y
            )
            end = self._image_to_widget(
                self._rect_current.x(),
                self._rect_current.y(),
                scale,
                offset_x,
                offset_y,
            )
            painter.setBrush(fill)
            painter.drawRect(QRect(start, end).normalized())
            return

        if self._tool == TOOL_POLYGON and self._polygon_points:
            widget_points = [
                self._image_to_widget(x, y, scale, offset_x, offset_y)
                for x, y in self._polygon_points
            ]
            preview = list(widget_points)
            if self._cursor_image_point is not None:
                preview.append(
                    self._image_to_widget(
                        *self._cursor_image_point, scale, offset_x, offset_y
                    )
                )
            painter.drawPolyline(QPolygon(preview))
            painter.setBrush(color)
            painter.setPen(QPen(color, 1))
            for point in widget_points:
                painter.drawEllipse(point, _VERTEX_RADIUS, _VERTEX_RADIUS)

    # ----- edição da forma selecionada ------------------------------------

    def _selected_index(self) -> int | None:
        for index, shape in enumerate(self._shapes):
            if shape.selected:
                return index
        return None

    @staticmethod
    def _handle_points(shape: AnnotationShape) -> list[tuple[int, int]]:
        if shape.kind == ANNOTATION_KIND_RECT and len(shape.points) == 2:
            return AnnotationCanvasWidget._rect_corners(shape.points)
        return list(shape.points)

    @staticmethod
    def _rect_corners(
        points: list[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        (x0, y0), (x1, y1) = points
        left, right = min(x0, x1), max(x0, x1)
        top, bottom = min(y0, y1), max(y0, y1)
        return [(left, top), (right, top), (right, bottom), (left, bottom)]

    def _nearest_handle(self, pos: QPoint, widget_points: list[QPoint]) -> int | None:
        for index, point in enumerate(widget_points):
            if (point - pos).manhattanLength() <= _HANDLE_HIT:
                return index
        return None

    def _begin_edit(self, pos: QPoint) -> bool:
        index = self._selected_index()
        if index is None:
            return False
        shape = self._shapes[index]
        scale, offset_x, offset_y, _, _ = self._layout_metrics()
        handle_points = self._handle_points(shape)
        widget_handles = [
            self._image_to_widget(x, y, scale, offset_x, offset_y)
            for x, y in handle_points
        ]
        hit = self._nearest_handle(pos, widget_handles)
        if hit is not None:
            if shape.kind == ANNOTATION_KIND_RECT and len(shape.points) == 2:
                self._edit_drag = _EditDrag(
                    index=index,
                    mode=_EDIT_CORNER,
                    anchor=handle_points[(hit + 2) % 4],
                )
            else:
                self._edit_drag = _EditDrag(index=index, mode=_EDIT_VERTEX, vertex=hit)
            return True
        if self._point_inside(pos, shape, scale, offset_x, offset_y):
            anchor = self._widget_to_image(pos, clamp=True)
            if anchor is not None:
                self._edit_drag = _EditDrag(index=index, mode=_EDIT_MOVE, last=anchor)
                return True
        return False

    def _point_inside(
        self,
        pos: QPoint,
        shape: AnnotationShape,
        scale: float,
        offset_x: int,
        offset_y: int,
    ) -> bool:
        widget_points = [
            self._image_to_widget(x, y, scale, offset_x, offset_y)
            for x, y in shape.points
        ]
        if shape.kind == ANNOTATION_KIND_RECT and len(widget_points) == 2:
            return QRect(widget_points[0], widget_points[1]).normalized().contains(pos)
        return QPolygon(widget_points).containsPoint(pos, Qt.FillRule.OddEvenFill)

    def _apply_edit(self, image_point: tuple[int, int]) -> None:
        drag = self._edit_drag
        if drag is None or not 0 <= drag.index < len(self._shapes):
            return
        shape = self._shapes[drag.index]
        if drag.mode == _EDIT_MOVE:
            self._move_shape(shape, drag, image_point)
        elif drag.mode == _EDIT_VERTEX:
            shape.points[drag.vertex] = image_point
        elif drag.mode == _EDIT_CORNER:
            shape.points = self._resize_rect(drag.anchor, image_point)

    def _move_shape(
        self,
        shape: AnnotationShape,
        drag: _EditDrag,
        image_point: tuple[int, int],
    ) -> None:
        last_x, last_y = drag.last
        dx, dy = image_point[0] - last_x, image_point[1] - last_y
        xs = [x for x, _ in shape.points]
        ys = [y for _, y in shape.points]
        max_x = self._image.width() - 1
        max_y = self._image.height() - 1
        dx = max(-min(xs), min(dx, max_x - max(xs)))
        dy = max(-min(ys), min(dy, max_y - max(ys)))
        shape.points = [(x + dx, y + dy) for x, y in shape.points]
        drag.last = image_point

    @staticmethod
    def _resize_rect(
        anchor: tuple[int, int], image_point: tuple[int, int]
    ) -> list[tuple[int, int]]:
        ax, ay = anchor
        left, right = min(ax, image_point[0]), max(ax, image_point[0])
        top, bottom = min(ay, image_point[1]), max(ay, image_point[1])
        if right - left < _MIN_RECT_SIZE:
            right = left + _MIN_RECT_SIZE
        if bottom - top < _MIN_RECT_SIZE:
            bottom = top + _MIN_RECT_SIZE
        return [(left, top), (right, bottom)]

    def _reset_in_progress(self) -> None:
        self._drawing_rect = False
        self._polygon_points = []
        self._cursor_image_point = None
        self._edit_drag = None

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

    @staticmethod
    def _image_to_widget(
        x: int,
        y: int,
        scale: float,
        offset_x: int,
        offset_y: int,
    ) -> QPoint:
        return QPoint(offset_x + int(x * scale), offset_y + int(y * scale))

    @staticmethod
    def _dedupe(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        for point in points:
            if not result or (
                abs(result[-1][0] - point[0]) > 2 or abs(result[-1][1] - point[1]) > 2
            ):
                result.append(point)
        return result
