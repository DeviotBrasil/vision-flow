# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Vision Flow (modo pasta / onedir)."""

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None

project_root = Path(SPECPATH).parent
APP_SLUG = os.environ.get("VISIONFLOW_APP_SLUG", "VisionFlow")

src_pkg = project_root / "src" / "visionflow"
icon_path = project_root / "packaging" / "visionflow.ico"
app_version_file = project_root / "packaging" / "app_version.txt"
version_info_file = project_root / "packaging" / "version_info.txt"

pyside_datas, pyside_binaries, pyside_hiddenimports = collect_all("PySide6")
cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all("cv2")

runtime_src = src_pkg / "infrastructure" / "camera" / "opt" / "runtime"

if app_version_file.is_file():
    datas_version = [(str(app_version_file), "visionflow")]
else:
    datas_version = []

datas = [
    *datas_version,
    (str(src_pkg / "presentation" / "themes"), "visionflow/presentation/themes"),
    (
        str(src_pkg / "presentation" / "resources" / "icons"),
        "visionflow/presentation/resources/icons",
    ),
    (
        str(src_pkg / "presentation" / "resources" / "images"),
        "visionflow/presentation/resources/images",
    ),
    (
        str(runtime_src),
        "visionflow/infrastructure/camera/opt/runtime",
    ),
]

datas += pyside_datas + cv2_datas

binaries = pyside_binaries + cv2_binaries
hiddenimports = pyside_hiddenimports + cv2_hiddenimports

a = Analysis(
    [str(src_pkg / "__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_SLUG,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path.is_file() else None,
    version=str(version_info_file) if version_info_file.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_SLUG,
)
