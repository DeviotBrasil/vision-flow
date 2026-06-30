"""Dimensões mínimas da janela principal (fonte única para layout e app)."""

from PySide6.QtCore import QSize

WINDOW_MINIMUM_SIZE = QSize(1280, 800)
SIDEBAR_WIDTH = 260
TITLE_BAR_HEIGHT = 47

# Alturas mínimas de conteúdo (rolagem vertical em vez de compressão).
SCREEN_PREVIEW_MIN_HEIGHT = 240
SCREEN_WIZARD_STACK_MIN_HEIGHT = 480

# Painel inferior (``MainRecentPanel`` na Principal + rodapé da sidebar).
# Padding espelha ``#sidebar_footer`` em ``global.qss`` e margens do painel.
STRIP_PAD_TOP = 14
STRIP_PAD_BOTTOM = 13
STRIP_HEADER_HEIGHT = 12
STRIP_HEADER_TO_BODY = 8
STRIP_THUMB_VIEWPORT_HEIGHT = 58  # miniatura 54 px + margem interna 4 px
STRIP_SCROLLBAR_RESERVE = 10  # barra horizontal 6 px + margem QSS 4 px

BOTTOM_PANEL_HEIGHT = (
    STRIP_PAD_TOP
    + STRIP_HEADER_HEIGHT
    + STRIP_HEADER_TO_BODY
    + STRIP_THUMB_VIEWPORT_HEIGHT
    + STRIP_SCROLLBAR_RESERVE
    + STRIP_PAD_BOTTOM
)
