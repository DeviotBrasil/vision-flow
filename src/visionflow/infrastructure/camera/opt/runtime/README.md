# Runtime OPT SciCam (Win64_x64)

Binários proprietários do SDK **OPT Machine Vision** (SciCam), versionados neste
repositório para que o Vision Flow funcione sem instalação separada do runtime.

A redistribuição neste projeto foi autorizada pelo mantenedor junto à OPT. Não
utilize estes arquivos fora do escopo licenciado do SDK.

## Atualizar

Com o OPT Machine Vision instalado no Windows:

```bash
python scripts/sync_opt_runtime.py
```

O script copia `Win64_x64` para esta pasta e atualiza `MANIFEST.json`.
