"""Ações compartilhadas de gravação (popup de detalhe)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QWidget

from visionflow.domain.use_cases.recordings import RecordingService
from visionflow.presentation.widgets.recording_detail_dialog import (
    RecordingDetailDialog,
)

_DELETE_FAILED_MESSAGE = (
    "Não foi possível excluir a gravação. "
    "Feche outros programas que estejam usando o vídeo e tente novamente."
)


def show_recording_detail(
    parent: QWidget,
    recording_service: RecordingService,
    recording_id: int,
    *,
    on_deleted: Callable[[], None] | None = None,
    on_delete_failed: Callable[[str], None] | None = None,
) -> None:
    """Abre o popup de detalhe; exclui via serviço e chama callbacks."""

    recording = recording_service.get(recording_id)

    if recording is None:
        return

    dialog = RecordingDetailDialog(recording, parent)

    def handle_delete(rid: int) -> None:

        if recording_service.delete(rid):
            if on_deleted is not None:
                on_deleted()

        elif on_delete_failed is not None:
            on_delete_failed(_DELETE_FAILED_MESSAGE)

    dialog.delete_requested.connect(handle_delete)

    dialog.exec()
