"""Casos de uso de datasets YOLO: classes, imagens e anotações.

Depende apenas do contrato :class:`YoloRepository`; não conhece SQL nem Qt.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from visionflow.domain.contracts.yolo_repository import YoloRepository
from visionflow.domain.entities.yolo import (
    ANNOTATION_KIND_RECT,
    YoloAnnotation,
    YoloClass,
    YoloDataset,
    YoloDatasetImage,
    YoloExportAnnotation,
    YoloExportImage,
    YoloExportPayload,
)

_logger = logging.getLogger(__name__)


class YoloDatasetService:
    """Orquestra a criação e edição de datasets de segmentação YOLO."""

    def __init__(self, repository: YoloRepository) -> None:
        self._repository = repository

    def create_dataset(self, name: str) -> YoloDataset | None:
        """Cria um dataset com nome não vazio."""
        clean = name.strip()
        if not clean:
            return None
        dataset_id = self._repository.create_dataset(clean)
        _logger.info("Dataset YOLO criado id=%s nome=%s.", dataset_id, clean)
        return YoloDataset(id=dataset_id, name=clean)

    def list_datasets(self) -> list[YoloDataset]:
        """Lista os datasets existentes."""
        return self._repository.list_datasets()

    def get_dataset(self, dataset_id: int) -> YoloDataset | None:
        """Detalhe de um dataset."""
        return self._repository.get_dataset(dataset_id)

    def rename_dataset(self, dataset_id: int, name: str) -> bool:
        """Renomeia um dataset; ignora nome vazio."""
        clean = name.strip()
        if not clean:
            return False
        self._repository.rename_dataset(dataset_id, clean)
        return True

    def delete_dataset(self, dataset_id: int) -> None:
        """Remove o dataset e tudo o que depende dele."""
        self._repository.delete_dataset(dataset_id)
        _logger.info("Dataset YOLO removido id=%s.", dataset_id)

    def list_classes(self, dataset_id: int) -> list[YoloClass]:
        """Lista as classes do dataset (ordenadas pelo índice)."""
        return self._repository.list_classes(dataset_id)

    def add_class(self, dataset_id: int, name: str, color: str) -> YoloClass | None:
        """Cria uma classe com índice contíguo; recusa nome duplicado/vazio."""
        clean = name.strip()
        if not clean:
            return None
        existing = self._repository.list_classes(dataset_id)
        if any(item.name.casefold() == clean.casefold() for item in existing):
            return None
        order_index = len(existing)
        class_id = self._repository.add_class(dataset_id, clean, color, order_index)
        return YoloClass(
            id=class_id,
            dataset_id=dataset_id,
            name=clean,
            color=color,
            order_index=order_index,
        )

    def update_class(self, class_id: int, *, name: str, color: str) -> bool:
        """Atualiza nome e cor de uma classe; recusa nome vazio."""
        clean = name.strip()
        if not clean:
            return False
        self._repository.update_class(class_id, name=clean, color=color)
        return True

    def delete_class(self, class_id: int) -> None:
        """Remove a classe e suas anotações."""
        self._repository.delete_class(class_id)

    def list_images(self, dataset_id: int) -> list[YoloDatasetImage]:
        """Lista as imagens vinculadas ao dataset."""
        return self._repository.list_images(dataset_id)

    def add_images(self, dataset_id: int, capture_ids: Iterable[int]) -> int:
        """Vincula capturas ao dataset; retorna quantas foram adicionadas."""
        added = 0
        for capture_id in capture_ids:
            if self._repository.add_image(dataset_id, capture_id) is not None:
                added += 1
        if added:
            _logger.info(
                "Dataset id=%s: %s imagem(ns) adicionada(s).", dataset_id, added
            )
        return added

    def remove_image(self, image_id: int) -> None:
        """Remove uma imagem do dataset."""
        self._repository.remove_image(image_id)

    def count_annotations(self, image_id: int) -> int:
        """Quantidade de anotações de uma imagem."""
        return self._repository.count_annotations(image_id)

    def classes_by_image(self, dataset_id: int) -> dict[int, list[str]]:
        """Classes distintas anotadas em cada imagem do dataset (em ordem)."""
        return self._repository.classes_by_image(dataset_id)

    def annotation_count_by_class(self, dataset_id: int) -> dict[int, int]:
        """Total de anotações por classe (``class_id`` -> total)."""
        return self._repository.annotation_count_by_class(dataset_id)

    def list_annotations(self, image_id: int) -> list[YoloAnnotation]:
        """Lista as anotações de uma imagem."""
        return self._repository.list_annotations(image_id)

    def set_annotations(self, image_id: int, annotations: list[YoloAnnotation]) -> None:
        """Substitui as anotações de uma imagem."""
        self._repository.set_annotations(image_id, annotations)

    def build_export_payload(self, dataset_id: int) -> YoloExportPayload | None:
        """Monta o payload completo para exportação Ultralytics de segmentação.

        Retângulos (2 cantos) são convertidos em polígonos de 4 vértices.
        """
        dataset = self._repository.get_dataset(dataset_id)
        if dataset is None:
            return None
        classes = self._repository.list_classes(dataset_id)
        class_index_by_id = {
            int(item.id or 0): index for index, item in enumerate(classes)
        }
        images = self._repository.list_images(dataset_id)
        export_images: list[YoloExportImage] = []
        for image in images:
            if not image.file_path or image.id is None:
                continue
            annotations = self._repository.list_annotations(image.id)
            export_annotations = [
                YoloExportAnnotation(
                    class_index=class_index_by_id[annotation.class_id],
                    points=self._polygon_points(annotation),
                )
                for annotation in annotations
                if annotation.class_id in class_index_by_id
            ]
            export_images.append(
                YoloExportImage(
                    file_path=image.file_path,
                    annotations=export_annotations,
                )
            )
        return YoloExportPayload(
            dataset_name=dataset.name,
            class_names=[item.name for item in classes],
            images=export_images,
        )

    @staticmethod
    def _polygon_points(
        annotation: YoloAnnotation,
    ) -> list[tuple[float, float]]:
        """Converte retângulo (2 cantos) em 4 vértices; mantém polígonos."""
        points = annotation.points
        if annotation.kind == ANNOTATION_KIND_RECT and len(points) == 2:
            (x1, y1), (x2, y2) = points
            left, right = min(x1, x2), max(x1, x2)
            top, bottom = min(y1, y2), max(y1, y2)
            return [(left, top), (right, top), (right, bottom), (left, bottom)]
        return list(points)
