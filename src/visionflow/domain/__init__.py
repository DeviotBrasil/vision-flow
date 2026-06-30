"""Camada de domínio do Vision Flow.

Contém entidades, contratos (ports) e serviços/use cases com as regras de
negócio. Esta camada é pura: não importa PySide6, sqlite3, ctypes nem qualquer
outra camada (presentation/infrastructure). Depende apenas da biblioteca padrão
e de ``numpy`` (tipo fundamental dos frames).
"""
