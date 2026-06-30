# Instruções de IA — Vision Flow

Você atua como **Engenheiro de Software Sênior** no Vision Flow. Gere código
**robusto, performático e enxuto**.

---

## Documentação de referência

Consulte o documento certo para cada necessidade — **não duplique** regras que
já estão nos outros arquivos.

| Necessidade | Documento |
|-------------|-----------|
| Escopo, funcionalidades, regras de negócio, roadmap | [`PRD.md`](PRD.md) |
| Arquitetura, pastas, camadas, threads, contratos, QSS, câmera, SDK | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Instalação, execução, ruff, ambiente de dev | [`README.md`](README.md) |

---

## Skills do agente

Quando a tarefa corresponder a uma skill abaixo, **leia o `SKILL.md` completo
antes** de agir — as skills têm fluxos e restrições que não estão duplicadas
neste arquivo.

### Projeto (versionadas no repositório)

| Necessidade | Skill | Caminho |
|-------------|-------|---------|
| Revisão de código do Vision Flow (sugestões, SOLID, arquitetura; **sem implementar**) | `revisao-codigo` | [`.cursor/skills/revisao-codigo/SKILL.md`](.cursor/skills/revisao-codigo/SKILL.md) |

### Globais do operador (`~/.cursor/skills-cursor/`)

Disponíveis na máquina local; não versionadas neste repo.

| Necessidade | Skill | Caminho |
|-------------|-------|---------|
| Escolher revisão Bugbot ou Security | `review` | `~/.cursor/skills-cursor/review/SKILL.md` |
| Revisão automatizada (subagent Bugbot) | `review-bugbot` | `~/.cursor/skills-cursor/review-bugbot/SKILL.md` |
| Revisão de segurança (subagent) | `review-security` | `~/.cursor/skills-cursor/review-security/SKILL.md` |
| PR merge-ready (comentários, conflitos, CI) | `babysit` | `~/.cursor/skills-cursor/babysit/SKILL.md` |
| Dividir trabalho em PRs pequenos | `split-to-prs` | `~/.cursor/skills-cursor/split-to-prs/SKILL.md` |
| Criar/atualizar regra Cursor ou `AGENTS.md` | `create-rule` | `~/.cursor/skills-cursor/create-rule/SKILL.md` |
| Criar nova skill (`SKILL.md`) | `create-skill` | `~/.cursor/skills-cursor/create-skill/SKILL.md` |
| Criar hooks (`hooks.json`, scripts) | `create-hook` | `~/.cursor/skills-cursor/create-hook/SKILL.md` |
| Criar subagent customizado | `create-subagent` | `~/.cursor/skills-cursor/create-subagent/SKILL.md` |
| Migrar rules/commands para skills | `migrate-to-skills` | `~/.cursor/skills-cursor/migrate-to-skills/SKILL.md` |
| Cursor Automations | `automate` | `~/.cursor/skills-cursor/automate/SKILL.md` |
| Prompt/skill em intervalo (`/loop`) | `loop` | `~/.cursor/skills-cursor/loop/SKILL.md` |
| Status line do CLI Cursor | `statusline` | `~/.cursor/skills-cursor/statusline/SKILL.md` |
| Config do CLI (`cli-config.json`) | `update-cli-config` | `~/.cursor/skills-cursor/update-cli-config/SKILL.md` |
| Ajustes em `settings.json` do Cursor/VS Code | `update-cursor-settings` | `~/.cursor/skills-cursor/update-cursor-settings/SKILL.md` |
| Executar comando literal (`/shell`) | `shell` | `~/.cursor/skills-cursor/shell/SKILL.md` |
| Cursor SDK (agentes programáticos) | `sdk` | `~/.cursor/skills-cursor/sdk/SKILL.md` |
| Artefato visual interativo (tabelas, análises) | `canvas` | `~/.cursor/skills-cursor/canvas/SKILL.md` |

**Prioridade no Vision Flow:** para *code review* com sugestões alinhadas a
`ARCHITECTURE.md` e sem editar arquivos, use **`revisao-codigo`**. Para revisão
automatizada de diff (Bugbot/Security), use as skills `review-*`. Não misture os
dois fluxos na mesma resposta.

---

## Regras obrigatórias do agente

### Antes de codar

1. Leia **`PRD.md`** quando a tarefa envolver comportamento do produto, telas,
   fluxos do operador ou regras de negócio.
2. Leia **`ARCHITECTURE.md`** quando a tarefa envolver estrutura de pastas,
   novas dependências entre camadas, persistência, câmera, workers ou UI.
3. Se algo estiver **ambíguo ou contraditório**, não invente: registre a
   suposição em uma linha ou peça esclarecimento **antes** de codar.

### Ao implementar

- Respeite a regra de dependência: `presentation → domain ← infrastructure`;
  composição/injeção **somente** em `app.py` (detalhes em `ARCHITECTURE.md`).
- **Não** reintroduza suporte a Linux/WSL — o projeto é Windows-only.
- **Não** use ORM, `import *` no Qt, nem acople UI a exceções de SDK.
- O código deve passar em `ruff check src/`.
- Siga as convenções de idioma e QSS descritas em `ARCHITECTURE.md`.

### Comunicação

- **Português (Brasil):** explicações ao usuário, comentários, logs, textos de UI.
- **Inglês:** nomes de variáveis, funções, classes, tabelas SQLite e chaves de
  dicionário.

### Escopo das mudanças

- Diff mínimo e focado na tarefa; não refatore nem documente além do pedido.
- Não crie commits nem PRs sem solicitação explícita do usuário.
- **Não** adicione testes automatizados nem arquivos em `tests/` salvo pedido
  explícito do usuário (validação: `ruff check src/` e smoke manual).
