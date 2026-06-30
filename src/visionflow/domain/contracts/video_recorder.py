"""Contrato de gravação de vídeo (port para adapters OpenCV/ffmpeg)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class VideoRecorderPort(ABC):
    """Encapsula escrita de frames em arquivo de vídeo."""

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Indica se há um arquivo aberto para gravação."""
        raise NotImplementedError

    @property
    @abstractmethod
    def frame_count(self) -> int:
        """Quantidade de frames já gravados na sessão atual."""
        raise NotImplementedError

    @abstractmethod
    def start(self, path: str | Path, width: int, height: int, fps: float) -> None:
        """Abre o arquivo de saída e prepara a sessão."""
        raise NotImplementedError

    @abstractmethod
    def write_frame(self, frame: np.ndarray) -> bool:
        """Grava um frame RGB8 ou mono. Retorna ``False`` se dimensão divergir."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> str | None:
        """Finaliza a gravação e devolve o caminho, ou ``None`` se vazia."""
        raise NotImplementedError
