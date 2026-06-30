"""Diálogo modal de anotação de uma imagem do dataset YOLO."""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from visionflow.branding import SETTINGS_ANNOTATION_LAST_CLASS
from visionflow.domain.entities.yolo import (
    ANNOTATION_KIND_RECT,
    YoloAnnotation,
    YoloClass,
    YoloDatasetImage,
)
from visionflow.domain.use_cases.yolo_dataset import YoloDatasetService
from visionflow.presentation.app_settings import app_settings
from visionflow.presentation.preview_size_utils import (
    DIALOG_ACTIONS_SPACING,
    DIALOG_BODY_PAD,
)
from visionflow.presentation.system_dialogs import (
    apply_dialog_theme,
    show_info_message,
)
from visionflow.presentation.widgets.annotation_canvas_widget import (
    TOOL_POLYGON,
    TOOL_RECT,
    TOOL_SELECT,
    AnnotationCanvasWidget,
    AnnotationShape,
)
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_DANGER_OUTLINE,
    VARIANT_NEUTRAL_OUTLINE,
    VARIANT_PRIMARY,
    VARIANT_PRIMARY_OUTLINE,
    create_button,
    set_variant,
)
from visionflow.presentation.window_chrome import apply_native_dialog_flags

_DIALOG_MIN_WIDTH = 880
_DIALOG_MIN_HEIGHT = 600
_SIDE_PANEL_WIDTH = 260


@dataclass
class _WorkingAnnotation:
    """Anotação em edição, com pontos em coordenadas de pixel da imagem."""

    class_id: int
    kind: str
    points: list[tuple[int, int]] = field(default_factory=list)


class AnnotationDialog(QDialog):
    """Editor visual de anotações (retângulos e polígonos) de uma imagem."""

    def __init__(
        self,
        image: YoloDatasetImage,
        service: YoloDatasetService,
        classes: list[YoloClass],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._image_record = image
        self._service = service
        self._classes = classes
        self._class_by_id = {int(item.id or 0): item for item in classes}
        self._qimage = self._load_image(image.file_path or "")
        self._img_w = max(self._qimage.width(), 1)
        self._img_h = max(self._qimage.height(), 1)
        self._annotations: list[_WorkingAnnotation] = []

        apply_native_dialog_flags(self)
        self.setObjectName("annotation_dialog")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setModal(True)
        self.setWindowTitle(f"Anotar imagem #{image.capture_id}")
        self.setMinimumSize(_DIALOG_MIN_WIDTH, _DIALOG_MIN_HEIGHT)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            DIALOG_BODY_PAD, DIALOG_BODY_PAD, DIALOG_BODY_PAD, DIALOG_BODY_PAD
        )
        root.setSpacing(DIALOG_ACTIONS_SPACING)

        root.addWidget(self._build_subtitle())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(DIALOG_ACTIONS_SPACING)

        self._canvas = AnnotationCanvasWidget()
        self._canvas.set_image(self._qimage)
        self._canvas.shape_completed.connect(self._on_shape_completed)
        self._canvas.shape_edited.connect(self._on_shape_edited)
        body.addWidget(self._canvas, 1)
        body.addWidget(self._build_side_panel())
        root.addLayout(body, 1)

        root.addLayout(self._build_actions())

        self._load_existing_annotations()
        self._restore_last_active_class()
        self._on_class_changed()
        self._select_tool(TOOL_RECT)
        self._refresh_canvas_shapes()
        apply_dialog_theme(self)

    def showEvent(self, event: QShowEvent) -> None:
        apply_dialog_theme(self)
        super().showEvent(event)

    def _build_subtitle(self) -> QLabel:
        if not self._classes:
            text = "Crie ao menos uma classe no dataset antes de anotar."
        else:
            text = (
                "Retângulo: arraste. Polígono: clique para adicionar pontos e "
                "dê duplo-clique (ou Enter) para fechar. Mover / Redimensionar: "
                "selecione uma anotação na lista e arraste as alças ou o interior."
            )
        label = QLabel(text)
        label.setObjectName("capture_edit_subtitle")
        label.setWordWrap(True)
        return label

    def _build_side_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(_SIDE_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self._panel_label("Classe ativa"))
        self._class_combo = QComboBox()
        for item in self._classes:
            self._class_combo.addItem(item.name, int(item.id or 0))
        self._class_combo.setEnabled(bool(self._classes))
        self._class_combo.currentIndexChanged.connect(self._on_class_changed)
        layout.addWidget(self._class_combo)

        layout.addWidget(self._panel_label("Ferramenta"))
        tools = QHBoxLayout()
        tools.setContentsMargins(0, 0, 0, 0)
        tools.setSpacing(6)
        self._rect_button = create_button(
            "Retângulo", variant=VARIANT_PRIMARY_OUTLINE, shape=SHAPE_PILL
        )
        self._rect_button.clicked.connect(lambda: self._select_tool(TOOL_RECT))
        self._polygon_button = create_button(
            "Polígono", variant=VARIANT_PRIMARY_OUTLINE, shape=SHAPE_PILL
        )
        self._polygon_button.clicked.connect(lambda: self._select_tool(TOOL_POLYGON))
        tools.addWidget(self._rect_button)
        tools.addWidget(self._polygon_button)
        layout.addLayout(tools)

        self._edit_button = create_button(
            "Mover / Redimensionar",
            variant=VARIANT_PRIMARY_OUTLINE,
            shape=SHAPE_PILL,
        )
        self._edit_button.clicked.connect(lambda: self._select_tool(TOOL_SELECT))
        layout.addWidget(self._edit_button)

        self._finish_button = create_button(
            "Concluir polígono", variant=VARIANT_PRIMARY_OUTLINE, shape=SHAPE_PILL
        )
        self._finish_button.clicked.connect(self._canvas_finish_polygon)
        layout.addWidget(self._finish_button)

        self._undo_button = create_button(
            "Desfazer ponto", variant=VARIANT_NEUTRAL_OUTLINE, shape=SHAPE_PILL
        )
        self._undo_button.clicked.connect(self._on_undo_clicked)
        layout.addWidget(self._undo_button)

        layout.addWidget(self._panel_label("Anotações"))
        self._list = QListWidget()
        self._list.setObjectName("annotation_list")
        self._list.currentRowChanged.connect(self._refresh_canvas_shapes)
        layout.addWidget(self._list, 1)

        self._remove_button = create_button(
            "Remover anotação", variant=VARIANT_DANGER_OUTLINE, shape=SHAPE_PILL
        )
        self._remove_button.clicked.connect(self._on_remove_annotation)
        layout.addWidget(self._remove_button)

        return panel

    def _build_actions(self) -> QHBoxLayout:
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(DIALOG_ACTIONS_SPACING)
        cancel = create_button(
            "Cancelar", variant=VARIANT_NEUTRAL_OUTLINE, shape=SHAPE_PILL
        )
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        actions.addStretch()
        save = create_button("Salvar", variant=VARIANT_PRIMARY, shape=SHAPE_PILL)
        save.clicked.connect(self._on_save)
        actions.addWidget(save)
        return actions

    @staticmethod
    def _panel_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("capture_edit_field_label")
        return label

    def _select_tool(self, tool: str) -> None:
        self._tool = tool
        self._canvas.set_tool(tool)
        for button, value in (
            (self._rect_button, TOOL_RECT),
            (self._polygon_button, TOOL_POLYGON),
            (self._edit_button, TOOL_SELECT),
        ):
            set_variant(
                button,
                VARIANT_PRIMARY if tool == value else VARIANT_PRIMARY_OUTLINE,
            )
        is_polygon = tool == TOOL_POLYGON
        self._finish_button.setEnabled(is_polygon)
        self._undo_button.setEnabled(is_polygon)

    def _canvas_finish_polygon(self) -> None:
        self._canvas.finish_polygon()

    def _on_undo_clicked(self) -> None:
        self._canvas.undo_last_point()

    def _active_class_id(self) -> int | None:
        if not self._classes:
            return None
        data = self._class_combo.currentData()
        return int(data) if data is not None else None

    def _restore_last_active_class(self) -> None:
        raw = app_settings().value(SETTINGS_ANNOTATION_LAST_CLASS)
        if raw is None:
            return
        try:
            class_id = int(raw)
        except (TypeError, ValueError):
            return
        if class_id not in self._class_by_id:
            return
        index = self._class_combo.findData(class_id)
        if index >= 0:
            self._class_combo.setCurrentIndex(index)

    def _on_class_changed(self) -> None:
        class_id = self._active_class_id()
        if class_id is not None and class_id in self._class_by_id:
            app_settings().setValue(SETTINGS_ANNOTATION_LAST_CLASS, class_id)
            self._canvas.set_active_color(self._class_by_id[class_id].color)

    def _on_shape_completed(self, kind: str, points: object) -> None:
        class_id = self._active_class_id()
        if class_id is None:
            show_info_message(
                self,
                "Anotar imagem",
                "Crie e selecione uma classe antes de desenhar.",
            )
            return
        image_points = [(int(x), int(y)) for x, y in points]  # type: ignore[misc]
        self._annotations.append(
            _WorkingAnnotation(class_id=class_id, kind=kind, points=image_points)
        )
        self._canvas.clear_in_progress()
        self._refresh_list()
        self._list.setCurrentRow(len(self._annotations) - 1)
        self._refresh_canvas_shapes()

    def _on_shape_edited(self, index: int, points: object) -> None:
        if not 0 <= index < len(self._annotations):
            return
        self._annotations[index].points = [
            (int(x), int(y))
            for x, y in points  # type: ignore[misc]
        ]
        self._refresh_canvas_shapes()

    def _on_remove_annotation(self) -> None:
        row = self._list.currentRow()
        if 0 <= row < len(self._annotations):
            self._annotations.pop(row)
            self._refresh_list()
            self._refresh_canvas_shapes()

    def _on_save(self) -> None:
        image_id = int(self._image_record.id or 0)
        annotations = [
            YoloAnnotation(
                image_id=image_id,
                class_id=working.class_id,
                kind=working.kind,
                points=self._to_normalized(working.points),
            )
            for working in self._annotations
        ]
        self._service.set_annotations(image_id, annotations)
        self.accept()

    def _load_existing_annotations(self) -> None:
        image_id = int(self._image_record.id or 0)
        for annotation in self._service.list_annotations(image_id):
            self._annotations.append(
                _WorkingAnnotation(
                    class_id=annotation.class_id,
                    kind=annotation.kind,
                    points=self._to_image_coords(annotation.points),
                )
            )
        self._refresh_list()

    def _refresh_list(self) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for index, working in enumerate(self._annotations, start=1):
            class_name = self._class_name(working.class_id)
            kind_label = (
                "retângulo" if working.kind == ANNOTATION_KIND_RECT else "polígono"
            )
            item = QListWidgetItem(f"#{index} {class_name} — {kind_label}")
            self._list.addItem(item)
        self._list.blockSignals(False)

    def _refresh_canvas_shapes(self) -> None:
        current = self._list.currentRow()
        shapes = [
            AnnotationShape(
                kind=working.kind,
                points=list(working.points),
                color=self._class_color(working.class_id),
                selected=index == current,
            )
            for index, working in enumerate(self._annotations)
        ]
        self._canvas.set_shapes(shapes)

    def _class_name(self, class_id: int) -> str:
        item = self._class_by_id.get(class_id)
        return item.name if item is not None else "(classe removida)"

    def _class_color(self, class_id: int) -> str:
        item = self._class_by_id.get(class_id)
        return item.color if item is not None else "#9E9E9E"

    def _to_normalized(
        self, points: list[tuple[int, int]]
    ) -> list[tuple[float, float]]:
        return [(x / self._img_w, y / self._img_h) for x, y in points]

    def _to_image_coords(
        self, points: list[tuple[float, float]]
    ) -> list[tuple[int, int]]:
        return [(round(x * self._img_w), round(y * self._img_h)) for x, y in points]

    @staticmethod
    def _load_image(file_path: str) -> QImage:
        if not file_path:
            return QImage()
        image = QImage(file_path)
        return image if not image.isNull() else QImage()
