"""Diálogo modal para selecionar capturas a adicionar a um dataset YOLO.

Replica a experiência da tela Capturas: filtro de período e ações acima da
grade, grade de miniaturas paginada e barra de paginação abaixo, com seleção
preservada entre páginas. A paginação e a seleção são delegadas ao
:class:`FilteredGalleryController`, compartilhado com as telas de galeria.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from visionflow.domain.entities.capture import Capture
from visionflow.domain.use_cases.captures import CaptureService
from visionflow.presentation.filtered_gallery_controller import (
    FilteredGalleryBindings,
    FilteredGalleryController,
)
from visionflow.presentation.list_screen_common import (
    DEFAULT_PAGE_SIZE,
    FILTER_PAD_H,
    FOOTER_PAD_V,
    GALLERY_PAGE_SIZES,
    QUICK_DATE_FILTERS,
)
from visionflow.presentation.media_thumbnail_loader import MediaThumbnailLoader
from visionflow.presentation.system_dialogs import apply_dialog_theme
from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_NEUTRAL_OUTLINE,
    VARIANT_PRIMARY,
    create_button,
)
from visionflow.presentation.widgets.capture_gallery_grid import CaptureGalleryGrid
from visionflow.presentation.widgets.date_filter_utils import quick_filter_range
from visionflow.presentation.widgets.date_range_picker import DateRangePicker
from visionflow.presentation.widgets.pagination_bar import PaginationBar
from visionflow.presentation.widgets.quick_date_filter_bar import (
    QuickDateFilterBar,
)
from visionflow.presentation.window_chrome import apply_native_dialog_flags

_PICKER_MIN_WIDTH = 980
_PICKER_MIN_HEIGHT = 640
_RELAYOUT_DEBOUNCE_MS = 120
_DEFAULT_PRESET = "month"


class CapturePickerDialog(QDialog):
    """Galeria de capturas paginada com filtro de período e seleção múltipla."""

    def __init__(
        self,
        capture_service: CaptureService,
        thumbnail_loader: MediaThumbnailLoader,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._captures = capture_service

        apply_native_dialog_flags(self)
        self.setObjectName("capture_picker_dialog")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setModal(True)
        self.setWindowTitle("Adicionar imagens ao dataset")
        self.setMinimumSize(_PICKER_MIN_WIDTH, _PICKER_MIN_HEIGHT)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())

        self._gallery = CaptureGalleryGrid(thumbnail_loader)
        self._controller = FilteredGalleryController(
            self._gallery,
            FilteredGalleryBindings(
                dates=self._date_picker.selected_dates,
                load_page=self._captures.list_filtered_page,
                list_ids=self._captures.list_filtered_ids,
                populate=self._populate,
                on_changed=self._on_controller_changed,
            ),
        )
        self._gallery.set_selection_handler(self._controller.on_card_toggled)
        root.addWidget(self._gallery, 1)

        self._pagination = PaginationBar(
            page_sizes=GALLERY_PAGE_SIZES,
            default_page_size=DEFAULT_PAGE_SIZE,
            on_page_size_changed=self._controller.on_page_size_changed,
            on_prev=self._controller.on_prev_page,
            on_next=self._controller.on_next_page,
            on_page_selected=self._controller.on_page_selected,
        )
        self._controller.bind_pagination(self._pagination)
        root.addWidget(self._pagination)

        self._relayout_timer = QTimer(self)
        self._relayout_timer.setSingleShot(True)
        self._relayout_timer.setInterval(_RELAYOUT_DEBOUNCE_MS)
        self._relayout_timer.timeout.connect(self._gallery.relayout_if_columns_changed)

        start, end = quick_filter_range(_DEFAULT_PRESET)
        self._date_picker.apply_range(start, end)
        self._controller.reload(reset_page=True)

    def selected_capture_ids(self) -> list[int]:
        """Retorna os ``id`` das capturas marcadas."""
        return self._controller.selected_list()

    def showEvent(self, event: QShowEvent) -> None:
        apply_dialog_theme(self)
        super().showEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout_timer.start()

    # ----- construção da UI ------------------------------------------------

    def _build_toolbar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("captures_filter_bar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(
            FILTER_PAD_H, FOOTER_PAD_V, FILTER_PAD_H, FOOTER_PAD_V
        )
        layout.setSpacing(9)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        de_label = QLabel("De")
        de_label.setObjectName("captures_filter_label")
        layout.addWidget(de_label)

        self._date_picker = DateRangePicker(
            start_object_name="captures_start_date",
            end_object_name="captures_end_date",
        )
        self._date_picker.dates_changed.connect(self._on_dates_changed)
        layout.addWidget(self._date_picker.start_date)
        ate_label = QLabel("Até")
        ate_label.setObjectName("captures_filter_label")
        layout.addWidget(ate_label)
        layout.addWidget(self._date_picker.end_date)

        self._quick_filters = QuickDateFilterBar(
            QUICK_DATE_FILTERS,
            default_preset=_DEFAULT_PRESET,
            on_preset_clicked=self._on_quick_filter,
        )
        layout.addWidget(self._quick_filters)
        layout.addStretch()

        self._select_all_button = create_button(
            "Selecionar todas",
            variant=VARIANT_NEUTRAL_OUTLINE,
            shape=SHAPE_PILL,
            icon_name="icon_check.svg",
        )
        self._select_all_button.clicked.connect(self._on_select_all_clicked)
        layout.addWidget(self._select_all_button)

        cancel = create_button(
            "Cancelar", variant=VARIANT_NEUTRAL_OUTLINE, shape=SHAPE_PILL
        )
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)

        self._confirm = create_button(
            "Adicionar", variant=VARIANT_PRIMARY, shape=SHAPE_PILL
        )
        self._confirm.clicked.connect(self.accept)
        layout.addWidget(self._confirm)
        return frame

    # ----- integração com o controller ------------------------------------

    def _populate(self, entries: list[Capture]) -> None:
        self._gallery.set_captures(entries, on_card_clicked=self._controller.toggle_one)

    def _on_dates_changed(self) -> None:
        self._controller.clear_selection(refresh=False)
        self._quick_filters.clear_selection()
        self._controller.reload(reset_page=True)

    def _on_quick_filter(self, preset: str) -> None:
        self._controller.clear_selection(refresh=False)
        start, end = quick_filter_range(preset)
        self._date_picker.apply_range(start, end)
        self._controller.reload(reset_page=True)

    def _on_select_all_clicked(self) -> None:
        self._controller.select_all_or_clear()

    def _on_controller_changed(self) -> None:
        self._select_all_button.setEnabled(self._controller.has_results())
        self._select_all_button.setText(
            "Desmarcar todas"
            if self._controller.shows_deselect_all()
            else "Selecionar todas"
        )
        count = self._controller.selected_count
        self._confirm.setEnabled(count > 0)
        self._confirm.setText(f"Adicionar ({count})" if count else "Adicionar")
