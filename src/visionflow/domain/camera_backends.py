"""Identificadores e metadados dos backends de câmera suportados."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BACKEND_OPT = "opt"
BACKEND_UVC = "uvc"
BACKEND_VIDEO = "video"

DiscoverMode = Literal["scan", "file_picker"]

DEVICE_TABLE_COLUMN_KEYS = frozenset(
    {
        "index",
        "name",
        "model",
        "serial",
        "ip",
        "mac",
        "interface",
        "tl_type",
        "opencv_index",
        "video_path",
        "resolution",
        "fps",
        "duration",
    }
)

_OPT_DEVICE_TABLE_COLUMNS = (
    ("#", "index"),
    ("Nome", "name"),
    ("Modelo", "model"),
    ("Nº Série", "serial"),
    ("IP", "ip"),
    ("MAC", "mac"),
    ("Interface", "interface"),
    ("Tipo", "tl_type"),
)

_UVC_DEVICE_TABLE_COLUMNS = (
    ("#", "index"),
    ("Nome", "name"),
    ("Índice DirectShow", "opencv_index"),
)

_VIDEO_DEVICE_TABLE_COLUMNS = (
    ("Arquivo", "name"),
    ("Caminho", "video_path"),
    ("Resolução", "resolution"),
    ("FPS", "fps"),
    ("Duração", "duration"),
)


@dataclass(frozen=True)
class DeviceTableColumn:
    """Coluna exibida na tabela de dispositivos do wizard."""

    header: str
    key: str


@dataclass(frozen=True)
class BackendDescriptor:
    """Metadados de um backend de câmera (domínio puro, sem factories)."""

    id: str
    label: str
    supports_trigger: bool
    discover_mode: DiscoverMode
    uses_opencv_index: bool
    requires_video_path: bool
    wizard_devices_subtitle: str
    wizard_search_button_label: str
    wizard_info_title: str
    wizard_info_description: str
    device_table_columns: tuple[DeviceTableColumn, ...]
    devices_found_status_template: str
    devices_empty_status_template: str


def _columns(spec: tuple[tuple[str, str], ...]) -> tuple[DeviceTableColumn, ...]:
    columns = tuple(DeviceTableColumn(header, key) for header, key in spec)
    for column in columns:
        if column.key not in DEVICE_TABLE_COLUMN_KEYS:
            raise ValueError(f"Chave de coluna desconhecida no backend: {column.key!r}")
    return columns


BACKEND_REGISTRY: dict[str, BackendDescriptor] = {
    BACKEND_OPT: BackendDescriptor(
        id=BACKEND_OPT,
        label="OPT Machine Vision",
        supports_trigger=True,
        discover_mode="scan",
        uses_opencv_index=False,
        requires_video_path=False,
        wizard_devices_subtitle="Dispositivos encontrados na rede ou USB",
        wizard_search_button_label="Buscar dispositivos",
        wizard_info_title="OPT Machine Vision",
        wizard_info_description=(
            "Suporte a câmeras GigE Vision e USB3 Vision. SDK compatível com GenICam."
        ),
        device_table_columns=_columns(_OPT_DEVICE_TABLE_COLUMNS),
        devices_found_status_template="{count} dispositivo(s) encontrado(s).",
        devices_empty_status_template="Nenhum dispositivo encontrado.",
    ),
    BACKEND_UVC: BackendDescriptor(
        id=BACKEND_UVC,
        label="Webcam USB (UVC)",
        supports_trigger=False,
        discover_mode="scan",
        uses_opencv_index=True,
        requires_video_path=False,
        wizard_devices_subtitle="Webcams USB detectadas no sistema",
        wizard_search_button_label="Buscar webcams",
        wizard_info_title="Webcam USB (UVC)",
        wizard_info_description=(
            "Webcams USB genéricas via OpenCV (DirectShow). Sem trigger externo."
        ),
        device_table_columns=_columns(_UVC_DEVICE_TABLE_COLUMNS),
        devices_found_status_template="{count} webcam(s) encontrada(s).",
        devices_empty_status_template="Nenhuma webcam encontrada.",
    ),
    BACKEND_VIDEO: BackendDescriptor(
        id=BACKEND_VIDEO,
        label="Vídeo (arquivo)",
        supports_trigger=False,
        discover_mode="file_picker",
        uses_opencv_index=False,
        requires_video_path=True,
        wizard_devices_subtitle="Arquivo de vídeo selecionado",
        wizard_search_button_label="Importar vídeo",
        wizard_info_title="Vídeo (arquivo)",
        wizard_info_description=(
            "Importação de arquivo de vídeo. Preview em loop no assistente; "
            "na tela Principal, player com pausar e seek. Sem trigger externo."
        ),
        device_table_columns=_columns(_VIDEO_DEVICE_TABLE_COLUMNS),
        devices_found_status_template="Vídeo importado com sucesso.",
        devices_empty_status_template="Nenhum vídeo importado.",
    ),
}

BACKEND_ORDER: tuple[str, ...] = (BACKEND_OPT, BACKEND_UVC, BACKEND_VIDEO)


def get_backend_descriptor(backend: str) -> BackendDescriptor | None:
    """Retorna o descritor do backend ou ``None`` se desconhecido."""
    return BACKEND_REGISTRY.get(backend)


def is_valid_backend(backend: str) -> bool:
    """Indica se ``backend`` é um identificador suportado."""
    return backend in BACKEND_REGISTRY


def backend_supports_trigger(backend: str) -> bool:
    """Indica se o backend expõe trigger externo (GenICam)."""
    descriptor = BACKEND_REGISTRY.get(backend)
    return descriptor.supports_trigger if descriptor is not None else False
