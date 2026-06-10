---
title: DGE fonte - DGE 2.0 - Core Schema Blueprint
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-core-schema-blueprint.md.'
source_path: docs/architecture/dge-2.0-core-schema-blueprint.md
---

# DGE 2.0 - Core Schema Blueprint

Fonte original DGE 2.0: `docs/architecture/dge-2.0-core-schema-blueprint.md`.

---

# DGE 2.0 - Core Schema Blueprint

## Decisao Central

A DGE 2.0 nao deve importar cenario da DGE 1.0.

O primeiro cenario oficial da DGE 2.0 deve nascer de uma coleta inicial auditada de premissas e KPIs, seguida de revisao/aprovacao, gerando:

```txt
Baseline Collection
  -> Scenario Snapshot v1
  -> Projection Engine Run
  -> Projection Version v1 official
```

A DGE 1.0 pode ser usada como referencia historica para lembrar campos uteis, erros e aprendizados, mas nao como origem oficial de dados nem dependencia tecnica.

## Regra Do Core

Core e tudo que todos os modulos precisam para existir, auditar, versionar, aprovar, rastrear e explicar.

Nao pertencem ao core:

- produtos;
- estoque detalhado;
- commerce orders;
- fulfillment;
- frete;
- logistics shipments;
- automacoes;
- RAI training examples.

Esses modulos devem depender do core, nao morar dentro dele.

## Blocos Do Core

### 1. Identidade Operacional

Tabelas:

- `tenants`
- `projects`
- `operational_nodes`

Objetivo:

- definir tenant, projeto, unidade, franquia, hub, loja, centro de estoque, ecommerce e operacao central;
- permitir escopo de dados, usuarios, aprovacoes, relatórios e cockpit.

### 2. Usuarios, Acesso E Responsabilidade

Tabelas:

- `tenant_users`
- `tenant_user_roles`
- `tenant_user_node_assignments`
- `tenant_user_responsibilities`

Objetivo:

- controlar quem ve, quem preenche, quem revisa, quem aprova e quem audita;
- permitir acesso por unidade, franquia, regiao, cargo e responsabilidade.

### 3. Auditoria E Governanca

Tabelas:

- `audit_log_entries`
- `timeline_events`
- `approval_workflows`
- `approval_requests`
- `approval_decisions`

Objetivo:

- toda acao sensivel deve gerar rastro;
- toda mudanca oficial deve ter fluxo de aprovacao;
- toda decisao importante deve aparecer na cronologia operacional.

### 4. Coleta Inicial / Baseline Collection

Tabelas:

- `baseline_collection_runs`
- `baseline_collection_items`
- `baseline_collection_reviews`

Objetivo:

- coletar premissas e KPIs iniciais para criar o primeiro cenario oficial;
- impedir que o primeiro scenario snapshot nasca de JSON solto ou import da DGE 1.0;
- guardar fonte, confianca, evidencias, usuario responsavel e aprovacao.

Fluxo:

```txt
Ativacao DGE 2.0
  -> Coleta Inicial
  -> Revisao por superior
  -> Auditoria final
  -> Scenario Snapshot v1
  -> Projection Version v1 official
```

Campos esperados na coleta inicial:

- GMV atual;
- GMV marketplace;
- pedidos mensais;
- ticket medio;
- taxas marketplace;
- custo operacional marketplace;
- checkout fee;
- cancelamento;
- devolucao/garantia;
- clientes sem contato direto;
- conversao esperada do canal proprio;
- abandono de carrinho;
- recuperacao de carrinho;
- recompra;
- CAC;
- LTV;
- frete medio;
- frete pago pelo cliente;
- subsidio de frete;
- retirada em loja;
- prazo atual;
- prazo esperado com hubs;
- capacidade operacional;
- cobertura macro de estoque;
- investimento inicial;
- mensalidade;
- custo operacional adicional;
- horizonte de analise;
- prazo de implantacao.

### 5. Scenario Foundation

Tabelas:

- `scenario_snapshots`
- `scenario_premises`
- `scenario_kpi_snapshots`
- `scenario_versions`

Objetivo:

- representar o cenario oficial como snapshot versionado;
- separar KPIs projetados/derivados do cenario dos KPIs observados diarios;
- permitir comparacao entre cenarios, versoes e reforecasts.

Regra:

- `scenario_snapshots.baseline_collection_run_id` deve existir para cenario inicial oficial;
- cenarios exploratorios podem nascer como simulation, mas nao viram official sem governanca.

### 6. Projection Foundation

Tabelas:

- `projection_versions`
- `projection_version_links`
- `projection_assumption_values`
- `projection_kpi_outputs`
- `calculation_runs`
- `formula_execution_traces`
- `projection_states`
- `projection_state_trace_packs`
- `projection_variance_rules`

Objetivo:

- versionar toda projecao;
- preservar historico de forecast e reforecast;
- registrar premissas, KPIs projetados, formulas, estados mensais e trace packs;
- permitir comparacao entre versoes.

### 7. Reforecast E Suporte

Tabelas:

- `projection_reforecast_proposals`
- `projection_reforecast_decisions`
- `projection_support_requests`
- `projection_support_request_events`
- `projection_technical_explanations`

Objetivo:

- permitir solicitacao de revisao de projecao;
- permitir solicitacao de revogacao de reforecast;
- permitir solicitacao de explicacao tecnica;
- controlar SLA CAOS Lab;
- manter historico cronologico e auditable.

### 8. Data Source E Qualidade

Tabelas:

- `data_sources`
- `ingestion_batches`
- `data_quality_assessments`
- `source_payload_fingerprints`

Objetivo:

- identificar origem dos dados;
- medir confianca;
- rastrear imports manuais e automatizados;
- preparar entrada futura de Bling, ecommerce, Frenet, Loggi e n8n.

## Primeiro Fluxo Oficial Da DGE 2.0

```txt
1. Tenant/project criado
2. Unidades/franquias/hubs cadastrados
3. Usuarios e responsabilidades configurados
4. Baseline collection aberta
5. Operador/gestor preenche premissas e KPIs
6. Superior revisa
7. Auditor final aprova
8. Scenario Snapshot v1 nasce da coleta aprovada
9. Projection Engine 2.0 executa
10. Calculation Run e Formula Traces sao persistidos
11. Projection Version v1 official e criada
12. Timeline registra a origem da projecao oficial
13. Coleta diaria observada comeca
14. Fechamento mensal compara projetado vs observado
15. Adaptive Projection pode sugerir reforecast proposal
```

## Contrato Conceitual De Status

Baseline collection:

- `draft`
- `submitted`
- `under_review`
- `approved`
- `rejected`
- `superseded`

Scenario:

- `simulation`
- `official_initial`
- `official_reforecast`
- `archived`

Projection version:

- `draft`
- `preview`
- `simulation`
- `official`
- `reforecast_proposal`
- `approved_reforecast`
- `superseded`
- `revocation_requested`
- `revoked`
- `restored`

Support request:

- `open`
- `triage`
- `waiting_customer`
- `waiting_caos`
- `resolved`
- `rejected`
- `expired`

## Proximo Passo Tecnico

Criar `dge-2.0/db/schema-dge-2-core.sql` com:

1. tabelas fundacionais ausentes;
2. alteracoes necessarias nas tabelas ja existentes;
3. indices minimos;
4. constraints para preservar versionamento e auditoria;
5. compatibilidade com `schema-dge-2.sql` atual.
