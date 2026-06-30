"""Configuração de textos e rótulos das telas de galeria paginada."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class GalleryScreenConfig:
    """Textos de contagem, exportação e exclusão em lote."""

    item_singular: str
    item_plural: str
    zip_basename_prefix: str
    db_count_singular: str
    db_count_plural: str
    filtered_count_singular: str
    filtered_count_plural: str
    delete_failed_message: str

    def export_basename(self) -> str:
        return f"{self.zip_basename_prefix}_{uuid4().hex}"

    def delete_failed_feedback(self, failed_count: int) -> str:
        return self.delete_failed_message.format(count=failed_count)
