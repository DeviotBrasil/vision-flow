"""Conversão de payloads de imagem do SDK OPT para ``numpy``."""

from __future__ import annotations

import ctypes
from typing import Any

import numpy as np

from visionflow.domain.contracts.camera import CameraError


def bgr_to_rgb(frame: np.ndarray) -> np.ndarray:
    """Converte BGR8 para RGB de exibição (Qt espera RGB888)."""
    return frame[:, :, ::-1]


def build_mono_pixel_types(sdk: Any) -> frozenset[int]:
    """Formatos monocromáticos convertidos para Mono8; demais usam BGR8 + swap."""
    if sdk is None:
        return frozenset()
    names = (
        "Mono1p",
        "Mono2p",
        "Mono4p",
        "Mono8s",
        "Mono8",
        "Mono10",
        "Mono10p",
        "Mono12",
        "Mono12p",
        "Mono14",
        "Mono16",
        "Mono10Packed",
        "Mono12Packed",
        "Mono14p",
    )
    values = []
    for name in names:
        member = getattr(sdk.SciCamPixelType, name, None)
        if member is not None:
            values.append(int(member))
    return frozenset(values)


def read_image_bytes(
    image_data: ctypes.c_void_p, size: int, *, error_class: type[CameraError]
) -> np.ndarray:
    if not image_data.value:
        raise error_class("Buffer de imagem vazio no payload.")
    buf = (ctypes.c_ubyte * size).from_address(image_data.value)
    return np.frombuffer(buf, dtype=np.uint8, count=size)


def pixel_format_name(sdk: Any, pixel_type: int) -> str:
    try:
        return sdk.SciCamPixelType(pixel_type).name
    except ValueError:
        return f"0x{pixel_type:08X}"
