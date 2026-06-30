# Fontes de marca (Vision Flow)

Coloque aqui os PNGs exportados do design:

| Arquivo | Destino gerado |
|---------|----------------|
| `favicon.png` | `src/visionflow/presentation/resources/icons/icon_app.svg` |
| `logo.png` | `src/visionflow/presentation/resources/images/logo.svg` |

Regenerar os SVGs empacotados:

```bash
python scripts/generate_brand_svgs.py
```

Os PNGs não entram no instalador; apenas os `.svg` gerados são empacotados.
