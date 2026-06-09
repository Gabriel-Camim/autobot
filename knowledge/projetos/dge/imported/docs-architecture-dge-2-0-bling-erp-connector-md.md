---
title: DGE fonte - DGE 2.0 Bling ERP Connector
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-bling-erp-connector.md.'
source_path: docs/architecture/dge-2.0-bling-erp-connector.md
---

# DGE 2.0 Bling ERP Connector

Fonte original DGE 2.0: `docs/architecture/dge-2.0-bling-erp-connector.md`.

---

# DGE 2.0 Bling ERP Connector

## Purpose

Bling should be treated as an ERP operational source, not as a KPI engine.

The DGE must ingest operational facts from Bling, normalize them, and then derive KPIs internally.

## Status

```txt
module_status: active
maturity: v1_5_live_gate
```

Bling now has a governed live gate. Real API calls are still opt-in and read-only by default.

The Integration Readiness Lock is active:

```txt
GET /api/integrations/readiness-lock/bling
POST /api/integrations/readiness-lock/bling/check
POST /api/integrations/readiness-lock/bling/dry-run
POST /api/integrations/readiness-lock/bling/live-probe
```

Bling can be `assisted_import_ready` for local dry-run/import flows and `live_api_probe_ready` after a successful read-only probe. It must not be considered `production_ready` until fetch preview, assisted import, idempotency, rollback, Exception Hub mapping, Data Intake fallback, BI and owner/admin gates are green.

## Target Flow

```txt
Bling API/Webhook
  -> live probe
  -> fetch preview
  -> normalizer
  -> dry-run
  -> assisted import
  -> reconciliation
  -> Exception Hub
  -> Cockpit/BI
  -> Data Intake fallback
```

## Active Preparation

The system now has:

```txt
external_integration_runs
integration_readiness_checks
bling_fetch_previews
bling_integration_mappings
automation_webhook_events
```

Active endpoints:

```txt
POST /api/integrations/runs
GET /api/integrations/runs
POST /api/integrations/bling/orders/fetch-preview
POST /api/integrations/bling/inventory/fetch-preview
POST /api/integrations/bling/invoices/fetch-preview
POST /api/integrations/bling/webhooks
GET /api/integrations/bling/mappings
POST /api/integrations/bling/mappings
```

Fetch-preview endpoints only call Bling when explicitly allowed. Otherwise they operate on assisted payloads and persist preview traces without canonical writes.

## Bling Responsibilities

Expected import operations:

- products;
- inventory by SKU;
- deposits/stores/unit mapping;
- sales;
- orders;
- customers when legally appropriate;
- invoices/status as fiscal-operational context;
- webhooks as trace/import suggestion, not automatic import.

## Destination Tables

Inventory:

```txt
products
operational_nodes
inventory_availability_snapshots
inventory_availability_items
```

Sales/orders:

```txt
commerce_orders or erp_sales_orders
commerce_order_items or erp_sales_order_items
commerce_payments or erp_payment_facts
```

Readiness/preview:

```txt
integration_readiness_checks
bling_fetch_previews
bling_integration_mappings
automation_webhook_events
```

## Guardrails

- Bling payloads should be preserved in metadata only when safe.
- Bling facts should not directly overwrite official KPIs.
- Duplicate order risk must be handled before Bling and ecommerce integrations are both active.
- Deposits and stores from Bling must map into `operational_nodes`.
- Daily snapshots are DGE canonical records; Bling is one source.
- Bling inventory is observed evidence/reconciliation, not canonical ERP balance.
- Orders are prioritized before inventory.
- Webhooks never import automatically in v1.5.

## Still Not Active

- OAuth callback/refresh automation;
- write-back to Bling;
- automatic import from webhook;
- production-ready promotion;
- Bling as stock source of truth.

## Readiness Guardrail

Bling remains an auxiliary source for sales, invoices and assisted imports.

It must not:

- overwrite DGE canonical stock;
- bypass Data Intake or governed import endpoints;
- hide unknown SKU conflicts;
- create production automation without readiness checks;
- store raw credentials in readiness history.
