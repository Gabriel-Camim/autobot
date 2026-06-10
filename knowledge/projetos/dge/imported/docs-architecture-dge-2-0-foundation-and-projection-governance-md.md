---
title: DGE fonte - DGE 2.0 - Foundation and Projection Governance Blueprint
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-foundation-and-projection-governance.md.'
source_path: docs/architecture/dge-2.0-foundation-and-projection-governance.md
---

# DGE 2.0 - Foundation and Projection Governance Blueprint

Fonte original DGE 2.0: `docs/architecture/dge-2.0-foundation-and-projection-governance.md`.

---

# DGE 2.0 - Foundation and Projection Governance Blueprint

## Decisao Estrutural

A DGE 2.0 sera reconstruida como sistema proprio. A DGE 1.0 fica preservada como prototipo historico e referencia de produto, mas nao deve ser dependencia tecnica da DGE 2.0.

Regra:

- Pode consultar a DGE 1.0 como memoria de aprendizado.
- Nao pode importar codigo, repositorios, stores, APIs, contexto IA ou calculos da DGE 1.0.
- Toda fundacao operacional, banco, projection engine, repositories e governanca devem nascer dentro de `dge-2.0/`.

## Objetivo Da Fundacao

Criar uma base DGE 2.0 capaz de sustentar:

- operacao diaria;
- coleta inicial auditada de premissas e KPIs;
- cenarios oficiais;
- projection engine rastreavel;
- forecast e reforecast versionados;
- historico cronologico de todas as alteracoes;
- solicitacoes de revisao, revogacao e explicacao tecnica;
- suporte e SLA CAOS Lab;
- RAI traces e futura preparacao para ML/fine-tuning.

## Fronteira DGE 2.0

Arquivos dentro de `dge-2.0/` nao devem importar caminhos fora de `dge-2.0/`, exceto pacotes npm.

Importacoes proibidas:

- `src/*`
- `api/*`
- `ai_contexts/*`
- `server/memoryRepository.js`
- `server/postgresAdapter.js`
- `server/aiContextStore.js`
- qualquer modulo legado usado como runtime da DGE 1.0.

Excecoes temporarias devem ser tratadas como divida tecnica bloqueante, nao como arquitetura.

## Core Schema Proprio

A DGE 2.0 precisa de schema fundacional proprio. Tabelas hoje herdadas do core antigo devem ser recriadas ou assumidas explicitamente como parte de `dge-2.0/db`.

Base minima:

- `tenants`
- `projects`
- `scenario_snapshots`
- `scenario_premises`
- `kpi_snapshots`
- `baseline_collection_runs`
- `baseline_collection_items`
- `baseline_collection_reviews`
- `projection_versions`
- `projection_version_links`
- `projection_kpi_outputs`
- `projection_assumption_values`
- `projection_reforecast_proposals`
- `projection_reforecast_decisions`
- `projection_support_requests`
- `projection_support_request_events`
- `projection_variance_rules`
- `audit_log_entries`

## Projection, Forecast E Reforecast

Definicoes:

- Projection: calculo de um cenario a partir de premissas.
- Forecast: leitura esperada oficial para um periodo.
- Reforecast: nova versao governada da projeção/forecast oficial, criada depois que dados observados justificam revisao.
- Simulation: calculo exploratorio sem efeito oficial.
- Preview: leitura de impacto sem mutacao oficial.

Nenhum reforecast deve alterar ou sobrescrever a versao anterior. Toda mudanca cria nova versao.

## Baseline Collection

O primeiro cenario oficial da DGE 2.0 nao deve ser importado da DGE 1.0.

Ele deve nascer de uma coleta inicial auditada:

```txt
Ativacao DGE 2.0
  -> Coleta Inicial de Premissas e KPIs
  -> Revisao/Aprovacao
  -> Scenario Snapshot v1
  -> Projection Engine
  -> Projection Version v1 official
```

Essa coleta inicial deve registrar fonte, confianca, evidencias, responsavel, aprovador e auditoria final.

## Lifecycle Projetivo

Fluxo recomendado:

```txt
Scenario Input
  -> Scenario Snapshot
  -> Calculation Run
  -> Formula Execution Traces
  -> Projection States
  -> Projection Version
  -> Official Forecast
  -> Observed KPI Collection
  -> Variance Detection
  -> Adaptive Suggestion
  -> Reforecast Proposal
  -> Human Approval
  -> Official Reforecast Version
  -> Historical Timeline
  -> Review / Revocation / Technical Explanation Requests
```

## Projection Engine 2.0

O motor novo deve ser trace-first: o calculo ja nasce rastreavel.

Camadas:

- Input Layer: normaliza premissas, unidades, defaults e ranges.
- Formula Execution Layer: executa formulas versionadas do registry.
- Monthly Projection Layer: aplica ativacao, ramp-up, crescimento e cronologia.
- Operational Constraint Layer: aplica estoque, frete, hubs, SLA, capacidade e gargalos.
- Scenario Summary Layer: gera KPIs, payback, ROI, margem, risco e alertas.
- Trace Layer: registra formula traces, projection states e trace packs.
- Persistence Layer: grava snapshots, runs, estados, outputs e eventos.

Arquivos recomendados:

```txt
dge-2.0/server/modules/finance/
  projectionCore.js
  projectionFormulaExecutor.js
  projectionMonthlyModel.js
  projectionOutputs.js
  projectionScenarioSummary.js
  projectionEngine.js
```

## Repositories DGE 2.0

Substituir `memoryRepository` por repositories proprios:

```txt
dge-2.0/server/repositories/
  context.repository.js
  scenarioSnapshot.repository.js
  projectionVersion.repository.js
  calculationRun.repository.js
  formulaTrace.repository.js
  projectionState.repository.js
  supportRequest.repository.js
  auditLog.repository.js
```

O `scenario.service.js` deve orquestrar repositories DGE 2.0, nao persistencia legada.

## Projection Families

Familias que o motor deve suportar, com maturidade progressiva:

- `financial_projection`
- `channel_migration_projection`
- `commerce_growth_projection`
- `inventory_resilience_projection`
- `fulfillment_capacity_projection`
- `freight_margin_projection`
- `logistics_sla_projection`
- `crm_retention_projection`
- `marketing_efficiency_projection`
- `unit_expansion_projection`
- `franchise_projection`
- `cashflow_projection`
- `operational_risk_projection`

Cada familia deve declarar:

- objetivos;
- formulas principais;
- KPIs projetados;
- KPIs observaveis equivalentes;
- tolerancias de variancia;
- regras futuras de recalibracao;
- nivel de maturidade: `active`, `beta`, `blueprint`, `future`, `disabled`.

## Historical Projection Access

A DGE deve permitir acesso cronologico a todas as versoes:

- projeção original;
- forecasts oficiais;
- reforecasts aprovados;
- simulacoes;
- previews;
- versoes revogadas;
- explicacoes tecnicas;
- solicitacoes de revisao;
- solicitacoes de revogacao;
- decisoes humanas;
- SLA e responsavel CAOS Lab.

Regra de ouro:

- nenhuma versao some;
- nenhuma versao oficial e sobrescrita;
- toda alteracao cria evento cronologico;
- toda decisao sensivel tem trilha de aprovacao.

## Projection Support And SLA

Tipos de solicitacao:

- `projection_review_request`
- `reforecast_revocation_request`
- `technical_explanation_request`
- `projection_correction_request`
- `assumption_dispute_request`
- `sla_support_request`

Campos minimos:

- `projection_version_id`
- `reforecast_id`
- `requested_by_user_id`
- `scope_type`
- `scope_key`
- `reason_code`
- `reason_notes`
- `priority`
- `status`
- `sla_due_at`
- `assigned_to`
- `technical_response`
- `decision`
- `metadata`

Estados:

- `open`
- `triage`
- `waiting_customer`
- `waiting_caos`
- `resolved`
- `rejected`
- `revocation_requested`
- `revoked`
- `expired`

## RAI, ML E Fine-Tuning

Toda explicacao tecnica, revisao e revogacao pode gerar RAI trace.

Mas apenas dados aprovados, higienizados e curados podem virar exemplo de treino futuro.

Fontes elegiveis para datasets:

- calculation runs auditados;
- formula traces aprovados;
- support requests resolvidos;
- reforecast decisions aprovadas;
- RAI traces revisados;
- variancias observadas com qualidade suficiente.

## Roadmap De Execucao

Ordem recomendada:

1. Criar `check:dge2-boundary`.
2. Remover dependencias legadas detectadas.
3. Criar `schema-dge-2-core.sql`.
4. Criar repositories DGE 2.0.
5. Reescrever `scenario.service.js` para repositories novos.
6. Reescrever `projectionEngine` como pure core DGE 2.0.
7. Implementar `projection_versions`.
8. Implementar support requests e SLA.
9. Integrar adaptive projection ao fluxo de reforecast proposal.
10. Integrar RAI trace nas explicacoes tecnicas.

Blueprint especifico da engine:

- `dge-2.0/docs/architecture/dge-2.0-projection-engine-platform-blueprint.md`
