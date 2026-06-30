"""Cabeçalho compartilhado de telas de listagem (Capturas, Logs)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

_HEADER_PAD_H = 34
_HEADER_PAD_V = 21


class ListScreenHeader(QFrame):
    """Título e subtítulo dinâmico para telas de histórico."""

    def __init__(
        self,
        *,
        object_name: str,
        title: str,
        title_object_name: str,
        subtitle_object_name: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setFixedHeight(100)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            _HEADER_PAD_H, _HEADER_PAD_V, _HEADER_PAD_H, _HEADER_PAD_V
        )
        layout.setSpacing(11)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName(title_object_name)
        text_col.addWidget(title_label)

        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName(subtitle_object_name)
        text_col.addWidget(self.subtitle_label)

        layout.addLayout(text_col)
        layout.addStretch()
