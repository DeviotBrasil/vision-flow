"""Contrato de repositório da configuração da câmera (port de persistência)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from visionflow.domain.entities.camera_config import CameraConfig


class CameraConfigRepository(ABC):
    """Persistência da configuração única da câmera selecionada."""

    @abstractmethod
    def save(self, config: CameraConfig) -> None:
        """Salva (upsert) a configuração da câmera."""
        raise NotImplementedError

    @abstractmethod
    def load(self) -> CameraConfig | None:
        """Retorna a configuração salva, ou ``None`` se não houver."""
        raise NotImplementedError
