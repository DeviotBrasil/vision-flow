"""Constantes e helpers compartilhados pelas telas de listagem com filtro."""

from __future__ import annotations

import math

from visionflow.domain.gallery_defaults import GALLERY_PAGE_SIZE

GALLERY_PAGE_SIZES = (50, 100, 500, 1000)
DEFAULT_PAGE_SIZE = GALLERY_PAGE_SIZE
FILTER_PAD_H = 34
FOOTER_PAD_V = 13
FILTER_HEIGHT = 61
QUICK_DATE_FILTERS: tuple[tuple[str, str], ...] = (
    ("today", "Hoje"),
    ("month", "Mês"),
)


def format_count_label(count: int, *, singular: str, plural: str) -> str:
    """Formata contagem com singular/plural em português."""
    if count == 1:
        return f"1 {singular}"
    return f"{count} {plural}"


def total_pages(filtered_total: int, page_size: int) -> int:
    """Calcula o total de páginas para paginação."""
    if filtered_total == 0:
        return 0
    return math.ceil(filtered_total / page_size)
