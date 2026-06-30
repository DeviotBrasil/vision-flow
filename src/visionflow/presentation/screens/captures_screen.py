"""Tela Capturas — histórico com filtro por data e paginação."""

from __future__ import annotations

from datetime import date
from typing import Any, ClassVar

from visionflow.domain.entities.capture import Capture
from visionflow.domain.entities.filtered_page import FilteredPage
from visionflow.domain.use_cases.captures import CaptureService
from visionflow.presentation.gallery_batch_types import DeleteManyFn
from visionflow.presentation.gallery_import_controller import (
    GalleryImportBindings,
    GalleryImportController,
)
from visionflow.presentation.gallery_screen_config import GalleryScreenConfig
from visionflow.presentation.gallery_zip_export_controller import (
    GalleryZipExportBindings,
    GalleryZipExportController,
)
from visionflow.presentation.media_thumbnail_loader import MediaThumbnailLoader
from visionflow.presentation.screens.filtered_gallery_screen import (
    FilteredGalleryScreen,
)
from visionflow.presentation.system_dialogs import open_image_file_paths
from visionflow.presentation.widgets.capture_actions import show_capture_detail
from visionflow.presentation.widgets.capture_gallery_grid import CaptureGalleryGrid
from visionflow.presentation.widgets.responsive_gallery_grid import (
    ResponsiveGalleryGrid,
)

_CAPTURES_GALLERY_CONFIG = GalleryScreenConfig(
    item_singular="captura",
    item_plural="capturas",
    zip_basename_prefix="capturas",
    db_count_singular="imagem cadastrada no banco",
    db_count_plural="imagens cadastradas no banco",
    filtered_count_singular="imagem encontrada no período",
    filtered_count_plural="imagens encontradas no período",
    delete_failed_message="{count} captura(s) não puderam ser excluídas.",
)


class CapturesScreen(FilteredGalleryScreen):
    """Galeria paginada de capturas com filtro por intervalo de datas."""

    PAGE_ID: ClassVar[str] = "captures"
    TITLE: ClassVar[str] = "Capturas"
    ADD_ICON_NAME: ClassVar[str] = "icon_image.svg"
    GALLERY_CONFIG: ClassVar[GalleryScreenConfig] = _CAPTURES_GALLERY_CONFIG

    def __init__(
        self,
        capture_service: CaptureService,
        thumbnail_loader: MediaThumbnailLoader,
        parent=None,
    ) -> None:
        self._captures = capture_service
        self._thumbnail_loader = thumbnail_loader
        super().__init__(parent)

    def _create_gallery(self) -> ResponsiveGalleryGrid:
        return CaptureGalleryGrid(self._thumbnail_loader)

    def _create_export_controller(self) -> GalleryZipExportController:
        return GalleryZipExportController(
            self,
            jobs=self._background_jobs,
            bindings=GalleryZipExportBindings(
                list_by_ids=self._captures.list_by_ids,
                write_zip=CaptureService.write_zip,
                save_dialog_title="Salvar capturas",
                empty_selection_message="Nenhuma captura disponível para exportar.",
                skipped_file_label="imagem(ns)",
                zero_added_message="Nenhuma imagem encontrada no disco para exportar.",
            ),
            on_finished=self._on_export_feedback,
        )

    def _create_import_controller(self) -> GalleryImportController:
        return GalleryImportController(
            self,
            jobs=self._background_jobs,
            bindings=GalleryImportBindings(
                pick_paths=open_image_file_paths,
                import_files=self._captures.import_from_files,
                item_label="imagem(ns)",
            ),
            on_finished=self._on_import_feedback,
        )

    def _delete_many_fn(self) -> DeleteManyFn:
        return self._captures.delete_many

    def _pagination_kwargs(self) -> dict[str, str]:
        return {}

    def _database_total_count(self) -> int:
        return self._captures.count()

    def _load_filtered_page(
        self,
        start_date: date,
        end_date: date,
        page: int,
        page_size: int,
    ) -> FilteredPage[Capture]:
        return self._captures.list_filtered_page(
            start_date,
            end_date,
            page,
            page_size,
        )

    def _list_filtered_ids(
        self,
        start_date: date,
        end_date: date,
    ) -> list[int]:
        return self._captures.list_filtered_ids(start_date, end_date)

    def _populate_gallery(self, entries: list[Any]) -> None:
        self._gallery.set_captures(
            entries,
            on_card_clicked=self._on_thumbnail_clicked,
        )

    def _on_thumbnail_clicked(self, capture_id: int) -> None:
        show_capture_detail(
            self,
            self._captures,
            capture_id,
            on_deleted=self._on_capture_deleted,
            on_edited=self._on_capture_edited,
        )

    def _on_capture_deleted(self) -> None:
        self._reload_page(reset_page=False)

    def _on_capture_edited(self) -> None:
        self._reload_page(reset_page=False)
