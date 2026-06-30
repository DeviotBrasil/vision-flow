"""Entidade de configuração da câmera selecionada."""

from __future__ import annotations

from dataclasses import dataclass

from visionflow.domain.camera_backends import BACKEND_OPT


@dataclass
class CameraConfig:
    """Configuração única da câmera escolhida pelo usuário (persistida)."""

    model: str
    backend: str = BACKEND_OPT
    name: str = ""
    serial: str = ""
    ip: str = ""
    mac: str = ""
    interface: str = ""
    tl_type: str = ""
    device_index: int | None = None
    opencv_index: int | None = None
    video_path: str | None = None
    updated_at: str | None = None
