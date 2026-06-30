"""Perfis de exportação de datasets YOLO (segmentação Ultralytics)."""

from __future__ import annotations

from enum import Enum


class YoloExportFormat(Enum):
    """Define variações do ``data.yaml`` para compatibilidade entre versões."""

    ultralytics_v8 = "ultralytics_v8"
    ultralytics_v11 = "ultralytics_v11"
    ultralytics_v26 = "ultralytics_v26"

    @classmethod
    def choices(cls) -> tuple[YoloExportFormat, ...]:
        return (
            cls.ultralytics_v8,
            cls.ultralytics_v11,
            cls.ultralytics_v26,
        )

    @classmethod
    def from_settings_value(cls, value: str | None) -> YoloExportFormat:
        if not value:
            return DEFAULT_YOLO_EXPORT_FORMAT
        try:
            return cls(value)
        except ValueError:
            return DEFAULT_YOLO_EXPORT_FORMAT


DEFAULT_YOLO_EXPORT_FORMAT = YoloExportFormat.ultralytics_v26
