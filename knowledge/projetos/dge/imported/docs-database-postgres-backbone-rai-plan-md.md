---
title: DGE fonte - Plano Postgres Backbone RAI-ready
category: projetos
tags:
- dge
- fonte-original
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/database/postgres-backbone-rai-plan.md.'
source_path: docs/database/postgres-backbone-rai-plan.md
---

# Plano Postgres Backbone RAI-ready

Fonte original DGE 2.0: `docs/database/postgres-backbone-rai-plan.md`.

---

# Plano Postgres Backbone RAI-ready

## Objetivo

Criar a espinha dorsal Postgres da DGE preparada para Retrieval-Augmented Intelligence, sem quebrar a aplicacao atual.

A aplicacao continua podendo usar JSON local enquanto `DATABASE_URL` nao existir. O Postgres entra como destino oficial quando a infraestrutura estiver pronta.

## Diretriz Da Build 1

```txt
Frontend mostra, simula e orienta.
Backend valida, calcula, gera, registra e audita.
Postgres preserva a memoria oficial.
RAI recupera contexto confiavel para aumentar a inteligencia da IA.
```

Autenticacao real fica fora do escopo por enquanto porque a Build 1 e fechada.

## O Que RAI Significa Aqui

RAI = Retrieval-Augmented Intelligence.

Camada que recupera contexto de:

- documentos;
- diretrizes;
- cenarios;
- KPIs;
- contratos;
- anexos;
- sprints;
- traces de IA autorizadas;
- futuros dados de ecommerce, ERP, estoque, frete e CRM.

O objetivo nao e executar acoes. O objetivo e responder com contexto rastreavel.

## Fase 1 - Schema E MER

Entregas:

- `docs/database/dge-mer-rai.md`
- `db/schema-core.sql`
- `db/schema-retrieval.sql`
- `db/schema-commerce-future.sql`

Resultado esperado:

- entidades core documentadas;
- chaves primarias e estrangeiras definidas;
- tabelas N:N identificadas;
- retrieval desenhado sem embeddings obrigatorios;
- ecommerce futuro planejado.

## Fase 2 - Repository

Criar uma interface unica de memoria:

```txt
server/memoryRepository.js
server/localJsonAdapter.js
server/postgresAdapter.js
```

O restante do backend deve, aos poucos, deixar de chamar arquivos JSON diretamente e passar a chamar o repository.

## Fase 3 - Adapter Local

O adapter local preserva o comportamento atual:

- scenario snapshots em JSON;
- ai traces em JSON;
- sprint memory em JSON;
- contract memory em JSON;
- contract activations em JSON;
- documents e versions no acervo atual.

Isso reduz risco e permite migrar tela por tela.

## Fase 4 - Adapter Postgres

O adapter Postgres fica preparado, mas so ativa quando `DATABASE_URL` existir.

Regras:

- se `DATABASE_URL` nao existir, usar adapter local;
- se `DATABASE_URL` existir, usar adapter Postgres;
- se Postgres falhar em producao, expor erro claro;
- em desenvolvimento, permitir fallback controlado.

## Fase 5 - Migracao Futura

Script futuro:

```txt
scripts/migrate-local-memory-to-postgres.js
```

Ordem de migracao:

1. tenants e projects seed;
2. scenario_snapshots;
3. scenario_premises;
4. kpis e kpi_snapshots;
5. ai_conversations, ai_messages e ai_traces;
6. documents e document_versions;
7. sprints;
8. contracts, annexes e activations;
9. retrieval_sources e retrieval_chunks derivados.

## Fase 6 - Finance Engine Oficial

Depois do backbone, criar:

```txt
server/domain/finance/calculations.js
server/domain/finance/projectionEngine.js
server/domain/scenario/scenarioValidator.js
POST /api/scenarios/calculate
```

O frontend envia premissas. O backend calcula e registra snapshot oficial.

## O Que Nao Entra Agora

- autenticacao real;
- ecommerce real;
- Bling real;
- Frenet real;
- embeddings/pgvector;
- agentes executando acoes;
- permissoes complexas;
- refatoracao completa do App.jsx.

## Definition Of Done

- schemas criados;
- docs criados;
- repository criado;
- adapter local funcionando;
- adapter Postgres preparado;
- lint e syntax check passando;
- build passando;
- nenhuma feature atual quebrada.
