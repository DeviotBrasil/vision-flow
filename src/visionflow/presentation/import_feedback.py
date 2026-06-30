"""Mensagens de feedback para importação em lote."""

from __future__ import annotations


def format_import_feedback(
    *,
    added: int,
    failed_count: int,
    skipped_count: int,
    total: int,
    item_label: str,
) -> str:
    """Monta texto de banner após importação."""
    if added == 0 and failed_count == 0 and skipped_count > 0:
        return (
            f"Nenhum arquivo novo; {skipped_count} "
            f"{item_label} já existente(s) no repositório."
        )
    if added == 0:
        return f"Nenhum arquivo pôde ser importado ({total} selecionado(s))."

    if failed_count > 0 and added > 0:
        return (
            f"{added} de {total} {item_label} importado(s); {failed_count} ignorado(s)."
        )

    parts = [f"{added} {item_label} importada(s)"]
    if skipped_count > 0:
        parts.append(f"{skipped_count} já existente(s)")
    if failed_count > 0:
        parts.append(f"{failed_count} ignorado(s)")
    if len(parts) == 1:
        return parts[0]
    return "; ".join(parts) + "."
