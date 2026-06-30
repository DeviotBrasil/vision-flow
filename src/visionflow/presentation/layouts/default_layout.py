import logging

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLayout,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from visionflow.presentation.camera_controller import (
    STATE_CONNECTED,
    STATE_CONNECTING,
    CameraController,
)
from visionflow.presentation.navigation import navigable_page_ids
from visionflow.presentation.screens import SCREEN_BY_ID
from visionflow.presentation.screens.factory import ScreenFactory
from visionflow.presentation.system_dialogs import confirm_disconnect_camera
from visionflow.presentation.widgets.screen_scroll import wrap_screen_in_scroll
from visionflow.presentation.widgets.sidebar import Sidebar
from visionflow.presentation.widgets.title_bar import TitleBar
from visionflow.presentation.window_constraints import (
    SIDEBAR_WIDTH,
    TITLE_BAR_HEIGHT,
    WINDOW_MINIMUM_SIZE,
)

_logger = logging.getLogger(__name__)


class DefaultLayout:
    """Composição da interface principal (barra superior, menu lateral e conteúdo)."""

    def setup_ui(
        self,
        parent,
        theme_manager,
        controller: CameraController,
        screen_factories: dict[str, ScreenFactory],
    ):
        """Monta os widgets da janela principal e define o widget central."""
        if not parent.objectName():
            parent.setObjectName("DefaultLayout")

        self.title_bar = TitleBar(theme_manager)
        self.title_bar.setFixedHeight(TITLE_BAR_HEIGHT)

        self.sidebar = Sidebar(theme_manager)
        self.sidebar.setFixedWidth(SIDEBAR_WIDTH)
        self._navigable_pages = navigable_page_ids()

        # Controlador único de câmera compartilhado pelas telas Principal/Câmera.
        self.camera_controller = controller
        self._screen_factories = screen_factories
        if self.camera_controller.is_sdk_available():
            _logger.info("SDK da câmera OPT disponível.")
        else:
            _logger.warning(
                "SDK da câmera OPT indisponível; execute "
                "scripts/sync_opt_runtime.py e verifique os logs."
            )

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("content_stack")

        self._screens: dict[str, QWidget] = {}
        self._page_hosts: dict[str, QScrollArea] = {}
        self._current_page_id = "principal"
        self._register_screens()

        self.sidebar.page_requested.connect(self._show_page)

        self.content_frame = QFrame()
        self.content_frame.setObjectName("content_frame")
        self.content_frame.setMinimumWidth(WINDOW_MINIMUM_SIZE.width() - SIDEBAR_WIDTH)
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.content_stack)

        self.center_frame = QFrame()
        self.center_frame.setObjectName("center_frame")
        self.center_frame.setMinimumHeight(
            WINDOW_MINIMUM_SIZE.height() - TITLE_BAR_HEIGHT
        )

        center_layout = QHBoxLayout(self.center_frame)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        center_layout.addWidget(self.sidebar)
        center_layout.addWidget(self.content_frame, 1)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("main_frame")
        self.main_frame.setMinimumSize(WINDOW_MINIMUM_SIZE)
        self.main_frame.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding,
        )

        main_layout = QVBoxLayout(self.main_frame)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(self.center_frame, 1)

        parent.setCentralWidget(self.main_frame)
        parent.resize(WINDOW_MINIMUM_SIZE)

        self._theme_manager = theme_manager
        self._show_page("principal")

    def _register_screens(self) -> None:
        """Instancia cada tela e adiciona ao stack (com ou sem scroll externo)."""
        for page_id, screen_cls in SCREEN_BY_ID.items():
            screen = self._build_screen(page_id, screen_cls)
            uses_outer_scroll = getattr(screen_cls, "USES_OUTER_SCROLL", True)
            if uses_outer_scroll:
                host = wrap_screen_in_scroll(screen)
            else:
                screen.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
                host = screen
            self._screens[page_id] = screen
            self._page_hosts[page_id] = host
            self.content_stack.addWidget(host)

    def _build_screen(self, page_id: str, screen_cls: type[QWidget]) -> QWidget:
        """Constrói a tela via factory registrada ou construtor padrão."""
        factory = self._screen_factories.get(page_id)
        if factory is not None:
            return factory()
        return screen_cls()

    def _show_page(self, page_id: str) -> None:
        if page_id not in self._navigable_pages:
            return
        if (
            self._current_page_id == "principal"
            and page_id != "principal"
            and self.camera_controller.state in (STATE_CONNECTED, STATE_CONNECTING)
        ):
            parent = self.content_stack.window()
            if not confirm_disconnect_camera(parent):
                self.sidebar.set_active_page("principal")
                return
            self.camera_controller.disconnect()
        self._current_page_id = page_id
        host = self._page_hosts.get(page_id)
        if host is not None:
            self.content_stack.setCurrentWidget(host)
        screen = self._screens.get(page_id)
        if screen is not None:
            refresh = getattr(screen, "refresh_recent_media", None)
            if not callable(refresh):
                refresh = getattr(screen, "refresh_captures", None)
            if not callable(refresh):
                refresh = getattr(screen, "refresh", None)
            if callable(refresh):
                refresh()
        if page_id == "camera":
            screen = self._screens.get("camera")
            reset = getattr(screen, "reset_wizard_entry", None)
            if callable(reset):
                reset()

    def screen(self, page_id: str) -> QWidget | None:
        """Retorna a instância da tela pelo identificador de navegação."""
        return self._screens.get(page_id)

    def shutdown_screens(self) -> None:
        """Encerra recursos das telas (threads de miniatura, etc.) ao fechar o app."""
        for screen in self._screens.values():
            shutdown = getattr(screen, "shutdown", None)
            if callable(shutdown):
                shutdown()
