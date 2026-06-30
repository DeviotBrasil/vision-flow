"""Caminhos de recursos da interface (camada de apresentação).

Centraliza a localização de ícones, imagens e temas. Caminhos de dados de
runtime e binários nativos ficam em :mod:`visionflow.infrastructure.paths`.
"""

from pathlib import Path

PRESENTATION_DIR = Path(__file__).resolve().parent

RESOURCES_DIR = PRESENTATION_DIR / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"
IMAGES_DIR = RESOURCES_DIR / "images"
THEMES_DIR = PRESENTATION_DIR / "themes"
