"""Use case puro: localizar um dispositivo salvo na lista descoberta."""

from __future__ import annotations

from typing import Any

from visionflow.domain.camera_backends import get_backend_descriptor
from visionflow.domain.entities.camera_config import CameraConfig
from visionflow.domain.entities.device_info import DeviceInfo

_MATCH_KEYS = ("serial", "ip", "name")


def criteria_from_config(config: CameraConfig) -> dict[str, Any]:
    """Extrai critérios de casamento a partir da configuração persistida."""
    descriptor = get_backend_descriptor(config.backend)
    if descriptor is None:
        return {}

    if descriptor.requires_video_path:
        if config.video_path:
            return {"video_path": config.video_path}
        return {}

    criteria: dict[str, Any] = {
        key: value for key in _MATCH_KEYS if (value := getattr(config, key, "") or "")
    }
    if descriptor.uses_opencv_index:
        if config.opencv_index is not None:
            criteria["opencv_index"] = config.opencv_index
        elif config.device_index is not None:
            criteria["device_index"] = config.device_index
    return criteria


def _match_by_extra(
    devices: list[DeviceInfo],
    criteria: dict[str, Any],
    *,
    extra_key: str,
    criteria_key: str,
) -> DeviceInfo | None:
    wanted = criteria.get(criteria_key)
    if wanted is None or wanted == "":
        return None
    for device in devices:
        if device.extra.get(extra_key) == wanted:
            return device
    return None


def _match_by_index(
    devices: list[DeviceInfo], criteria: dict[str, Any]
) -> DeviceInfo | None:
    wanted_index = criteria.get("device_index")
    if wanted_index is None:
        return None
    for device in devices:
        if device.index == wanted_index:
            return device
    return None


def find_saved_device(
    devices: list[DeviceInfo], criteria: dict[str, Any]
) -> DeviceInfo | None:
    """Casa um dispositivo descoberto com a configuração salva.

    Tenta, em ordem, por ``serial``, ``ip`` e ``name``; para webcams UVC,
    tenta também por ``opencv_index`` e ``device_index``; para vídeo, por
    ``video_path``; devolve o primeiro que casar ou ``None``.
    """
    criteria = criteria or {}

    matched = _match_by_extra(
        devices, criteria, extra_key="video_path", criteria_key="video_path"
    )
    if matched is not None:
        return matched

    for key in _MATCH_KEYS:
        wanted = criteria.get(key)
        if not wanted:
            continue
        for device in devices:
            if getattr(device, key, None) == wanted:
                return device

    matched = _match_by_extra(
        devices, criteria, extra_key="opencv_index", criteria_key="opencv_index"
    )
    if matched is not None:
        return matched

    matched = _match_by_index(devices, criteria)
    if matched is not None:
        return matched

    return None
