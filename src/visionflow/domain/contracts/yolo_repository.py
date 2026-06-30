"""Contrato de persistência de datasets YOLO (classes, imagens e anotações)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from visionflow.domain.entities.yolo import (
    YoloAnnotation,
    YoloClass,
    YoloDataset,
    YoloDatasetImage,
)


class YoloRepository(ABC):
    """Operações de persistência para datasets de segmentação YOLO."""

    @abstractmethod
    def create_dataset(self, name: str) -> int:
        """Cria um dataset e devolve seu ``id``."""
        ...

    @abstractmethod
    def list_datasets(self) -> list[YoloDataset]:
        """Lista todos os datasets (mais recentes primeiro)."""
        ...

    @abstractmethod
    def get_dataset(self, dataset_id: int) -> YoloDataset | None:
        """Detalhe de um dataset pelo ``id``."""
        ...

    @abstractmethod
    def rename_dataset(self, dataset_id: int, name: str) -> None:
        """Renomeia um dataset existente."""
        ...

    @abstractmethod
    def delete_dataset(self, dataset_id: int) -> None:
        """Remove o dataset e, em cascata, classes/imagens/anotações."""
        ...

    @abstractmethod
    def add_class(
        self, dataset_id: int, name: str, color: str, order_index: int
    ) -> int:
        """Cria uma classe no dataset e devolve seu ``id``."""
        ...

    @abstractmethod
    def list_classes(self, dataset_id: int) -> list[YoloClass]:
        """Lista as classes do dataset ordenadas por ``order_index``."""
        ...

    @abstractmethod
    def update_class(self, class_id: int, *, name: str, color: str) -> None:
        """Atualiza nome e cor de uma classe."""
        ...

    @abstractmethod
    def delete_class(self, class_id: int) -> None:
        """Remove a classe e, em cascata, suas anotações."""
        ...

    @abstractmethod
    def add_image(self, dataset_id: int, capture_id: int) -> int | None:
        """Vincula uma captura ao dataset.

        Returns:
            O ``id`` do vínculo criado, ou ``None`` se a captura já pertencia
            ao dataset.
        """
        ...

    @abstractmethod
    def list_images(self, dataset_id: int) -> list[YoloDatasetImage]:
        """Lista as imagens do dataset (com ``file_path`` da captura)."""
        ...

    @abstractmethod
    def remove_image(self, image_id: int) -> None:
        """Remove o vínculo de imagem e, em cascata, suas anotações."""
        ...

    @abstractmethod
    def count_annotations(self, image_id: int) -> int:
        """Quantidade de anotações de uma imagem."""
        ...

    @abstractmethod
    def classes_by_image(self, dataset_id: int) -> dict[int, list[str]]:
        """Classes distintas anotadas em cada imagem do dataset (em ordem)."""
        ...

    @abstractmethod
    def annotation_count_by_class(self, dataset_id: int) -> dict[int, int]:
        """Quantidade de anotações por classe (``class_id`` -> total)."""
        ...

    @abstractmethod
    def list_annotations(self, image_id: int) -> list[YoloAnnotation]:
        """Lista as anotações de uma imagem."""
        ...

    @abstractmethod
    def set_annotations(self, image_id: int, annotations: list[YoloAnnotation]) -> None:
        """Substitui todas as anotações de uma imagem."""
        ...
