"""Diálogo modal para recortar uma captura salva."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QWidget

from visionflow.domain.entities.capture import Capture
from visionflow.domain.use_cases.captures import CaptureService
from visionflow.presentation.icon_colors import INFO, icon_role_color
from visionflow.presentation.icon_sizes import TOOLBAR_ICON
from visionflow.presentation.icon_utils import tinted_icon
from visionflow.presentation.image_utils import crop_qimage
from visionflow.presentation.system_dialogs import (
    apply_dialog_theme,
    show_info_message,
)
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_PRIMARY_OUTLINE,
    create_button,
)
from visionflow.presentation.widgets.capture_edit_common import (
    EDIT_DIALOG_MIN_HEIGHT,
    EDIT_DIALOG_MIN_WIDTH,
    CaptureEditDialogBase,
    accept_if_saved,
    apply_dialog_shell,
    build_edit_dialog_root,
    build_save_actions,
    configure_edit_form,
    dimensions_subtitle,
    edit_form_label,
    edit_subtitle_label,
    frame_from_qimage,
    load_capture_image,
    replace_capture,
    save_capture_as_new,
)
from visionflow.presentation.widgets.crop_preview_dialog import CropPreviewDialog
from visionflow.presentation.widgets.image_crop_widget import ImageCropWidget
from visionflow.presentation.widgets.integer_spin_field import IntegerSpinField

_UNAVAILABLE_MESSAGE = "Não foi possível preparar a imagem recortada."


class CaptureCropDialog(CaptureEditDialogBase):
    """Recorte interativo com salvamento direto da região selecionada."""

    def __init__(
        self,
        capture: Capture,
        capture_service: CaptureService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._capture = capture
        self._capture_service = capture_service
        self._capture_id = int(capture.id or 0)
        self._source_image = load_capture_image(capture)
        self._syncing_crop = False

        apply_dialog_shell(
            self,
            object_name="capture_edit_dialog",
            title=f"Recortar captura #{self._capture_id}",
            min_width=EDIT_DIALOG_MIN_WIDTH,
            min_height=EDIT_DIALOG_MIN_HEIGHT,
        )

        root = build_edit_dialog_root()
        self.setLayout(root)

        root.addWidget(edit_subtitle_label(dimensions_subtitle(self._source_image)))

        self._crop_widget = ImageCropWidget()
        self._crop_widget.set_image(self._source_image)
        self._crop_widget.crop_rect_changed.connect(self._on_crop_rect_changed)
        root.addWidget(self._crop_widget, 1)

        form = QFormLayout()
        configure_edit_form(form)

        img_w = max(self._source_image.width(), 1)
        img_h = max(self._source_image.height(), 1)

        self._crop_x = IntegerSpinField()
        self._crop_x.setRange(0, img_w - 1)
        self._crop_x.valueChanged.connect(self._on_crop_spin_changed)

        self._crop_y = IntegerSpinField()
        self._crop_y.setRange(0, img_h - 1)
        self._crop_y.valueChanged.connect(self._on_crop_spin_changed)

        self._crop_w = IntegerSpinField()
        self._crop_w.setRange(1, img_w)
        self._crop_w.valueChanged.connect(self._on_crop_spin_changed)

        self._crop_h = IntegerSpinField()
        self._crop_h.setRange(1, img_h)
        self._crop_h.valueChanged.connect(self._on_crop_spin_changed)

        form.addRow(edit_form_label("X"), self._crop_x)
        form.addRow(edit_form_label("Y"), self._crop_y)
        form.addRow(edit_form_label("Largura"), self._crop_w)
        form.addRow(edit_form_label("Altura"), self._crop_h)
        root.addLayout(form)

        root.addLayout(self._build_actions())

        self._sync_crop_spinboxes_from_widget()
        apply_dialog_theme(self)

    def _build_actions(self) -> QHBoxLayout:
        actions = build_save_actions(
            self,
            on_replace=self._on_replace,
            on_save_new=self._on_save_new,
        )
        preview = create_button(
            "Visualizar",
            variant=VARIANT_PRIMARY_OUTLINE,
            shape=SHAPE_PILL,
            icon=tinted_icon("icon_crop.svg", icon_role_color(INFO), TOOLBAR_ICON),
        )
        preview.clicked.connect(self._on_preview)
        actions.insertWidget(1, preview)
        return actions

    def _on_preview(self) -> None:
        cropped = self._cropped_image()
        if cropped is None or cropped.isNull():
            show_info_message(
                self,
                "Visualizar recorte",
                "Não foi possível gerar a visualização do recorte.",
            )
            return
        dialog = CropPreviewDialog(cropped, parent=self)
        dialog.exec()

    def _cropped_image(self):
        if self._source_image.isNull():
            return None
        x, y, w, h = self._crop_widget.crop_rect()
        try:
            return crop_qimage(self._source_image, x, y, w, h)
        except ValueError:
            return None

    def _edited_frame(self):
        cropped = self._cropped_image()
        if cropped is None:
            return None
        return frame_from_qimage(cropped)

    def _on_replace(self) -> None:
        accept_if_saved(
            self,
            title="Recortar captura",
            frame=self._edited_frame(),
            unavailable_message=_UNAVAILABLE_MESSAGE,
            save=lambda frame: replace_capture(
                self, self._capture_service, self._capture, frame
            ),
        )

    def _on_save_new(self) -> None:
        accept_if_saved(
            self,
            title="Recortar captura",
            frame=self._edited_frame(),
            unavailable_message=_UNAVAILABLE_MESSAGE,
            save=lambda frame: save_capture_as_new(
                self, self._capture_service, self._capture, frame
            ),
        )

    def _set_crop_spins(self, x: int, y: int, w: int, h: int) -> None:
        for spin, value in (
            (self._crop_x, x),
            (self._crop_y, y),
            (self._crop_w, w),
            (self._crop_h, h),
        ):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

    def _sync_crop_spinboxes_from_widget(self) -> None:
        x, y, w, h = self._crop_widget.crop_rect()
        self._syncing_crop = True
        self._set_crop_spins(x, y, w, h)
        self._syncing_crop = False

    def _on_crop_rect_changed(self, x: int, y: int, w: int, h: int) -> None:
        if self._syncing_crop:
            return
        self._syncing_crop = True
        self._set_crop_spins(x, y, w, h)
        self._syncing_crop = False

    def _on_crop_spin_changed(self) -> None:
        if self._syncing_crop:
            return
        self._crop_widget.set_crop_rect(
            self._crop_x.value(),
            self._crop_y.value(),
            self._crop_w.value(),
            self._crop_h.value(),
        )
