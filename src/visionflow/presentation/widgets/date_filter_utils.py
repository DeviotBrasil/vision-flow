"""Utilitários de filtro rápido por data (telas Capturas e Logs)."""

from __future__ import annotations

from datetime import date, timedelta


def quick_filter_range(
    preset: str,
    *,
    reference: date | None = None,
) -> tuple[date, date]:
    today = reference or date.today()
    if preset == "today":
        return today, today
    if preset == "yesterday":
        day = today - timedelta(days=1)
        return day, day
    if preset == "month":
        return today.replace(day=1), today
    return today, today


def quick_filter_day(preset: str, *, reference: date | None = None) -> date:
    start, _end = quick_filter_range(preset, reference=reference)
    return start
