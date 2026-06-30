"""Indicador de etapas (wizard) com círculos numerados e conectores."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from visionflow.presentation.icon_sizes import (
    STEPPER_CHEVRON_ICON,
    STEPPER_DONE_ICON,
)
from visionflow.presentation.icon_utils import tinted_pixmap
from visionflow.presentation.style_utils import set_property

_CONNECTOR_COLOR = "#d2d2d7"


class Stepper(QFrame):
    """Barra de etapas com estados ativo/concluído/pendente.

    ``set_current(index)`` marca a etapa atual; etapas anteriores são exibidas
    como concluídas.
    """

    def __init__(self, steps: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("stepper")
        self._steps = steps
        self._current = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._circles: list[QLabel] = []
        self._labels: list[QLabel] = []

        for position, title in enumerate(steps):
            if position > 0:
                connector = QLabel()
                connector.setObjectName("stepper_connector")
                connector.setAlignment(Qt.AlignmentFlag.AlignCenter)
                connector.setPixmap(
                    tinted_pixmap(
                        "icon_chevron_right.svg", _CONNECTOR_COLOR, STEPPER_CHEVRON_ICON
                    )
                )
                layout.addWidget(connector)

            step = QFrame()
            step.setObjectName("stepper_step")
            step_layout = QHBoxLayout(step)
            step_layout.setContentsMargins(0, 0, 0, 0)
            step_layout.setSpacing(11)

            circle = QLabel(str(position + 1))
            circle.setObjectName("stepper_circle")
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setProperty("state", "pending")

            label = QLabel(title)
            label.setObjectName("stepper_label")
            label.setProperty("state", "pending")

            step_layout.addWidget(circle)
            step_layout.addWidget(label)
            layout.addWidget(step)

            self._circles.append(circle)
            self._labels.append(label)

        layout.addStretch()
        self.set_current(0)

    def set_current(self, index: int, *, mark_current_done: bool = False) -> None:
        """Define a etapa atual (0-based) e atualiza os estados visuais.

        Com ``mark_current_done=True``, a etapa atual também usa o ícone de
        sucesso (como as etapas anteriores concluídas).
        """
        self._current = index
        for position, (circle, label) in enumerate(
            zip(self._circles, self._labels, strict=True)
        ):
            if position < index or (mark_current_done and position == index):
                state = "done"
            elif position == index:
                state = "active"
            else:
                state = "pending"
            self._apply_circle(circle, position, state)
            set_property(circle, "state", state)
            set_property(label, "state", state)

    @staticmethod
    def _apply_circle(circle: QLabel, position: int, state: str) -> None:
        if state == "done":
            circle.setText("")
            circle.setPixmap(
                tinted_pixmap("icon_check.svg", "#FFFFFF", STEPPER_DONE_ICON)
            )
        else:
            circle.setPixmap(QPixmap())
            circle.setText(str(position + 1))
