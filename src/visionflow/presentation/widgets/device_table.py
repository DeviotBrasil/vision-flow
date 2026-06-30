"""Tabela de dispositivos encontrados na busca de câmeras."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from visionflow.domain.camera_backends import (
    BACKEND_OPT,
    BACKEND_REGISTRY,
    DeviceTableColumn,
    get_backend_descriptor,
)
from visionflow.domain.entities.device_info import DeviceInfo
from visionflow.presentation.format_utils import (
    format_time_ms,
    format_video_resolution,
)

_DEFAULT_COLUMNS = get_backend_descriptor(BACKEND_OPT).device_table_columns

_COL_CENTER = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
_COL_LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

ColumnResolver = Callable[[DeviceInfo], str]


def _column_alignment(key: str) -> Qt.AlignmentFlag:
    if key == "index":
        return _COL_CENTER
    return _COL_LEFT


def _format_fps(fps: object) -> str:
    if not isinstance(fps, (int, float)) or fps <= 0:
        return ""
    return f"{fps:.1f}"


def _build_column_resolvers() -> dict[str, ColumnResolver]:
    return {
        "index": lambda device: str(device.index + 1),
        "name": lambda device: device.name,
        "model": lambda device: device.model,
        "serial": lambda device: device.serial,
        "ip": lambda device: device.ip,
        "mac": lambda device: device.mac,
        "interface": lambda device: device.interface,
        "tl_type": lambda device: device.tl_type,
        "opencv_index": lambda device: str(device.extra.get("opencv_index", "")),
        "video_path": lambda device: str(device.extra.get("video_path", "")),
        "resolution": lambda device: format_video_resolution(
            device.extra.get("width"),
            device.extra.get("height"),
        ),
        "fps": lambda device: _format_fps(device.extra.get("fps")),
        "duration": lambda device: format_time_ms(device.extra.get("duration_ms")),
    }


def _validate_column_resolvers(resolvers: dict[str, ColumnResolver]) -> None:
    missing: set[str] = set()
    for descriptor in BACKEND_REGISTRY.values():
        for column in descriptor.device_table_columns:
            if column.key not in resolvers:
                missing.add(column.key)
    if missing:
        keys = ", ".join(sorted(missing))
        raise RuntimeError(f"DeviceTable sem resolver para chave(s) de coluna: {keys}")


_COLUMN_RESOLVERS = _build_column_resolvers()
_validate_column_resolvers(_COLUMN_RESOLVERS)


class DeviceTable(QTableWidget):
    """Lista os dispositivos descobertos e sinaliza mudança de seleção."""

    selection_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(0, 0, parent)
        self.setObjectName("device_table")
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)

        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setHighlightSections(False)

        self._current_columns: tuple[DeviceTableColumn, ...] = _DEFAULT_COLUMNS
        self._devices: list[DeviceInfo] = []
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.set_column_profile(_DEFAULT_COLUMNS)

    def set_column_profile(self, columns: tuple[DeviceTableColumn, ...]) -> None:
        """Reconfigura cabeçalhos e limpa linhas conforme o backend selecionado."""
        if not columns:
            return
        self._current_columns = columns
        self._devices = []
        self.clearSelection()
        self.setRowCount(0)
        self.setColumnCount(len(columns))

        header = self.horizontalHeader()
        for column, spec in enumerate(columns):
            header_item = QTableWidgetItem(spec.header)
            header_item.setTextAlignment(_column_alignment(spec.key))
            self.setHorizontalHeaderItem(column, header_item)
            if spec.key == "index":
                header.setSectionResizeMode(
                    column, QHeaderView.ResizeMode.ResizeToContents
                )
            else:
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        self.selection_changed.emit()

    def set_devices(self, devices: list[DeviceInfo]) -> None:
        """Popula a tabela com os dispositivos descobertos."""
        self._devices = list(devices)
        self.clearSelection()
        self.setRowCount(len(self._devices))
        for row, device in enumerate(self._devices):
            for column, spec in enumerate(self._current_columns):
                resolver = _COLUMN_RESOLVERS.get(spec.key)
                value = resolver(device) if resolver is not None else ""
                item = QTableWidgetItem(value)
                item.setTextAlignment(_column_alignment(spec.key))
                self.setItem(row, column, item)

    def selected_device(self) -> DeviceInfo | None:
        """Retorna o ``DeviceInfo`` da linha selecionada, se houver."""
        row = self.currentRow()
        if 0 <= row < len(self._devices):
            return self._devices[row]
        return None

    def _on_selection_changed(self) -> None:
        self.selection_changed.emit()
