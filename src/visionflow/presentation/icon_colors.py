"""Cores semânticas para tingir ícones SVG na UI, por tema.

O QSS não recolore SVGs rasterizados (ver ``icon_utils``); por isso as cores de
ícone por papel (sucesso, info, perigo, etc.) ficam centralizadas aqui,
espelhando a paleta dos temas, em vez de espalhar hex pelas telas.
"""

from __future__ import annotations

from visionflow.presentation.themes.theme_manager import ThemeManager

# Papéis semânticos de ícone.
SUCCESS = "success"
INFO = "info"
DANGER = "danger"
NEUTRAL = "neutral"
DISABLED = "disabled"

_ICON_ROLE_COLORS: dict[str, dict[str, str]] = {
    ThemeManager.LIGHT: {
        SUCCESS: "#34C759",
        INFO: "#0066CC",
        DANGER: "#FF3B30",
        NEUTRAL: "#6E6E73",
        DISABLED: "#AEAEB2",
    },
    ThemeManager.DARK: {
        SUCCESS: "#30D158",
        INFO: "#409CFF",
        DANGER: "#FF453A",
        NEUTRAL: "#8E8E93",
        DISABLED: "#636366",
    },
}


def icon_role_color(role: str, theme: str | None = None) -> str:
    """Cor hex do ícone para o ``role`` semântico e o tema (ativo se ``None``)."""
    theme_key = theme or ThemeManager.saved_theme()
    palette = _ICON_ROLE_COLORS.get(theme_key, _ICON_ROLE_COLORS[ThemeManager.LIGHT])
    return palette.get(role, palette[NEUTRAL])
