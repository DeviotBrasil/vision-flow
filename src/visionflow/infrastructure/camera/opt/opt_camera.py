"""Adapter concreto para câmeras OPT Machine Vision (SDK SciCam).

Encapsula o SDK nativo (``ctypes``) atrás do contrato :class:`CameraPort`.
Toda chamada nativa é protegida para que falhas de hardware/SDK não derrubem
o processo: os erros viram exceções :class:`OPTCameraError` tratáveis pela
camada de UI. Esta classe devolve frames como ``numpy.ndarray`` bruto; a
conversão para exibição (Qt/cv2) fica fora daqui.

O SDK nativo é carregado de forma preguiçosa (na primeira utilização), depois
que ``infrastructure.camera.native.ensure_native_lib_path`` já preparou o
caminho das bibliotecas — evitando carregar binários nativos só por importar.
"""

from __future__ import annotations

import contextlib
import ctypes
import logging
import socket
import struct
import threading
from types import SimpleNamespace
from typing import Any

import numpy as np

from visionflow.domain.contracts.camera import (
    CameraError,
    IncompleteFrameError,
    TriggerCapableCamera,
    TriggerWaitError,
)
from visionflow.domain.entities.device_info import DeviceInfo
from visionflow.domain.entities.discover_context import DiscoverContext

# Estado de carregamento do SDK (mutável: evita ``global`` em ``_load_sdk``).
_state = SimpleNamespace(sdk=None, error=None, tried=False)

_logger = logging.getLogger(__name__)

_GRAB_BUFFER_COUNT = 32
# Timeout de captura: maior na captura única; menor no preview ao vivo, para que
# o encerramento da thread não fique preso em um grab bloqueante ao fechar.
_GRAB_TIMEOUT_SINGLE_MS = 15000
_GRAB_TIMEOUT_LIVE_MS = 200
_GRAB_TIMEOUT_DRAIN_MS = 100
_GRAB_INCOMPLETE_RETRIES = 2
_DRAIN_MAX_ATTEMPTS = 8

_SDK_ERROR_HINTS: dict[int, str] = {
    100100053: (
        "Imagem incompleta na rede GigE — verifique MTU/jumbo na placa e no switch "
        "e se o tamanho de pacote (GevSCPSPacketSize) foi negociado."
    ),
    100100029: "Buffer de captura insuficiente no SDK.",
    100100024: (
        "Timeout na captura — verifique a configuração da câmera no software do "
        "fabricante (modo contínuo, trigger, MTU/jumbo) e o firewall na rede GigE."
    ),
    100100025: "Aguardando trigger externo — nenhum evento recebido no intervalo.",
}

_TRIGGER_WAIT_CODES = frozenset({100100024, 100100025})


def _load_sdk() -> None:
    """Importa o binding nativo do SDK uma única vez (preguiçoso e seguro)."""
    if _state.tried:
        return
    _state.tried = True
    try:
        from visionflow.infrastructure.camera.opt._sdk import (  # noqa: PLC0415
            SCI_CAM_PAYLOAD_ATTRIBUTE,
            SCI_CAMERA_OK,
            SCI_DEVICE_INFO_LIST,
            SciCam_Payload_ConvertImage,
            SciCam_Payload_GetAttribute,
            SciCam_Payload_GetImage,
            SciCamDeviceXmlType,
            SciCamera,
            SciCamGrabStrategy,
            SciCamPayloadMode,
            SciCamPixelType,
            SciCamTLType,
        )

        _state.sdk = SimpleNamespace(
            SCI_CAM_PAYLOAD_ATTRIBUTE=SCI_CAM_PAYLOAD_ATTRIBUTE,
            SCI_CAMERA_OK=SCI_CAMERA_OK,
            SCI_DEVICE_INFO_LIST=SCI_DEVICE_INFO_LIST,
            SciCam_Payload_ConvertImage=SciCam_Payload_ConvertImage,
            SciCam_Payload_GetAttribute=SciCam_Payload_GetAttribute,
            SciCam_Payload_GetImage=SciCam_Payload_GetImage,
            SciCamera=SciCamera,
            SciCamDeviceXmlType=SciCamDeviceXmlType,
            SciCamGrabStrategy=SciCamGrabStrategy,
            SciCamPayloadMode=SciCamPayloadMode,
            SciCamPixelType=SciCamPixelType,
            SciCamTLType=SciCamTLType,
        )
    except Exception as exc:  # qualquer falha de carregamento nativo
        _state.error = exc
        _logger.error("Falha ao carregar SDK SciCam (OPT).", exc_info=True)


class OptCameraError(CameraError):
    """Erro de operação com a câmera OPT (SDK indisponível ou falha nativa)."""


OPTCameraError = OptCameraError


def sdk_available() -> bool:
    """Indica se o SDK nativo SciCam pôde ser carregado."""
    _load_sdk()
    return _state.error is None


def sdk_import_error() -> Exception | None:
    """Retorna a exceção de carregamento do SDK, se houver."""
    _load_sdk()
    return _state.error


def _sdk_call_ok(result: int) -> bool:
    return _state.sdk is not None and result == _state.sdk.SCI_CAMERA_OK


def _bgr_to_rgb(frame: np.ndarray) -> np.ndarray:
    """Converte BGR8 para RGB de exibição (Qt espera RGB888)."""
    return frame[:, :, ::-1]


def _build_mono_pixel_types() -> frozenset[int]:
    """Formatos monocromáticos convertidos para Mono8; demais usam BGR8 + swap."""
    if _state.sdk is None:
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
        member = getattr(_state.sdk.SciCamPixelType, name, None)
        if member is not None:
            values.append(int(member))
    return frozenset(values)


def _cstr(buffer: Any) -> str:
    """Converte um array ``c_ubyte`` terminado em ``NUL`` para ``str``."""
    chars = []
    for value in buffer:
        if value == 0:
            break
        chars.append(chr(value))
    return "".join(chars)


def _uint32_to_ip(value: int) -> str:
    """Converte um IPv4 em ``uint32`` (ordem do host) para a forma pontilhada."""
    try:
        packed = struct.pack("!I", socket.htonl(value))
        return socket.inet_ntoa(packed)
    except OSError:
        return ""


def _mac_to_str(mac: Any) -> str:
    return ":".join(f"{byte:02X}" for byte in mac)


def _try_set_enum_by_string(cam: Any, key: str, value: str) -> bool:
    """Define enum GenICam; prioriza ``SetEnumValueByStringEx`` (demo OPT)."""
    if _state.sdk is None:
        return False
    xml_camera = int(_state.sdk.SciCamDeviceXmlType.SciCam_DeviceXml_Camera)
    try:
        ex_result = cam.SciCam_SetEnumValueByStringEx(xml_camera, key, value)
    except OSError:
        _logger.warning(
            "Falha nativa ao definir %s=%s (handle inválido ou dispositivo fechado).",
            key,
            value,
        )
        return False
    if _sdk_call_ok(ex_result):
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
    if _sdk_call_ok(legacy_result):
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


def _apply_sdk_setting(cam: Any, label: str, action: Any) -> None:
    """Aplica parâmetro interno do SDK e registra falhas sem abortar a conexão."""
    try:
        result = action()
        if isinstance(result, int) and not _sdk_call_ok(result):
            _logger.warning("SDK: %s retornou código %s.", label, result)
    except Exception as exc:
        _logger.warning("SDK: falha ao %s: %s", label, exc)


def _clear_payload_buffer_logged(cam: Any, *, context: str) -> None:
    """Limpa o buffer de payloads do SDK sem propagar falha para a UI."""
    try:
        code = cam.SciCam_ClearPayloadBuffer()
        if code != _state.sdk.SCI_CAMERA_OK:
            _logger.debug("%s: ClearPayloadBuffer código %s.", context, code)
    except Exception as exc:
        _logger.warning("%s: ClearPayloadBuffer falhou: %s", context, exc)


def _configure_sdk_grabbing(cam: Any) -> None:
    """Parâmetros internos do SDK — não altera GenICam da câmera."""
    _apply_sdk_setting(
        cam,
        "definir buffer de grab",
        lambda: cam.SciCam_SetGrabBufferCount(_GRAB_BUFFER_COUNT),
    )
    _apply_sdk_setting(
        cam,
        "definir timeout de grab",
        lambda: cam.SciCam_SetGrabTimeout(_GRAB_TIMEOUT_SINGLE_MS),
    )
    # Latest evita fila de frames antigos no preview (menor latência).
    strategy = _state.sdk.SciCamGrabStrategy.SciCam_GrabStrategy_Latest
    _apply_sdk_setting(
        cam,
        "definir estratégia de grab",
        lambda: cam.SciCam_SetGrabStrategy(strategy),
    )


_INCOMPLETE_GRAB_CODES = frozenset({100100053})


class OptCamera(TriggerCapableCamera):
    """Câmera OPT GigE/USB3 acessada via SDK SciCam.

    Fluxo típico: :meth:`discover` → :meth:`select_device` → :meth:`connect`
    → repetidas chamadas a :meth:`grab` → :meth:`disconnect`.
    """

    def __init__(self) -> None:
        _load_sdk()
        self._cam = _state.sdk.SciCamera() if _state.sdk is not None else None
        self._device_list: Any | None = None
        self._selected_index: int | None = None
        self._connected = False
        self._mono_pixel_types = _build_mono_pixel_types()
        self._io_lock = threading.Lock()
        self._trigger_listen_active = False

    # -- Descoberta -----------------------------------------------------------

    def discover(self, *, context: DiscoverContext | None = None) -> list[DeviceInfo]:
        """Escaneia a rede e retorna as câmeras OPT disponíveis."""
        del context
        self._require_sdk()
        with self._io_lock:
            if self._connected:
                raise OptCameraError(
                    "Não é possível buscar dispositivos com a câmera conectada. "
                    "Desconecte antes de uma nova busca."
                )
            return self._discover_locked()

    def _discover_locked(self) -> list[DeviceInfo]:
        device_list = _state.sdk.SCI_DEVICE_INFO_LIST()
        result = _state.sdk.SciCamera.SciCam_DiscoveryDevices(
            device_list, _state.sdk.SciCamTLType.SciCam_TLType_Unkown
        )
        if result != _state.sdk.SCI_CAMERA_OK:
            _logger.error("Falha na busca de câmeras (código %s).", result)
            raise OptCameraError(f"Falha ao buscar câmeras (código {result}).")

        # Mantém a lista viva: ``connect`` usa o ``SCI_DEVICE_INFO`` por índice.
        self._device_list = device_list
        devices: list[DeviceInfo] = []
        for index in range(device_list.count):
            devices.append(self._parse_device(index, device_list.pDevInfo[index]))
        _logger.info("Busca concluída: %d dispositivo(s) encontrado(s).", len(devices))
        return devices

    def _parse_device(self, index: int, dev: Any) -> DeviceInfo:
        if dev.tlType == _state.sdk.SciCamTLType.SciCam_TLType_Gige:
            info = dev.info.gigeInfo
            name = _cstr(info.name) or _cstr(info.userDefineName)
            return DeviceInfo(
                index=index,
                name=name,
                model=_cstr(info.modelName),
                serial=_cstr(info.serialNumber),
                ip=_uint32_to_ip(info.ip),
                mac=_mac_to_str(info.mac),
                interface=_cstr(info.adapterName),
                tl_type="GigE",
            )
        if dev.tlType == _state.sdk.SciCamTLType.SciCam_TLType_Usb3:
            info = dev.info.usb3Info
            name = _cstr(info.name) or _cstr(info.userDefineName)
            return DeviceInfo(
                index=index,
                name=name,
                model=_cstr(info.modelName),
                serial=_cstr(info.serialNumber),
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

    def select_device(self, index: int) -> None:
        """Seleciona, pelo índice da última busca, o dispositivo a conectar."""
        if self._device_list is None or not 0 <= index < self._device_list.count:
            raise OptCameraError("Índice de dispositivo inválido.")
        self._selected_index = index

    # -- Ciclo de vida --------------------------------------------------------

    def connect(self) -> None:
        """Cria, abre o dispositivo selecionado e inicia a aquisição."""
        with self._io_lock:
            self._connect_locked()

    def _connect_locked(self) -> None:
        self._require_sdk()
        if self._device_list is None or self._selected_index is None:
            raise OptCameraError("Nenhum dispositivo selecionado para conexão.")

        dev = self._device_list.pDevInfo[self._selected_index]
        device_info = self._parse_device(self._selected_index, dev)
        _logger.info(
            "Conectando câmera índice=%s modelo=%s serial=%s ip=%s.",
            self._selected_index,
            device_info.model,
            device_info.serial,
            device_info.ip,
        )
        self._check(self._cam.SciCam_CreateDevice(dev), "criar dispositivo")
        try:
            self._check(self._cam.SciCam_OpenDevice(), "abrir dispositivo")
            self._set_trigger_mode_locked(False)
            _configure_sdk_grabbing(self._cam)
            self._check(self._cam.SciCam_StartGrabbing(), "iniciar aquisição")
        except OptCameraError:
            _logger.error(
                "Falha ao conectar câmera índice=%s.",
                self._selected_index,
            )
            self._safe_cleanup()
            raise
        self._connected = True
        # Após conectar, o preview ao vivo usa um timeout curto para não prender
        # a thread em um grab bloqueante no encerramento.
        self._apply_grab_timeout(_GRAB_TIMEOUT_LIVE_MS)
        _logger.info("Câmera conectada e aquisição iniciada.")

    def _apply_grab_timeout(self, timeout_ms: int) -> None:
        if self._cam is None:
            return
        with contextlib.suppress(Exception):
            self._cam.SciCam_SetGrabTimeout(timeout_ms)

    def disconnect(self) -> None:
        """Para a aquisição, fecha e destrói o handle do dispositivo."""
        with self._io_lock:
            if self._cam is None:
                self._connected = False
                return
            if not self._connected:
                return
            self._connected = False
            self._trigger_listen_active = False
            _logger.info("Desconectando câmera.")
            # Marca desconectado antes do nativo para o loop de grab não competir.
            with contextlib.suppress(OptCameraError, OSError):
                self._set_trigger_mode_locked(False)
            with contextlib.suppress(Exception):
                self._cam.SciCam_StopGrabbing()
            self._safe_cleanup()
            _logger.info("Câmera desconectada.")

    def _safe_cleanup(self) -> None:
        with contextlib.suppress(Exception):
            self._cam.SciCam_CloseDevice()
        with contextlib.suppress(Exception):
            self._cam.SciCam_DeleteDevice()

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def supports_trigger(self) -> bool:
        return True

    def set_trigger_mode(self, enabled: bool) -> None:
        """Ativa ou desativa ``TriggerMode`` (On/Off) na câmera."""
        with self._io_lock:
            if enabled:
                # Prepara SDK antes de ligar TriggerMode — evita frame residual do live.
                self._trigger_listen_active = True
                self._apply_grab_strategy(
                    _state.sdk.SciCamGrabStrategy.SciCam_GrabStrategy_Upcoming
                )
                self._apply_grab_timeout(_GRAB_TIMEOUT_SINGLE_MS)
                _clear_payload_buffer_logged(self._cam, context="trigger_on")
                self._set_trigger_mode_locked(True)
                drained = self._drain_pending_frames_locked()
                _logger.info(
                    "Escuta de trigger preparada (%d frame(s) residual descartado(s)).",
                    drained,
                )
            else:
                self._set_trigger_mode_locked(False)
                self._trigger_listen_active = False
                self._apply_grab_strategy(
                    _state.sdk.SciCamGrabStrategy.SciCam_GrabStrategy_Latest
                )
                self._apply_grab_timeout(_GRAB_TIMEOUT_LIVE_MS)
                _clear_payload_buffer_logged(self._cam, context="trigger_off")

    def _drain_pending_frames_locked(self) -> int:
        """Descarta frames já no buffer sem aguardar novo evento de trigger."""
        drained = 0
        self._apply_grab_timeout(_GRAB_TIMEOUT_DRAIN_MS)
        _clear_payload_buffer_logged(self._cam, context="drain")
        for _ in range(_DRAIN_MAX_ATTEMPTS):
            payload = ctypes.c_void_p()
            code = self._cam.SciCam_Grab(payload)
            if code == _state.sdk.SCI_CAMERA_OK:
                drained += 1
                try:
                    self._cam.SciCam_FreePayload(payload)
                except Exception as exc:
                    _logger.warning("Drenagem: falha ao liberar payload: %s", exc)
                continue
            if code in _TRIGGER_WAIT_CODES or code in _INCOMPLETE_GRAB_CODES:
                break
            break
        self._apply_grab_timeout(_GRAB_TIMEOUT_SINGLE_MS)
        return drained

    def _apply_grab_strategy(self, strategy: Any) -> None:
        _apply_sdk_setting(
            self._cam,
            "definir estratégia de grab",
            lambda: self._cam.SciCam_SetGrabStrategy(strategy),
        )

    def _set_trigger_mode_locked(self, enabled: bool) -> None:
        self._require_sdk()
        value = "On" if enabled else "Off"
        if not _try_set_enum_by_string(self._cam, "TriggerMode", value):
            raise OptCameraError(f"Falha ao definir TriggerMode={value}.")

    # -- Aquisição ------------------------------------------------------------

    def grab(self, *, single: bool = False) -> tuple[np.ndarray, dict[str, Any]]:
        """Captura um frame, devolvendo ``(ndarray, metadados)``.

        Os metadados incluem ``frame_id``, ``timestamp``, ``width``,
        ``height``, ``pixel_format`` e ``channels``.

        Com ``single=True`` (captura/trigger único) usa um timeout maior; o
        preview ao vivo (``single=False``) usa o timeout curto configurado na
        conexão.
        """
        self._require_sdk()
        with self._io_lock:
            if not self._connected:
                raise OptCameraError("Câmera não está conectada.")
            return self._grab_locked(single=single)

    def _grab_locked(
        self, *, single: bool = False
    ) -> tuple[np.ndarray, dict[str, Any]]:
        if single:
            self._apply_grab_timeout(_GRAB_TIMEOUT_SINGLE_MS)
        try:
            return self._grab_payload()
        finally:
            if single and not self._trigger_listen_active:
                self._apply_grab_timeout(_GRAB_TIMEOUT_LIVE_MS)

    def _grab_payload(self) -> tuple[np.ndarray, dict[str, Any]]:
        payload = ctypes.c_void_p()
        last_code = _state.sdk.SCI_CAMERA_OK
        for attempt in range(1, _GRAB_INCOMPLETE_RETRIES + 1):
            last_code = self._cam.SciCam_Grab(payload)
            if last_code == _state.sdk.SCI_CAMERA_OK:
                break
            if last_code in _INCOMPLETE_GRAB_CODES:
                with contextlib.suppress(Exception):
                    if payload.value:
                        self._cam.SciCam_FreePayload(payload)
                    payload = ctypes.c_void_p()
                _logger.debug(
                    "Grab incompleto (código %s), tentativa %s/%s.",
                    last_code,
                    attempt,
                    _GRAB_INCOMPLETE_RETRIES,
                )
                continue
            break
        if last_code in _INCOMPLETE_GRAB_CODES:
            raise IncompleteFrameError(
                f"Frame incompleto na rede GigE (código {last_code})."
            )
        if last_code in _TRIGGER_WAIT_CODES:
            raise TriggerWaitError(f"Aguardando trigger (código {last_code}).")
        self._check(last_code, "capturar frame")
        try:
            attribute = _state.sdk.SCI_CAM_PAYLOAD_ATTRIBUTE()
            self._check(
                _state.sdk.SciCam_Payload_GetAttribute(payload, attribute),
                "ler atributos do frame",
            )
            if not attribute.isComplete:
                raise IncompleteFrameError(
                    "Frame incompleto recebido da câmera (payload)."
                )
            mode_2d = _state.sdk.SciCamPayloadMode.SciCam_PayloadMode_2D
            if attribute.payloadMode != mode_2d:
                raise OptCameraError("Payload recebido não é uma imagem 2D.")

            frame, meta = self._convert_payload(payload, attribute)
        finally:
            self._cam.SciCam_FreePayload(payload)
        return frame, meta

    @staticmethod
    def _read_image_bytes(image_data: ctypes.c_void_p, size: int) -> np.ndarray:
        if not image_data.value:
            raise OptCameraError("Buffer de imagem vazio no payload.")
        buf = (ctypes.c_ubyte * size).from_address(image_data.value)
        return np.frombuffer(buf, dtype=np.uint8, count=size)

    def _try_native_frame(
        self,
        image_data: ctypes.c_void_p,
        pixel_type: int,
        width: int,
        height: int,
    ) -> tuple[np.ndarray, int] | None:
        """Cópia direta quando o pixel já está em Mono8/RGB8/BGR8 (sem ConvertImage)."""
        pixel_enum = _state.sdk.SciCamPixelType
        if pixel_type == int(pixel_enum.Mono8):
            flat = self._read_image_bytes(image_data, width * height)
            return flat.reshape(height, width).copy(), 1
        if pixel_type == int(pixel_enum.BGR8):
            flat = self._read_image_bytes(image_data, width * height * 3)
            frame = flat.reshape(height, width, 3).copy()
            return _bgr_to_rgb(frame), 3
        if pixel_type == int(pixel_enum.RGB8):
            flat = self._read_image_bytes(image_data, width * height * 3)
            return flat.reshape(height, width, 3).copy(), 3
        return None

    def _convert_payload(
        self, payload: Any, attribute: Any
    ) -> tuple[np.ndarray, dict[str, Any]]:
        image_data = ctypes.c_void_p()
        self._check(
            _state.sdk.SciCam_Payload_GetImage(payload, image_data),
            "ler dados de imagem",
        )

        pixel_type = attribute.imgAttr.pixelType
        width = int(attribute.imgAttr.width)
        height = int(attribute.imgAttr.height)

        native = self._try_native_frame(image_data, pixel_type, width, height)
        if native is not None:
            frame, channels = native
        else:
            is_mono = pixel_type in self._mono_pixel_types
            pixel_enum = _state.sdk.SciCamPixelType
            # O SDK OPT documenta inversão B/R ao converter para RGB8; BGR8 + swap
            # produz cores corretas para exibição em RGB (Qt).
            out_type = pixel_enum.Mono8 if is_mono else pixel_enum.BGR8
            channels = 1 if is_mono else 3

            dst_size = ctypes.c_int()
            self._check(
                _state.sdk.SciCam_Payload_ConvertImage(
                    attribute.imgAttr, image_data, out_type, None, dst_size, True
                ),
                "calcular tamanho da imagem",
            )
            dst_buffer = (ctypes.c_ubyte * dst_size.value)()
            self._check(
                _state.sdk.SciCam_Payload_ConvertImage(
                    attribute.imgAttr, image_data, out_type, dst_buffer, dst_size, True
                ),
                "converter formato de pixel",
            )
            flat = np.frombuffer(dst_buffer, dtype=np.uint8, count=dst_size.value)
            if channels == 1:
                frame = flat.reshape(height, width).copy()
            else:
                frame = _bgr_to_rgb(flat.reshape(height, width, channels).copy())

        meta = {
            "frame_id": int(attribute.frameID),
            "timestamp": int(attribute.timeStamp),
            "width": width,
            "height": height,
            "pixel_format": self._pixel_format_name(pixel_type),
            "channels": channels,
        }
        return frame, meta

    @staticmethod
    def _pixel_format_name(pixel_type: int) -> str:
        try:
            return _state.sdk.SciCamPixelType(pixel_type).name
        except ValueError:
            return f"0x{pixel_type:08X}"

    # -- Auxiliares -----------------------------------------------------------

    def _require_sdk(self) -> None:
        if _state.sdk is None or self._cam is None:
            raise OptCameraError(
                "SDK SciCam (OPT) indisponível: execute "
                "python scripts/sync_opt_runtime.py. "
                f"Detalhe: {_state.error}"
            )

    @staticmethod
    def _check(result: int, action: str) -> None:
        if result != _state.sdk.SCI_CAMERA_OK:
            hint = _SDK_ERROR_HINTS.get(result)
            if hint:
                _logger.error("Falha ao %s (código %s): %s", action, result, hint)
                raise OptCameraError(f"Falha ao {action} (código {result}): {hint}")
            _logger.error("Falha ao %s (código %s).", action, result)
            raise OptCameraError(f"Falha ao {action} (código {result}).")


OPTCam = OptCamera
