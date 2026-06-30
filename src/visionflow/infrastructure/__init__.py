"""Camada de infraestrutura do Vision Flow.

Implementa os contratos do domínio: persistência (SQLite), comunicação com a
câmera (adapter OPT), visão computacional/IA (OpenCV, YOLO) e caminhos/bootstrap
de recursos de runtime. Não importa PySide6.
"""
