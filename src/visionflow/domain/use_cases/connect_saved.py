"""Use case: reconectar a câmera salva a partir da configuração persistida."""

from __future__ import annotations

from dataclasses import dataclass

from visionflow.domain.camera_backends import get_backend_descriptor
from visionflow.domain.contracts.camera import CameraError, CameraPort
from visionflow.domain.entities.camera_config import CameraConfig
from visionflow.domain.entities.discover_context import DiscoverContext
from visionflow.domain.use_cases.devices import (
    criteria_from_config,
    find_saved_device,
)


@dataclass(frozen=True)
class SavedConnectionPlan:
    """Plano de reconexão com dispositivo já descoberto."""

    device_index: int


@dataclass(frozen=True)
class SavedConnectionFailure:
    """Falha ao preparar reconexão com câmera salva."""

    message: str


def resolve_saved_device(
    camera: CameraPort,
    config: CameraConfig,
) -> SavedConnectionPlan | SavedConnectionFailure:
    """Descobre dispositivos e casa com a configuração salva.

    Returns:
        Plano com índice do dispositivo ou falha com mensagem para a UI.
    """
    descriptor = get_backend_descriptor(config.backend)
    if descriptor is None:
        return SavedConnectionFailure(
            message=f"Backend de câmera desconhecido: {config.backend!r}"
        )

    if descriptor.requires_video_path and not config.video_path:
        return SavedConnectionFailure(
            message=("Configuração de vídeo incompleta. Reconfigure na tela Câmera.")
        )

    discover_context: DiscoverContext | None = None
    if descriptor.requires_video_path and config.video_path:
        discover_context = DiscoverContext(video_path=config.video_path)

    try:
        devices = camera.discover(context=discover_context)
    except CameraError as exc:
        return SavedConnectionFailure(message=str(exc))

    criteria = criteria_from_config(config)
    match = find_saved_device(devices, criteria)
    if match is None:
        return SavedConnectionFailure(message="Câmera configurada não foi encontrada.")

    return SavedConnectionPlan(device_index=match.index)
