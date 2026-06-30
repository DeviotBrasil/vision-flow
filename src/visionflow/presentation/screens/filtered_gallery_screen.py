"""Base compartilhada pelas telas de galeria com filtro por data."""

from __future__ import annotations

from abc import abstractmethod
from datetime import date
from typing import Any, ClassVar

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QResizeEvent
from PySide6.QtWidgets import QVBoxLayout, QWidget

from visionflow.domain.entities.filtered_page import FilteredPage
from visionflow.presentation.background_job_controller import (
    BackgroundJobController,
)
from visionflow.presentation.bulk_delete_controller import (
    BulkDeleteBindings,
    BulkDeleteController,
)
from visionflow.presentation.filtered_gallery_controller import (
    FilteredGalleryBindings,
    FilteredGalleryController,
)
from visionflow.presentation.gallery_batch_types import DeleteManyFn
from visionflow.presentation.gallery_screen_config import GalleryScreenConfig
from visionflow.presentation.job_status import GALLERY_JOB_BUSY_MESSAGE
from visionflow.presentation.list_screen_common import (
    DEFAULT_PAGE_SIZE,
    FILTER_PAD_H,
    GALLERY_PAGE_SIZES,
    format_count_label,
)
from visionflow.presentation.system_dialogs import confirm_bulk_delete
from visionflow.presentation.widgets.date_filter_utils import quick_filter_range
from visionflow.presentation.widgets.feedback_banner import FeedbackBanner
from visionflow.presentation.widgets.filtered_date_toolbar import (
    FilteredDateToolbar,
)
from visionflow.presentation.widgets.filtered_date_toolbar_actions import (
    FilteredDateToolbarActions,
)
from visionflow.presentation.widgets.list_screen_header import ListScreenHeader
from visionflow.presentation.widgets.pagination_bar import PaginationBar
from visionflow.presentation.widgets.responsive_gallery_grid import (
    ResponsiveGalleryGrid,
)

_RELAYOUT_DEBOUNCE_MS = 120


class FilteredGalleryScreen(QWidget):
    """Galeria paginada com filtro De/Até, presets, ZIP e paginação."""

    PAGE_ID: ClassVar[str]
    TITLE: ClassVar[str]
    GALLERY_CONFIG: ClassVar[GalleryScreenConfig]
    ADD_ICON_NAME: ClassVar[str | None] = None
    USES_OUTER_SCROLL: ClassVar[bool] = False

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName(f"{self.PAGE_ID}_screen")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._gallery_busy = False
        self._background_jobs = BackgroundJobController(
            self,
            on_busy=self._set_gallery_actions_enabled,
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = ListScreenHeader(
            object_name=f"{self.PAGE_ID}_header",
            title=self.TITLE,
            title_object_name=f"{self.PAGE_ID}_header_title",
            subtitle_object_name=f"{self.PAGE_ID}_header_subtitle",
        )
        root.addWidget(self._header)

        self._filter_bar = FilteredDateToolbar(
            screen_prefix=self.PAGE_ID,
            add_icon_name=self.ADD_ICON_NAME,
            actions=FilteredDateToolbarActions(
                on_dates_changed=self._on_dates_changed,
                on_quick_filter=self._on_quick_filter_clicked,
                on_download_zip=self._on_download_zip,
                on_bulk_delete=self._on_bulk_delete_clicked,
                on_select_all=self._on_select_all_clicked,
                on_add=self._on_add_clicked if self.ADD_ICON_NAME else None,
            ),
        )
        self._filter_bar.connect_theme()
        root.addWidget(self._filter_bar)
        root.addWidget(self._build_feedback_banner())

        self._gallery = self._create_gallery()
        self._controller = FilteredGalleryController(
            self._gallery,
            FilteredGalleryBindings(
                dates=self._selected_dates,
                load_page=self._load_filtered_page,
                list_ids=self._list_filtered_ids,
                populate=self._populate_gallery,
                on_changed=self._on_controller_changed,
            ),
        )
        self._gallery.set_selection_handler(self._controller.on_card_toggled)
        self._relayout_timer = QTimer(self)
        self._relayout_timer.setSingleShot(True)
        self._relayout_timer.setInterval(_RELAYOUT_DEBOUNCE_MS)
        self._relayout_timer.timeout.connect(self._gallery.relayout_if_columns_changed)
        root.addWidget(self._gallery, 1)

        pagination_kwargs = self._pagination_kwargs()
        self._pagination = PaginationBar(
            page_sizes=GALLERY_PAGE_SIZES,
            default_page_size=DEFAULT_PAGE_SIZE,
            on_page_size_changed=self._controller.on_page_size_changed,
            on_prev=self._controller.on_prev_page,
            on_next=self._controller.on_next_page,
            on_page_selected=self._controller.on_page_selected,
            **pagination_kwargs,
        )
        self._controller.bind_pagination(self._pagination)
        root.addWidget(self._pagination)

        self._export_controller = self._create_export_controller()
        self._import_controller = self._create_import_controller()
        self._bulk_delete_controller = BulkDeleteController(
            jobs=self._background_jobs,
            bindings=BulkDeleteBindings(
                delete_many=self._delete_many_fn(),
                item_label=self.GALLERY_CONFIG.item_plural,
                on_finished=self._on_bulk_delete_finished,
                on_failed=self._on_bulk_delete_failed,
                on_busy=self._on_gallery_job_busy,
            ),
        )
        self._update_selection_buttons()
        self.refresh()

    def refresh(self) -> None:
        self._reload_page(reset_page=False)

    def shutdown(self) -> None:
        self._on_screen_closing()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.shutdown()
        super().closeEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._relayout_timer.start()

    def _build_feedback_banner(self) -> FeedbackBanner:
        self._feedback_banner = FeedbackBanner(
            banner_object_name=f"{self.PAGE_ID}_feedback_banner",
            text_object_name=f"{self.PAGE_ID}_feedback_banner_text",
            horizontal_padding=FILTER_PAD_H,
        )
        return self._feedback_banner

    def _on_export_feedback(self, message: str | None) -> None:
        if message is None:
            self._feedback_banner.hide_message()
        else:
            self._feedback_banner.show_message(message)

    def _on_download_zip(self) -> None:
        if not self._controller.selected_ids or self._gallery_busy:
            return
        self._export_controller.start_export(
            self._controller.selected_list(),
            suggested_basename=self.GALLERY_CONFIG.export_basename(),
        )

    def _on_add_clicked(self) -> None:
        if self._gallery_busy:
            return
        self._import_controller.start_import()

    def _on_import_feedback(self, message: str | None) -> None:
        if message is None:
            self._feedback_banner.hide_message()
        else:
            self._feedback_banner.show_message(message)
        self._controller.reload(reset_page=False)

    def _selected_dates(self) -> tuple[date, date]:
        return self._filter_bar.date_picker.selected_dates()

    def _on_dates_changed(self) -> None:
        self._controller.clear_selection(refresh=False)
        self._filter_bar.quick_filters.clear_selection()
        self._controller.reload(reset_page=True)

    def _on_quick_filter_clicked(self, preset: str) -> None:
        self._controller.clear_selection(refresh=False)
        start, end = quick_filter_range(preset)
        self._filter_bar.date_picker.apply_range(start, end)
        self._controller.reload(reset_page=True)

    def _reload_page(self, *, reset_page: bool) -> None:
        """Recarrega a página atual (mantido para uso das subclasses)."""
        self._controller.reload(reset_page=reset_page)

    def _on_controller_changed(self) -> None:
        self._update_summary_labels()
        self._update_selection_buttons()

    def _update_summary_labels(self) -> None:
        config = self.GALLERY_CONFIG
        db_text = format_count_label(
            self._database_total_count(),
            singular=config.db_count_singular,
            plural=config.db_count_plural,
        )
        if self._controller.filtered_total != self._database_total_count():
            filtered_text = format_count_label(
                self._controller.filtered_total,
                singular=config.filtered_count_singular,
                plural=config.filtered_count_plural,
            )
            self._header.subtitle_label.setText(f"{db_text} · {filtered_text}")
        else:
            self._header.subtitle_label.setText(db_text)

    def _on_select_all_clicked(self) -> None:
        if self._gallery_busy:
            return
        self._controller.select_all_or_clear()

    def _update_selection_buttons(self) -> None:
        count = self._controller.selected_count
        has_selection = count > 0 and not self._gallery_busy
        has_results = self._controller.has_results() and not self._gallery_busy
        select_all = self._filter_bar.select_all_button
        if select_all is not None:
            select_all.setEnabled(has_results)
            select_all.setText(
                "Desmarcar todas"
                if self._controller.shows_deselect_all()
                else "Selecionar todas"
            )
        self._filter_bar.update_download_button(enabled=has_selection)
        add_button = self._filter_bar.add_button
        if add_button is not None:
            add_button.setEnabled(not self._gallery_busy)
        self._filter_bar.update_delete_button(
            label=self._bulk_delete_label(count),
            enabled=has_selection,
        )

    def _bulk_delete_label(self, count: int) -> str:
        if count == 0:
            return "Excluir"
        return f"Excluir ({count})"

    def _set_gallery_actions_enabled(self, enabled: bool) -> None:
        self._gallery_busy = not enabled
        self._update_selection_buttons()

    def _on_bulk_delete_clicked(self) -> None:
        if not self._controller.selected_ids or self._gallery_busy:
            return
        count = self._controller.selected_count
        config = self.GALLERY_CONFIG
        if not confirm_bulk_delete(
            self,
            count=count,
            item_singular=config.item_singular,
            item_plural=config.item_plural,
        ):
            return
        self._bulk_delete_controller.start_delete(self._controller.selected_list())

    def _on_bulk_delete_failed(self) -> None:
        self._feedback_banner.show_message(
            "Não foi possível excluir os itens selecionados."
        )

    def _on_gallery_job_busy(self) -> None:
        self._feedback_banner.show_message(GALLERY_JOB_BUSY_MESSAGE)

    def _on_bulk_delete_finished(self, _deleted: int, failed_ids: list[int]) -> None:
        if failed_ids:
            self._feedback_banner.show_message(
                self.GALLERY_CONFIG.delete_failed_feedback(len(failed_ids))
            )
        self._controller.clear_selection(refresh=False)
        self._controller.reload(reset_page=False)

    @abstractmethod
    def _create_gallery(self) -> ResponsiveGalleryGrid:
        raise NotImplementedError

    @abstractmethod
    def _create_export_controller(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def _create_import_controller(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def _delete_many_fn(self) -> DeleteManyFn:
        raise NotImplementedError

    @abstractmethod
    def _pagination_kwargs(self) -> dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def _database_total_count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def _load_filtered_page(
        self,
        start_date: date,
        end_date: date,
        page: int,
        page_size: int,
    ) -> FilteredPage[Any]:
        raise NotImplementedError

    @abstractmethod
    def _list_filtered_ids(
        self,
        start_date: date,
        end_date: date,
    ) -> list[int]:
        raise NotImplementedError

    @abstractmethod
    def _populate_gallery(self, entries: list[Any]) -> None:
        raise NotImplementedError

    def _on_screen_closing(self) -> None:
        """Hook para liberar recursos (ex.: thread de miniaturas)."""
        self._background_jobs.shutdown()
