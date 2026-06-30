"""Tamanhos de renderização de ícones (pixmaps).

O QSS não define o tamanho do bitmap gerado a partir de SVG; estes valores
são a única fonte de verdade para ``QIcon.pixmap()`` e ``setIconSize()``.
"""

from PySide6.QtCore import QSize

NAV_ICON = QSize(15, 15)
TITLE_ACTION_ICON = QSize(15, 15)
TITLE_WORDMARK_HEIGHT = 20
TITLE_SMALL_ICON = QSize(11, 11)

# Telas de conteúdo (Principal e Câmera).
CONTENT_ACTION_ICON = QSize(14, 14)
TOOLBAR_ICON = QSize(13, 13)
TOOLBAR_SMALL_ICON = QSize(12, 12)
STEPPER_CHEVRON_ICON = QSize(15, 15)
STEPPER_DONE_ICON = QSize(12, 12)
INFO_ICON = QSize(16, 16)
