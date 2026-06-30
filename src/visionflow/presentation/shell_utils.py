"""Integração com o shell do Windows."""

from __future__ import annotations

import logging
import os
from pathlib import Path

_logger = logging.getLogger(__name__)


def open_folder_in_explorer(folder: Path) -> None:
    """Abre uma pasta no Windows Explorer."""
    path = Path(folder)
    try:
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)
    except OSError:
        _logger.exception("Falha ao abrir pasta no Explorer: %s", path)
