"""Entidade com os metadados de um dispositivo de câmera localizado."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeviceInfo:
    """Metadados de um dispositivo de câmera encontrado pela busca de rede.

    Genérico (sem dependência de SDK específico). Os adapters de hardware
    (ex.: OPT) preenchem estes campos a partir das estruturas nativas.
    """

    index: int
    name: str
    model: str
    serial: str
    ip: str
    mac: str
    interface: str
    tl_type: str
    extra: dict[str, Any] = field(default_factory=dict)
