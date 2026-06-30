"""Entidades do domínio de datasets YOLO (segmentação).

Coordenadas das anotações são sempre **normalizadas** (0..1) em relação às
dimensões da imagem, tornando-as independentes da resolução e prontas para a
exportação no formato Ultralytics de segmentação.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Tipos de anotação suportados pelo canvas e pela persistência.
ANNOTATION_KIND_RECT = "rect"
ANNOTATION_KIND_POLYGON = "polygon"


@dataclass
class YoloDataset:
    """Um dataset YOLO nomeado (agrupa classes, imagens e anotações)."""

    name: str
    id: int | None = None
    created_at: str | None = None


@dataclass
class YoloClass:
    """Uma classe/label do dataset.

    ``order_index`` define o índice da classe no arquivo YOLO (0-based,
    contíguo dentro do dataset).
    """

    name: str
    color: str
    order_index: int
    dataset_id: int | None = None
    id: int | None = None


@dataclass
class YoloDatasetImage:
    """Vínculo entre uma captura e um dataset.

    ``file_path``, ``width`` e ``height`` vêm do *join* com a tabela
    ``captures`` e podem ser ``None`` quando não consultados.
    """

    dataset_id: int
    capture_id: int
    id: int | None = None
    file_path: str | None = None
    width: int | None = None
    height: int | None = None


@dataclass
class YoloAnnotation:
    """Uma anotação (retângulo ou polígono) sobre uma imagem do dataset.

    ``points`` são pares ``(x, y)`` normalizados (0..1). Para ``rect`` há dois
    pares (cantos opostos); para ``polygon`` há a lista de vértices.
    """

    image_id: int
    class_id: int
    kind: str
    points: list[tuple[float, float]] = field(default_factory=list)
    id: int | None = None


@dataclass
class YoloExportAnnotation:
    """Anotação já resolvida para exportação (índice da classe + vértices)."""

    class_index: int
    points: list[tuple[float, float]]


@dataclass
class YoloExportImage:
    """Imagem do dataset com suas anotações resolvidas para exportação."""

    file_path: str
    annotations: list[YoloExportAnnotation] = field(default_factory=list)


@dataclass
class YoloExportPayload:
    """Conjunto completo necessário para gerar o ZIP Ultralytics de segmentação."""

    dataset_name: str
    class_names: list[str]
    images: list[YoloExportImage]
