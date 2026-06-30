"""Tela Datasets — montagem e anotação de datasets YOLO de segmentação."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar, TypeVar

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPixmap, QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from visionflow.branding import SETTINGS_YOLO_EXPORT_FORMAT
from visionflow.domain.entities.capture import Capture
from visionflow.domain.entities.yolo import YoloClass, YoloDatasetImage
from visionflow.domain.use_cases.captures import CaptureService
from visionflow.domain.use_cases.yolo_dataset import YoloDatasetService
from visionflow.domain.yolo_export_format import (
    DEFAULT_YOLO_EXPORT_FORMAT,
    YoloExportFormat,
)
from visionflow.presentation.app_settings import app_settings
from visionflow.presentation.background_job_controller import (
    BackgroundJobController,
)
from visionflow.presentation.list_screen_common import (
    FILTER_PAD_H,
    FOOTER_PAD_V,
)
from visionflow.presentation.media_thumbnail_loader import MediaThumbnailLoader
from visionflow.presentation.selection_model import SelectionModel
from visionflow.presentation.system_dialogs import (
    confirm_bulk_delete,
    show_info_message,
)
from visionflow.presentation.themes.theme_manager import ThemeManager
from visionflow.presentation.widgets.annotation_dialog import AnnotationDialog
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_DANGER_OUTLINE,
    VARIANT_NEUTRAL_OUTLINE,
    VARIANT_PRIMARY_OUTLINE,
    create_button,
    update_outline_action_button,
)
from visionflow.presentation.widgets.capture_picker_dialog import (
    CapturePickerDialog,
)
from visionflow.presentation.widgets.class_editor_dialog import ClassEditorDialog
from visionflow.presentation.widgets.dataset_image_gallery_grid import (
    DatasetImageGalleryGrid,
)
from visionflow.presentation.widgets.list_screen_header import ListScreenHeader
from visionflow.presentation.widgets.text_input_dialog import prompt_text
from visionflow.presentation.yolo_export_controller import YoloExportController
from visionflow.presentation.yolo_export_labels import (
    yolo_export_format_label,
    yolo_export_format_tooltip,
)

_SIDE_PANEL_WIDTH = 240
_RELAYOUT_DEBOUNCE_MS = 120
_SAVE_ICON = "icon_download.svg"

_T = TypeVar("_T")


class DatasetsScreen(QWidget):
    """Gerencia datasets YOLO: classes, imagens e exportação anotada."""

    PAGE_ID: ClassVar[str] = "datasets"
    TITLE: ClassVar[str] = "Datasets"
    USES_OUTER_SCROLL: ClassVar[bool] = False

    def __init__(
        self,
        yolo_service: YoloDatasetService,
        capture_service: CaptureService,
        thumbnail_loader: MediaThumbnailLoader,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("datasets_screen")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._service = yolo_service
        self._captures = capture_service
        self._thumbnail_loader = thumbnail_loader
        self._dataset_id: int | None = None
        self._classes: list[YoloClass] = []
        self._images_by_id: dict[int, YoloDatasetImage] = {}
        self._image_selection = SelectionModel()
        self._busy = False

        self._background_jobs = BackgroundJobController(self, on_busy=self._on_busy)
        self._export_controller = YoloExportController(
            self,
            jobs=self._background_jobs,
            service=yolo_service,
            on_finished=self._on_export_finished,
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = ListScreenHeader(
            object_name="datasets_header",
            title=self.TITLE,
            title_object_name="datasets_header_title",
            subtitle_object_name="datasets_header_subtitle",
        )
        root.addWidget(self._header)
        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_body(), 1)

        self._relayout_timer = QTimer(self)
        self._relayout_timer.setSingleShot(True)
        self._relayout_timer.setInterval(_RELAYOUT_DEBOUNCE_MS)
        self._relayout_timer.timeout.connect(self._gallery.relayout_if_columns_changed)

        self.refresh()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._connect_theme_manager()

    def _connect_theme_manager(self) -> None:
        window = self.window()
        manager = getattr(window, "theme_manager", None)
        if not isinstance(manager, ThemeManager):
            return
        if getattr(self, "_theme_connected", False):
            return
        manager.theme_changed.connect(self._on_theme_changed)
        self._theme_connected = True

    def _on_theme_changed(self, theme: str) -> None:
        self._update_download_button(theme=theme)

    # ----- construção da UI ------------------------------------------------

    def _build_toolbar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("datasets_toolbar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(
            FILTER_PAD_H, FOOTER_PAD_V, FILTER_PAD_H, FOOTER_PAD_V
        )
        layout.setSpacing(9)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        dataset_label = QLabel("Dataset:")
        dataset_label.setObjectName("datasets_toolbar_label")
        layout.addWidget(dataset_label)
        self._dataset_combo = QComboBox()
        self._dataset_combo.setMinimumWidth(220)
        self._dataset_combo.currentIndexChanged.connect(self._on_dataset_changed)
        layout.addWidget(self._dataset_combo)

        self._new_dataset_btn = create_button(
            "Novo", variant=VARIANT_PRIMARY_OUTLINE, shape=SHAPE_PILL
        )
        self._new_dataset_btn.clicked.connect(self._on_new_dataset)
        layout.addWidget(self._new_dataset_btn)

        self._rename_dataset_btn = create_button(
            "Renomear", variant=VARIANT_NEUTRAL_OUTLINE, shape=SHAPE_PILL
        )
        self._rename_dataset_btn.clicked.connect(self._on_rename_dataset)
        layout.addWidget(self._rename_dataset_btn)

        self._delete_dataset_btn = create_button(
            "Excluir", variant=VARIANT_DANGER_OUTLINE, shape=SHAPE_PILL
        )
        self._delete_dataset_btn.clicked.connect(self._on_delete_dataset)
        layout.addWidget(self._delete_dataset_btn)

        layout.addStretch()

        format_label = QLabel("YOLO:")
        format_label.setObjectName("datasets_toolbar_label")
        layout.addWidget(format_label)
        self._export_format_combo = QComboBox()
        self._export_format_combo.setObjectName("datasets_export_format")
        self._export_format_combo.setMinimumWidth(72)
        for export_format in YoloExportFormat.choices():
            self._export_format_combo.addItem(
                yolo_export_format_label(export_format), export_format
            )
            index = self._export_format_combo.count() - 1
            self._export_format_combo.setItemData(
                index,
                yolo_export_format_tooltip(export_format),
                Qt.ItemDataRole.ToolTipRole,
            )
        self._export_format_combo.currentIndexChanged.connect(
            self._on_export_format_changed
        )
        self._restore_export_format()
        layout.addWidget(self._export_format_combo)

        self._download_btn = create_button(
            "Salvar",
            variant=VARIANT_NEUTRAL_OUTLINE,
            shape=SHAPE_PILL,
            icon_name=_SAVE_ICON,
        )
        self._download_btn.clicked.connect(self._on_download_zip)
        layout.addWidget(self._download_btn)

        return frame

    def _build_body(self) -> QWidget:
        body = QWidget()
        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_classes_panel())
        layout.addWidget(self._build_images_panel(), 1)
        return body

    def _build_images_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_images_toolbar())

        self._gallery = DatasetImageGalleryGrid(self._thumbnail_loader)
        self._gallery.set_selection_handler(self._on_image_selection_toggled)
        layout.addWidget(self._gallery, 1)
        return panel

    def _build_images_toolbar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("datasets_images_toolbar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(
            FILTER_PAD_H, FOOTER_PAD_V, FILTER_PAD_H, FOOTER_PAD_V
        )
        layout.setSpacing(9)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        label = QLabel("Imagens:")
        label.setObjectName("datasets_toolbar_label")
        layout.addWidget(label)
        layout.addStretch()

        self._add_images_btn = create_button(
            "Adicionar imagens", variant=VARIANT_PRIMARY_OUTLINE, shape=SHAPE_PILL
        )
        self._add_images_btn.clicked.connect(self._on_add_images)
        layout.addWidget(self._add_images_btn)

        self._select_all_images_btn = create_button(
            "Selecionar todas",
            variant=VARIANT_NEUTRAL_OUTLINE,
            shape=SHAPE_PILL,
            icon_name="icon_check.svg",
        )
        self._select_all_images_btn.clicked.connect(self._on_select_all_images)
        layout.addWidget(self._select_all_images_btn)

        self._delete_images_btn = create_button(
            "Excluir", variant=VARIANT_DANGER_OUTLINE, shape=SHAPE_PILL
        )
        self._delete_images_btn.clicked.connect(self._on_delete_images)
        layout.addWidget(self._delete_images_btn)
        return frame

    def _build_classes_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("datasets_classes_panel")
        panel.setFixedWidth(_SIDE_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel("Classes")
        title.setObjectName("datasets_classes_title")
        layout.addWidget(title)

        self._classes_list = QListWidget()
        self._classes_list.setObjectName("datasets_classes_list")
        self._classes_list.currentRowChanged.connect(self._update_class_buttons)
        layout.addWidget(self._classes_list, 1)

        self._new_class_btn = create_button(
            "Nova classe", variant=VARIANT_PRIMARY_OUTLINE, shape=SHAPE_PILL
        )
        self._new_class_btn.clicked.connect(self._on_new_class)
        layout.addWidget(self._new_class_btn)

        self._edit_class_btn = create_button(
            "Editar", variant=VARIANT_NEUTRAL_OUTLINE, shape=SHAPE_PILL
        )
        self._edit_class_btn.clicked.connect(self._on_edit_class)
        layout.addWidget(self._edit_class_btn)

        self._delete_class_btn = create_button(
            "Excluir", variant=VARIANT_DANGER_OUTLINE, shape=SHAPE_PILL
        )
        self._delete_class_btn.clicked.connect(self._on_delete_class)
        layout.addWidget(self._delete_class_btn)

        return panel

    # ----- ciclo de vida / recarga ----------------------------------------

    def refresh(self) -> None:
        self._reload_datasets()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._relayout_timer.start()

    def shutdown(self) -> None:
        self._background_jobs.shutdown()

    def _reload_datasets(self) -> None:
        datasets = self._service.list_datasets()
        self._dataset_combo.blockSignals(True)
        self._dataset_combo.clear()
        for dataset in datasets:
            self._dataset_combo.addItem(dataset.name, int(dataset.id or 0))
        self._dataset_combo.blockSignals(False)

        if datasets:
            target = self._dataset_id or int(datasets[0].id or 0)
            index = self._dataset_combo.findData(target)
            self._dataset_combo.setCurrentIndex(max(index, 0))
            self._dataset_id = int(self._dataset_combo.currentData())
        else:
            self._dataset_id = None
        self._reload_dataset_content()

    def _reload_dataset_content(self) -> None:
        self._reload_classes()
        self._reload_images()
        self._update_subtitle()
        self._update_toolbar_buttons()

    def _for_dataset(self, fn: Callable[[int], _T], default: _T) -> _T:
        """Executa ``fn`` para o dataset atual ou devolve ``default`` sem ele."""
        if self._dataset_id is None:
            return default
        return fn(self._dataset_id)

    def _reload_classes(self) -> None:
        self._classes = self._for_dataset(self._service.list_classes, [])
        counts = self._for_dataset(self._service.annotation_count_by_class, {})
        self._classes_list.blockSignals(True)
        self._classes_list.clear()
        for item in self._classes:
            count = counts.get(int(item.id or 0), 0)
            entry = QListWidgetItem(
                self._color_icon(item.color), f"{item.name} ({count})"
            )
            entry.setData(Qt.ItemDataRole.UserRole, int(item.id or 0))
            self._classes_list.addItem(entry)
        self._classes_list.blockSignals(False)
        self._update_class_buttons()

    def _reload_images(self) -> None:
        images = self._for_dataset(self._service.list_images, [])
        self._images_by_id = {int(img.id or 0): img for img in images}
        self._image_selection.clear()
        classes_by_image = self._for_dataset(self._service.classes_by_image, {})
        captions = {
            image_id: ", ".join(names) for image_id, names in classes_by_image.items()
        }
        captures = [
            Capture(
                id=int(img.id or 0),
                file_path=img.file_path or "",
                width=img.width,
                height=img.height,
            )
            for img in images
        ]
        self._gallery.set_captions(captions)
        self._gallery.set_captures(captures, on_card_clicked=self._on_image_clicked)
        self._update_image_action_buttons()

    # ----- datasets --------------------------------------------------------

    def _on_dataset_changed(self) -> None:
        data = self._dataset_combo.currentData()
        self._dataset_id = int(data) if data is not None else None
        self._reload_dataset_content()

    def _on_new_dataset(self) -> None:
        name = prompt_text(
            self, title="Novo dataset", label="Nome do dataset", initial=""
        )
        if not name:
            return
        dataset = self._service.create_dataset(name)
        if dataset is None:
            show_info_message(self, "Novo dataset", "Informe um nome válido.")
            return
        self._dataset_id = dataset.id
        self._reload_datasets()

    def _on_rename_dataset(self) -> None:
        if self._dataset_id is None:
            return
        current = self._dataset_combo.currentText()
        name = prompt_text(
            self, title="Renomear dataset", label="Novo nome", initial=current
        )
        if not name:
            return
        if self._service.rename_dataset(self._dataset_id, name):
            self._reload_datasets()

    def _on_delete_dataset(self) -> None:
        if self._dataset_id is None:
            return
        if not confirm_bulk_delete(
            self, count=1, item_singular="dataset", item_plural="datasets"
        ):
            return
        self._service.delete_dataset(self._dataset_id)
        self._dataset_id = None
        self._reload_datasets()

    # ----- classes ---------------------------------------------------------

    def _on_new_class(self) -> None:
        if self._dataset_id is None:
            return
        dialog = ClassEditorDialog(self, title="Nova classe")
        if dialog.exec() != ClassEditorDialog.DialogCode.Accepted:
            return
        created = self._service.add_class(
            self._dataset_id, dialog.class_name(), dialog.color_hex()
        )
        if created is None:
            show_info_message(
                self,
                "Nova classe",
                "Nome inválido ou já existente neste dataset.",
            )
            return
        self._reload_classes()

    def _on_edit_class(self) -> None:
        selected = self._selected_class()
        if selected is None:
            return
        dialog = ClassEditorDialog(
            self,
            title="Editar classe",
            name=selected.name,
            color=selected.color,
        )
        if dialog.exec() != ClassEditorDialog.DialogCode.Accepted:
            return
        if self._service.update_class(
            int(selected.id or 0),
            name=dialog.class_name(),
            color=dialog.color_hex(),
        ):
            self._reload_classes()

    def _on_delete_class(self) -> None:
        selected = self._selected_class()
        if selected is None:
            return
        if not confirm_bulk_delete(
            self, count=1, item_singular="classe", item_plural="classes"
        ):
            return
        self._service.delete_class(int(selected.id or 0))
        self._reload_classes()

    def _selected_class(self) -> YoloClass | None:
        row = self._classes_list.currentRow()
        if 0 <= row < len(self._classes):
            return self._classes[row]
        return None

    # ----- imagens / anotação ---------------------------------------------

    def _on_add_images(self) -> None:
        if self._dataset_id is None or self._busy:
            return
        dialog = CapturePickerDialog(
            self._captures,
            self._thumbnail_loader,
            parent=self,
        )
        if dialog.exec() != CapturePickerDialog.DialogCode.Accepted:
            return
        capture_ids = dialog.selected_capture_ids()
        if not capture_ids:
            return
        self._service.add_images(self._dataset_id, capture_ids)
        self._reload_images()
        self._update_subtitle()
        self._update_toolbar_buttons()

    def _on_image_clicked(self, image_id: int) -> None:
        image = self._images_by_id.get(image_id)
        if image is None:
            return
        dialog = AnnotationDialog(image, self._service, self._classes, parent=self)
        if dialog.exec() == AnnotationDialog.DialogCode.Accepted:
            self._reload_classes()
            self._reload_images()

    def _on_image_selection_toggled(self, image_id: int, checked: bool) -> None:
        self._image_selection.set_one(image_id, checked)
        self._update_image_action_buttons()

    def _on_select_all_images(self) -> None:
        all_ids = set(self._images_by_id)
        if self._image_selection.shows_deselect_all(len(all_ids)):
            self._image_selection.clear()
        else:
            self._image_selection.select_all(all_ids)
        self._gallery.apply_selection(self._image_selection.selected_ids)
        self._update_image_action_buttons()

    def _on_delete_images(self) -> None:
        if self._busy or not self._image_selection.count:
            return
        count = self._image_selection.count
        if not confirm_bulk_delete(
            self, count=count, item_singular="imagem", item_plural="imagens"
        ):
            return
        for image_id in self._image_selection.as_list():
            self._service.remove_image(image_id)
        self._reload_classes()
        self._reload_images()
        self._update_subtitle()
        self._update_toolbar_buttons()

    def _on_download_zip(self) -> None:
        if self._dataset_id is None or self._busy or not self._images_by_id:
            return
        export_format = self._selected_export_format()
        self._export_controller.start_export(
            self._dataset_id,
            suggested_basename=self._export_basename(),
            export_format=export_format,
        )

    def _selected_export_format(self) -> YoloExportFormat:
        value = self._export_format_combo.currentData()
        if isinstance(value, YoloExportFormat):
            return value
        return DEFAULT_YOLO_EXPORT_FORMAT

    def _restore_export_format(self) -> None:
        saved = YoloExportFormat.from_settings_value(
            app_settings().value(SETTINGS_YOLO_EXPORT_FORMAT)
        )
        self._export_format_combo.blockSignals(True)
        try:
            for index in range(self._export_format_combo.count()):
                if self._export_format_combo.itemData(index) is saved:
                    self._export_format_combo.setCurrentIndex(index)
                    return
        finally:
            self._export_format_combo.blockSignals(False)
        self._export_format_combo.setToolTip(
            yolo_export_format_tooltip(self._selected_export_format())
        )

    def _on_export_format_changed(self) -> None:
        export_format = self._selected_export_format()
        self._export_format_combo.setToolTip(
            yolo_export_format_tooltip(export_format)
        )
        app_settings().setValue(SETTINGS_YOLO_EXPORT_FORMAT, export_format.value)

    def _on_export_finished(self, message: str | None) -> None:
        if message is not None:
            show_info_message(self, "Exportar dataset", message)

    # ----- estado / helpers ------------------------------------------------

    def _on_busy(self, enabled: bool) -> None:
        self._busy = not enabled
        self._update_toolbar_buttons()

    def _update_subtitle(self) -> None:
        if self._dataset_id is None:
            self._header.subtitle_label.setText(
                "Crie um dataset para começar a anotar."
            )
            return
        image_count = len(self._images_by_id)
        class_count = len(self._classes)
        self._header.subtitle_label.setText(
            f"{image_count} imagem(ns) · {class_count} classe(s)"
        )

    def _update_toolbar_buttons(self) -> None:
        has_dataset = self._dataset_id is not None and not self._busy
        self._rename_dataset_btn.setEnabled(has_dataset)
        self._delete_dataset_btn.setEnabled(has_dataset)
        self._add_images_btn.setEnabled(has_dataset)
        self._new_dataset_btn.setEnabled(not self._busy)
        self._dataset_combo.setEnabled(not self._busy)
        self._export_format_combo.setEnabled(not self._busy)
        self._update_download_button()
        self._new_class_btn.setEnabled(has_dataset)
        self._update_class_buttons()
        self._update_image_action_buttons()

    def _update_class_buttons(self) -> None:
        has_selection = self._selected_class() is not None and not self._busy
        self._edit_class_btn.setEnabled(has_selection)
        self._delete_class_btn.setEnabled(has_selection)

    def _update_image_action_buttons(self) -> None:
        total = len(self._images_by_id)
        has_images = total > 0 and not self._busy
        shows_deselect = self._image_selection.shows_deselect_all(total)
        self._select_all_images_btn.setEnabled(has_images)
        self._select_all_images_btn.setText(
            "Desmarcar todas" if shows_deselect else "Selecionar todas"
        )
        count = self._image_selection.count
        self._delete_images_btn.setEnabled(count > 0 and not self._busy)
        self._delete_images_btn.setText(f"Excluir ({count})" if count else "Excluir")

    def _update_download_button(self, theme: str | None = None) -> None:
        can_save = (
            self._dataset_id is not None and bool(self._images_by_id) and not self._busy
        )
        update_outline_action_button(
            self._download_btn,
            enabled=can_save,
            icon_name=_SAVE_ICON,
            theme=theme,
        )

    def _export_basename(self) -> str:
        name = self._dataset_combo.currentText().strip() or "dataset"
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)
        return f"dataset_yolo_{safe}"

    @staticmethod
    def _color_icon(hex_color: str) -> QIcon:
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(hex_color))
        return QIcon(pixmap)
