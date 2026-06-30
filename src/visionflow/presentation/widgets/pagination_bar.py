"""Barra de paginação com tamanho de página e navegação."""

from __future__ import annotations

import math
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton

from visionflow.presentation.widgets.app_buttons import (
    SHAPE_PILL,
    VARIANT_NEUTRAL_OUTLINE,
    create_button,
)

_FOOTER_PAD_H = 34
_FOOTER_PAD_V = 13
_FOOTER_HEIGHT = 61
_MAX_PAGE_BUTTONS = 3


class PaginationBar(QFrame):
    """Rodapé com itens por página, anterior/próxima e faixa exibida."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        page_sizes: tuple[int, ...],
        default_page_size: int,
        on_page_size_changed: Callable[[int], None],
        on_prev: Callable[[], None],
        on_next: Callable[[], None],
        on_page_selected: Callable[[int], None],
        object_name: str = "captures_footer",
        range_label_object_name: str = "captures_range_label",
        footer_caption_object_name: str = "captures_footer_caption",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setFixedHeight(_FOOTER_HEIGHT)
        self._page_selected_callback = on_page_selected
        self._page_buttons: list[QPushButton] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            _FOOTER_PAD_H, _FOOTER_PAD_V, _FOOTER_PAD_H, _FOOTER_PAD_V
        )
        layout.setSpacing(0)

        left = QHBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.addLayout(
            self._build_page_size_row(
                page_sizes,
                default_page_size,
                on_page_size_changed,
                footer_caption_object_name,
            )
        )
        layout.addLayout(left)
        layout.addStretch(1)

        center = QHBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(8)
        center.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.prev_button = create_button(
            "Anterior",
            variant=VARIANT_NEUTRAL_OUTLINE,
            shape=SHAPE_PILL,
        )
        self.prev_button.clicked.connect(on_prev)
        center.addWidget(self.prev_button)

        self.page_numbers_host = QHBoxLayout()
        self.page_numbers_host.setContentsMargins(0, 0, 0, 0)
        self.page_numbers_host.setSpacing(4)
        center.addLayout(self.page_numbers_host)

        self.next_button = create_button(
            "Próxima",
            variant=VARIANT_NEUTRAL_OUTLINE,
            shape=SHAPE_PILL,
            icon_name="icon_chevron_right.svg",
        )
        self.next_button.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.next_button.clicked.connect(on_next)
        center.addWidget(self.next_button)
        layout.addLayout(center)
        layout.addStretch(1)

        self.range_label = QLabel()
        self.range_label.setObjectName(range_label_object_name)
        self.range_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self.range_label)

    def _build_page_size_row(
        self,
        page_sizes: tuple[int, ...],
        default_page_size: int,
        on_page_size_changed: Callable[[int], None],
        footer_caption_object_name: str = "captures_footer_caption",
    ) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(9)
        caption = QLabel("Itens por página")
        caption.setObjectName(footer_caption_object_name)
        row.addWidget(caption)

        group = QButtonGroup(self)
        group.setExclusive(True)
        self._page_size_buttons: dict[int, QPushButton] = {}
        for size in page_sizes:
            button = create_button(
                str(size),
                variant=VARIANT_NEUTRAL_OUTLINE,
                shape=SHAPE_PILL,
                checkable=True,
            )
            if size == default_page_size:
                button.setChecked(True)
            button.clicked.connect(
                lambda _checked, s=size: self._on_page_size_button(
                    s, on_page_size_changed
                )
            )
            group.addButton(button)
            self._page_size_buttons[size] = button
            row.addWidget(button)
        return row

    @staticmethod
    def _on_page_size_button(size: int, callback: Callable[[int], None]) -> None:
        callback(size)

    def update_state(
        self,
        *,
        page: int,
        page_size: int,
        filtered_total: int,
    ) -> None:
        total_pages = (
            0 if filtered_total == 0 else math.ceil(filtered_total / page_size)
        )
        while self.page_numbers_host.count():
            item = self.page_numbers_host.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._page_buttons.clear()

        if total_pages > 0:
            start_page, end_page = self._visible_page_range(page, total_pages)
            for page_num in range(start_page, end_page + 1):
                button = create_button(
                    str(page_num),
                    variant=VARIANT_NEUTRAL_OUTLINE,
                    shape=SHAPE_PILL,
                    checkable=True,
                )
                button.setChecked(page_num == page)
                button.clicked.connect(
                    lambda _checked, p=page_num: self._on_page_selected(p)
                )
                self._page_buttons.append(button)
                self.page_numbers_host.addWidget(button)

        if filtered_total == 0:
            self.range_label.setText("0 de 0")
        else:
            start_item = (page - 1) * page_size + 1
            end_item = min(page * page_size, filtered_total)
            self.range_label.setText(f"{start_item}-{end_item} de {filtered_total}")

        self.prev_button.setEnabled(page > 1 and filtered_total > 0)
        self.next_button.setEnabled(page < total_pages and filtered_total > 0)

    @staticmethod
    def _visible_page_range(page: int, total_pages: int) -> tuple[int, int]:
        if total_pages <= _MAX_PAGE_BUTTONS:
            return 1, total_pages
        if page <= 2:
            return 1, _MAX_PAGE_BUTTONS
        if page >= total_pages - 1:
            return total_pages - _MAX_PAGE_BUTTONS + 1, total_pages
        return page - 1, page + 1

    def _on_page_selected(self, page: int) -> None:
        self._page_selected_callback(page)
