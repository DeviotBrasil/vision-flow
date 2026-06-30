"""Exportação de datasets YOLO de segmentação para arquivo ZIP (Ultralytics)."""

from __future__ import annotations

import logging
import zipfile
from collections.abc import Callable
from pathlib import Path

from visionflow.domain.entities.yolo import (
    YoloExportImage,
    YoloExportPayload,
)
from visionflow.domain.yolo_dataset_layout import (
    DEFAULT_VAL_RATIO,
    classes_txt,
    data_yaml_text,
    image_arcname,
    label_text_from_annotations,
    split_name,
    val_indices,
)
from visionflow.domain.yolo_export_format import (
    DEFAULT_YOLO_EXPORT_FORMAT,
    YoloExportFormat,
)

_logger = logging.getLogger(__name__)


class YoloExportService:
    """Gera a estrutura Ultralytics de segmentação em um arquivo ZIP."""

    @staticmethod
    def write_zip(
        payload: YoloExportPayload,
        target_path: str,
        *,
        export_format: YoloExportFormat = DEFAULT_YOLO_EXPORT_FORMAT,
        val_ratio: float = DEFAULT_VAL_RATIO,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> tuple[int, int]:
        """Grava o dataset em ZIP no layout Ultralytics de segmentação.

        Estrutura: ``images/{train,val}``, ``labels/{train,val}``,
        ``data.yaml`` e ``classes.txt``. Cada rótulo usa o formato de
        segmentação ``class_idx x1 y1 ... xn yn`` (normalizado).

        Returns:
            Tupla ``(adicionadas, ignoradas)``; ignoradas = imagens cujo
            arquivo está ausente no disco.
        """

        existing: list[YoloExportImage] = []

        skipped = 0

        total = len(payload.images)

        for index, image in enumerate(payload.images, start=1):
            source = Path(image.file_path or "")

            if not source.is_file():
                skipped += 1

                _logger.warning("Imagem ausente no disco: %s", image.file_path)

            else:
                existing.append(image)

            if on_progress is not None:
                on_progress(index, total)

        val_set = val_indices(len(existing), val_ratio)

        added = 0

        with zipfile.ZipFile(
            target_path, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for position, image in enumerate(existing):
                split = split_name(position, val_set=val_set)

                YoloExportService._write_image_entry(archive, image, split, position)

                added += 1

            YoloExportService._write_metadata(archive, payload, export_format)

        return added, skipped

    @staticmethod
    def _write_image_entry(
        archive: zipfile.ZipFile,
        image: YoloExportImage,
        split: str,
        position: int,
    ) -> None:

        arcname = image_arcname(position, image.file_path)

        archive.write(image.file_path, arcname=f"images/{split}/{arcname}")

        label_name = f"{Path(arcname).stem}.txt"

        label_text = label_text_from_annotations(image.annotations)

        archive.writestr(f"labels/{split}/{label_name}", label_text)

    @staticmethod
    def _write_metadata(
        archive: zipfile.ZipFile,
        payload: YoloExportPayload,
        export_format: YoloExportFormat,
    ) -> None:

        names = payload.class_names

        archive.writestr(
            "data.yaml", data_yaml_text(names, export_format=export_format)
        )

        archive.writestr("classes.txt", classes_txt(names))
