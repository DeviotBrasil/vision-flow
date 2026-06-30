"""Layout Ultralytics de segmentação para exportação ZIP de datasets YOLO."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from visionflow.domain.yolo_export_format import (
    DEFAULT_YOLO_EXPORT_FORMAT,
    YoloExportFormat,
)

DEFAULT_VAL_RATIO = 0.2
MIN_POLYGON_POINTS = 3


class _ExportAnnotation(Protocol):
    class_index: int
    points: list[tuple[float, float]]


def clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def split_for(position: int, val_ratio: float) -> str:
    if val_ratio <= 0:
        return "train"
    step = max(2, round(1 / val_ratio))
    return "val" if position % step == step - 1 else "train"


def val_indices(count: int, val_ratio: float) -> set[int]:
    """Índices destinados à validação, garantindo ao menos 1 quando possível."""
    if count < 2 or val_ratio <= 0:
        return set()
    indices = {pos for pos in range(count) if split_for(pos, val_ratio) == "val"}
    if not indices:
        indices.add(count - 1)
    return indices


def split_name(position: int, *, val_set: set[int]) -> str:
    """Nome do split para a posição, respeitando o conjunto de validação."""
    return "val" if position in val_set else "train"


def image_arcname(index: int, file_path: str) -> str:
    suffix = Path(file_path).suffix.lower() or ".jpg"
    return f"img_{index:06d}{suffix}"


def label_text_from_annotations(
    annotations: list[_ExportAnnotation],
) -> str:
    lines: list[str] = []
    for annotation in annotations:
        if len(annotation.points) < MIN_POLYGON_POINTS:
            continue
        coords = " ".join(
            f"{clamp(value):.6f}" for point in annotation.points for value in point
        )
        lines.append(f"{annotation.class_index} {coords}")
    return "\n".join(lines) + ("\n" if lines else "")


def data_yaml_text(
    class_names: list[str],
    *,
    export_format: YoloExportFormat = DEFAULT_YOLO_EXPORT_FORMAT,
    dataset_root: Path | None = None,
) -> str:
    """Gera ``data.yaml`` para o perfil Ultralytics selecionado."""
    path_value = dataset_root.resolve().as_posix() if dataset_root else "."
    lines = [
        f"path: {path_value}",
        "train: images/train",
        "val: images/val",
        f"nc: {len(class_names)}",
    ]
    if export_format is not YoloExportFormat.ultralytics_v8:
        lines.append("task: segment")
    if export_format is YoloExportFormat.ultralytics_v26:
        names_repr = ", ".join(repr(name) for name in class_names)
        lines.append(f"names: [{names_repr}]")
    else:
        lines.append("names:")
        lines.extend(
            f'  {index}: "{name}"' if ":" in name else f"  {index}: {name}"
            for index, name in enumerate(class_names)
        )
    return "\n".join(lines) + "\n"


def classes_txt(class_names: list[str]) -> str:
    return "\n".join(class_names) + ("\n" if class_names else "")
