---
title: DGE fonte - DGE 2.0 Fulfillment Control Tower
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-fulfillment-control-tower.md.'
source_path: docs/architecture/dge-2.0-fulfillment-control-tower.md
---

# DGE 2.0 Fulfillment Control Tower

Fonte original DGE 2.0: `docs/architecture/dge-2.0-fulfillment-control-tower.md`.

---

# DGE 2.0 Fulfillment Control Tower

## Purpose

The Fulfillment Control Tower is the DGE layer that audits and explains how orders can be fulfilled across hubs, stores, pickup, Loggi, Frenet, and future internal transfers.

It is not the ecommerce checkout runtime.

## Current Backend Scope

Implemented endpoints:

```txt
POST /api/fulfillment/analyze-order
GET /api/fulfillment/analyses
GET /api/fulfillment/kpis
POST /api/fulfillment/kpis/publish-daily-snapshot
POST /api/kpis/bottlenecks/fulfillment/run
```

Implemented tables:

```txt
fulfillment_analyses
fulfillment_options
fulfillment_option_items
```

## Non-Runtime Guarantees

Every analysis must preserve:

```txt
checkoutRuntime=false
stockReservationAttempted=false
officialProjectionMutation=false
```

This means DGE analyzes and recommends. It does not block checkout, reserve stock, issue labels, or mutate ecommerce rules in this phase.

## Fulfillment States

Official v1 states:

```txt
single_hub_fulfillable
decentralized_order_stock
multi_hub_split_required
internal_transfer_recommended
partial_stock_available
unfulfillable
manual_review_required
```

## Analysis Logic V1

Input:

- commerce order;
- commerce order items;
- latest inventory availability by hub up to analysis date.

Logic:

1. Find hubs that can fulfill all order items.
2. If a single hub can fulfill all items, create `single_hub_fulfillable` option.
3. If no hub can fulfill all items but each item exists somewhere, mark `decentralized_order_stock`.
4. For decentralized stock, create:
   - `split_shipping` option;
   - `internal_transfer_then_shipping` option.
5. If some items are missing, create `partial_stock_available` or `unfulfillable`.
6. Persist analysis, options, item-level origin evidence, and timeline event.

## Why This Comes Before Frenet

Frenet and Loggi should receive freight/shipping context only after DGE can explain:

- which hub has stock;
- whether the order can leave from one hub;
- whether multiple labels may be needed;
- whether internal transfer may reduce external freight;
- whether human review is required.

## Cockpit Use

The future internal cockpit should expose:

- orders with decentralized stock;
- orders with single-hub fulfillment available;
- orders that may generate multiple labels;
- orders requiring internal transfer;
- partial/unfulfillable orders;
- manual review queue.

## KPI Layer

Current derived KPIs:

```txt
fulfillment_analysis_count
fulfillment_single_hub_fulfillable_count
fulfillment_decentralized_order_stock_count
fulfillment_internal_transfer_recommended_count
fulfillment_split_shipping_option_count
fulfillment_manual_review_required_count
fulfillment_unfulfillable_count
fulfillment_decentralized_order_stock_rate_percent
fulfillment_internal_transfer_rate_percent
```

These KPIs can be published as daily KPI snapshots without mutating checkout or official projections.

## Bottleneck Layer

Current signals:

```txt
fulfillment_decentralized_stock_pressure
fulfillment_internal_transfer_pressure
fulfillment_split_shipping_pressure
fulfillment_manual_review_queue
```

The detector supports:

```txt
daily
weekly
monthly
```

## Smoke

```txt
npm run smoke:fulfillment-analysis
npm run smoke:fulfillment-kpis
```
