---
title: DGE fonte - DGE 2.0 Operational Nervous System v1
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-operational-nervous-system.md.'
source_path: docs/architecture/dge-2.0-operational-nervous-system.md
---

# DGE 2.0 Operational Nervous System v1

Fonte original DGE 2.0: `docs/architecture/dge-2.0-operational-nervous-system.md`.

---

# DGE 2.0 Operational Nervous System v1

## Papel

O Operational Nervous System e a camada que conecta eventos, excecoes, impacto, SLA, responsavel, resolucao, BI e futura IA/RAI.

Ele evita que Data Intake, ERP, Commerce, approvals, bottlenecks, reforecast, integracoes e automacoes criem filas paralelas sem linguagem comum.

Fluxo canonico:

```txt
evento -> excecao -> causa -> impacto -> responsavel -> SLA -> resolucao -> evidencia -> BI -> RAI futuro
```

## Contratos

- `operational.exception_hub.v1`
- `operational.exception_graph.v1`
- `operational.exception_impact.v1`
- `operational.resolution_policy.v1`
- `data.intake.coverage_lock.v1`

## Interfaces

- `GET /api/operations/exception-hub`
- `GET /api/operations/exception-hub/:exceptionKey`
- `POST /api/operations/exception-hub/:exceptionKey/link`
- `POST /api/operations/exception-hub/:exceptionKey/resolve`
- `GET /api/operations/exception-impact`
- `GET /api/operations/data-intake/coverage-lock`

## Fontes Normalizadas

O hub le e normaliza:

- Data Intake obligations/submissions;
- `validation_failed` e `module_write_failed`;
- ERP exceptions;
- Commerce exceptions;
- payment failures e checkout friction;
- approval requests;
- operational exceptions antigas de governance;
- bottleneck signals;
- reforecast cases e stale proposals/previews;
- integration runs;
- automation readiness failures.

O hub nao substitui os centros de excecao de dominio. ERP, Commerce, Governance e Data Intake continuam sendo fontes da verdade. O hub conecta, prioriza, deduplica, explica impacto e delega resolucao.

## Exception Graph

Links cross-module ficam em `operational_exception_graph_links`.

Node types:

- `data_intake_obligation`
- `data_intake_submission`
- `approval_request`
- `commerce_exception`
- `erp_exception`
- `governance_exception`
- `bottleneck_signal`
- `reforecast_case`
- `projection_version`
- `automation_run`
- `integration_run`
- `order`
- `sku`
- `hub`
- `customer_hash`
- `channel`

Edge types:

- `caused_by`
- `blocks`
- `duplicates`
- `resolves`
- `supersedes`
- `impacts_projection`
- `impacts_customer`
- `impacts_inventory`
- `requires_approval`
- `dispatched_from`
- `evidence_for`

O grafo pode ter links manuais/governados e links derivados, como grupos provaveis de duplicidade por pedido, SKU, cliente, hub ou causa.

## Prioridade E Impacto

Cada excecao recebe:

- `priorityScore`;
- impacto financeiro estimado;
- impacto em cliente;
- impacto em estoque;
- impacto em projecao;
- impacto em BI;
- impacto em auditoria;
- bloqueio operacional;
- root cause provavel;
- role responsavel;
- proxima acao.

Isso transforma o cockpit em uma fila operacional explicavel: nao basta listar pendencias, a DGE precisa dizer por que aquilo importa.

## Resolution Delegation

O hub pode receber uma intencao de resolucao, mas delega para o dominio correto:

- Commerce exception -> Commerce Exception Center;
- ERP exception -> ERP Exception Center;
- Governance exception -> Operational Governance;
- Data Intake, approvals, bottlenecks e reforecast exigem resolucao pelo fluxo especifico quando nao houver delegacao segura.

Guardrails:

- `system_integration` nao resolve excecao final;
- resolucao exige actor, role e justificativa;
- marketplaces seguem benchmark/projecao;
- nenhuma cobranca, cupom, email ou contato automatico;
- nenhuma projection version nasce do hub;
- nenhum write direto ignora servico modular.

## Data Intake Coverage Lock

O coverage lock impede que novos modulos entrem por portas laterais.

Cada endpoint mutavel importante deve estar classificado como:

- coberto por collector;
- runtime sistemico direto permitido;
- integracao externa assistida;
- fora de escopo v1;
- bloqueado por falta de routing.

Antes de integrar Frenet, Loggi, Bling real, n8n ou frontend, essa camada deve continuar verde.

## Integration Readiness Lock

O proximo gate antes de qualquer integracao real e `integration.readiness_lock.v1`.

Ele classifica Bling, Frenet, Loggi, n8n, ecommerce real e gateway de pagamento por:

- contrato;
- normalizador/payload contract;
- dry-run;
- Data Intake coverage;
- Exception Hub mapping;
- idempotencia;
- BI;
- fallback manual;
- credencial/config sem expor segredo;
- blast radius.

Estados:

- `not_configured`;
- `contract_declared`;
- `local_dry_run_ready`;
- `assisted_import_ready`;
- `automation_trace_ready`;
- `live_api_probe_ready`;
- `production_ready`;
- `blocked`.

Falhas de readiness entram no Exception Hub como `source_system = integration_readiness` e aparecem no cockpit como tickets da lane `integrations_automations`.

Esse lock nao substitui os exception centers de dominio. Ele apenas impede que uma integracao real avance sem rota de excecao, BI, auditoria e contingencia.

## BI / Superset

Datasets:

- `bi_operational_exception_hub_dataset`
- `bi_operational_exception_graph_dataset`
- `bi_exception_root_cause_unified_dataset`
- `bi_exception_resolution_sla_unified_dataset`
- `bi_data_intake_coverage_lock_dataset`
- `bi_exception_projection_impact_dataset`
- `bi_integration_readiness_lock_dataset`
- `bi_integration_provider_capabilities_dataset`
- `bi_integration_readiness_checks_dataset`
- `bi_integration_exception_mapping_dataset`
- `bi_automation_orchestration_readiness_dataset`

Dashboards afetados:

- Operations Cockpit;
- Executive Reports;
- AI/RAI Observability;
- Reforecast Control;
- ERP Intelligence;
- Commerce Intelligence.

## Maturidade

Estado v1:

- backend-first;
- deterministico;
- sem LLM runtime;
- sem frontend;
- sem automacao externa;
- pronto para Superset e futuro RAI.

O passo natural depois deste bloco e usar o hub como base para integracoes reais e automacoes n8n, porque qualquer falha ja tera caminho padrao de excecao, impacto, responsavel e resolucao.
