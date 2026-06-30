"""Modelo de seleção múltipla reutilizável para galerias/listas.

Centraliza o estado "conjunto selecionado + selecionar/desmarcar todas" usado
tanto pelo :class:`FilteredGalleryController` quanto pela tela de datasets,
evitando duplicar a lógica de alternância e do botão "Selecionar/Desmarcar
todas". Mantém-se na camada de apresentação e não conhece UI nem SQL.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass
class SelectionModel:
    """Conjunto de ids selecionados com suporte a 'selecionar todas'.

    ``select_all_active`` indica que a seleção representa "todos os itens do
    filtro atual" (útil quando há paginação e nem todos os ids estão na
    página corrente).
    """

    selected_ids: set[int] = field(default_factory=set)
    select_all_active: bool = False

    @property
    def count(self) -> int:
        return len(self.selected_ids)

    def as_list(self) -> list[int]:
        return list(self.selected_ids)

    def set_one(self, item_id: int, checked: bool) -> None:
        """Define a seleção de um item a partir de um checkbox."""
        self.select_all_active = False
        if checked:
            self.selected_ids.add(item_id)
        else:
            self.selected_ids.discard(item_id)

    def toggle_one(self, item_id: int) -> None:
        """Alterna a seleção de um item (clique no corpo do card)."""
        self.select_all_active = False
        if item_id in self.selected_ids:
            self.selected_ids.discard(item_id)
        else:
            self.selected_ids.add(item_id)

    def select_all(self, ids: Iterable[int]) -> None:
        self.selected_ids = set(ids)
        self.select_all_active = True

    def clear(self) -> None:
        self.selected_ids.clear()
        self.select_all_active = False

    def shows_deselect_all(self, total: int) -> bool:
        """``True`` quando o botão deve oferecer 'Desmarcar todas'."""
        if total <= 0:
            return False
        if self.select_all_active:
            return True
        return self.count >= total
