"""Comportamento compartilhado de seleção nos cards da galeria."""

from __future__ import annotations

from visionflow.presentation.style_utils import set_property
from visionflow.presentation.widgets.gallery_card_checkbox import (
    CHECKBOX_MARGIN,
    CHECKBOX_SIZE,
    GalleryCardCheckbox,
)


class GallerySelectableCardMixin:
    """Mixin com checkbox e estado visual de seleção."""

    _item_id: int
    _checkbox: GalleryCardCheckbox

    def _init_gallery_selection_ui(
        self,
        *,
        item_id: int,
        card_width: int,
    ) -> GalleryCardCheckbox:
        self._item_id = item_id
        checkbox = GalleryCardCheckbox(self)
        checkbox.move(
            card_width - CHECKBOX_SIZE - CHECKBOX_MARGIN,
            CHECKBOX_MARGIN,
        )
        checkbox.toggled.connect(self._on_selection_checkbox_toggled)
        self._checkbox = checkbox
        return checkbox

    def _apply_selected_state(self, selected: bool) -> None:
        self._checkbox.set_checked(selected)
        set_property(self, "selected", "true" if selected else "false")

    def set_selected(self, selected: bool) -> None:
        self._apply_selected_state(selected)

    def _on_selection_checkbox_toggled(self, checked: bool) -> None:
        self._apply_selected_state(checked)
        self._emit_selection_toggled(checked)

    def _emit_selection_toggled(self, checked: bool) -> None:
        raise NotImplementedError

    def _raise_selection_checkbox(self) -> None:
        self._checkbox.raise_()
