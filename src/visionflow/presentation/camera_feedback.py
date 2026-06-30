"""Feedback unificado de erros de câmera nas telas (log + UI)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

_logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QAbstractButton, QLabel

    from visionflow.presentation.widgets.camera_preview import CameraPreview
    from visionflow.presentation.widgets.metadata_chips import MetadataChips


def log_camera_issue(
    logger: logging.Logger,
    screen_label: str,
    message: str,
    *,
    event: str = "erro de câmera",
) -> None:
    """Registra falha de câmera com rótulo da tela."""
    logger.warning("%s: %s — %s", screen_label, event, message)


def show_preview_error(preview: CameraPreview, message: str) -> None:
    """Exibe mensagem de erro no preview da câmera."""
    preview.show_placeholder(message)


def apply_live_frame(
    preview: CameraPreview,
    frame: object,
    meta: object,
    *,
    chips: MetadataChips | None = None,
) -> None:
    """Atualiza preview (e chips opcionais) com o frame ao vivo."""
    try:
        preview.show_frame(frame)
        if chips is not None:
            chips.update_metadata(meta)
    except (TypeError, ValueError) as exc:
        _logger.warning("Frame ignorado na UI: %s", exc)


@dataclass(frozen=True)
class WizardErrorContext:
    """Estado da UI do wizard necessário para exibir erros de câmera."""

    screen_label: str
    wizard_step: int
    step_devices: int
    step_connection: int
    devices_status: QLabel | None = None
    connect_button: QAbstractButton | None = None
    preview: CameraPreview | None = None


def report_wizard_camera_error(
    logger: logging.Logger,
    message: str,
    ctx: WizardErrorContext,
    *,
    event: str = "erro de câmera",
) -> None:
    """Atualiza a UI do wizard conforme a etapa ativa."""
    log_camera_issue(logger, ctx.screen_label, message, event=event)
    if ctx.wizard_step == ctx.step_devices and ctx.devices_status is not None:
        ctx.devices_status.setText(message)
    elif ctx.wizard_step == ctx.step_connection:
        if ctx.connect_button is not None:
            ctx.connect_button.setEnabled(True)
        if ctx.preview is not None:
            show_preview_error(ctx.preview, message)
