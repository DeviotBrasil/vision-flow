"""Helpers de trigger e configuração interna do SDK OPT."""

from __future__ import annotations

import logging
from typing import Any

_logger = logging.getLogger(__name__)

GRAB_BUFFER_COUNT = 32
GRAB_TIMEOUT_SINGLE_MS = 15000
GRAB_TIMEOUT_LIVE_MS = 200
GRAB_TIMEOUT_DRAIN_MS = 100
DRAIN_MAX_ATTEMPTS = 8


def sdk_call_ok(sdk: Any, result: int) -> bool:
    return sdk is not None and result == sdk.SCI_CAMERA_OK


def try_set_enum_by_string(cam: Any, sdk: Any, key: str, value: str) -> bool:
    """Define enum GenICam; prioriza ``SetEnumValueByStringEx`` (demo OPT)."""
    if sdk is None:
        return False
    xml_camera = int(sdk.SciCamDeviceXmlType.SciCam_DeviceXml_Camera)
    try:
        ex_result = cam.SciCam_SetEnumValueByStringEx(xml_camera, key, value)
    except OSError:
        _logger.warning(
            "Falha nativa ao definir %s=%s (handle inválido ou dispositivo fechado).",
            key,
            value,
        )
        return False
    if sdk_call_ok(sdk, ex_result):
        _logger.info("Parâmetro %s=%s aplicado (DeviceXml_Camera).", key, value)
        return True
    try:
        legacy_result = cam.SciCam_SetEnumValueByString(key, value)
    except OSError:
        _logger.warning(
            "Falha nativa ao definir %s=%s (API legada; handle inválido).",
            key,
            value,
        )
        return False
    if sdk_call_ok(sdk, legacy_result):
        _logger.info("Parâmetro %s=%s aplicado (API legada).", key, value)
        return True
    _logger.warning(
        "Não foi possível definir %s=%s (Ex=%s, legado=%s).",
        key,
        value,
        ex_result,
        legacy_result,
    )
    return False


def apply_sdk_setting(cam: Any, label: str, action: Any) -> None:
    """Aplica parâmetro interno do SDK e registra falhas sem abortar a conexão."""
    try:
        result = action()
        if isinstance(result, int) and not sdk_call_ok(
            getattr(action, "__self__", None), result
        ):
            _logger.warning("SDK: %s retornou código %s.", label, result)
    except Exception as exc:
        _logger.warning("SDK: falha ao %s: %s", label, exc)


def clear_payload_buffer_logged(cam: Any, sdk: Any, *, context: str) -> None:
    """Limpa o buffer de payloads do SDK sem propagar falha para a UI."""
    try:
        code = cam.SciCam_ClearPayloadBuffer()
        if code != sdk.SCI_CAMERA_OK:
            _logger.debug("%s: ClearPayloadBuffer código %s.", context, code)
    except Exception as exc:
        _logger.warning("%s: ClearPayloadBuffer falhou: %s", context, exc)


def configure_sdk_grabbing(cam: Any, sdk: Any) -> None:
    """Parâmetros internos do SDK — não altera GenICam da câmera."""
    try:
        result = cam.SciCam_SetGrabBufferCount(GRAB_BUFFER_COUNT)
        if isinstance(result, int) and not sdk_call_ok(sdk, result):
            _logger.warning("SDK: definir buffer de grab retornou código %s.", result)
    except Exception as exc:
        _logger.warning("SDK: falha ao definir buffer de grab: %s", exc)
    try:
        result = cam.SciCam_SetGrabTimeout(GRAB_TIMEOUT_SINGLE_MS)
        if isinstance(result, int) and not sdk_call_ok(sdk, result):
            _logger.warning("SDK: definir timeout de grab retornou código %s.", result)
    except Exception as exc:
        _logger.warning("SDK: falha ao definir timeout de grab: %s", exc)
    strategy = sdk.SciCamGrabStrategy.SciCam_GrabStrategy_Latest
    try:
        result = cam.SciCam_SetGrabStrategy(strategy)
        if isinstance(result, int) and not sdk_call_ok(sdk, result):
            _logger.warning(
                "SDK: definir estratégia de grab retornou código %s.", result
            )
    except Exception as exc:
        _logger.warning("SDK: falha ao definir estratégia de grab: %s", exc)
