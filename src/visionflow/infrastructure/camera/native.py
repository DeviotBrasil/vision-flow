"""Bootstrap de bibliotecas nativas do fabricante (SDK OPT/SciCam).

Resolve onde está ``SciCamSDK.dll`` (``infrastructure/camera/opt/runtime`` no
projeto ou, em desenvolvimento, runtime OPT instalado), registra diretórios no
processo e prepara ``PATH`` / ``GENICAM_GENTL64_PATH`` antes de qualquer
carregamento via ``ctypes``.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from visionflow.infrastructure.paths import OPT_RUNTIME_DIR

_logger = logging.getLogger(__name__)

SDK_DLL_NAME = "SciCamSDK.dll"
SYNC_COMMAND = "python scripts/sync_opt_runtime.py"

# Runtime padrão do OPT Machine Vision (fallback quando o runtime embutido está vazio).
_OPT_RUNTIME_DIRS = (
    Path(r"C:\Program Files (x86)\OPTMV\Development\Windows\Runtime\Win64_x64"),
    Path(r"C:\Program Files (x86)\OPTMV\Development\Windows\Runtime\Win32_x86"),
)


class _NativeState:
    lib_dir: Path | None = None
    prepared: bool = False


_state = _NativeState()


def _is_64bit() -> bool:
    return sys.maxsize > 2**32


def _opt_runtime_candidates() -> tuple[Path, ...]:
    if _is_64bit():
        return _OPT_RUNTIME_DIRS
    return (_OPT_RUNTIME_DIRS[1], _OPT_RUNTIME_DIRS[0])


def _gentl_path_candidates() -> list[Path]:
    raw = os.environ.get("GENICAM_GENTL64_PATH", "").strip()
    if not raw:
        return []
    return [Path(part.strip()) for part in raw.split(os.pathsep) if part.strip()]


def bundled_lib_dir() -> Path | None:
    """Retorna o runtime embutido se ``SciCamSDK.dll`` estiver presente."""
    resolved = OPT_RUNTIME_DIR.resolve()
    if (resolved / SDK_DLL_NAME).is_file():
        return resolved
    return None


def is_bundled_sdk_available() -> bool:
    """Indica se ``SciCamSDK.dll`` está versionado no projeto."""
    return bundled_lib_dir() is not None


def _lib_search_roots(lib_dir: Path) -> list[Path]:
    """Raiz do runtime e subpastas (ex.: ``AHD/``, ``SciBridgeModule/``)."""
    roots: list[Path] = [lib_dir.resolve()]
    for child in sorted(lib_dir.iterdir()):
        if child.is_dir():
            roots.append(child.resolve())
    return roots


def _prepend_env_path(key: str, entries: list[str]) -> None:
    current = [
        part.strip()
        for part in os.environ.get(key, "").split(os.pathsep)
        if part.strip()
    ]
    for entry in reversed(entries):
        if entry not in current:
            current.insert(0, entry)
    os.environ[key] = os.pathsep.join(current)


def resolve_opt_lib_dir() -> Path | None:
    """Retorna o diretório que contém ``SciCamSDK.dll``, ou ``None`` se ausente."""
    if _state.lib_dir is not None:
        return _state.lib_dir

    bundled = bundled_lib_dir()
    if bundled is not None:
        _state.lib_dir = bundled
        _logger.debug("SciCamSDK.dll encontrado no runtime embutido.")
        return _state.lib_dir

    seen: set[Path] = set()
    candidates: list[Path] = []
    candidates.extend(_gentl_path_candidates())
    candidates.extend(_opt_runtime_candidates())

    for directory in candidates:
        resolved = directory.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / SDK_DLL_NAME).is_file():
            _state.lib_dir = resolved
            _logger.info(
                "SciCamSDK.dll encontrado no runtime OPT instalado: %s", resolved
            )
            return _state.lib_dir

    return None


def ensure_native_lib_path() -> None:
    """Prepara o ambiente para carregar as DLLs do SDK OPT/SciCam.

    Seguro para chamar múltiplas vezes e em ambientes sem o SDK instalado.
    """
    if _state.prepared:
        return

    lib_dir = resolve_opt_lib_dir()
    if lib_dir is None:
        _logger.warning(
            "SciCamSDK.dll não encontrado em %s. Execute: %s",
            OPT_RUNTIME_DIR,
            SYNC_COMMAND,
        )
        return

    _state.prepared = True
    roots = _lib_search_roots(lib_dir)
    for root in roots:
        os.add_dll_directory(str(root))

    _prepend_env_path("GENICAM_GENTL64_PATH", [str(lib_dir)])
    _prepend_env_path("PATH", [str(root) for root in roots])

    if is_bundled_sdk_available():
        _logger.debug(
            "Ambiente nativo preparado com SDK embutido (dir=%s, roots=%s).",
            lib_dir,
            len(roots),
        )
    else:
        _logger.debug(
            "Ambiente nativo preparado com runtime OPT instalado (dir=%s).",
            lib_dir,
        )
