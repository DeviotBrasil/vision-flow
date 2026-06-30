"""Rótulos e tooltips dos perfis de exportação YOLO (camada de apresentação)."""

from __future__ import annotations

from visionflow.domain.yolo_export_format import YoloExportFormat

YOLO_EXPORT_FORMAT_LABELS: dict[YoloExportFormat, str] = {
    YoloExportFormat.ultralytics_v8: "V8",
    YoloExportFormat.ultralytics_v11: "V11",
    YoloExportFormat.ultralytics_v26: "V26",
}

YOLO_EXPORT_FORMAT_TOOLTIPS: dict[YoloExportFormat, str] = {
    YoloExportFormat.ultralytics_v8: (
        "YOLOv8 / Ultralytics 8.x: data.yaml sem task; names como dicionário."
    ),
    YoloExportFormat.ultralytics_v11: (
        "Ultralytics 9-11: data.yaml com task: segment; names como dicionário."
    ),
    YoloExportFormat.ultralytics_v26: (
        "Ultralytics 12-26: data.yaml com task: segment; names como lista."
    ),
}


def yolo_export_format_label(export_format: YoloExportFormat) -> str:
    return YOLO_EXPORT_FORMAT_LABELS[export_format]


def yolo_export_format_tooltip(export_format: YoloExportFormat) -> str:
    return YOLO_EXPORT_FORMAT_TOOLTIPS[export_format]
