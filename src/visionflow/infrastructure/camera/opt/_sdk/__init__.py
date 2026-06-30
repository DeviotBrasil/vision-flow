"""Binding ctypes vendorizado do SDK SciCam (OPT Machine Vision).

Código de terceiros adaptado do SDK SciCam (OPT Machine Vision).
As únicas mudanças em relação ao original são:

* o carregamento da biblioteca nativa aponta para ``opt/runtime`` e é **lazy**
  (proxy ``SciCamCtrlDll`` em ``SciCamPayload_header``; bootstrap em
  ``native.ensure_native_lib_path``);
* os imports entre módulos passaram a ser relativos ao pacote.

Por ser código vendorizado de terceiros, este subpacote é excluído do
``ruff`` (ver ``pyproject.toml``). O adapter ``OPTCam`` é quem oferece uma
API limpa para o restante da aplicação.
"""

from .SciCam_class import *  # noqa: F401,F403
from .SciCamErrorDefine_const import *  # noqa: F401,F403
from .SciCamInfo_header import *  # noqa: F401,F403
from .SciCamPayload_header import *  # noqa: F401,F403
