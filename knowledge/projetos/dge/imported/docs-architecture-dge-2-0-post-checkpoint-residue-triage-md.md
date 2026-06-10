---
title: DGE fonte - DGE 2.0 Post-Checkpoint Residue Triage
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-post-checkpoint-residue-triage.md.'
source_path: docs/architecture/dge-2.0-post-checkpoint-residue-triage.md
---

# DGE 2.0 Post-Checkpoint Residue Triage

Fonte original DGE 2.0: `docs/architecture/dge-2.0-post-checkpoint-residue-triage.md`.

---

# DGE 2.0 Post-Checkpoint Residue Triage

## Contexto

Depois do checkpoint `3acab24`, o backbone oficial da DGE 2.0 ficou versionado e seguro. A triagem pos-checkpoint separa o que ainda estava no worktree para evitar mistura entre:

- DGE 2.0 oficial;
- app raiz/DGE 1.0 preservado como prototipo;
- artefatos gerados por contexto/contratos;
- entregaveis editaveis;
- docs antigas migradas.

## Decisoes

### DGE 2.0

Estado: preservado no checkpoint principal.

Acao: nao limpar nem mover codigo da DGE 2.0 neste ciclo. O diretorio `dge-2.0/` continua sendo a fronteira oficial do novo backbone.

### Entregavel editavel

Estado anterior: DOCX em `docs/deliverables/`.

Acao: mover para `dge-2.0/deliverables/`, junto dos entregaveis oficiais da DGE 2.0.

Racional: o PDF/DOCX tecnico-executivo pertence ao pacote DGE 2.0, nao ao legado da raiz.

### Root app antigo

Estado: alteracoes tracked e arquivos novos em `src/`, `server/`, `db/`, `vite.config.js`, `.env.example` e scripts.

Acao: preservar em checkpoint separado.

Racional: as mudancas parecem estabilizacao/prototipo util do app raiz, incluindo contratos de dados e boundary de erro. Elas nao devem contaminar o checkpoint DGE 2.0, mas tambem nao devem ser descartadas automaticamente.

### AI contexts gerados

Estado: alteracoes em `ai_contexts/generated`, `ai_contexts/versioned` e indice RAG.

Acao: preservar em checkpoint separado de artefatos gerados.

Racional: sao grandes e ruidosos, mas podem ter valor documental/rastreavel. Devem ficar separados do codigo-fonte principal.

### Docs database antigas

Estado: docs removidas em `docs/database/`.

Acao: preservar remocao no checkpoint do root app.

Racional: copias oficiais existem em `dge-2.0/docs/database/`, entao a raiz antiga nao deve manter documentos que confundem a fronteira da DGE 2.0.

## Estado Alvo

Ao fim da limpeza:

- DGE 2.0 permanece intacta;
- entregavel editavel fica dentro de `dge-2.0/deliverables/`;
- root app antigo fica preservado separadamente;
- artefatos gerados ficam preservados separadamente;
- worktree deve ficar limpo ou com residuos pequenos e explicaveis.
