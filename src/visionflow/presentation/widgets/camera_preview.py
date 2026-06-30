"""Área de visualização de vídeo/imagem da câmera."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from visionflow.presentation.image_utils import ndarray_to_qpixmap
from visionflow.presentation.style_utils import repolish


class CameraPreview(QFrame):
    """Exibe o frame ao vivo (``QPixmap``) com estados de placeholder.

    Mantém o pixmap original e o reescala preservando a proporção sempre que o
    widget é redimensionado.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("camera_preview")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._canvas = QLabel()
        self._canvas.setObjectName("camera_preview_canvas")
        self._canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._canvas.setScaledContents(False)
        layout.addWidget(self._canvas)

        self._source: QPixmap | None = None
        self.show_placeholder("Nenhuma câmera conectada")

    def show_placeholder(self, message: str) -> None:
        """Mostra um texto centralizado e limpa o frame atual."""
        self._source = None
        self._canvas.setProperty("state", "placeholder")
        repolish(self._canvas)
        self._canvas.setText(message)

    def show_frame(self, frame: np.ndarray) -> None:
        """Exibe um frame (``numpy.ndarray``) ao vivo."""
        if frame is None:
            return
        pixmap = ndarray_to_qpixmap(frame)
        if pixmap.isNull():
            return
        self._source = pixmap
        self._canvas.setProperty("state", "live")
        repolish(self._canvas)
        self._canvas.setText("")
        self._rescale()

    def clear_frame(self) -> None:
        """Remove o frame exibido, voltando ao placeholder padrão."""
        self.show_placeholder("Nenhuma câmera conectada")

    def _rescale(self) -> None:
        if self._source is None or self._source.isNull():
            return
        # FastTransformation prioriza latência no preview ao vivo (não capturas).
        self._canvas.setPixmap(
            self._source.scaled(
                self._canvas.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._rescale()
