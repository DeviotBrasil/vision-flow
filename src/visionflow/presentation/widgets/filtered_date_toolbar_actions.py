"""Callbacks da barra de filtro por data."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class FilteredDateToolbarActions:
    """Ações opcionais e obrigatórias da toolbar de galeria."""

    on_dates_changed: Callable[[], None]
    on_quick_filter: Callable[[str], None]
    on_download_zip: Callable[[], None]
    on_bulk_delete: Callable[[], None] | None = None
    on_select_all: Callable[[], None] | None = None
    on_add: Callable[[], None] | None = None
