"""Contrato de importação de arquivos de imagem para o repositório local."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ImportedImage:
    """Resultado da importação de um arquivo de imagem para o repositório."""

    file_path: str
    width: int
    height: int


class ImageFileImporter(ABC):
    """Importa arquivos de imagem externos (implementação thread-safe)."""

    @abstractmethod
    def import_file(self, source_path: str) -> ImportedImage:
        """Importa o arquivo e devolve caminho destino + dimensões."""
        raise NotImplementedError
