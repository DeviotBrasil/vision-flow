"""Contrato de dispositivo de câmera (port).

A implementação concreta (ex.: adapter OPT na infraestrutura) encapsula o SDK
do fabricante e devolve frames como ``numpy.ndarray`` bruto. Esta camada não
conhece detalhes de hardware nem de UI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from visionflow.domain.entities.device_info import DeviceInfo
from visionflow.domain.entities.discover_context import DiscoverContext


class CameraError(RuntimeError):
    """Erro de operação com a câmera (SDK indisponível ou falha nativa).

    As implementações concretas (adapters) levantam esta exceção (ou uma
    subclasse) para que a camada de apresentação trate falhas de hardware sem
    conhecer detalhes do SDK.
    """


class IncompleteFrameError(CameraError):
    """Frame incompleto ou corrompido na rede — seguro ignorar no preview ao vivo."""


class TriggerWaitError(CameraError):
    """Timeout ou espera de trigger sem frame — reagendar grab no modo escuta."""


class CameraPort(ABC):
    """Interface comum para todas as câmeras suportadas (padrão adapter).

    Implementações devem tratar falhas nativas sem derrubar o processo,
    permitindo um startup seguro mesmo sem dispositivo conectado.
    """

    @abstractmethod
    def discover(self, *, context: DiscoverContext | None = None) -> list[DeviceInfo]:
        """Escaneia e retorna os dispositivos disponíveis.

        Implementações devem recusar a busca enquanto :attr:`is_connected` for
        verdadeiro, para não invalidar o dispositivo em uso.

        O backend ``video`` usa :attr:`~DiscoverContext.video_path`; demais
        backends ignoram ``context``.
        """
        raise NotImplementedError

    @abstractmethod
    def select_device(self, index: int) -> None:
        """Seleciona, pelo índice da última busca, o dispositivo a conectar."""
        raise NotImplementedError

    @abstractmethod
    def connect(self) -> None:
        """Abre a conexão com o dispositivo selecionado."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Encerra a conexão e libera os recursos do dispositivo."""
        raise NotImplementedError

    @abstractmethod
    def grab(self, *, single: bool = False) -> tuple[np.ndarray, dict[str, Any]]:
        """Captura um frame, devolvendo ``(ndarray, metadados)``.

        O ``ndarray`` deve ser **independente** (cópia), seguro para uso após
        o próximo grab ou após emitir o frame para outra thread.

        O parâmetro ``single`` afeta apenas backends com trigger (timeout
        diferenciado); demais backends tratam como grab normal.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Indica se o dispositivo está conectado e pronto para capturar."""
        raise NotImplementedError


class TriggerCapableCamera(CameraPort):
    """Extensão de :class:`CameraPort` para dispositivos com trigger GenICam."""

    @property
    @abstractmethod
    def supports_trigger(self) -> bool:
        """Indica se o dispositivo suporta trigger externo (GenICam)."""
        raise NotImplementedError

    @abstractmethod
    def set_trigger_mode(self, enabled: bool) -> None:
        """Ativa ou desativa o modo trigger na câmera (GenICam ``TriggerMode``).

        ``enabled=True`` mapeia para ``On``; ``False`` para ``Off``.
        Falhas de hardware levantam :class:`CameraError`.
        """
        raise NotImplementedError


def camera_supports_trigger(camera: CameraPort) -> bool:
    """Indica se a instância expõe trigger externo."""
    return isinstance(camera, TriggerCapableCamera) and camera.supports_trigger


class VideoPlaybackPort(CameraPort):
    """Extensão de :class:`CameraPort` para arquivo de vídeo com playback."""

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        """Indica se o vídeo está em reprodução."""
        raise NotImplementedError

    @property
    @abstractmethod
    def position_ms(self) -> int:
        """Posição atual de reprodução em milissegundos."""
        raise NotImplementedError

    @property
    @abstractmethod
    def duration_ms(self) -> int:
        """Duração total do vídeo em milissegundos."""
        raise NotImplementedError

    @property
    @abstractmethod
    def fps(self) -> float:
        """Taxa de frames por segundo do arquivo."""
        raise NotImplementedError

    @abstractmethod
    def play(self) -> None:
        """Inicia ou retoma a reprodução."""
        raise NotImplementedError

    @abstractmethod
    def pause(self) -> None:
        """Pausa a reprodução mantendo o frame atual."""
        raise NotImplementedError

    @abstractmethod
    def seek_by_seconds(self, delta: float) -> None:
        """Desloca a posição relativa em segundos."""
        raise NotImplementedError

    @abstractmethod
    def seek_to_ms(self, position_ms: int) -> None:
        """Desloca para posição absoluta em milissegundos."""
        raise NotImplementedError

    @abstractmethod
    def set_loop_on_end(self, enabled: bool) -> None:
        """Define se o vídeo reinicia ao fim (preview em loop do wizard)."""
        raise NotImplementedError


def camera_supports_video_playback(camera: CameraPort) -> bool:
    """Indica se a instância expõe controles de playback de vídeo."""
    return isinstance(camera, VideoPlaybackPort)
