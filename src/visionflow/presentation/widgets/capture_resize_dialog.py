"""Diálogo modal para redimensionar uma captura salva."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QCheckBox, QFormLayout, QLabel, QWidget

from visionflow.domain.entities.capture import Capture
from visionflow.domain.use_cases.captures import CaptureService
from visionflow.presentation.image_utils import resize_qimage
from visionflow.presentation.system_dialogs import apply_dialog_theme
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
from visionflow.presentation.widgets.integer_spin_field import IntegerSpinField

_MAX_DIMENSION = 8192
_PREVIEW_MAX_HEIGHT = 360
_PREVIEW_MIN_WIDTH = 320
_UNAVAILABLE_MESSAGE = "Não foi possível preparar a imagem redimensionada."


class CaptureResizeDialog(CaptureEditDialogBase):
    """Redimensionamento com preview ao vivo e salvamento direto."""

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

        apply_dialog_shell(
            self,
            object_name="capture_edit_dialog",
            title=f"Redimensionar captura #{self._capture_id}",
            min_width=EDIT_DIALOG_MIN_WIDTH,
            min_height=EDIT_DIALOG_MIN_HEIGHT,
        )

        root = build_edit_dialog_root()
        self.setLayout(root)

        root.addWidget(edit_subtitle_label(dimensions_subtitle(self._source_image)))

        self._preview = QLabel()
        self._preview.setObjectName("capture_edit_preview")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(_PREVIEW_MIN_WIDTH)
        root.addWidget(self._preview, 1)

        form = QFormLayout()
        configure_edit_form(form)

        img_w = max(self._source_image.width(), 1)
        img_h = max(self._source_image.height(), 1)

        self._resize_w = IntegerSpinField()
        self._resize_w.setRange(1, _MAX_DIMENSION)
        self._resize_w.setValue(min(img_w, _MAX_DIMENSION))
        self._resize_w.valueChanged.connect(self._on_resize_width_changed)

        self._resize_h = IntegerSpinField()
        self._resize_h.setRange(1, _MAX_DIMENSION)
        self._resize_h.setValue(min(img_h, _MAX_DIMENSION))
        self._resize_h.valueChanged.connect(self._on_resize_height_changed)

        self._keep_aspect = QCheckBox("Manter proporção")
        self._keep_aspect.setChecked(True)
        self._keep_aspect.stateChanged.connect(lambda _state: self._refresh_preview())

        form.addRow(edit_form_label("Largura"), self._resize_w)
        form.addRow(edit_form_label("Altura"), self._resize_h)
        form.addRow(edit_form_label(""), self._keep_aspect)
        root.addLayout(form)

        root.addLayout(
            build_save_actions(
                self,
                on_replace=self._on_replace,
                on_save_new=self._on_save_new,
            )
        )

        self._refresh_preview()
        apply_dialog_theme(self)

    def _resized_image(self):
        if self._source_image.isNull():
            return None
        try:
            return resize_qimage(
                self._source_image,
                self._resize_w.value(),
                self._resize_h.value(),
                keep_aspect=self._keep_aspect.isChecked(),
            )
        except ValueError:
            return None

    def _edited_frame(self):
        resized = self._resized_image()
        if resized is None:
            return None
        return frame_from_qimage(resized)

    def _on_replace(self) -> None:
        accept_if_saved(
            self,
            title="Redimensionar captura",
            frame=self._edited_frame(),
            unavailable_message=_UNAVAILABLE_MESSAGE,
            save=lambda frame: replace_capture(
                self, self._capture_service, self._capture, frame
            ),
        )

    def _on_save_new(self) -> None:
        accept_if_saved(
            self,
            title="Redimensionar captura",
            frame=self._edited_frame(),
            unavailable_message=_UNAVAILABLE_MESSAGE,
            save=lambda frame: save_capture_as_new(
                self, self._capture_service, self._capture, frame
            ),
        )

    def _sync_aspect_from_width(self) -> None:
        img_w = max(self._source_image.width(), 1)
        img_h = max(self._source_image.height(), 1)
        aspect = img_w / img_h
        new_h = max(1, round(self._resize_w.value() / aspect))
        self._resize_h.blockSignals(True)
        self._resize_h.setValue(min(new_h, _MAX_DIMENSION))
        self._resize_h.blockSignals(False)

    def _sync_aspect_from_height(self) -> None:
        img_w = max(self._source_image.width(), 1)
        img_h = max(self._source_image.height(), 1)
        aspect = img_w / img_h
        new_w = max(1, round(self._resize_h.value() * aspect))
        self._resize_w.blockSignals(True)
        self._resize_w.setValue(min(new_w, _MAX_DIMENSION))
        self._resize_w.blockSignals(False)

    def _on_resize_width_changed(self) -> None:
        if self._keep_aspect.isChecked() and not self._source_image.isNull():
            self._sync_aspect_from_width()
        self._refresh_preview()

    def _on_resize_height_changed(self) -> None:
        if self._keep_aspect.isChecked() and not self._source_image.isNull():
            self._sync_aspect_from_height()
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if self._source_image.isNull():
            self._preview.setText("Imagem indisponível")
            return
        preview = self._resized_image()
        if preview is None:
            self._preview.setText("Imagem indisponível")
            return
        pixmap = QPixmap.fromImage(preview)
        max_w = max(self._preview.width() - 8, _PREVIEW_MIN_WIDTH)
        max_h = _PREVIEW_MAX_HEIGHT
        if pixmap.width() > max_w or pixmap.height() > max_h:
            pixmap = pixmap.scaled(
                max_w,
                max_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._preview.setPixmap(pixmap)
