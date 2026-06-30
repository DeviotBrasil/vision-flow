"""Caminhos de dados e binários nativos (camada de infraestrutura).

Centraliza diretórios gerados em runtime (banco SQLite, capturas) e a
localização dos binários nativos do fabricante (DLLs/SDK). Logs da aplicação
são persistidos na tabela ``app_logs`` do SQLite. Recursos de UI (ícones,
temas) ficam em :mod:`visionflow.presentation.paths`.
"""

import os
import sys
from pathlib import Path

from visionflow.branding import DB_FILENAME, ENV_DATA_DIR

PACKAGE_DIR = Path(__file__).resolve().parents[1]


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _app_install_root() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return PACKAGE_DIR.parents[1]


PROJECT_ROOT = _app_install_root()

# Runtime nativo OPT SciCam (Win64_x64), versionado junto ao adapter.
OPT_RUNTIME_DIR = Path(__file__).resolve().parent / "camera" / "opt" / "runtime"


def _resolve_data_dir() -> Path:
    override = os.environ.get(ENV_DATA_DIR, "").strip()
    if override:
        return Path(override)
    if _is_frozen():
        return _app_install_root() / "data"
    return PACKAGE_DIR.parents[1] / "data"


# Dados gerados em tempo de execução (banco SQLite e imagens capturadas).
DATA_DIR = _resolve_data_dir()
DB_PATH = DATA_DIR / DB_FILENAME
CAPTURES_DIR = DATA_DIR / "captures"
RECORDINGS_DIR = DATA_DIR / "recordings"
THUMBS_DIR = DATA_DIR / "thumbs"


def ensure_data_dirs() -> None:
    """Cria os diretórios de dados em tempo de execução, se ainda não existirem."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
