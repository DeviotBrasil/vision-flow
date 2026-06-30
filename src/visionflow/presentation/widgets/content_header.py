"""Cabeçalho das telas de conteúdo (título + subtítulo)."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class ContentHeader(QFrame):
    """Cabeçalho com título (Heading 1) e subtítulo descritivo."""

    def __init__(self, title: str, subtitle: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("content_header")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._title = QLabel(title)
        self._title.setObjectName("content_header_title")
        layout.addWidget(self._title)

        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("content_header_subtitle")
        self._subtitle.setVisible(bool(subtitle))
        layout.addWidget(self._subtitle)

    def set_subtitle(self, subtitle: str) -> None:
        """Atualiza o subtítulo, ocultando-o quando vazio."""
        self._subtitle.setText(subtitle)
        self._subtitle.setVisible(bool(subtitle))
