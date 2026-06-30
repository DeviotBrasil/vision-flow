"""Botões padronizados (``vfVariant`` / ``vfShape`` no QSS)."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy

from visionflow.presentation.icon_colors import DISABLED, icon_role_color
from visionflow.presentation.icon_sizes import TOOLBAR_ICON
from visionflow.presentation.icon_utils import tinted_icon
from visionflow.presentation.style_utils import repolish
from visionflow.presentation.themes.theme_manager import ThemeManager
from visionflow.presentation.widgets.pill_controls import PillPushButton

VARIANT_PRIMARY = "primary"
VARIANT_SECONDARY = "secondary"
VARIANT_SUCCESS = "success"
VARIANT_DANGER = "danger"
VARIANT_PRIMARY_OUTLINE = "primary-outline"
VARIANT_DANGER_OUTLINE = "danger-outline"
VARIANT_NEUTRAL_OUTLINE = "neutral-outline"

SHAPE_DEFAULT = "default"
SHAPE_PILL = "pill"

PILL_BUTTON_HEIGHT = 33
PILL_BUTTON_ICON = TOOLBAR_ICON
# Wizard / conteúdo: alinhado à toolbar (antes era 34px + ícone 14px).
CONTENT_BUTTON_HEIGHT = PILL_BUTTON_HEIGHT
CONTENT_BUTTON_ICON = TOOLBAR_ICON

_ICON_COLORS: dict[str, dict[str, str]] = {
    ThemeManager.LIGHT: {
        VARIANT_PRIMARY: "#FFFFFF",
        VARIANT_SECONDARY: "#1D1D1F",
        VARIANT_SUCCESS: "#FFFFFF",
        VARIANT_DANGER: "#FFFFFF",
        VARIANT_PRIMARY_OUTLINE: "#0066CC",
        VARIANT_DANGER_OUTLINE: "#FF3B30",
        VARIANT_NEUTRAL_OUTLINE: "#6E6E73",
    },
    ThemeManager.DARK: {
        VARIANT_PRIMARY: "#FFFFFF",
        VARIANT_SECONDARY: "#F5F5F7",
        VARIANT_SUCCESS: "#FFFFFF",
        VARIANT_DANGER: "#FFFFFF",
        VARIANT_PRIMARY_OUTLINE: "#409CFF",
        VARIANT_DANGER_OUTLINE: "#FF453A",
        VARIANT_NEUTRAL_OUTLINE: "#8E8E93",
    },
}


def current_theme() -> str:
    """Tema persistido (para cor de ícone antes do ``ThemeManager`` existir)."""
    return ThemeManager.saved_theme()


def icon_color(variant: str, theme: str | None = None) -> str:
    """Cor do ícone alinhada à variante e ao tema ativo."""
    theme_key = theme or current_theme()
    palette = _ICON_COLORS.get(theme_key, _ICON_COLORS[ThemeManager.LIGHT])
    return palette.get(variant, palette[VARIANT_PRIMARY])


def _apply_pill_metrics(button: QPushButton) -> None:
    """Toolbar e modais em pílula (tamanho original da Principal)."""
    button.setFixedHeight(PILL_BUTTON_HEIGHT)
    button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    if not button.icon().isNull():
        button.setIconSize(PILL_BUTTON_ICON)


def _apply_content_metrics(button: QPushButton) -> None:
    """Botões retangulares (wizard Câmera) no mesmo tamanho da toolbar."""
    button.setFixedHeight(CONTENT_BUTTON_HEIGHT)
    button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    if not button.icon().isNull():
        button.setIconSize(CONTENT_BUTTON_ICON)


def create_button(  # noqa: PLR0913
    text: str,
    *,
    variant: str = VARIANT_PRIMARY,
    shape: str = SHAPE_DEFAULT,
    icon_name: str | None = None,
    icon: QIcon | None = None,
    icon_size: QSize | None = None,
    checkable: bool = False,
) -> QPushButton:
    """Instancia um botão com variante QSS e ícone opcional tingido."""
    button_cls = PillPushButton if shape == SHAPE_PILL else QPushButton
    button = button_cls(text)
    button.setProperty("vfVariant", variant)
    button.setProperty("vfShape", shape)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setAutoDefault(False)
    button.setDefault(False)
    button.setCheckable(checkable)

    if shape == SHAPE_PILL:
        resolved_icon_size = icon_size or PILL_BUTTON_ICON
    else:
        resolved_icon_size = icon_size or CONTENT_BUTTON_ICON

    resolved_icon = icon
    if resolved_icon is None and icon_name:
        resolved_icon = tinted_icon(icon_name, icon_color(variant), resolved_icon_size)
    if resolved_icon is not None:
        button.setIcon(resolved_icon)
        button.setIconSize(resolved_icon_size)

    if shape == SHAPE_PILL:
        _apply_pill_metrics(button)
    else:
        _apply_content_metrics(button)
    repolish(button)
    return button


def refresh_button_icon_for_state(
    button: QPushButton,
    icon_name: str,
    *,
    variant: str,
    theme: str | None = None,
) -> None:
    """Atualiza a cor do ícone conforme habilitado/desabilitado (outline danger)."""
    if button.icon().isNull():
        return
    theme_key = theme or current_theme()
    color = (
        icon_color(variant, theme_key)
        if button.isEnabled()
        else icon_role_color(DISABLED, theme_key)
    )
    button.setIcon(tinted_icon(icon_name, color, button.iconSize()))


def set_variant(
    button: QPushButton,
    variant: str,
    *,
    icon_name: str | None = None,
    theme: str | None = None,
) -> None:
    """Atualiza a variante (e opcionalmente o ícone) de um botão existente."""
    button.setProperty("vfVariant", variant)
    if icon_name is not None:
        button.setIcon(
            tinted_icon(
                icon_name,
                icon_color(variant, theme),
                button.iconSize(),
            )
        )
    repolish(button)


def update_outline_action_button(
    button: QPushButton,
    *,
    enabled: bool,
    icon_name: str,
    enabled_variant: str = VARIANT_PRIMARY_OUTLINE,
    theme: str | None = None,
) -> None:
    """Alterna variante/ícone de botão outline (padrão Salvar das galerias)."""
    variant = enabled_variant if enabled else VARIANT_NEUTRAL_OUTLINE
    button.setEnabled(enabled)
    set_variant(button, variant, icon_name=icon_name, theme=theme)
    refresh_button_icon_for_state(button, icon_name, variant=variant, theme=theme)


def button_row(*, align_left: bool = False) -> QHBoxLayout:
    """Linha horizontal para grupos de ação (rodapé de wizard, etc.)."""
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)
    if not align_left:
        row.addStretch()
    return row
