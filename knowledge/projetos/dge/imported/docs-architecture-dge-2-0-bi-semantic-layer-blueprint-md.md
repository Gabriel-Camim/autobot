---
title: DGE fonte - DGE 2.0 - BI Semantic Layer Blueprint
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-bi-semantic-layer-blueprint.md.'
source_path: docs/architecture/dge-2.0-bi-semantic-layer-blueprint.md
---

# DGE 2.0 - BI Semantic Layer Blueprint

Fonte original DGE 2.0: `docs/architecture/dge-2.0-bi-semantic-layer-blueprint.md`.

---

# DGE 2.0 - BI Semantic Layer Blueprint

## Decisao

BI e Superset fazem parte da arquitetura oficial da DGE 2.0.

O cockpit, Superset, relatorios periodicos e IA da DGE nao devem consultar tabelas cruas como fonte primaria. A camada inicial de BI deve ser composta por views SQL controladas, com nomes estaveis e semantica clara.

## Principios

- filtros temporais de BI sao apenas exibicao;
- projection engine e reforecast usam horizonte tecnico/modelado;
- datasets devem preservar tenant, project e chaves de rastreabilidade;
- datasets devem expor campos JSON ricos quando ainda nao houver normalizacao madura;
- dashboards executivos usam datasets agregaveis;
- exploracao analitica usa datasets detalhados;
- IA/RAI usa datasets rastreaveis, com origem e contexto;
- Superset deve consumir views certificadas, nao tabelas operacionais cruas.

## Camadas De Dataset

### Projection BI

- `bi_projection_versions_dataset`
- `bi_projection_monthly_outputs_dataset`
- `bi_projection_states_dataset`
- `bi_projection_channel_runtime_dataset`
- `bi_progressive_formulas_dataset`
- `bi_formula_runtime_overrides_dataset`
- `bi_projection_trace_packs_dataset`
- `bi_official_reforecast_lineage_dataset`
- `bi_projection_active_state_dataset`
- `bi_reforecast_dependency_queue_dataset`
- `bi_official_reforecast_explainability_dataset`
- `bi_official_reforecast_monthly_impact_dataset`
- `bi_reforecast_evidence_ledger_dataset`
- `bi_official_channel_reforecast_dataset`
- `bi_official_inventory_reforecast_dataset`
- `bi_active_projection_reference_dataset`

Uso:

- timeline de versoes;
- comparacao de forecasts/reforecasts;
- explicabilidade oficial de reforecast com motivo, evidencia, impacto e estado ativo posterior;
- classificacao de familia de reforecast (`channel_runtime`, `formula_reforecast`, `freight_reforecast`, `mixed_reforecast`, `general_reforecast`);
- impacto mensal baseline vs official por metrica;
- ledger de evidencias e overrides para auditoria/RAI;
- projection explorer;
- runtime canalizado de canal proprio vs marketplaces;
- runtime de capacidade de estoque via `projection.inventoryRuntime.v1`;
- curvas progressivas;
- formula swaps e runtime overrides materializados;
- formula trace packs;
- referencia oficial ativa para cockpit e BI.

### Formula, Trace E Explicabilidade

- `bi_formula_registry_dataset`
- `bi_formula_execution_traces_dataset`

Uso:

- catalogo de formulas;
- auditoria de calculo;
- rastreio de inputs/outputs;
- preparacao de explicacoes tecnicas;
- base futura para RAI e suporte.

### Observado, Variancia E Reforecast

- `bi_daily_kpi_values_dataset`
- `bi_monthly_kpi_traces_dataset`
- `bi_observed_projection_variances_dataset`
- `bi_reforecast_cases_dataset`
- `bi_inventory_reforecast_cases_dataset`
- `bi_reforecast_proposals_dataset`
- `bi_reforecast_decisions_dataset`
- `bi_reforecast_diff_summary_dataset`
- `bi_reforecast_version_timeline_dataset`

Uso:

- acompanhamento diario;
- trace mensal;
- forecast vs realizado;
- variancias;
- cases de reforecast;
- decisoes e aprovacoes de reforecast;
- diff baseline vs preview;
- timeline executiva de versoes, aprovacoes, revogacoes e formula swaps.

### Gargalos E Impacto Operacional

- `bi_bottleneck_signals_dataset`
- `bi_projection_impact_traces_dataset`

Uso:

- gargalos por dominio;
- recorrencia por cadencia;
- sinais que impactam projecao;
- fila executiva de risco operacional.

### Governanca E Aprovacoes

- `bi_approval_flow_dataset`
- `bi_manual_kpi_collection_blueprint_dataset`
- `bi_manual_collection_obligations_dataset`
- `bi_manual_collection_status_dataset`
- `bi_manual_collection_role_queue_dataset`
- `bi_data_intake_routing_dataset`
- `bi_data_intake_endpoint_map_dataset`
- `bi_data_intake_automation_readiness_dataset`
- `bi_data_intake_submissions_dataset`
- `bi_data_intake_submission_audit_dataset`
- `bi_data_intake_sla_dataset`
- `bi_data_intake_coverage_lock_dataset`

Uso:

- pedidos de aprovacao;
- decisoes por etapa;
- SLA e pendencias futuras;
- obrigacoes da Data Intake Layer por data, role, canal, hub, sourceMode e status;
- roteamento de cada collector para endpoint modular, payload esperado, auditoria e readiness de automacao;
- leitura de missing today, ready to publish snapshot e approved audited;
- estado ativo da projecao, baseline stale e fila logica de reforecast;
- trilha de auditoria operacional.

Os nomes `bi_manual_*` permanecem como aliases legados de compatibilidade. A semantica oficial e Data Intake. Os datasets `bi_data_intake_*` sao os nomes canonicos para routing, mapa de endpoint e readiness de automacao.

### Operational Nervous System

- `bi_operational_exception_hub_dataset`
- `bi_operational_exception_graph_dataset`
- `bi_exception_root_cause_unified_dataset`
- `bi_exception_resolution_sla_unified_dataset`
- `bi_exception_projection_impact_dataset`
- `bi_integration_readiness_lock_dataset`
- `bi_integration_provider_capabilities_dataset`
- `bi_integration_readiness_checks_dataset`
- `bi_integration_exception_mapping_dataset`
- `bi_automation_orchestration_readiness_dataset`
- `bi_bling_live_probe_dataset`
- `bi_bling_fetch_preview_dataset`
- `bi_bling_import_plan_dataset`
- `bi_bling_reconciliation_dataset`
- `bi_bling_webhook_events_dataset`
- `bi_bling_mapping_gaps_dataset`
- `bi_bling_error_mapping_dataset`
- `bi_roadmap_blocker_dataset`
- `bi_erp_operational_debt_dataset`

Uso:

- fila unificada de excecoes operacionais;
- dedupe e links entre Data Intake, ERP, Commerce, approvals, bottlenecks, stale reforecast e integracoes;
- causa raiz provavel;
- impacto em cliente, estoque, BI, auditoria e projecao;
- SLA/TMA de resolucao por role, hub, SKU, pedido, customer hash e canal;
- base RAI-ready para explicar por que uma operacao exigiu acao.
- prontidao de Bling, Frenet, Loggi, n8n, ecommerce real e payment gateway antes de qualquer runtime externo real.
- gate Bling real: probe, preview, webhook trace, mapping, reconciliation e erros sem expor credenciais ou promover estoque Bling a canonico.
- registro oficial de divida/bloqueio de roadmap por origem, urgencia, owner, macro bloqueada e status.

### Operacao, Estoque, Commerce, Frete E Logistica

- `bi_operational_nodes_dataset`
- `bi_products_dataset`
- `bi_inventory_availability_dataset`
- `bi_commerce_orders_dataset`
- `bi_commerce_order_items_dataset`
- `bi_commerce_behavior_events_dataset`
- `bi_commerce_exception_cases_dataset`
- `bi_payment_failure_trace_dataset`
- `bi_checkout_friction_dataset`
- `bi_customer_behavior_trace_dataset`
- `bi_commerce_erp_exception_join_dataset`
- `bi_freight_economics_dataset`
- `bi_fulfillment_options_dataset`
- `bi_logistics_shipments_dataset`
- `bi_logistics_events_dataset`
- `bi_cdd_own_stock_dataset` (planned)
- `bi_cdd_replenishment_capacity_dataset` (planned)
- `bi_online_publishable_stock_policy_dataset` (planned)
- `bi_purchase_receipt_distribution_dataset` (planned)
- `bi_inbound_distribution_gap_dataset` (planned)
- `bi_supplier_inbound_allocation_dataset` (planned)
- `bi_distribution_accounting_dataset` (planned)
- `bi_distribution_valuation_dataset` (planned)
- `bi_fiscal_document_request_dataset` (planned)
- `bi_nfe_requirement_dataset` (planned)
- `bi_hub_distributed_value_dataset` (planned)
- `bi_franchisee_fiscal_flow_dataset` (planned)
- `bi_inventory_cost_flow_dataset` (planned)
- `bi_expected_margin_by_destination_dataset` (planned)

## Materialization Decision

Na v1 atual, os datasets BI continuam como views live. Materialized views ficam adiadas para o macro `BI/Superset Semantic Foundation`.

A decisao futura sera por dataset, considerando:

- volume;
- latencia;
- frequencia de escrita;
- custo de query;
- SLA de freshness;
- sensibilidade;
- estrategia de refresh.

Nao existe threshold automatico oficial para materializacao nesta etapa.

Uso:

- unidades e hubs;
- produtos/SKUs;
- estoque por unidade;
- pedidos;
- itens;
- frete como percentual do pedido;
- fulfillment;
- etiquetas, postagens, entregas e eventos logisticos.
- CDD own stock separado de capacidade de reposicao dos hubs.
- distribuicao de entrada de fornecedor por SKU, destino, ownership e status.
- classificacao fiscal/contabil futura de distribuicoes, transfers, NF-e requirement e margem gerencial.

### IA, RAI E Relatorios Inteligentes

- `bi_ai_agent_runs_dataset`
- `bi_rai_traces_dataset`
- `bi_rai_trace_steps_dataset`
- `bi_rai_training_examples_dataset`

Uso:

- runs de agentes;
- caminho cognitivo rastreavel;
- passos de decisao;
- elegibilidade para fine-tuning;
- relatorios gerados por IA;
- auditoria de recomendacoes.

## Roadmap De Evolucao

1. Views SQL controladas.
2. Catalogo de datasets certificados no Superset.
3. Dashboards oficiais por dominio.
4. Explorar e salvar graficos/tabelas customizados.
5. Relatorios periodicos com datasets certificados.
6. IA da DGE consumindo datasets semanticamente controlados.
7. Materialized views para performance quando volume justificar.
8. Row-level security e policy por tenant/unidade/cargo.

## Superset Integration Contract v1

Fonte do catalogo:

- `dge-2.0/server/modules/bi/biDatasetCatalog.js`

Contrato:

- `dge-2.0/server/contracts/biDataset.contract.js`

Validacao:

- `npm run smoke:bi-datasets`

O catalogo define para cada dataset:

- `viewName`;
- `title`;
- `domain`;
- `owner`;
- `description`;
- `grain`;
- `primaryTimeColumn`;
- `metrics`;
- `dimensions`;
- `recommendedFilters`;
- `certified`;
- `audience`;
- `dashboardFamilies`;
- `aiReadable`;
- `refreshPolicy`;
- `securityPolicy`.

### Dashboards Iniciais Recomendados

1. `Executive Overview`
2. `Projection Explorer`
3. `Reforecast Control`
4. `Operation Bottlenecks`
5. `Commerce & Freight`
6. `Inventory & Fulfillment`
7. `AI/RAI Observability`

### Politica De Uso Pela IA

A IA da DGE pode usar datasets certificados como fonte analitica, desde que:

- o dataset esteja no catalogo;
- `aiReadable = true`;
- o acesso respeite tenant/project;
- campos sensiveis sejam filtrados pela camada de orchestration futura;
- a resposta cite dataset/view utilizada;
- traces RAI registrem o caminho cognitivo e fontes consultadas.

### Politica De Refresh

No v1, as views operam em `view_live_query`.

A materializacao nao acontece automaticamente por threshold no v1. A decisao foi adiada para `BI/Superset Semantic Foundation`.

Nesse macro futuro, cada dataset sera avaliado por volume, latencia, frequencia de escrita, custo da query, SLA de freshness, sensibilidade e estrategia de refresh. Quando fizer sentido, ele podera migrar para materialized view ou tabela analitica mantendo o mesmo contrato semantico.

### RLS E Seguranca

Toda view BI deve preservar:

- `tenant_id`;
- `project_id`.

Datasets com unidade/hub devem preservar tambem chaves como:

- `node_id`;
- `node_key`;
- `scope_type`;
- `scope_key`.

No v1, a policy fica declarada no catalogo. A aplicacao real de RLS por Superset/Postgres fica para a etapa de seguranca e orchestration.

## Limites Do v1

- views ainda nao substituem uma camada OLAP completa;
- algumas colunas JSON permanecem semi-estruturadas;
- RAI/AI datasets podem ficar vazios ate agentes reais rodarem;
- Superset deve ser configurado depois, apontando para essas views;
- permissoes finas por tenant/unidade/cargo ficam para etapa de seguranca e orchestration.
