# PRD — Vision Flow

Documento de **negócio**: visão do produto, funcionalidades e roadmap. Detalhes
técnicos em [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 1. Visão geral

**Vision Flow** é um **sistema desktop de visão computacional** para **coleta
de imagens** e **geração de datasets YOLO**. O operador configura a câmera (OPT
GigE/USB3, webcam UVC ou arquivo de vídeo), acompanha o preview ao vivo, coleta
dados e monta datasets anotados de segmentação prontos para exportação e uso
externo com Ultralytics (v8–v26).

**Plataforma alvo:** Windows (ambiente de produção e desenvolvimento).

### Fluxo principal

1. **Aquisição** — conectar câmera ou vídeo; preview, captura, trigger (OPT) e
   gravação MP4.
2. **Organização** — histórico local de capturas e gravações; importação e
   exportação.
3. **Anotação e exportação** — datasets YOLO de segmentação a partir das imagens
   coletadas; download em ZIP compatível com Ultralytics v8–v26.

---

## 2. Personas e objetivos

| Persona | Objetivo |
|---------|----------|
| Operador | Conectar câmera, acompanhar preview, coletar capturas/gravações e consultar histórico |
| Engenheiro de visão | Configurar aquisição, organizar dados capturados e exportar para uso externo |
| Engenheiro de ML | Montar datasets anotados de segmentação e exportar ZIP para treino externo (Ultralytics) |

---

## 3. Funcionalidades

### 3.1 Implementadas

#### Câmera (assistente em 3 etapas)

- Seleção do backend de câmera: **OPT Machine Vision** (GigE / USB3),
  **Webcam USB (UVC)** ou **Vídeo (arquivo)**.
- Busca de dispositivos (OPT via SDK SciCam; UVC via OpenCV/DirectShow) ou
  **importação de arquivo de vídeo** (`.mp4`, `.avi`, `.mkv`, `.mov`, `.wmv`).
- Etapa *Dispositivos* em largura total (botão de busca/importação e tabela).
- Conexão e teste com **preview ao vivo** (sem captura nem trigger no assistente).
- Gravação da configuração (`backend`, identificação do dispositivo) para uso
  automático na tela Principal.
- Runtime SciCam **embutido** no projeto (`opt/runtime/`, Git LFS); fallback para
  instalação OPT em `Program Files` apenas se o runtime versionado estiver vazio.
- Se o SDK OPT estiver indisponível, o fluxo OPT fica desabilitado com feedback
  claro; o fluxo UVC permanece utilizável.

#### Tela Principal

- Indicador de status de conexão com a câmera.
- Iniciar/parar operação (conecta à câmera previamente configurada).
- **Preview ao vivo** do fluxo de imagens.
- **Capturar** o frame exibido no momento (desabilitado com trigger ativo ou
  enquanto o trigger está sendo habilitado).
- **Gravar** — inicia/para gravação de vídeo **MP4** do fluxo ao vivo
  (desabilitado com trigger ativo ou enquanto o trigger está sendo habilitado).
  Ao parar, o arquivo é registrado no histórico de gravações.
- **Trigger** — toggle de escuta (somente câmeras OPT): estados no próprio botão
  (*Trigger desabilitado* → *Habilitando trigger...* → *Trigger habilitado* →
  *Aguardando trigger...* no preview; inverso ao desligar). Com o modo ativo,
  aguarda eventos de trigger externo (hardware), atualiza o preview e **salva
  cada captura automaticamente** na faixa inferior. O operador configura
  ``TriggerSource`` no software OPT; o app alterna ``TriggerMode`` On/Off.
  Preview ao vivo e trigger são mutuamente exclusivos. Em webcams UVC e em
  **vídeo importado** o botão permanece visível, porém **desabilitado** (sem
  trigger GenICam).
- **Vídeo (arquivo):** controles de reprodução na Principal — pausar/retomar,
  avançar/retroceder 5 s e slider de posição; fim do arquivo pausa no último
  frame (sem loop). Captura e gravação funcionam no frame exibido.
- Contador de capturas realizadas **no dia corrente**.
- Painel inferior com abas **Capturas** e **Gravações** — faixa das **últimas 10
  do dia** em cada aba, com miniaturas assíncronas (cache lazy em disco em
  `data/thumbs/`; leitura fora da thread da GUI).
- Popup nativo do Windows por captura: visualizar, **baixar**, **recortar** e
  **redimensionar** (janelas separadas; atualizar a captura atual ou salvar como
  nova) e **excluir**.
- Popup nativo por gravação na aba **Gravações**: reproduzir, **baixar** e
  **excluir**.
- Confirmação ao sair da Principal com câmera **conectada ou conectando** (diálogo
  temático Sim/Não; desconectar antes de trocar de tela).

#### Histórico de capturas

- Tela **Capturas** com filtro por data início/fim, grid paginado, **seleção
  múltipla** (*selecionar/desmarcar todas* no período filtrado) e popup de
  detalhe (visualizar, baixar, recortar, redimensionar, excluir) igual ao da
  Principal.
- **Adicionar** imagens externas (JPEG/PNG/BMP/TIFF/WebP) via diálogo de
  arquivos; importação na thread principal com popup de progresso.
- **Excluir** itens selecionados em lote (confirmação temática).
- **Baixar ZIP** dos itens **selecionados** na galeria, com nomes únicos por
  captura (`captura_{id}_{arquivo}`); consulta SQLite e compactação na thread
  principal com popup de progresso; banner de aviso quando há arquivos ausentes
  no disco.

#### Histórico de gravações

- Tela **Gravações** com filtro por data início/fim, grid paginado, **seleção
  múltipla** e popup de detalhe (reproduzir, baixar, excluir).
- **Adicionar** vídeos externos (`.mp4`) via diálogo de arquivos; arquivos fora
  de `data/recordings/` são copiados para o repositório local.
- **Excluir** itens selecionados em lote (confirmação temática).
- **Baixar ZIP** dos itens **selecionados** (`gravacao_{id}_{arquivo}`); mesmo
  fluxo de progresso e avisos da tela Capturas.

#### Datasets YOLO (segmentação)

- Tela **Datasets** para montar e anotar datasets de segmentação no formato
  Ultralytics, a partir das imagens já capturadas.
- Gerenciamento de **datasets nomeados** (criar, renomear, excluir); seleção do
  dataset ativo por combo.
- **Classes/labels** com nome e cor; índice YOLO contíguo (0-based) por dataset;
  nome único (sem diferenciar maiúsculas) por dataset. A lista de classes mostra
  o **contador de anotações** de cada uma.
- **Adicionar imagens** a partir da galeria de capturas, via diálogo com filtro
  por período (atalhos + intervalo de datas), paginação e *selecionar/desmarcar
  todas* (espelha a tela Capturas).
- **Anotação** de cada imagem com **retângulos** e **polígonos** (pontos
  personalizados); a forma selecionada pode ser **movida e redimensionada** no
  canvas. Coordenadas guardadas **normalizadas** (0..1), independentes da
  resolução.
- Galeria de imagens do dataset exibe, abaixo do id, **as classes anotadas** em
  cada imagem; suporta **seleção múltipla** e **exclusão em lote** de imagens.
- Seletor **YOLO** na toolbar (V8, V11, V26) com tooltip explicando o perfil de
  `data.yaml`; a preferência é persistida entre sessões.
- **Salvar ZIP** no layout Ultralytics de segmentação (`images/{train,val}`,
  `labels/{train,val}`, `data.yaml`, `classes.txt`); compactação na thread
  principal com popup de progresso. Aviso apenas em erro ou imagens ausentes.

#### Logs do sistema

- Tela **Logs** com atalho *Hoje*, filtro por dia, busca por texto
  (debounce), tabela estilo planilha com cores por nível, exportação **CSV** do
  resultado filtrado (até 100.000 registros) e ação **Limpar logs** (remove
  todos os registros, com confirmação).
- Exibição limitada a **5.000** registros por consulta; subtítulo da tela indica
  contagem filtrada e aviso quando o total filtrado excede o limite.
- Registros persistidos no SQLite (`app_logs`) via handler de logging; na
  inicialização remove entradas com mais de **90 dias**.

#### Persistência e dados

- Configuração única da câmera selecionada (`backend`, série/IP para OPT;
  `opencv_index` para UVC).
- Registro de cada captura com metadados (resolução, formato, data/hora).
- Registro de cada gravação com metadados (resolução, duração, tamanho,
  data/hora).
- Imagens salvas como **JPEG** em `data/captures/` (nome com timestamp para
  ordenação na pasta).
- Vídeos salvos como **MP4** em `data/recordings/` (nome com timestamp).

#### Navegação e chrome

- Menu lateral: **Principal**, **Capturas**, **Gravações**, **Datasets**,
  **Câmera** e **Logs**.
- Barra superior: wordmark **DEVIOT** (`logo.svg`), versão, subtítulo **Sistema de visão computacional para coleta de imagens e geração de datasets YOLO**,
  alternância de tema e perfil do operador (sem notificações).

#### Experiência geral

- Interface com temas **claro** e **escuro** (preferência persistida).
- Diálogos de confirmação e detalhe de captura respeitam o tema ativo (preview
  da imagem permanece com fundo preto).
- Operação da câmera e miniaturas em thread de fundo; importação, exclusão e
  compactação ZIP na thread principal com popup de progresso (UI indisponível
  durante o modal, mas responsiva via repintura entre itens).
- Aplicação inicia mesmo sem câmera ou SDK disponível (degradação graciosa).

### 3.2 Planejadas (não implementadas)

| Tela | Propósito |
|------|-----------|
| Configurações | Parâmetros globais do sistema |
| Ajuda | Documentação e suporte ao operador |

---

## 4. Regras de negócio

1. **Uma câmera ativa por vez** — a configuração salva define qual dispositivo a
   tela Principal tenta conectar automaticamente.
2. **Edição opcional de capturas** — o operador pode recortar ou redimensionar uma
   imagem salva pelo popup de detalhe. **Atualizar captura** sobrescreve o JPEG e
   atualiza `width`/`height`, preservando `id`, `captured_at`, `frame_id` e
   `pixel_format`. **Gerar nova captura** cria registro e arquivo independentes.
   Exclusão continua removendo registro e arquivo.
3. **Identificação de dispositivo** — reconexão OPT prioriza número de série e
   IP; reconexão UVC prioriza `opencv_index` (índice DirectShow), com fallback
   para `device_index` em configurações antigas; reconexão de **vídeo** prioriza
   `video_path` (caminho absoluto normalizado).
4. **Degradação graciosa** — ausência de câmera ou SDK não impede abrir o
   software; o operador recebe feedback claro e pode acessar o assistente de
   configuração.
5. **Persistência de capturas só na Principal** — eventos `capture_ready` gravam
   no SQLite apenas quando a tela Principal está visível; o assistente Câmera é
   somente teste de preview.
6. **Configuração GigE/GenICam no OPT** — parâmetros de rede, pixel e trigger
   (exceto ``TriggerMode`` On/Off) são definidos no software do fabricante; o app
   não reconfigura a câmera na conexão.
7. **Trigger só em OPT** — webcams UVC e arquivos de vídeo não suportam escuta
   de trigger; o worker e o controlador recusam ativação mesmo se solicitada
   programaticamente.
8. **Retenção de logs** — registros em `app_logs` com mais de 90 dias são
   removidos automaticamente na abertura do aplicativo.
9. **Exportação por contexto** — nas telas **Capturas** e **Gravações**, ZIP e
   exclusão operam sobre os itens **selecionados** (com opção de selecionar
   todas no período filtrado). Na tela **Logs**, o CSV exporta o conjunto
   **filtrado** (sem seleção individual). Na tela **Datasets**, o ZIP exporta o
   dataset inteiro e a exclusão de imagens é por seleção.
10. **Gravação na Principal** — um único fluxo MP4 por vez; desabilitada com
    trigger ativo. Ao parar, o arquivo é registrado no SQLite; gravações vazias
    (nenhum frame) são descartadas sem registro.
11. **Anotações YOLO de segmentação** — coordenadas sempre normalizadas (0..1);
    retângulos são exportados como polígonos de 4 vértices; anotações com menos
    de 3 vértices são descartadas na exportação.
12. **Índice de classe contíguo** — cada classe recebe `order_index` 0-based por
    dataset; a exportação usa essa ordem em `data.yaml`/`classes.txt`. Nomes de
    classe são únicos (case-insensitive) dentro do dataset.
13. **Exportação Ultralytics (v8–v26)** — divisão treino/validação (~20% para
    validação por padrão); imagens ausentes no disco são ignoradas com aviso; um
    ZIP sem nenhuma imagem válida é removido. O perfil selecionado ajusta o
    `data.yaml` (`task: segment`, formato de `names`) para compatibilidade com a
    versão alvo do Ultralytics.
14. **Treino externo** — o Vision Flow **não treina modelos**; o operador usa o
    ZIP exportado com ferramentas Ultralytics (CLI, notebook ou outro ambiente).
