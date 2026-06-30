"""Chips de metadados do frame (resolução, pixel, frame ID, timestamp)."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from visionflow.presentation.format_utils import format_resolution


class _Chip(QFrame):
    """Chip individual com uma legenda e um valor."""

    def __init__(self, caption: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("metadata_chip")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._caption = QLabel(caption)
        self._caption.setObjectName("metadata_chip_caption")
        self._value = QLabel("—")
        self._value.setObjectName("metadata_chip_value")

        layout.addWidget(self._caption)
        layout.addWidget(self._value)

    def set_value(self, value: str) -> None:
        self._value.setText(value or "—")


class MetadataChips(QFrame):
    """Linha de chips com os metadados do último frame."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("metadata_chips")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._resolution = _Chip("RESOLUÇÃO")
        self._pixel = _Chip("FORMATO DE PIXEL")
        self._frame_id = _Chip("FRAME ID")
        self._timestamp = _Chip("TIMESTAMP")

        for chip in (self._resolution, self._pixel, self._frame_id, self._timestamp):
            chip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            layout.addWidget(chip, 1)

    def update_metadata(self, meta: dict[str, Any]) -> None:
        """Atualiza os chips a partir dos metadados do frame."""
        resolution = format_resolution(meta.get("width"), meta.get("height"))
        self._resolution.set_value(resolution)
        self._pixel.set_value(str(meta.get("pixel_format", "—")))
        frame_id = meta.get("frame_id")
        self._frame_id.set_value(str(frame_id) if frame_id is not None else "—")
        timestamp = meta.get("timestamp")
        self._timestamp.set_value(str(timestamp) if timestamp is not None else "—")

    def clear(self) -> None:
        """Limpa todos os chips."""
        for chip in (self._resolution, self._pixel, self._frame_id, self._timestamp):
            chip.set_value("—")
