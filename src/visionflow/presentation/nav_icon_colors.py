"""Cores dos ícones de navegação (mesmas de ``#nav_text`` nos QSS de tema)."""

from __future__ import annotations

from visionflow.presentation.themes.theme_manager import ThemeManager

_NAV_ICON_COLORS: dict[str, dict[str, str]] = {
    ThemeManager.LIGHT: {
        "enabled": "#1D1D1F",
        "active": "#0066CC",
        "disabled": "#D2D2D7",
    },
    ThemeManager.DARK: {
        "enabled": "#F5F5F7",
        "active": "#409CFF",
        "disabled": "#48484A",
    },
}


def nav_icon_color(state: str, theme: str) -> str:
    """Retorna a cor hex do ícone para o ``state`` do item e o tema ativo."""
    palette = _NAV_ICON_COLORS.get(theme, _NAV_ICON_COLORS[ThemeManager.LIGHT])
    return palette.get(state, palette["enabled"])
