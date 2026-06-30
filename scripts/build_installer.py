#!/usr/bin/env python3
"""Gera o instalador Windows do Vision Flow (PyInstaller + Inno Setup)."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from visionflow.branding import (  # noqa: E402
    APP_DISPLAY_NAME,
    APP_EXE_NAME,
    APP_PUBLISHER,
    APP_SETUP_PREFIX,
    APP_SLUG,
    ICON_APP_SVG,
    INNO_APP_ID,
)

SPEC_PATH = PROJECT_ROOT / "packaging" / "visionflow.spec"
ISS_PATH = PROJECT_ROOT / "packaging" / "installer.iss"
INNO_BRANDING_PATH = PROJECT_ROOT / "packaging" / "branding.iss"
ICON_PATH = PROJECT_ROOT / "packaging" / "visionflow.ico"
ENV_APP_SLUG = "VISIONFLOW_APP_SLUG"

APP_VERSION_FILE = PROJECT_ROOT / "packaging" / "app_version.txt"
VERSION_INFO_FILE = PROJECT_ROOT / "packaging" / "version_info.txt"
OPT_DLL = (
    PROJECT_ROOT
    / "src"
    / "visionflow"
    / "infrastructure"
    / "camera"
    / "opt"
    / "runtime"
    / "SciCamSDK.dll"
)
DIST_APP = PROJECT_ROOT / "dist" / APP_SLUG


def _read_version() -> str:
    text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    msg = "version não encontrada em pyproject.toml"
    raise RuntimeError(msg)


def _version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = version.split(".")
    nums: list[int] = []
    for part in parts[:4]:
        digits = "".join(ch for ch in part if ch.isdigit())
        nums.append(int(digits or "0"))
    while len(nums) < 4:
        nums.append(0)
    return nums[0], nums[1], nums[2], nums[3]


def write_app_version_files() -> str:
    """Grava versão para PyInstaller (metadata do exe e runtime da UI)."""
    version = _read_version()
    APP_VERSION_FILE.write_text(f"{version}\n", encoding="utf-8")
    filevers = _version_tuple(version)
    VERSION_INFO_FILE.write_text(
        "\n".join(
            [
                "# UTF-8",
                "# Gerado por scripts/build_installer.py — não editar.",
                "VSVersionInfo(",
                "  ffi=FixedFileInfo(",
                f"    filevers={filevers},",
                f"    prodvers={filevers},",
                "    mask=0x3f,",
                "    flags=0x0,",
                "    OS=0x40004,",
                "    fileType=0x1,",
                "    subtype=0x0,",
                "    date=(0, 0)",
                "  ),",
                "  kids=[",
                "    StringFileInfo([",
                "      StringTable(",
                "        '040904B0',",
                "        [",
                f"          StringStruct('CompanyName', '{APP_PUBLISHER}'),",
                f"          StringStruct('FileDescription', '{APP_DISPLAY_NAME}'),",
                f"          StringStruct('FileVersion', '{version}'),",
                f"          StringStruct('InternalName', '{APP_SLUG}'),",
                f"          StringStruct('OriginalFilename', '{APP_EXE_NAME}'),",
                f"          StringStruct('ProductName', '{APP_DISPLAY_NAME}'),",
                f"          StringStruct('ProductVersion', '{version}'),",
                "        ]",
                "      )",
                "    ]),",
                "    VarFileInfo([VarStruct('Translation', [1033, 1200])])",
                "  ]",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return version


def write_inno_branding() -> None:
    """Gera ``packaging/branding.iss`` a partir de ``visionflow.branding``."""
    braced_app_id = "{{" + INNO_APP_ID + "}}"
    content = (
        "; Gerado por scripts/build_installer.py — não editar.\n"
        f'#define MyAppName "{APP_DISPLAY_NAME}"\n'
        f'#define MyAppPublisher "{APP_PUBLISHER}"\n'
        f'#define MyAppExeName "{APP_EXE_NAME}"\n'
        f'#define MyAppDistDir "{APP_SLUG}"\n'
        f'#define MyAppSetupPrefix "{APP_SETUP_PREFIX}"\n'
        f'#define MyAppInnoAppId "{braced_app_id}"\n'
    )
    INNO_BRANDING_PATH.write_text(content, encoding="utf-8")


def ensure_opt_runtime() -> None:
    if OPT_DLL.is_file():
        return
    print(
        "SciCamSDK.dll ausente. Execute: git lfs install && git lfs pull",
        file=sys.stderr,
    )
    raise SystemExit(1)


def _icon_needs_regenerate() -> bool:
    if not ICON_PATH.is_file():
        return True
    if not ICON_APP_SVG.is_file():
        return False
    return ICON_APP_SVG.stat().st_mtime > ICON_PATH.stat().st_mtime


def ensure_app_icon() -> None:
    if not _icon_needs_regenerate():
        return
    if not ICON_APP_SVG.is_file():
        msg = f"Ícone SVG ausente: {ICON_APP_SVG}"
        raise RuntimeError(msg)

    app = QGuiApplication.instance() or QGuiApplication([])
    renderer = QSvgRenderer(str(ICON_APP_SVG))
    size = QSize(256, 256)
    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    ICON_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not pixmap.save(str(ICON_PATH), "ICO"):
        msg = f"Falha ao gravar ícone: {ICON_PATH}"
        raise RuntimeError(msg)
    del app


def _clean_build_artifacts() -> None:
    shutil.rmtree(PROJECT_ROOT / "build", ignore_errors=True)
    if DIST_APP.exists():
        shutil.rmtree(DIST_APP)
    ICON_PATH.unlink(missing_ok=True)


def run_pyinstaller() -> None:
    write_app_version_files()
    ensure_app_icon()
    env = os.environ.copy()
    env[ENV_APP_SLUG] = APP_SLUG
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC_PATH), "--noconfirm"],
        cwd=PROJECT_ROOT,
        check=True,
        env=env,
    )


def find_iscc() -> str:
    for name in ("ISCC", "ISCC.exe"):
        path = shutil.which(name)
        if path:
            return path
    default = Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")
    if default.is_file():
        return str(default)
    print(
        "Inno Setup não encontrado. Instale Inno Setup 6 e adicione ISCC ao PATH.\n"
        "https://jrsoftware.org/isinfo.php",
        file=sys.stderr,
    )
    raise SystemExit(1)


def run_inno() -> Path:
    version = _read_version()
    write_inno_branding()
    iscc = find_iscc()
    subprocess.run(
        [iscc, str(ISS_PATH), f"/DMyAppVersion={version}"],
        cwd=PROJECT_ROOT / "packaging",
        check=True,
    )
    setup = PROJECT_ROOT / "dist" / f"{APP_SETUP_PREFIX}-{version}.exe"
    if not setup.is_file():
        print(f"Instalador esperado não encontrado: {setup}", file=sys.stderr)
        raise SystemExit(1)
    return setup


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"Gera o instalador Windows do {APP_DISPLAY_NAME}.",
    )
    parser.add_argument(
        "--skip-installer",
        action="store_true",
        help=f"Executa só o PyInstaller (pasta dist/{APP_SLUG}/).",
    )
    parser.add_argument(
        "--skip-pyinstaller",
        action="store_true",
        help=f"Executa só o Inno Setup (exige dist/{APP_SLUG}/ existente).",
    )
    args = parser.parse_args()

    if args.skip_pyinstaller and args.skip_installer:
        print("Nada a fazer: informe ao menos uma etapa de build.", file=sys.stderr)
        return 1

    ensure_opt_runtime()

    if not args.skip_pyinstaller:
        _clean_build_artifacts()
        run_pyinstaller()
        print(f"Build PyInstaller: {DIST_APP}")

    if not args.skip_installer:
        exe_path = DIST_APP / APP_EXE_NAME
        if not exe_path.is_file():
            print(
                f"Pasta de build ausente ou incompleta: {exe_path}. "
                "Execute o PyInstaller primeiro.",
                file=sys.stderr,
            )
            return 1
        setup = run_inno()
        print(f"Instalador gerado: {setup}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
