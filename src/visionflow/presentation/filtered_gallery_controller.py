"""Controlador de paginação + seleção para galerias filtradas por data.

Encapsula o estado compartilhado (página, tamanho de página, total filtrado e
conjunto selecionado) e as transições de navegação/seleção usados tanto pelas
telas (:class:`FilteredGalleryScreen`) quanto pelo diálogo de seleção de
capturas. Mantém-se na camada de apresentação: opera sobre a grade e a barra de
paginação por meio de callbacks, sem conhecer regra de negócio nem SQL.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from visionflow.domain.entities.filtered_page import FilteredPage
from visionflow.presentation.list_screen_common import (
    DEFAULT_PAGE_SIZE,
    total_pages,
)
from visionflow.presentation.selection_model import SelectionModel
from visionflow.presentation.widgets.pagination_bar import PaginationBar
from visionflow.presentation.widgets.responsive_gallery_grid import (
    ResponsiveGalleryGrid,
)

DatesFn = Callable[[], tuple[date, date]]
LoadPageFn = Callable[[date, date, int, int], FilteredPage[Any]]
ListIdsFn = Callable[[date, date], list[int]]
PopulateFn = Callable[[list[Any]], None]


@dataclass(frozen=True)
class FilteredGalleryBindings:
    """Callbacks que ligam o controller à fonte de dados e à UI hospedeira.

    Attributes:
        dates: Intervalo De/Até atualmente selecionado.
        load_page: Carrega uma página filtrada (datas, página, tamanho).
        list_ids: Lista todos os ids do intervalo (para 'selecionar todas').
        populate: Renderiza as entradas na grade.
        on_changed: Hook após cada recarga/seleção (atualiza rótulos e botões).
    """

    dates: DatesFn
    load_page: LoadPageFn
    list_ids: ListIdsFn
    populate: PopulateFn
    on_changed: Callable[[], None]


class FilteredGalleryController:
    """Gerencia paginação e seleção de uma galeria filtrada por período."""

    def __init__(
        self,
        gallery: ResponsiveGalleryGrid,
        bindings: FilteredGalleryBindings,
    ) -> None:
        self._gallery = gallery
        self._dates = bindings.dates
        self._load_page = bindings.load_page
        self._list_ids = bindings.list_ids
        self._populate = bindings.populate
        self._on_changed = bindings.on_changed
        self._pagination: PaginationBar | None = None
        self.page = 1
        self.page_size = DEFAULT_PAGE_SIZE
        self.filtered_total = 0
        self._selection = SelectionModel()

    def bind_pagination(self, pagination: PaginationBar) -> None:
        """Associa a barra de paginação cujo estado o controller atualiza."""
        self._pagination = pagination

    # ----- estado de seleção (somente leitura) -----------------------------

    @property
    def selected_ids(self) -> set[int]:
        return self._selection.selected_ids

    @property
    def selected_count(self) -> int:
        return self._selection.count

    def selected_list(self) -> list[int]:
        return self._selection.as_list()

    def has_results(self) -> bool:
        return self.filtered_total > 0

    def shows_deselect_all(self) -> bool:
        """``True`` quando o botão deve oferecer 'Desmarcar todas'."""
        return self._selection.shows_deselect_all(self.filtered_total)

    # ----- carga / paginação ----------------------------------------------

    def reload(self, *, reset_page: bool) -> None:
        if reset_page:
            self.page = 1
        start_date, end_date = self._dates()
        result = self._load_page(start_date, end_date, self.page, self.page_size)
        self.filtered_total = result.total
        pages = total_pages(self.filtered_total, self.page_size)
        if 0 < pages < self.page:
            self.page = pages
            result = self._load_page(start_date, end_date, self.page, self.page_size)
        self._populate(result.entries)
        self._gallery.apply_selection(self.selected_ids)
        if self._pagination is not None:
            self._pagination.update_state(
                page=self.page,
                page_size=self.page_size,
                filtered_total=self.filtered_total,
            )
        self._on_changed()

    def on_prev_page(self) -> None:
        if self.page > 1:
            self.page -= 1
            self.reload(reset_page=False)

    def on_next_page(self) -> None:
        if self.page < total_pages(self.filtered_total, self.page_size):
            self.page += 1
            self.reload(reset_page=False)

    def on_page_selected(self, page: int) -> None:
        if page != self.page:
            self.page = page
            self.reload(reset_page=False)

    def on_page_size_changed(self, size: int) -> None:
        if self.page_size == size:
            return
        self.clear_selection(refresh=False)
        self.page_size = size
        self.reload(reset_page=True)

    # ----- seleção ---------------------------------------------------------

    def on_card_toggled(self, item_id: int, checked: bool) -> None:
        self._selection.set_one(item_id, checked)
        self._on_changed()

    def toggle_one(self, item_id: int) -> None:
        """Alterna a seleção de um item (clique no corpo do card)."""
        self._selection.toggle_one(item_id)
        self._gallery.apply_selection(self.selected_ids)
        self._on_changed()

    def select_all_or_clear(self) -> None:
        if self.filtered_total <= 0:
            return
        if self.shows_deselect_all():
            self.clear_selection()
            return
        start_date, end_date = self._dates()
        self._selection.select_all(self._list_ids(start_date, end_date))
        self._gallery.apply_selection(self.selected_ids)
        self._on_changed()

    def clear_selection(self, *, refresh: bool = True) -> None:
        self._selection.clear()
        if refresh:
            self._gallery.apply_selection(self.selected_ids)
        self._on_changed()
