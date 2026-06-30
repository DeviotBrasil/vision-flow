"""Helpers de dimensionamento de preview em popups de detalhe."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout


@dataclass(frozen=True)
class PreviewScaleLimits:
    max_width: int
    max_height: int
    fallback_width: int
    fallback_height: int


STANDARD_PREVIEW_LIMITS = PreviewScaleLimits(
    max_width=1280,
    max_height=900,
    fallback_width=320,
    fallback_height=240,
)

DIALOG_BODY_PAD = 16
DIALOG_ACTIONS_SPACING = 9
DIALOG_MIN_WIDTH = 360
DIALOG_MIN_HEIGHT = 280


@dataclass(frozen=True)
class PreviewDialogLayout:
    body_pad: int = DIALOG_BODY_PAD
    actions_spacing: int = DIALOG_ACTIONS_SPACING
    min_width: int = DIALOG_MIN_WIDTH
    min_height: int = DIALOG_MIN_HEIGHT


DEFAULT_PREVIEW_DIALOG_LAYOUT = PreviewDialogLayout()


def scaled_preview_size(
    width: int,
    height: int,
    limits: PreviewScaleLimits,
) -> tuple[int, int]:
    """Escala dimensões para caber no retângulo máximo, preservando proporção."""
    if width <= 0 or height <= 0:
        return limits.fallback_width, limits.fallback_height
    scale = min(
        limits.max_width / width,
        limits.max_height / height,
        1.0,
    )
    return max(1, int(width * scale)), max(1, int(height * scale))


def load_scaled_preview_pixmap(
    file_path: str,
    limits: PreviewScaleLimits = STANDARD_PREVIEW_LIMITS,
) -> QPixmap:
    """Carrega imagem do disco e escala para os limites do popup."""
    pixmap = QPixmap(file_path)
    if pixmap.isNull():
        return pixmap
    width, height = scaled_preview_size(pixmap.width(), pixmap.height(), limits)
    if width == pixmap.width() and height == pixmap.height():
        return pixmap
    return pixmap.scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def scaled_pixmap_from_source(
    pixmap: QPixmap,
    limits: PreviewScaleLimits = STANDARD_PREVIEW_LIMITS,
) -> QPixmap:
    """Escala um ``QPixmap`` já carregado para os limites do popup."""
    if pixmap.isNull():
        return pixmap
    width, height = scaled_preview_size(pixmap.width(), pixmap.height(), limits)
    if width == pixmap.width() and height == pixmap.height():
        return pixmap
    return pixmap.scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def build_fixed_preview_label(
    pixmap: QPixmap,
    *,
    object_name: str,
    limits: PreviewScaleLimits = STANDARD_PREVIEW_LIMITS,
    unavailable_text: str = "Imagem indisponível",
) -> tuple[QLabel, tuple[int, int]]:
    """Monta rótulo de preview com tamanho fixo e retorna dimensões do conteúdo."""
    preview = QLabel()
    preview.setObjectName(object_name)
    preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if pixmap.isNull():
        preview.setText(unavailable_text)
        preview.setMinimumSize(limits.fallback_width, limits.fallback_height)
        return preview, (limits.fallback_width, limits.fallback_height)

    scaled = scaled_pixmap_from_source(pixmap, limits)
    preview.setPixmap(scaled)
    preview.setFixedSize(scaled.size())
    return preview, (scaled.width(), scaled.height())


def finalize_preview_dialog_size(
    dialog: QDialog,
    subtitle: QLabel,
    content_size: tuple[int, int],
    actions: QHBoxLayout,
    layout: PreviewDialogLayout = DEFAULT_PREVIEW_DIALOG_LAYOUT,
) -> None:
    """Calcula e fixa o tamanho do diálogo com preview centralizado."""
    content_width, content_height = content_size
    root_layout = dialog.layout()
    if root_layout is not None:
        root_layout.activate()

    body_w = content_width + 2 * layout.body_pad
    subtitle_w = subtitle.sizeHint().width() + 2 * layout.body_pad
    actions_w = actions.sizeHint().width() + 2 * layout.body_pad
    body_h = (
        subtitle.sizeHint().height()
        + layout.actions_spacing
        + content_height
        + layout.actions_spacing
        + actions.sizeHint().height()
        + 2 * layout.body_pad
    )
    width = max(layout.min_width, body_w, subtitle_w, actions_w)
    height = max(layout.min_height, body_h)
    dialog.setFixedSize(width, height)


def build_preview_dialog_root(
    *,
    body_pad: int = DIALOG_BODY_PAD,
    actions_spacing: int = DIALOG_ACTIONS_SPACING,
) -> QVBoxLayout:
    root = QVBoxLayout()
    root.setContentsMargins(body_pad, body_pad, body_pad, body_pad)
    root.setSpacing(actions_spacing)
    return root
