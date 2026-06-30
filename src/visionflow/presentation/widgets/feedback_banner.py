"""Banner de feedback (erro ou aviso) reutilizável nas telas de listagem."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class FeedbackBanner(QFrame):
    """Faixa de mensagem oculta por padrão; estilizada via ``banner_object_name``."""

    def __init__(
        self,
        *,
        banner_object_name: str,
        text_object_name: str,
        horizontal_padding: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(banner_object_name)
        self.setVisible(False)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(horizontal_padding, 8, horizontal_padding, 8)
        layout.setSpacing(8)
        self._label = QLabel()
        self._label.setObjectName(text_object_name)
        self._label.setWordWrap(True)
        layout.addWidget(self._label, 1)

    def show_message(self, message: str) -> None:
        self._label.setText(message)
        self.setVisible(True)

    def hide_message(self) -> None:
        self.setVisible(False)
        self._label.clear()
