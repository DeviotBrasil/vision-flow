# Vision Flow

Sistema desktop de **visão computacional** para **coleta de imagens** e
**geração de datasets YOLO**. Captura com câmeras industriais OPT (GigE / USB3),
webcams USB (UVC) ou arquivo de vídeo; preview ao vivo, trigger externo (somente
OPT) e gravação MP4; montagem e anotação de **datasets YOLO de segmentação** com
exportação ZIP compatível com **Ultralytics v8–v26**; histórico de capturas e
gravações (importação, seleção, exclusão em lote e ZIP); logs persistidos no
SQLite e temas claro/escuro.

| Documento | Conteúdo |
|-----------|----------|
| [`PRD.md`](PRD.md) | Negócio, funcionalidades e roadmap |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Arquitetura técnica e estrutura do código |
| [`AGENTS.md`](AGENTS.md) | Instruções para agentes de IA no Cursor |

---

## Requisitos

- **Windows**
- **Python 3.12+**
- **OPT (GigE / USB3):** runtime SciCam **versionado** em
  `src/visionflow/infrastructure/camera/opt/runtime/` (clone com
  [Git LFS](https://git-lfs.com/)); sem instalação separada do OPT Machine Vision
- **Webcam UVC / vídeo:** OpenCV (`opencv-python`, já no `pyproject.toml`); sem SDK OPT

---

## Instalação

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -e ".[dev]"
```

> `pip install -e .` (sem `[dev]`) instala só dependências de execução.

Após clonar o repositório, baixe os binários do SDK com Git LFS:

```bash
git lfs install
git lfs pull
```

---

## Execução

```bash
visionflow
# ou
python -m visionflow
```

Debug no VS Code: configuração **Vision Flow** em `.vscode/launch.json`.

Sem o runtime OPT embutido (ou câmera), a aplicação abre normalmente. O
assistente permite configurar webcams UVC; o fluxo OPT fica desabilitado até o
SDK estar disponível.

### Atualizar runtime OPT

Com o OPT Machine Vision instalado no Windows (para obter uma versão mais nova
do fabricante):

```bash
python scripts/sync_opt_runtime.py
```

### Treinar com o dataset exportado

O Vision Flow **não treina modelos** — exporta o ZIP pronto para uso externo.
Após extrair o arquivo na tela **Datasets**, use o Ultralytics no seu ambiente
(com PyTorch instalado):

```bash
yolo segment train data=data.yaml model=yolo26n-seg.pt epochs=100
```

Escolha o modelo base (`yolov8n-seg.pt`, `yolo11n-seg.pt`, `yolo26n-seg.pt`, …)
de acordo com a versão do Ultralytics instalada. Na exportação, selecione o
perfil **YOLO** (V8, V11 ou V26); passe o mouse sobre o combo para ver o que
cada perfil altera no `data.yaml`.

---

## Qualidade de código

Configuração do [`ruff`](https://docs.astral.sh/ruff/) em `pyproject.toml`.
Validação local:

```bash
./.venv/Scripts/ruff check src/
./.venv/Scripts/ruff check src/ --fix
./.venv/Scripts/ruff format src/
```

Este projeto **não mantém suite de testes automatizados**; validação manual e
`ruff check src/` são a referência antes de commit.

### CI (GitHub Actions)

Workflow em [`.github/workflows/ci.yml`](.github/workflows/ci.yml): em cada push
na `main` e em pull requests, roda `ruff check src/` em `windows-latest` com
Python 3.12.

---

## Versionamento

A versão exibida na UI e no instalador vem de **`version`** em
[`pyproject.toml`](pyproject.toml) (fonte única). Após alterar, reinstale o
pacote editável para a UI refletir a mudança:

```bash
pip install -e ".[dev]"
```

Em runtime, `visionflow.version.app_version()` lê a metadata do pacote
(`importlib.metadata`); no **app empacotado** (PyInstaller), usa
`packaging/app_version.txt` gerado no build. A barra de título e o título da
janela consomem esse valor.

Para publicar uma release, alinhe a tag Git ao número em `pyproject.toml`
(ex.: versão `1.0.1` → tag `v1.0.1`).

---

## Identidade visual

| Arquivo | Uso |
|---------|-----|
| `packaging/brand/favicon.png` | Fonte do ícone (não empacotada) |
| `packaging/brand/logo.png` | Fonte do wordmark (não empacotada) |
| `presentation/resources/icons/icon_app.svg` | Ícone da janela, taskbar e base do `.ico` |
| `presentation/resources/images/logo.svg` | Logo horizontal (wordmark DEVIOT) |
| `packaging/visionflow.ico` | Ícone Windows (gerado em build; ignorado pelo Git) |

Constantes de marca (`APP_DISPLAY_NAME`, `APP_SUBTITLE`, paths do instalador) ficam
em `src/visionflow/branding.py`. O Inno Setup inclui `packaging/branding.iss`,
gerado automaticamente pelo build a partir desse módulo.

Para atualizar ícone ou wordmark a partir dos PNGs-fonte:

```bash
pip install -e ".[build]"
python scripts/generate_brand_svgs.py
```

O script `scripts/build_installer.py` gera `packaging/visionflow.ico` a
partir de `icon_app.svg` quando o `.ico` está ausente ou desatualizado.

---

## Qt Designer

```bash
./.venv/Lib/site-packages/PySide6/designer.exe
```

---

## Dados de runtime

Gerados em `data/` (não versionados):

- `visionflow.db` — SQLite (`captures`, `recordings`, `camera_config`,
  `app_logs`, `yolo_datasets`/`yolo_classes`/`yolo_dataset_images`/`yolo_annotations`, …)
- `captures/` — imagens JPEG (timestamp no nome do arquivo); reaproveitadas
  pelas imagens dos datasets YOLO
- `recordings/` — vídeos MP4 (timestamp no nome do arquivo)

Logs da aplicação vão para **console** (stderr) e para a tabela `app_logs` no
banco. Nível ajustável via `VISIONFLOW_LOG_LEVEL` (padrão `INFO`).

Em desenvolvimento, os dados ficam em `data/` na raiz do repositório. No app
instalado, ficam em `{pasta de instalação}\data\` (ex.:
`C:\Program Files\VisionFlow\data\`). Override opcional: `VISIONFLOW_DATA_DIR`.

---

## Distribuição / Instalador (Windows)

### Build local

Pré-requisitos na máquina de **build**:

- Python 3.12+ com venv e `pip install -e ".[dev,build]"`
- Git LFS com runtime OPT baixado (`git lfs pull`)
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`ISCC.exe` no PATH ou em
  `C:\Program Files (x86)\Inno Setup 6\`)

Gerar pasta empacotada e instalador:

```bash
python scripts/build_installer.py
```

Saídas:

- `dist/VisionFlow/` — app empacotado (PyInstaller, modo pasta)
- `dist/VisionFlow-Setup-<versão>.exe` — instalador Inno Setup

Flags úteis:

```bash
python scripts/build_installer.py --skip-installer   # só PyInstaller
python scripts/build_installer.py --skip-pyinstaller # só Inno Setup
```

**Smoke test pós-build:** instalar, abrir o app, confirmar
`{app}\data\visionflow.db`, preview UVC, gravação MP4 na Principal, exportação
ZIP na tela Datasets e fluxo OPT (se câmera disponível).

Limitações conhecidas:

- Instalador estimado ~150–350 MB (PySide6 + OpenCV + runtime OPT).
- O instalador **não** instala driver USB de kernel (`libusb0.sys`); câmeras
  USB3 OPT podem exigir driver do fabricante separado.
- **SmartScreen / “Windows protegeu seu PC”:** instaladores sem **assinatura
  Authenticode** são marcados como não reconhecidos. Isso é esperado até haver
  certificado de assinatura de código (EV/OV). O operador pode escolher
  **Mais informações → Executar assim mesmo**. Para distribuição corporativa,
  assine o `.exe` do instalador e o `VisionFlow.exe` com `SignTool` (Inno Setup:
  diretiva `SignTool` + `SignedUninstaller=yes`).

### Release no GitHub

Workflow [`.github/workflows/release.yml`](.github/workflows/release.yml):

| Gatilho | Resultado |
|---------|-----------|
| Push de tag `v*.*.*` (ex.: `v1.0.1`) | Build do instalador + anexo na **GitHub Release** |
| **Actions → Release → Run workflow** | Mesmo build; instalador como **artefato** (7 dias) |

Passos para publicar:

```bash
# 1. Atualizar version em pyproject.toml
# 2. Commit e tag alinhada à versão
git tag v1.2.5
git push origin main
git push origin v1.2.5
```

O job usa `windows-latest`, baixa o runtime OPT via Git LFS, instala Inno Setup
e executa `python scripts/build_installer.py`.

> **Download:** na página da Release, baixe o asset
> `VisionFlow-Setup-<versão>.exe`. Os arquivos automáticos *Source code
> (zip)* / *Source code (tar.gz)* contêm só o código-fonte, **não** o
> instalador.

---
