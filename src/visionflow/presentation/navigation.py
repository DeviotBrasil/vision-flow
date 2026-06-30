"""Configuração central de navegação (fonte de verdade única).

Define as seções, itens e estado (habilitado/badge) do menu lateral. Tanto
a ``Sidebar`` quanto o ``DefaultLayout`` consomem estas estruturas, evitando
duplicação de conhecimento sobre quais páginas existem e estão navegáveis.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class NavItemSpec:
    """Descreve um item do menu lateral.

    Attributes:
        page_id: Identificador único usado na navegação e no registro de telas.
        label: Texto exibido no item.
        icon: Nome do arquivo de ícone em ``presentation/resources/icons``.
        enabled: Se ``False``, o item aparece desabilitado e não navega.
        badge: Texto opcional de selo (ex.: ``"EM BREVE"``).
    """

    page_id: str
    label: str
    icon: str
    enabled: bool = True
    badge: str = ""


@dataclass(frozen=True)
class NavSection:
    """Agrupa itens sob um cabeçalho no menu lateral.

    Attributes:
        title: Cabeçalho da seção (exibido em maiúsculas).
        items: Itens pertencentes à seção, na ordem de exibição.
        section_key: Sufixo do ``objectName`` para estilos QSS (opcional).
    """

    title: str
    items: tuple[NavItemSpec, ...]
    section_key: str = ""


NAV_SECTIONS: tuple[NavSection, ...] = (
    NavSection(
        title="",
        items=(
            NavItemSpec("principal", "Principal", "icon_nav_home.svg"),
            NavItemSpec("captures", "Capturas", "icon_image.svg"),
            NavItemSpec("recordings", "Gravações", "icon_nav_youtube.svg"),
            NavItemSpec("datasets", "Datasets", "icon_nav_dataset.svg"),
            NavItemSpec("camera", "Câmera", "icon_nav_camera.svg"),
            NavItemSpec("logs", "Logs", "icon_info.svg"),
        ),
    ),
)

NAV_FOOTER: tuple[NavItemSpec, ...] = ()


def all_items() -> tuple[NavItemSpec, ...]:
    """Retorna todos os itens (seções + rodapé) na ordem de exibição."""
    section_items = tuple(item for section in NAV_SECTIONS for item in section.items)
    return section_items + NAV_FOOTER


def navigable_page_ids() -> frozenset[str]:
    """Conjunto de ``page_id`` cujos itens estão habilitados para navegação."""
    return frozenset(item.page_id for item in all_items() if item.enabled)
