"""Contrato de armazenamento de imagens (port).

A implementação concreta decide o formato (ex.: JPEG), o diretório e o nome do
arquivo. O domínio apenas solicita a gravação/remoção do frame.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class ImageStorage(ABC):
    """Armazena e remove imagens de captura em um meio persistente."""

    @abstractmethod
    def save(self, frame: np.ndarray) -> str:
        """Grava o frame e devolve o caminho do arquivo criado.

        Levanta exceção se a gravação falhar.
        """
        raise NotImplementedError

    @abstractmethod
    def overwrite(self, file_path: str, frame: np.ndarray) -> None:
        """Sobrescreve o JPEG existente no caminho informado.

        Levanta exceção se a gravação falhar.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, file_path: str) -> None:
        """Remove o arquivo de imagem (idempotente)."""
        raise NotImplementedError
