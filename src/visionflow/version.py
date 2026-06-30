"""Versão da aplicação (fonte: metadata do pacote ou arquivo empacotado no build)."""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_PACKAGE = "visionflow"
_VERSION_FILENAMES = ("app_version.txt", "VERSION")
_DEV_FALLBACK = "0.0.0.dev"


def _read_version_file(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def _bundled_version() -> str | None:
    pkg_dir = Path(__file__).resolve().parent
    for name in _VERSION_FILENAMES:
        value = _read_version_file(pkg_dir / name)
        if value is not None:
            return value
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        for name in _VERSION_FILENAMES:
            value = _read_version_file(Path(meipass) / "visionflow" / name)
            if value is not None:
                return value
    return None


def app_version() -> str:
    """Retorna a versão instalada ou fallback para execução fora do pacote."""
    try:
        return version(_PACKAGE)
    except PackageNotFoundError:
        pass
    bundled = _bundled_version()
    if bundled is not None:
        return bundled
    return _DEV_FALLBACK


__version__ = app_version()
