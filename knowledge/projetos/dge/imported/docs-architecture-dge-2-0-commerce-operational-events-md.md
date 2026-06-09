---
title: DGE fonte - DGE 2.0 Commerce Operational Events
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-commerce-operational-events.md.'
source_path: docs/architecture/dge-2.0-commerce-operational-events.md
---

# DGE 2.0 Commerce Operational Events

Fonte original DGE 2.0: `docs/architecture/dge-2.0-commerce-operational-events.md`.

---

# DGE 2.0 Commerce Operational Events

## Purpose

`commerce_operational_events` records the operational lifecycle around a commerce order without turning DGE into the ecommerce runtime.

This layer explains what happened to the order after it became a canonical fact: payment, invoice, cancellation, refund, fraud review, manual review, and customer service hold.

It is intentionally different from behavior tracking. Product views, sessions, app events, carts, checkout funnel, and campaign journeys remain in `commerce_behavior_events` as blueprint expansion.

## Current Scope

Build now:

- append-only event facts tied to `commerce_orders`;
- operational event list;
- operational KPIs;
- optional daily KPI snapshot publication;
- timeline registration for audit.

Current backend endpoints:

```txt
POST /api/commerce/orders/:id/events
GET /api/commerce/operational-events
GET /api/commerce/operational-kpis
POST /api/commerce/operational-kpis/publish-daily-snapshot
POST /api/kpis/bottlenecks/commerce-operational/run
```

## Event Types

Official v1 event types:

- `order_received`;
- `payment_pending`;
- `payment_approved`;
- `payment_failed`;
- `invoice_requested`;
- `invoice_issued`;
- `order_cancelled`;
- `refund_requested`;
- `refund_completed`;
- `fraud_review_requested`;
- `manual_review_required`;
- `customer_service_hold`.

## Contract

Every event must carry:

- `order_id`;
- `event_type`;
- `event_status`;
- `occurred_at`;
- `source`;
- `provider`;
- optional `actor_user_key`;
- `metadata`.

The event is append-only in v1. It does not mutate checkout, reserve stock, create labels, or alter official projections.

## KPIs

Operational KPIs derived from the event table:

- event count;
- touched order count;
- order received count;
- payment approved count;
- payment failed count;
- invoice issued count;
- order cancelled count;
- refund requested count;
- refund completed count;
- manual review event count;
- payment failure rate;
- cancellation rate.

These KPIs can be published into daily KPI snapshots as modeled/system facts, still requiring governance when used as audited operational data.

## Bottleneck Detection

The operational detector runs on published daily KPI snapshots and supports `daily`, `weekly`, and `monthly` cadence.

Current signals:

- `commerce_payment_failure_pressure`;
- `commerce_cancellation_pressure`;
- `commerce_manual_review_queue`;
- `commerce_refund_pressure`;
- `commerce_invoice_gap`.

The detector does not read checkout state directly and does not mutate orders. It explains operational pressure from already-published KPI facts.

## Why This Exists

Commerce order tables say what the order is. Operational events explain the journey:

- payment friction;
- invoice delay;
- cancellation pressure;
- support holds;
- refund/reverse-flow pressure;
- fraud/manual-review workload.

This gives future bottleneck detection a clean signal without mixing operational incidents with customer behavior tracking.

## Current Implementation Status

```txt
Status: v1 implemented
Module registry queue: ABCDEF.B
Smoke: npm run smoke:commerce-operational
Bottleneck smoke: npm run smoke:commerce-operational-bottlenecks
```
