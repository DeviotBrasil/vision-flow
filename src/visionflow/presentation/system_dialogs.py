"""Helpers para diálogos do sistema integrados ao tema Vision Flow."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette, QShowEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QLayout,
    QMessageBox,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)

from visionflow.presentation.style_utils import repolish
from visionflow.presentation.themes.theme_manager import ThemeManager

_PALETTE_DARK = {
    "window": "#1D1D1F",
    "window_text": "#F5F5F7",
    "base": "#2C2C2E",
    "alternate_base": "#3A3A3C",
    "text": "#F5F5F7",
    "button": "#3A3A3C",
    "button_text": "#F5F5F7",
    "highlight": "#0A84FF",
    "highlighted_text": "#FFFFFF",
    "mid": "#48484A",
    "dark": "#1D1D1F",
    "light": "#636366",
}
_PALETTE_LIGHT = {
    "window": "#FFFFFF",
    "window_text": "#1D1D1F",
    "base": "#FFFFFF",
    "alternate_base": "#F5F5F7",
    "text": "#1D1D1F",
    "button": "#FFFFFF",
    "button_text": "#1D1D1F",
    "highlight": "#0066CC",
    "highlighted_text": "#FFFFFF",
    "mid": "#D2D2D7",
    "dark": "#AEAEB2",
    "light": "#F5F5F7",
}


def _theme_is_dark() -> bool:
    return ThemeManager.is_saved_dark()


def _build_palette(*, dark: bool) -> QPalette:
    """Paleta completa para listas/campos do QFileDialog (papel Base/Text)."""
    colors = _PALETTE_DARK if dark else _PALETTE_LIGHT
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: "window",
        QPalette.ColorRole.WindowText: "window_text",
        QPalette.ColorRole.Base: "base",
        QPalette.ColorRole.AlternateBase: "alternate_base",
        QPalette.ColorRole.Text: "text",
        QPalette.ColorRole.Button: "button",
        QPalette.ColorRole.ButtonText: "button_text",
        QPalette.ColorRole.Highlight: "highlight",
        QPalette.ColorRole.HighlightedText: "highlighted_text",
        QPalette.ColorRole.Mid: "mid",
        QPalette.ColorRole.Dark: "dark",
        QPalette.ColorRole.Light: "light",
    }
    for role, key in roles.items():
        palette.setColor(role, QColor(colors[key]))
    return palette


_CONFIRM_DIALOG_MIN_WIDTH = 560


def _widen_message_box(box: QMessageBox, min_width: int) -> None:
    """Força largura mínima; ``setMinimumWidth`` sozinho é ignorado pelo QMessageBox."""
    layout = box.layout()
    if not isinstance(layout, QGridLayout):
        box.setMinimumWidth(min_width)
        return
    layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
    layout.addItem(
        QSpacerItem(
            min_width,
            0,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding,
        ),
        layout.rowCount(),
        0,
        1,
        layout.columnCount(),
    )


_SKIP_THEME_WIDGET_IDS = frozenset(
    {"capture_detail_preview", "capture_edit_preview"}
)


def _apply_palette_tree(root: QWidget, palette: QPalette) -> None:
    """Propaga paleta aos filhos (viewports mantêm fundo Base escuro/claro)."""
    root.setPalette(palette)
    root.setAutoFillBackground(True)
    for widget in root.findChildren(QWidget):
        if widget.objectName() in _SKIP_THEME_WIDGET_IDS:
            continue
        widget.setPalette(palette)
        widget.setAutoFillBackground(True)
        repolish(widget)
    repolish(root)


def apply_dialog_theme(dialog: QWidget) -> None:
    """Aplica paleta e QSS do tema ativo a um diálogo modal."""
    palette = _build_palette(dark=_theme_is_dark())
    _apply_palette_tree(dialog, palette)


class _ThemedFileDialog(QFileDialog):
    """QFileDialog que aplica paleta do tema ao exibir (corrige listas brancas)."""

    def __init__(self, *args, dark: bool, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._dark = dark
        self._palette = _build_palette(dark=dark)

    def showEvent(self, event: QShowEvent) -> None:
        _apply_palette_tree(self, self._palette)
        super().showEvent(event)


class _ThemedMessageBox(QMessageBox):
    """QMessageBox com paleta do tema ativo (evita texto ilegível no modo escuro)."""

    def __init__(self, *args, dark: bool, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._palette = _build_palette(dark=dark)

    def showEvent(self, event: QShowEvent) -> None:
        _apply_palette_tree(self, self._palette)
        super().showEvent(event)


def open_video_file_path(parent: QWidget | None) -> str | None:
    """Abre o diálogo Abrir arquivo de vídeo com o tema ativo da aplicação.

    Returns:
        Caminho escolhido ou ``None`` se o usuário cancelar.
    """
    selected = _open_existing_file_paths(
        parent,
        title="Importar vídeo",
        start_dir=_default_videos_dir(),
        file_filter="Vídeos (*.mp4 *.avi *.mkv *.mov *.wmv);;Todos (*.*)",
        multiple=False,
    )
    return selected[0] if selected else None


def open_image_file_paths(parent: QWidget | None) -> list[str]:
    """Abre o diálogo para selecionar imagens a importar (multi-seleção)."""
    return _open_existing_file_paths(
        parent,
        title="Adicionar imagens",
        start_dir=_default_pictures_dir(),
        file_filter=(
            "Imagens (*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff);;Todos (*.*)"
        ),
        multiple=True,
    )


def open_recording_file_paths(parent: QWidget | None) -> list[str]:
    """Abre o diálogo para selecionar gravações MP4 a importar (multi-seleção)."""
    return _open_existing_file_paths(
        parent,
        title="Adicionar gravações",
        start_dir=_default_videos_dir(),
        file_filter="Vídeos (*.mp4);;Todos (*.*)",
        multiple=True,
    )


def _default_pictures_dir() -> str:
    for name in ("Pictures", "Imagens"):
        candidate = Path.home() / name
        if candidate.is_dir():
            return str(candidate)
    return str(Path.home())


def _default_videos_dir() -> str:
    for name in ("Videos", "Vídeos"):
        candidate = Path.home() / name
        if candidate.is_dir():
            return str(candidate)
    return str(Path.home())


def dialog_parent(parent: QWidget | None) -> QWidget | None:
    """Retorna a janela principal adequada como parent de diálogos modais."""
    if parent is None:
        return None
    window = parent.window()
    return window if window is not None else parent


def _open_existing_file_paths(
    parent: QWidget | None,
    *,
    title: str,
    start_dir: str,
    file_filter: str,
    multiple: bool,
) -> list[str]:
    dialog = _ThemedFileDialog(
        dialog_parent(parent),
        title,
        start_dir,
        file_filter,
        dark=_theme_is_dark(),
    )
    dialog.setObjectName("visionflow_file_dialog")
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
    dialog.setFileMode(
        QFileDialog.FileMode.ExistingFiles
        if multiple
        else QFileDialog.FileMode.ExistingFile
    )
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    _apply_palette_tree(dialog, dialog._palette)
    dialog.raise_()
    dialog.activateWindow()

    if dialog.exec() != QFileDialog.DialogCode.Accepted:
        return []
    return dialog.selectedFiles()


def save_file_path(
    parent: QWidget | None,
    title: str,
    suggested_name: str,
    file_filter: str,
    *,
    start_dir: str | Path | None = None,
) -> str | None:
    """Abre o diálogo Salvar arquivo com o tema ativo da aplicação.

    Returns:
        Caminho escolhido ou ``None`` se o usuário cancelar.
    """
    start = Path(start_dir) if start_dir is not None else Path(suggested_name).parent
    dialog = _ThemedFileDialog(
        parent, title, str(start), file_filter, dark=_theme_is_dark()
    )
    dialog.setObjectName("visionflow_file_dialog")
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.selectFile(suggested_name)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    _apply_palette_tree(dialog, dialog._palette)

    if dialog.exec() != QFileDialog.DialogCode.Accepted:
        return None
    selected = dialog.selectedFiles()
    return selected[0] if selected else None


def show_info_message(
    parent: QWidget | None,
    title: str,
    text: str,
    *,
    informative_text: str = "",
) -> None:
    """Exibe um diálogo informativo com o tema ativo da aplicação."""
    box = _ThemedMessageBox(parent, dark=_theme_is_dark())
    box.setObjectName("visionflow_message_box")
    box.setWindowTitle(title)
    box.setText(text)
    if informative_text:
        box.setInformativeText(informative_text)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setDefaultButton(QMessageBox.StandardButton.Ok)
    ok_btn = box.button(QMessageBox.StandardButton.Ok)
    if ok_btn is not None:
        ok_btn.setText("OK")
    _apply_palette_tree(box, box._palette)
    _widen_message_box(box, _CONFIRM_DIALOG_MIN_WIDTH)
    box.exec()


def _confirm_yes_no(
    parent: QWidget | None,
    *,
    title: str,
    text: str,
    informative: str | None = None,
) -> bool:
    """Diálogo Sim/Não temático; botão padrão é Não."""
    box = _ThemedMessageBox(parent, dark=_theme_is_dark())
    box.setObjectName("visionflow_message_box")
    box.setWindowTitle(title)
    box.setText(text)
    if informative:
        box.setInformativeText(informative)
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    box.setDefaultButton(QMessageBox.StandardButton.No)
    _apply_palette_tree(box, box._palette)

    yes_btn = box.button(QMessageBox.StandardButton.Yes)
    if yes_btn is not None:
        yes_btn.setText("Sim")
    no_btn = box.button(QMessageBox.StandardButton.No)
    if no_btn is not None:
        no_btn.setText("Não")

    _widen_message_box(box, _CONFIRM_DIALOG_MIN_WIDTH)
    return box.exec() == QMessageBox.StandardButton.Yes


def confirm_action(
    parent: QWidget | None,
    *,
    title: str,
    text: str,
    informative: str | None = None,
) -> bool:
    """Diálogo Sim/Não temático genérico para confirmar uma ação."""
    return _confirm_yes_no(parent, title=title, text=text, informative=informative)


def confirm_disconnect_camera(parent: QWidget | None) -> bool:
    """Pergunta se o operador deseja desconectar a câmera ao sair da Principal.

    Returns:
        ``True`` se o usuário confirmar a desconexão; ``False`` para cancelar.
    """
    return _confirm_yes_no(
        parent,
        title="Atenção",
        text="A câmera está conectada.",
        informative="Deseja desconectar para sair da tela Principal?",
    )


def confirm_replace_capture(parent: QWidget | None) -> bool:
    """Confirma substituição irreversível da imagem da captura atual."""
    return _confirm_yes_no(
        parent,
        title="Atualizar captura",
        text="Substituir a imagem original?",
        informative=(
            "A captura atual será sobrescrita com a versão editada. "
            "Esta ação não pode ser desfeita."
        ),
    )


def confirm_bulk_delete(
    parent: QWidget | None,
    *,
    count: int,
    item_singular: str,
    item_plural: str,
) -> bool:
    """Confirma exclusão em lote de itens da galeria."""
    label = item_singular if count == 1 else f"{count} {item_plural}"
    return _confirm_yes_no(
        parent,
        title="Excluir",
        text=f"Excluir {label}?",
        informative="Esta ação não pode ser desfeita.",
    )


def confirm_clear_all_logs(parent: QWidget | None, *, count: int) -> bool:
    """Confirma exclusão irreversível de todos os registros de log."""
    label = f"{count:,}".replace(",", ".")
    return _confirm_yes_no(
        parent,
        title="Limpar logs",
        text=f"Excluir todos os {label} registros de log?",
        informative="Esta ação não pode ser desfeita.",
    )
