"""Cores do editor de recorte alinhadas ao tema ativo."""

from __future__ import annotations

from PySide6.QtGui import QColor

from visionflow.presentation.icon_colors import INFO, icon_role_color

_OVERLAY_ALPHA = 120


def crop_selection_color(theme: str | None = None) -> QColor:
    """Cor da borda e contorno das alças de recorte."""
    return QColor(icon_role_color(INFO, theme))


def crop_handle_fill_color() -> QColor:
    """Preenchimento das alças (contraste sobre a imagem)."""
    return QColor(255, 255, 255)


def crop_overlay_color() -> QColor:
    """Máscara escurecida sobre a área fora do recorte."""
    return QColor(0, 0, 0, _OVERLAY_ALPHA)
