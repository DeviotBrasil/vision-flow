"""Enumeração de dispositivos de vídeo via DirectShow (Windows).

O OpenCV (``CAP_DSHOW``) endereça webcams por índice numérico na mesma ordem
em que o DirectShow enumera a categoria ``VideoInputDeviceCategory``. Dispositivos
listados pelo DirectShow mas que não entregam frame (ex.: IR) não aparecem no
probe OpenCV; o casamento nome ↔ índice assume essa ordem compartilhada — em
máquinas com câmeras virtuais ou drivers fora de ordem o rótulo pode divergir.
"""

from __future__ import annotations

import ctypes
import logging
import threading
import uuid
from ctypes import POINTER, byref, c_ulong, c_void_p, wintypes
from dataclasses import dataclass

_logger = logging.getLogger(__name__)

CLSCTX_INPROC_SERVER = 0x1
COINIT_APARTMENTTHREADED = 0x2

_com_apartment = threading.local()


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]


def _guid(value: str) -> GUID:
    parsed = uuid.UUID(value)
    data4 = (ctypes.c_ubyte * 8)(*parsed.bytes[8:])
    return GUID(parsed.time_low, parsed.time_mid, parsed.time_hi_version, data4)


CLSID_SystemDeviceEnum = _guid("{62BE5D10-60EB-11d0-BD3B-00A0C911CE86}")
CLSID_VideoInputDeviceCategory = _guid("{860BB310-5D01-11d0-BD3B-00A0C911CE86}")
IID_ICreateDevEnum = _guid("{29840822-5B84-11d0-BD3B-00A0C911CE86}")
IID_IPropertyBag = _guid("{55272A00-42CB-11CE-8135-00AA004BB851}")


class IEnumMoniker(ctypes.Structure):
    _fields_ = [("lpVtbl", POINTER(c_void_p))]


class IMoniker(ctypes.Structure):
    _fields_ = [("lpVtbl", POINTER(c_void_p))]


class IPropertyBag(ctypes.Structure):
    _fields_ = [("lpVtbl", POINTER(c_void_p))]


class ICreateDevEnum(ctypes.Structure):
    _fields_ = [("lpVtbl", POINTER(c_void_p))]


LPENUMMONIKER = POINTER(IEnumMoniker)
LPMONIKER = POINTER(IMoniker)
LPPROPERTYBAG = POINTER(IPropertyBag)
LPCREATEENUM = POINTER(ICreateDevEnum)


class VARIANT(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("vt", wintypes.USHORT),
        ("wReserved1", wintypes.USHORT),
        ("wReserved2", wintypes.USHORT),
        ("wReserved3", wintypes.USHORT),
        ("bstrVal", c_void_p),
    ]


VT_BSTR = 8


@dataclass(frozen=True)
class DShowVideoDevice:
    """Entrada de vídeo DirectShow (ordem usada pelo índice OpenCV ``CAP_DSHOW``)."""

    friendly_name: str
    device_path: str


def _com_failed(hr: int) -> bool:
    return hr & 0x80000000 != 0


def _ensure_com_initialized() -> None:
    ole32 = ctypes.windll.ole32
    count = getattr(_com_apartment, "count", 0)
    if count == 0:
        hr = ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
        if _com_failed(hr):
            _logger.warning("DirectShow: CoInitializeEx falhou (hr=%s).", hr)
            raise OSError(hr, "CoInitializeEx falhou")
    _com_apartment.count = count + 1


def _release_com() -> None:
    count = getattr(_com_apartment, "count", 0)
    if count <= 0:
        return
    if count == 1:
        ctypes.windll.ole32.CoUninitialize()
        _com_apartment.count = 0
        return
    _com_apartment.count = count - 1


def _bstr_to_str(value: c_void_p) -> str:
    if not value:
        return ""
    return ctypes.wstring_at(value)


def _release(interface_ptr: ctypes._Pointer) -> None:
    if not interface_ptr:
        return
    release = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)(
        interface_ptr.contents.lpVtbl[2]
    )
    release(interface_ptr)


def _read_property_bag_string(prop_bag: LPPROPERTYBAG, name: str) -> str:
    oleaut32 = ctypes.windll.oleaut32
    variant = VARIANT()
    read = ctypes.WINFUNCTYPE(
        ctypes.HRESULT,
        LPPROPERTYBAG,
        wintypes.LPCOLESTR,
        POINTER(VARIANT),
        c_void_p,
    )(prop_bag.contents.lpVtbl[3])
    hr = read(prop_bag, name, byref(variant), None)
    try:
        if hr != 0 or variant.vt != VT_BSTR:
            return ""
        return _bstr_to_str(variant.bstrVal)
    finally:
        oleaut32.VariantClear(byref(variant))


def _create_video_enumerator() -> LPENUMMONIKER | None:
    ole32 = ctypes.windll.ole32
    dev_enum = LPCREATEENUM()
    hr = ole32.CoCreateInstance(
        byref(CLSID_SystemDeviceEnum),
        None,
        CLSCTX_INPROC_SERVER,
        byref(IID_ICreateDevEnum),
        byref(dev_enum),
    )
    if hr != 0 or not dev_enum:
        _logger.debug("DirectShow: CoCreateInstance falhou (hr=%s).", hr)
        return None

    create_class_enum = ctypes.WINFUNCTYPE(
        ctypes.HRESULT,
        LPCREATEENUM,
        POINTER(GUID),
        POINTER(LPENUMMONIKER),
        c_ulong,
    )(dev_enum.contents.lpVtbl[3])
    enum_moniker = LPENUMMONIKER()
    hr = create_class_enum(
        dev_enum,
        byref(CLSID_VideoInputDeviceCategory),
        byref(enum_moniker),
        0,
    )
    _release(dev_enum)
    if hr != 0 or not enum_moniker:
        _logger.debug("DirectShow: CreateClassEnumerator falhou (hr=%s).", hr)
        return None
    return enum_moniker


def _read_moniker_device(moniker: LPMONIKER) -> DShowVideoDevice | None:
    prop_bag = LPPROPERTYBAG()
    bind = ctypes.WINFUNCTYPE(
        ctypes.HRESULT,
        LPMONIKER,
        c_void_p,
        c_void_p,
        POINTER(GUID),
        POINTER(LPPROPERTYBAG),
    )(moniker.contents.lpVtbl[9])
    hr = bind(moniker, None, None, byref(IID_IPropertyBag), byref(prop_bag))
    if hr != 0 or not prop_bag:
        return None

    try:
        friendly_name = _read_property_bag_string(prop_bag, "FriendlyName")
        if not friendly_name:
            return None
        device_path = _read_property_bag_string(prop_bag, "DevicePath")
        return DShowVideoDevice(
            friendly_name=friendly_name,
            device_path=device_path,
        )
    finally:
        _release(prop_bag)


def _collect_video_devices(enum_moniker: LPENUMMONIKER) -> list[DShowVideoDevice]:
    next_moniker = ctypes.WINFUNCTYPE(
        ctypes.HRESULT,
        LPENUMMONIKER,
        c_ulong,
        POINTER(LPMONIKER),
        POINTER(c_ulong),
    )(enum_moniker.contents.lpVtbl[3])

    devices: list[DShowVideoDevice] = []
    while True:
        moniker = LPMONIKER()
        fetched = c_ulong()
        hr = next_moniker(enum_moniker, 1, byref(moniker), byref(fetched))
        if hr != 0 or fetched.value == 0 or not moniker:
            break
        try:
            device = _read_moniker_device(moniker)
            if device is not None:
                devices.append(device)
        finally:
            _release(moniker)
    return devices


def list_video_input_devices() -> list[DShowVideoDevice]:
    """Retorna dispositivos de vídeo DirectShow na ordem do índice OpenCV."""
    _ensure_com_initialized()
    enum_moniker: LPENUMMONIKER | None = None
    try:
        enum_moniker = _create_video_enumerator()
        if enum_moniker is None:
            return []
        return _collect_video_devices(enum_moniker)
    except OSError as exc:
        _logger.debug("DirectShow: enumeração indisponível: %s", exc)
        return []
    finally:
        if enum_moniker:
            _release(enum_moniker)
        _release_com()


def list_video_input_friendly_names() -> list[str]:
    """Retorna os nomes amigáveis dos dispositivos de vídeo DirectShow."""
    return [device.friendly_name for device in list_video_input_devices()]
