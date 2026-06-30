import logging

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtWidgets import QApplication

from visionflow.branding import QSETTINGS_APP, QSETTINGS_ORG
from visionflow.presentation.paths import ICONS_DIR, THEMES_DIR

_logger = logging.getLogger(__name__)


class ThemeManager(QObject):
    """Carrega temas QSS, persiste a escolha e notifica a UI via sinal.

    Aplica ``global.qss`` (estrutura e dimensões) seguido do tema (``light.qss``
    ou ``dark.qss`` com cores). A preferência é salva em ``QSettings``
    (chave ``ui/theme``).
    """

    DARK = "dark"
    LIGHT = "light"

    DEFAULT = LIGHT

    # Fonte única para o armazenamento da preferência de tema (QSettings).
    ORGANIZATION = QSETTINGS_ORG
    APPLICATION = QSETTINGS_APP
    SETTINGS_KEY = "ui/theme"
    _GLOBAL_QSS = "global.qss"
    # Token nos .qss substituído pelo caminho absoluto de resources/icons
    # (permite `image: url(...)` para sub-controles como a seta do QComboBox).
    _ICONS_TOKEN = "@ICONS_DIR@"

    theme_changed = Signal(str)

    def __init__(self, app: QApplication):
        """Associa o gerenciador à instância global da aplicação Qt.

        Args:
            app: Instância retornada por ``QApplication.instance()``.
        """
        super().__init__()
        self._app = app
        self._themes_dir = THEMES_DIR
        self._current = self.DEFAULT
        self._settings = self.settings()

    @classmethod
    def settings(cls) -> QSettings:
        """Devolve o ``QSettings`` da aplicação (org/app centralizados)."""
        return QSettings(cls.ORGANIZATION, cls.APPLICATION)

    @classmethod
    def saved_theme(cls) -> str:
        """Lê o tema persistido (ou o padrão), sem instanciar o gerenciador."""
        saved = cls.settings().value(cls.SETTINGS_KEY, cls.DEFAULT)
        return saved if saved in (cls.DARK, cls.LIGHT) else cls.DEFAULT

    @classmethod
    def is_saved_dark(cls) -> bool:
        """Indica se o tema persistido é o escuro."""
        return cls.saved_theme() == cls.DARK

    @property
    def current(self) -> str:
        """Nome do tema ativo (``"dark"`` ou ``"light"``)."""
        return self._current

    def is_dark(self) -> bool:
        """Indica se o tema escuro está ativo."""
        return self._current == self.DARK

    def apply_saved_theme(self) -> str:
        """Carrega o tema persistido em ``QSettings`` ou usa o padrão claro.

        Returns:
            Nome do tema aplicado.
        """
        theme = self.saved_theme()
        self.load_theme(theme)
        return theme

    def load_theme(self, theme_name: str) -> None:
        """Aplica global + tema QSS, persiste a escolha e emite ``theme_changed``.

        Args:
            theme_name: Identificador do tema (``"dark"`` ou ``"light"``).

        Raises:
            FileNotFoundError: Se algum arquivo ``.qss`` necessário não existir.
        """
        global_qss = self._read_qss(self._GLOBAL_QSS)
        theme_qss = self._read_qss(f"{theme_name}.qss")
        stylesheet = f"{global_qss}\n{theme_qss}".replace(
            self._ICONS_TOKEN, ICONS_DIR.as_posix()
        )
        self._app.setStyleSheet(stylesheet)
        self._current = theme_name
        self._settings.setValue(self.SETTINGS_KEY, theme_name)
        _logger.debug("Tema aplicado: %s.", theme_name)
        self.theme_changed.emit(theme_name)

    def toggle(self) -> str:
        """Alterna entre tema claro e escuro.

        Returns:
            Nome do tema recém-aplicado.
        """
        next_theme = self.LIGHT if self._current == self.DARK else self.DARK
        self.load_theme(next_theme)
        return next_theme

    def _read_qss(self, filename: str) -> str:
        path = self._themes_dir / filename
        if not path.is_file():
            _logger.error("Arquivo de tema não encontrado: %s", path)
            raise FileNotFoundError(f"Estilo não encontrado: {path}")
        return path.read_text(encoding="utf-8")
