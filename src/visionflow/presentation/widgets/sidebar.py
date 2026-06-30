"""Menu lateral de navegação principal."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from visionflow.presentation.icon_sizes import NAV_ICON
from visionflow.presentation.icon_utils import tinted_pixmap
from visionflow.presentation.nav_icon_colors import nav_icon_color
from visionflow.presentation.navigation import (
    NAV_FOOTER,
    NAV_SECTIONS,
    NavItemSpec,
    NavSection,
)
from visionflow.presentation.style_utils import repolish
from visionflow.presentation.themes.theme_manager import ThemeManager
from visionflow.presentation.window_constraints import BOTTOM_PANEL_HEIGHT

WORD_WRAP_THRESHOLD = 14


class NavItem(QFrame):
    """Item de navegação com ícone, rótulo e badge opcional."""

    clicked = Signal()

    def __init__(self, spec: NavItemSpec, theme: str):
        super().__init__()
        self.page_id = spec.page_id
        self._enabled = spec.enabled
        self._icon_name = spec.icon
        self._theme = theme

        self.setObjectName("nav_item" if spec.enabled else "nav_item_disabled")
        self.setProperty("active", False)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if spec.enabled
            else Qt.CursorShape.ArrowCursor
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(13)

        self._icon_label = QLabel()
        self._icon_label.setObjectName("nav_icon")
        self._icon_label.setFixedSize(NAV_ICON)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._text_label = QLabel(spec.label)
        self._text_label.setObjectName("nav_text")
        self._text_label.setProperty("state", "enabled" if spec.enabled else "disabled")
        word_wrap = not spec.enabled and len(spec.label) > WORD_WRAP_THRESHOLD
        if word_wrap:
            self._text_label.setWordWrap(True)
            self._text_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
        else:
            self._text_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )

        row_align = (
            Qt.AlignmentFlag.AlignTop if word_wrap else Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self._icon_label, 0, row_align)
        layout.addWidget(self._text_label, 1, row_align)

        if spec.badge:
            badge_label = QLabel(spec.badge)
            badge_label.setObjectName("nav_badge")
            badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(badge_label, 0, row_align)

        self.refresh_icon()

    @property
    def is_navigable(self) -> bool:
        """Indica se o item pode receber foco/seleção."""
        return self._enabled

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self.refresh_icon()

    def refresh_icon(self) -> None:
        state = self._text_label.property("state") or "enabled"
        color = nav_icon_color(state, self._theme)
        self._icon_label.setPixmap(tinted_pixmap(self._icon_name, color, NAV_ICON))

    def set_active(self, active: bool) -> None:
        if not self._enabled:
            return
        self.setProperty("active", active)
        self._text_label.setProperty("state", "active" if active else "enabled")
        self.refresh_icon()
        repolish(self)
        repolish(self._text_label)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._enabled and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class Sidebar(QFrame):
    """Barra lateral com grupos de navegação e links inferiores."""

    page_requested = Signal(str)

    def __init__(self, theme_manager: ThemeManager | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("menu_frame")
        self._theme_manager = theme_manager
        if theme_manager is not None:
            theme_manager.theme_changed.connect(self._on_theme_changed)

        self._items: dict[str, NavItem] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("sidebar_scroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        nav_container = QWidget()
        nav_container.setObjectName("sidebar_nav_container")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        for section in NAV_SECTIONS:
            nav_layout.addWidget(self._build_section(section))

        nav_layout.addStretch()

        scroll.setWidget(nav_container)
        root.addWidget(scroll, 1)

        if NAV_FOOTER:
            footer = QFrame()
            footer.setObjectName("sidebar_footer")
            footer.setFixedHeight(BOTTOM_PANEL_HEIGHT)
            footer_layout = QVBoxLayout(footer)
            footer_layout.setContentsMargins(0, 0, 0, 0)
            footer_layout.setSpacing(0)
            footer_layout.addStretch()

            for spec in NAV_FOOTER:
                footer_layout.addWidget(self._create_item(spec))

            root.addWidget(footer)

        self.set_active_page("principal")

    def _build_section(self, section: NavSection) -> QWidget:
        container = QWidget()
        if section.section_key:
            container.setObjectName(f"sidebar_section_{section.section_key}")
        else:
            container.setObjectName("sidebar_section")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for spec in section.items:
            layout.addWidget(self._create_item(spec))

        return container

    def _current_theme(self) -> str:
        if self._theme_manager is not None:
            return self._theme_manager.current
        return ThemeManager.DEFAULT

    def _on_theme_changed(self, _theme: str) -> None:
        theme = self._current_theme()
        for item in self._items.values():
            item.set_theme(theme)

    def _create_item(self, spec: NavItemSpec) -> NavItem:
        item = NavItem(spec, self._current_theme())
        item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        if spec.enabled:
            item.clicked.connect(lambda pid=spec.page_id: self._on_nav_clicked(pid))
        self._items[spec.page_id] = item
        return item

    def _on_nav_clicked(self, page_id: str) -> None:
        self.set_active_page(page_id)
        self.page_requested.emit(page_id)

    def set_active_page(self, page_id: str) -> None:
        for pid, item in self._items.items():
            item.set_active(pid == page_id)
