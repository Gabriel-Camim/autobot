---
title: DGE fonte - DGE 2.0 - Inventory Capacity Reforecast Directive
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-inventory-capacity-reforecast-directive.md.'
source_path: docs/architecture/dge-2.0-inventory-capacity-reforecast-directive.md
---

# DGE 2.0 - Inventory Capacity Reforecast Directive

Fonte original DGE 2.0: `docs/architecture/dge-2.0-inventory-capacity-reforecast-directive.md`.

---

# DGE 2.0 - Inventory Capacity Reforecast Directive

## Diretriz

Restricao de estoque do ERP e uma causa projetiva oficial, nao apenas um alerta operacional.

Quando o ERP canonico da DGE indicar ruptura, baixo estoque, reserva excessiva, pedido sem reserva, SKU Bling desconhecido ou GMV em risco, a DGE pode abrir um case `inventory_product_capacity` e conduzir o mesmo fluxo governado dos demais reforecasts.

## Fluxo Oficial

```txt
ERP ledger/balances/reservations
-> erp.operational_context.v1
-> erp.bottleneck_signal.v1
-> reforecast case inventory_product_capacity
-> preview com projection.inventoryRuntime.v1
-> proposta formal
-> aprovacao oficial
-> projection_version filha
-> explainability v2
-> BI/Superset
```

## Guardrails

- `projection.inventoryRuntime.v1` usa capacidade agregada; SKU bruto nao entra no projection core.
- Bling e fonte auxiliar de venda/nota/importacao, nao source of truth de estoque.
- Compra, transferencia interna e ajuste manual continuam como acao operacional/ticket futuro, nao execucao automatica de reforecast.
- A baseline original deve ser preservada por parent lineage.
- Officializacao exige aprovacao alta (`owner`, `admin`, `tenant_owner`, `tenant_admin`) e acknowledgements completos.
- Cases de canal podem ser bloqueados por estoque quando a restricao ERP explica a variancia.

## BI Obrigatorio

- `bi_projection_inventory_runtime_dataset`
- `bi_inventory_reforecast_cases_dataset`
- `bi_official_inventory_reforecast_dataset`
- `bi_reforecast_evidence_ledger_dataset`
- `bi_official_reforecast_explainability_dataset`

## Smokes

- `smoke:inventory-reforecast-case-from-erp`
- `smoke:inventory-reforecast-preview`
- `smoke:official-inventory-reforecast`
- `smoke:official-inventory-reforecast-explainability`

## Estado

Este bloco fecha o ciclo ERP -> projection core -> official reforecast v1 para restricao agregada de estoque.

Ficam fora deste ciclo:

- reforecast detalhado por SKU/categoria/hub;
- WMS completo;
- compra automatica;
- transferencia automatica entre hubs;
- pricing/campaign mitigation com IA.
