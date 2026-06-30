"""Parsing de dispositivos OPT a partir da lista do SDK SciCam."""

from __future__ import annotations

import socket
import struct
from typing import Any

from visionflow.domain.entities.device_info import DeviceInfo


def cstr(buffer: Any) -> str:
    """Converte um array ``c_ubyte`` terminado em ``NUL`` para ``str``."""
    chars = []
    for value in buffer:
        if value == 0:
            break
        chars.append(chr(value))
    return "".join(chars)


def uint32_to_ip(value: int) -> str:
    """Converte um IPv4 em ``uint32`` (ordem do host) para a forma pontilhada."""
    try:
        packed = struct.pack("!I", socket.htonl(value))
        return socket.inet_ntoa(packed)
    except OSError:
        return ""


def mac_to_str(mac: Any) -> str:
    return ":".join(f"{byte:02X}" for byte in mac)


def parse_opt_device(index: int, dev: Any, sdk: Any) -> DeviceInfo:
    """Mapeia entrada nativa do SDK para :class:`DeviceInfo`."""
    if dev.tlType == sdk.SciCamTLType.SciCam_TLType_Gige:
        info = dev.info.gigeInfo
        name = cstr(info.name) or cstr(info.userDefineName)
        return DeviceInfo(
            index=index,
            name=name,
            model=cstr(info.modelName),
            serial=cstr(info.serialNumber),
            ip=uint32_to_ip(info.ip),
            mac=mac_to_str(info.mac),
            interface=cstr(info.adapterName),
            tl_type="GigE",
        )
    if dev.tlType == sdk.SciCamTLType.SciCam_TLType_Usb3:
        info = dev.info.usb3Info
        name = cstr(info.name) or cstr(info.userDefineName)
        return DeviceInfo(
            index=index,
            name=name,
            model=cstr(info.modelName),
            serial=cstr(info.serialNumber),
            ip="",
            mac="",
            interface="USB3",
            tl_type="USB3",
        )
    return DeviceInfo(
        index=index,
        name=f"Dispositivo {index}",
        model="",
        serial="",
        ip="",
        mac="",
        interface="",
        tl_type="Desconhecido",
    )
