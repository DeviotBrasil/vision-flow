"""Identidade do produto (nome exibido e identificadores Windows)."""

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent

APP_DISPLAY_NAME = "Vision Flow"
APP_SLUG = "VisionFlow"
APP_EXE_NAME = f"{APP_SLUG}.exe"
APP_SETUP_PREFIX = f"{APP_SLUG}-Setup"
APP_PUBLISHER = APP_DISPLAY_NAME
APP_SUBTITLE = (
    "Sistema de visão computacional para coleta de imagens e geração de datasets YOLO"
)

ENV_DATA_DIR = "VISIONFLOW_DATA_DIR"
ENV_LOG_LEVEL = "VISIONFLOW_LOG_LEVEL"

DB_FILENAME = "visionflow.db"

# Inno Setup — identificador do produto (não reutilizar AppId legado).
INNO_APP_ID = "8F2E4B1C-3D5A-4F9E-B267-1C0D8E9F2A4B"

# Wordmark (`logo.svg`, viewBox 720×180).
LOGO_ASPECT_WIDTH = 720
LOGO_ASPECT_HEIGHT = 180

QSETTINGS_ORG = APP_SLUG
QSETTINGS_APP = APP_SLUG
SETTINGS_ANNOTATION_LAST_CLASS = "annotation/last_class_id"
SETTINGS_YOLO_EXPORT_FORMAT = "datasets/yolo_export_format"

ICON_APP_SVG = (
    _PACKAGE_DIR / "presentation" / "resources" / "icons" / "icon_app.svg"
)
LOGO_SVG = _PACKAGE_DIR / "presentation" / "resources" / "images" / "logo.svg"


def logo_wordmark_width(height: int) -> int:
    """Largura do wordmark proporcional à altura (mantém aspect ratio do SVG)."""
    return round(height * LOGO_ASPECT_WIDTH / LOGO_ASPECT_HEIGHT)
