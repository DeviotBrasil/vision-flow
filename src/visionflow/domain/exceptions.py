"""Exceções de domínio compartilhadas entre camadas."""


class PersistenceError(RuntimeError):
    """Falha ao persistir ou consultar dados via contrato de repositório."""
