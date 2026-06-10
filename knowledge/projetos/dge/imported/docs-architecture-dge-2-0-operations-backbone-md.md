---
title: DGE fonte - DGE 2.0 Operations Backbone
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-operations-backbone.md.'
source_path: docs/architecture/dge-2.0-operations-backbone.md
---

# DGE 2.0 Operations Backbone

Fonte original DGE 2.0: `docs/architecture/dge-2.0-operations-backbone.md`.

---

# DGE 2.0 Operations Backbone

## Purpose

The Operations Backbone starts with products, operational nodes, and inventory availability.

The goal is not automatic replenishment yet. The goal is to make stock reality traceable enough to explain commercial and projection deviations.

## Active v1

```txt
products
operational_nodes
inventory_availability_snapshots
inventory_availability_items
```

## Endpoints

```txt
POST /api/operations/products
POST /api/operations/nodes
POST /api/operations/inventory-availability
GET /api/operations/inventory-availability/latest
GET /api/operations/inventory-kpis
POST /api/operations/inventory-kpis/publish-daily-snapshot
```

## What It Answers

- Which SKUs exist?
- Which operational nodes exist?
- Which node has inventory?
- Which SKUs are available, low stock, or stockout?
- Which stock signals can explain GMV, order, or conversion variance?

## Boundaries

Active now:

- product/SKU registry;
- store/franchise/DC/hub node registry;
- manual/imported inventory availability snapshots;
- stockout and low-stock summary per snapshot.
- derived inventory KPIs as read model.

Not active yet:

- replenishment automation;
- lot/expiry tracking;
- WMS integration;
- Frenet logistics tracking;
- ship-from-store allocation;
- GMV-at-risk calculation.

## Future KPI Derivations

```txt
stockout_rate_percent
available_sku_count
low_stock_sku_count
inventory_node_availability_percent
gmv_at_risk_by_stockout
stock_coverage_days
```

The first read model is active:

```txt
GET /api/operations/inventory-kpis
```

It derives stockout, low-stock, available SKU, total available quantity, and node-level summaries from inventory availability snapshots. It does not publish these values into `daily_kpi_snapshots` yet.

## Governed KPI Publication

Inventory KPIs can now be published into the official daily KPI layer:

```txt
POST /api/operations/inventory-kpis/publish-daily-snapshot
```

Guardrails:

- requires `confirmPublish=true`;
- uses source `system`;
- uses automation level `automated`;
- marks confidence as `modeled`;
- writes metadata with source inventory KPIs, node key, stockout SKUs, and low-stock SKUs;
- does not mutate official projections.

## Inventory Bottleneck Cadences

Inventory bottleneck detection supports three intelligence cadences:

```txt
daily
weekly
monthly
```

Execution target:

```txt
POST /api/kpis/bottlenecks/inventory/run
```

Payload examples:

```json
{ "cadence": "daily", "referenceDate": "2026-05-13" }
{ "cadence": "weekly", "referenceDate": "2026-05-13" }
{ "cadence": "monthly", "referenceDate": "2026-05-31" }
```

The endpoint creates `bottleneck_detection_runs` and a timeline event. It is designed to be called later by daily, weekly, and monthly cron jobs.

Monthly KPI trace closure also checks inventory KPIs when they are present in official daily KPI snapshots.

## Rule

Inventory availability is an operational fact source. It should feed KPI intelligence and adaptive projections, but it should not directly mutate financial projections.

## ERP Ecommerce-First Promotion

The DGE now has a dedicated ERP ecommerce-first backbone.

This changes the role of this module:

- `products` remains compatible as a legacy/simple product registry;
- `inventory_availability_snapshots` becomes an audited snapshot/read model;
- `inventory_availability_items` becomes a derived/imported availability picture;
- canonical inventory should be read from ERP ledger movements, reservations and balances when available.

Preferred ERP endpoints:

```txt
POST /api/erp/products
POST /api/erp/inventory/movements
GET /api/erp/inventory/balances
POST /api/erp/inventory/reservations
POST /api/erp/inventory/publish-daily-snapshot
```

## ERP Source / Bling

Bling is no longer the primary ERP source of truth. It is an auxiliary sales/invoice/import source.

It should feed:

- sales/order imports;
- invoice/fiscal metadata when available;
- operational node/deposit mapping;
- contingency inventory import only through audit/reconciliation.

Bling should write through integration runs and normalizers before reaching canonical DGE tables, and it must not overwrite ERP inventory balances silently.
