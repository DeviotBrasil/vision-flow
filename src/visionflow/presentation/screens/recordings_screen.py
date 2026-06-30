"""Tela Gravações — histórico com filtro por data e paginação."""

from __future__ import annotations

from datetime import date
from typing import Any, ClassVar

from visionflow.domain.entities.filtered_page import FilteredPage
from visionflow.domain.entities.recording import Recording
from visionflow.domain.use_cases.recordings import RecordingService
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
from visionflow.presentation.system_dialogs import open_recording_file_paths
from visionflow.presentation.widgets.recording_actions import show_recording_detail
from visionflow.presentation.widgets.recording_gallery_grid import (
    RecordingGalleryGrid,
)
from visionflow.presentation.widgets.responsive_gallery_grid import (
    ResponsiveGalleryGrid,
)

_RECORDINGS_GALLERY_CONFIG = GalleryScreenConfig(
    item_singular="gravação",
    item_plural="gravações",
    zip_basename_prefix="gravacoes",
    db_count_singular="vídeo cadastrado no banco",
    db_count_plural="vídeos cadastrados no banco",
    filtered_count_singular="gravação encontrada no período",
    filtered_count_plural="gravações encontradas no período",
    delete_failed_message=(
        "{count} gravação(ões) não puderam ser excluídas. "
        "Feche outros programas que estejam usando o vídeo e tente novamente."
    ),
)


class RecordingsScreen(FilteredGalleryScreen):
    """Galeria paginada de gravações com filtro por intervalo de datas."""

    PAGE_ID: ClassVar[str] = "recordings"
    TITLE: ClassVar[str] = "Gravações"
    ADD_ICON_NAME: ClassVar[str] = "icon_nav_youtube.svg"
    GALLERY_CONFIG: ClassVar[GalleryScreenConfig] = _RECORDINGS_GALLERY_CONFIG

    def __init__(
        self,
        recording_service: RecordingService,
        thumbnail_loader: MediaThumbnailLoader,
        parent=None,
    ) -> None:
        self._recordings = recording_service
        self._thumbnail_loader = thumbnail_loader
        super().__init__(parent)

    def _create_gallery(self) -> ResponsiveGalleryGrid:
        return RecordingGalleryGrid(self._thumbnail_loader)

    def _create_export_controller(self) -> GalleryZipExportController:
        return GalleryZipExportController(
            self,
            jobs=self._background_jobs,
            bindings=GalleryZipExportBindings(
                list_by_ids=self._recordings.list_by_ids,
                write_zip=RecordingService.write_zip,
                save_dialog_title="Salvar gravações",
                empty_selection_message="Nenhuma gravação disponível para exportar.",
                skipped_file_label="vídeo(s)",
                zero_added_message="Nenhum vídeo encontrado no disco para exportar.",
            ),
            on_finished=self._on_export_feedback,
        )

    def _create_import_controller(self) -> GalleryImportController:
        return GalleryImportController(
            self,
            jobs=self._background_jobs,
            bindings=GalleryImportBindings(
                pick_paths=open_recording_file_paths,
                import_files=self._recordings.import_from_files,
                item_label="gravação(ões)",
            ),
            on_finished=self._on_import_feedback,
        )

    def _delete_many_fn(self) -> DeleteManyFn:
        return self._recordings.delete_many

    def _pagination_kwargs(self) -> dict[str, str]:
        return {
            "object_name": "recordings_footer",
            "range_label_object_name": "recordings_range_label",
            "footer_caption_object_name": "recordings_footer_caption",
        }

    def _database_total_count(self) -> int:
        return self._recordings.count()

    def _load_filtered_page(
        self,
        start_date: date,
        end_date: date,
        page: int,
        page_size: int,
    ) -> FilteredPage[Recording]:
        return self._recordings.list_filtered_page(
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
        return self._recordings.list_filtered_ids(start_date, end_date)

    def _populate_gallery(self, entries: list[Any]) -> None:
        self._gallery.set_recordings(
            entries,
            on_card_clicked=self._on_thumbnail_clicked,
        )

    def _on_thumbnail_clicked(self, recording_id: int) -> None:
        show_recording_detail(
            self,
            self._recordings,
            recording_id,
            on_deleted=self._on_recording_deleted,
            on_delete_failed=self._on_delete_failed,
        )

    def _on_recording_deleted(self) -> None:
        self._reload_page(reset_page=False)

    def _on_delete_failed(self, message: str) -> None:
        self._feedback_banner.show_message(message)
