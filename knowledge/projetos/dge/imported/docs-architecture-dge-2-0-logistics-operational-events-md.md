---
title: DGE fonte - DGE 2.0 Logistics Operational Events
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-logistics-operational-events.md.'
source_path: docs/architecture/dge-2.0-logistics-operational-events.md
---

# DGE 2.0 Logistics Operational Events

Fonte original DGE 2.0: `docs/architecture/dge-2.0-logistics-operational-events.md`.

---

# DGE 2.0 Logistics Operational Events

## Purpose

This layer stores canonical operational logistics facts before real Frenet, Loggi, pickup, or reverse logistics adapters exist.

It does not issue labels or execute delivery. It records what happened.

## Endpoints

```txt
POST /api/logistics/shipments
GET /api/logistics/shipments
POST /api/logistics/shipments/:id/events
POST /api/logistics/labels
POST /api/logistics/returns
GET /api/logistics/operational-kpis
```

## Tables

```txt
logistics_shipments
logistics_shipment_events
logistics_labels
logistics_returns
```

## Event Types

```txt
order_created
invoice_issued
label_requested
label_issued
picking_started
picked
packed
posted
in_transit
delivered
delivery_failed
cancelled
return_requested
reverse_logistics_requested
returned
```

## Boundary

DGE records operational logistics memory.

DGE does not:

- issue labels as source of truth;
- reserve stock;
- block checkout;
- notify customers as the primary channel;
- execute Frenet or Loggi.

Frenet, Loggi, pickup, and reverse logistics adapters should write into these canonical tables.

## Commerce Operational Events

After this logistics layer, a separate Commerce Operational Events v1 is recommended.

That layer should track commercial lifecycle facts such as:

- order received;
- payment approved;
- payment failed;
- order cancelled;
- invoice requested;
- invoice issued;
- refund requested;
- refund completed;
- customer service hold;
- fraud/manual review.

It should not be confused with behavior tracking such as product views, sessions, add to cart, or app events.

## Smoke

```txt
npm run smoke:logistics-operational
```
