"""Serviço de configuração da câmera (salvar/carregar a câmera selecionada)."""

from __future__ import annotations

from visionflow.domain.camera_backends import (
    get_backend_descriptor,
    is_valid_backend,
)
from visionflow.domain.contracts.camera_config_repository import (
    CameraConfigRepository,
)
from visionflow.domain.entities.camera_config import CameraConfig
from visionflow.domain.entities.device_info import DeviceInfo
from visionflow.domain.entities.video_path import normalize_video_path


class CameraConfigService:
    """Casos de uso da configuração da câmera selecionada."""

    def __init__(self, repository: CameraConfigRepository) -> None:
        self._repository = repository

    def save_from_device(self, device: DeviceInfo, *, backend: str) -> None:
        """Persiste a configuração a partir do dispositivo escolhido no wizard."""
        if not is_valid_backend(backend):
            raise ValueError(f"Backend de câmera inválido: {backend!r}")

        descriptor = get_backend_descriptor(backend)
        if descriptor is None:
            raise ValueError(f"Backend de câmera inválido: {backend!r}")

        opencv_index: int | None = None
        if descriptor.uses_opencv_index:
            raw_index = device.extra.get("opencv_index")
            if raw_index is not None:
                opencv_index = int(raw_index)

        video_path: str | None = None
        if descriptor.requires_video_path:
            raw_path = device.extra.get("video_path")
            if not raw_path:
                raise ValueError(
                    "Caminho do vídeo é obrigatório para o backend de vídeo."
                )
            video_path = normalize_video_path(str(raw_path))

        config = CameraConfig(
            model=device.model or device.tl_type,
            backend=backend,
            name=device.name,
            serial=device.serial,
            ip=device.ip,
            mac=device.mac,
            interface=device.interface,
            tl_type=device.tl_type,
            device_index=device.index,
            opencv_index=opencv_index,
            video_path=video_path,
        )
        self._repository.save(config)

    def load(self) -> CameraConfig | None:
        """Carrega a configuração da câmera salva, se houver."""
        return self._repository.load()
