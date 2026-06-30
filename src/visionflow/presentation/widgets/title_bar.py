"""Barra de título da janela principal."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton

from visionflow.branding import APP_SUBTITLE, logo_wordmark_width
from visionflow.presentation.icon_sizes import (
    TITLE_ACTION_ICON,
    TITLE_WORDMARK_HEIGHT,
)
from visionflow.presentation.paths import ICONS_DIR, IMAGES_DIR
from visionflow.presentation.themes.theme_manager import ThemeManager
from visionflow.version import app_version


class TitleIconButton(QToolButton):
    """Botão quadrado da barra de título (ícone centralizado, sem borda)."""

    def __init__(
        self,
        icon_name: str,
        tooltip: str = "",
        *,
        object_name: str = "title_icon_button",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setIcon(QIcon(str(ICONS_DIR / icon_name)))
        self.setIconSize(TITLE_ACTION_ICON)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setAutoRaise(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)


class TitleBar(QFrame):
    """Barra superior com logo, versão, subtítulo e alternância de tema."""

    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self._theme_manager = theme_manager

        self.setObjectName("top_frame")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(21, 0, 21, 0)
        layout.setSpacing(0)
        layout.addLayout(self._build_left())
        layout.addStretch()
        layout.addLayout(self._build_right())

        self._theme_manager.theme_changed.connect(self._update_theme_button)
        self._update_theme_button(self._theme_manager.current)

    def _build_left(self) -> QHBoxLayout:
        left = QHBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(11)

        separator = QFrame()
        separator.setObjectName("title_separator")
        separator.setFixedSize(1, 15)

        wordmark = QLabel()
        wordmark.setObjectName("title_wordmark")
        wordmark.setPixmap(
            QIcon(str(IMAGES_DIR / "logo.svg")).pixmap(
                logo_wordmark_width(TITLE_WORDMARK_HEIGHT),
                TITLE_WORDMARK_HEIGHT,
            )
        )

        version_label = QLabel(f"v{app_version()}")
        version_label.setObjectName("title_version")

        subtitle_label = QLabel(APP_SUBTITLE)
        subtitle_label.setObjectName("title_subtitle")

        left.addWidget(wordmark)
        left.addWidget(version_label)
        left.addWidget(separator)
        left.addWidget(subtitle_label)
        return left

    def _build_right(self) -> QHBoxLayout:
        right = QHBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(9)

        self.btn_theme = TitleIconButton(
            "icon_theme_dark.svg",
            "Alternar tema",
            object_name="btn_theme",
        )
        self.btn_theme.clicked.connect(self._theme_manager.toggle)

        right.addWidget(self.btn_theme)
        return right

    def _update_theme_button(self, _theme_name: str) -> None:
        is_dark = self._theme_manager.is_dark()
        icon_name = "icon_theme_light.svg" if is_dark else "icon_theme_dark.svg"
        tooltip = "Alternar para tema claro" if is_dark else "Alternar para tema escuro"
        self.btn_theme.setIcon(QIcon(str(ICONS_DIR / icon_name)))
        self.btn_theme.setToolTip(tooltip)
