---
title: DGE fonte - DGE 2.0 - ERP Intelligence Integration Backbone
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-erp-intelligence-integration-backbone.md.'
source_path: docs/architecture/dge-2.0-erp-intelligence-integration-backbone.md
---

# DGE 2.0 - ERP Intelligence Integration Backbone

Fonte original DGE 2.0: `docs/architecture/dge-2.0-erp-intelligence-integration-backbone.md`.

---

# DGE 2.0 - ERP Intelligence Integration Backbone

Este backbone conecta o ERP ecommerce-first da DGE aos consumidores inteligentes do sistema: KPIs, gargalos, cockpit, BI, projection core e reforecast dependency control.

## Decisao

- `erp_inventory_balances`, `erp_inventory_movements`, `erp_inventory_reservations` e `erp_stock_counts` sao a fonte operacional canonica de estoque.
- `inventory_availability_snapshots` continua como compatibilidade e fotografia auditavel, nao como origem primaria quando o ERP existe.
- Bling continua auxiliar para venda/nota/importacao assistida, sem sobrescrever estoque canonico.
- Projecoes recebem um resumo `projection.inventoryRuntime.v1`, nao linhas brutas de SKU.

## Interfaces

- `GET /api/erp/operational-context`
- `POST /api/kpis/erp/publish-daily-snapshot`
- `POST /api/kpis/bottlenecks/erp/run`
- `POST /api/projections/reforecast-cases/from-erp-bottleneck`
- `GET /api/operations/cockpit` com `erpDesk`

## Contratos

- `erp.operational_context.v1`
- `erp.kpi_derivation.v1`
- `erp.bottleneck_signal.v1`
- `projection.inventoryRuntime.v1`

## BI

- `bi_erp_operational_context_dataset`
- `bi_erp_inventory_kpi_daily_dataset`
- `bi_erp_bottleneck_signals_dataset`
- `bi_projection_inventory_runtime_dataset`
- `bi_erp_channel_capacity_dataset`
- `bi_inventory_reforecast_cases_dataset`
- `bi_official_inventory_reforecast_dataset`

## Reforecast

Evidencias ERP entram na classe `inventory_product_capacity`. Quando uma variancia de canal pode ser explicada por ruptura, baixo estoque ou GMV em risco, o case de canal pode ser bloqueado por dependencia ate o case de estoque ser resolvido.

### Inventory Capacity Reforecast v1

O ciclo ERP -> projecao -> reforecast esta governado:

```txt
erp.bottleneck_signal.v1
-> reforecast case inventory_product_capacity
-> preview com projection.inventoryRuntime.v1
-> proposta formal
-> aprovacao oficial
-> projection_version filha
-> explainability official.reforecast.explainability.v2
```

Guardrails:

- o projection core recebe capacidade agregada, nunca SKU bruto;
- Bling continua fonte auxiliar, nao source of truth de estoque;
- compra, transferencia e ajuste operacional viram tickets/futuro workflow, nao execucao automatica pelo reforecast;
- a baseline original permanece preservada;
- officializacao exige aprovacao owner/admin ou equivalente tenant.
