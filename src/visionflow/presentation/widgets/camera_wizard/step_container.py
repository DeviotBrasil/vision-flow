"""Layout compartilhado das etapas do wizard de câmera."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget


def build_step_container(
    title: str,
    subtitle: str,
    *,
    full_width: bool = False,
) -> tuple[QWidget, QVBoxLayout, QLabel]:
    page = QWidget()
    if full_width:
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    inner = QFrame()
    inner.setObjectName("wizard_step")
    if full_width:
        inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    else:
        inner.setMaximumWidth(620)
    column = QVBoxLayout(inner)
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(20)

    heading = QLabel(title)
    heading.setObjectName("wizard_step_title")
    column.addWidget(heading)

    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("wizard_step_subtitle")
    subtitle_label.setWordWrap(True)
    column.addWidget(subtitle_label)

    if full_width:
        outer.addWidget(inner, 1)
    else:
        outer.addWidget(inner)
        outer.addStretch()
    return page, column, subtitle_label
