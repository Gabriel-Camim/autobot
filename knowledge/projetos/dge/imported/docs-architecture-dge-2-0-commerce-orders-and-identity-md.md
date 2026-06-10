---
title: DGE fonte - DGE 2.0 Commerce Orders And Customer Identity
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-commerce-orders-and-identity.md.'
source_path: docs/architecture/dge-2.0-commerce-orders-and-identity.md
---

# DGE 2.0 Commerce Orders And Customer Identity

Fonte original DGE 2.0: `docs/architecture/dge-2.0-commerce-orders-and-identity.md`.

---

# DGE 2.0 Commerce Orders And Customer Identity

## Purpose

This document freezes the decision that the former `commerce_orders_minimal` skeleton is now an active commerce intelligence layer with orders, operational events, minimal behavior trace and governed exceptions.

Orders without customer identity are not enough for DGE 2.0 because projections, own-channel migration, repeat purchase, LTV, cohorts, Bling sales import, and future ecommerce/app intelligence all depend on knowing when the same buyer appears again.

The decision is not to build a complete commerce user system now. The decision is to create enough canonical identity to avoid blind orders.

## Current Scope

Build now:

- `commerce_customers`;
- `commerce_orders`;
- `commerce_order_items`;
- `commerce_order_payments`.
- `commerce_operational_events` for non-behavioral operational lifecycle facts.
- `commerce_behavior_events` as a minimal pseudonymous behavior trace, not a full CDP.
- `commerce_exception_resolutions` for governed commerce exception closure.

Current backend endpoints:

```txt
POST /api/commerce/customers
POST /api/commerce/orders
GET /api/commerce/orders
POST /api/commerce/orders/:id/events
GET /api/commerce/operational-events
POST /api/commerce/behavior-events
GET /api/commerce/behavior-events
GET /api/commerce/exceptions
POST /api/commerce/exceptions/:id/resolve
GET /api/commerce/order-kpis
POST /api/commerce/order-kpis/publish-daily-snapshot
GET /api/commerce/operational-kpis
POST /api/commerce/operational-kpis/publish-daily-snapshot
POST /api/kpis/bottlenecks/commerce/run
POST /api/kpis/bottlenecks/commerce-operational/run
```

Do not build now:

- sessions;
- device tracking;
- product views;
- full app behavior;
- complete funnel analytics;
- campaign journey;
- full CDP-style customer profile.

Those remain future layers. The current behavior trace is intentionally minimal and pseudonymous.

## Customer Identity Minimal

`commerce_customers` should support:

- `customer_hash` as the primary durable matching handle when raw identity should not be stored;
- `source` such as `bling`, `ecommerce`, `app`, `marketplace`, or `manual`;
- `acquisition_channel`;
- `first_order_date`;
- `last_order_date`;
- `order_count`;
- `related_node_id` when the customer is clearly tied to a unit, store, franchise, or operational node;
- `status` such as `new`, `returning`, `inactive`, or `vip_candidate`;
- `metadata` for provider ids and future enrichment.

Raw PII should not become a required DGE fact. If a future implementation stores personal data, it must be explicit, justified, and governed.

## Order Minimal

`commerce_orders` should support:

- provider and channel;
- provider order id;
- order number;
- order date;
- status;
- payment status;
- node id when available;
- `customer_id` when matched;
- `customer_hash` when only pseudonymous matching exists;
- gross amount;
- discount amount;
- shipping amount;
- net amount;
- currency;
- source;
- automation level;
- metadata.

Orders should be importable even when customer matching is incomplete, but the normalizer should always attempt to resolve or create a minimal customer identity.

## Items And Payments

`commerce_order_items` should connect order demand to product/SKU intelligence:

- order id;
- product id when matched;
- sku;
- name;
- quantity;
- unit price;
- discount amount;
- total amount;
- metadata.

`commerce_order_payments` should remain minimal:

- order id;
- provider payment id;
- method;
- status;
- amount;
- paid at;
- metadata.

## Operational Events

`commerce_operational_events` should explain the order lifecycle without becoming behavior tracking or checkout runtime:

- order received;
- payment pending, approved, or failed;
- invoice requested or issued;
- cancellation;
- refund requested or completed;
- fraud/manual review;
- customer service hold.

These events are append-only v1 facts. They can feed operational KPIs and daily snapshots, but they should not mutate official projections or perform transactional ecommerce actions.

## Minimal Behavior Trace

`commerce_behavior_events` records the minimum customer journey facts needed to explain ecommerce friction:

- checkout started;
- payment failed;
- payment approved;
- cart abandoned;
- order created;
- order cancelled;
- stock unavailable at checkout.

The trace may link `customer_hash`, `session_key`, `cart_key`, `order_key`, channel, provider, SKU and amount. It must not store raw PII. Payment failure automatically creates both an operational event and a behavior trace when a commerce order enters with `payment_status = failed` or a failed payment item.

## Commerce Exception Center

Commerce exceptions are generated from behavior events, payment/order mismatch and ERP-linked order failures:

- `payment_failure`;
- `checkout_friction`;
- `cart_abandonment`;
- `order_payment_mismatch`;
- `sku_mapping_failure`;
- `stock_unavailable`;
- `fulfillment_blocked`;
- `customer_identity_gap`.

Resolution is governed and safe. The DGE can acknowledge, mark future recovery need, link identity, retry ERP reconciliation, escalate or close without action. It does not retry payment, send email, create coupon, notify customer or mutate official projections.

Commerce exceptions also appear in the Operational Exception Hub:

```txt
GET /api/operations/exception-hub
GET /api/operations/exception-impact
```

The Commerce Exception Center remains the domain source of truth. The hub connects payment failures, checkout friction, ERP-linked SKU/stock issues, approvals, Data Intake failures and projection impact into a single operational queue.

## Why This Comes Before Frenet

Frenet needs order context to become meaningful.

Freight analysis depends on:

- order;
- items;
- destination;
- origin node;
- package profile;
- quoted freight;
- selected freight;
- realized freight;
- delivery status.

Without canonical commerce orders, logistics would become a detached shipment table and would be harder to audit.

## Future Behavior Expansion

Commerce behavior is broader than the current backend phase.

Future versions can add richer events when ecommerce/app tracking is ready and the event registry is clear:

- product view;
- search;
- add to cart;
- purchase completed;
- app goal completed;
- campaign touch.

The current block only implements the minimal trace needed for exception intelligence.

## Projection Impact

This block unlocks future calculations for:

- GMV by channel;
- repeat purchase;
- average order value;
- customer order frequency;
- customer cohort;
- own-channel migration;
- LTV;
- CAC payback;
- lost GMV from stockout;
- freight friction impact.

Every future formula should use registered formula definitions and calculation traces before it becomes official.

## Current Implementation Status

```txt
Status: v1 implemented
Module registry queue: Active commerce layer
Smoke: npm run smoke:commerce-orders
Operational smoke: npm run smoke:commerce-operational
Operational detection smoke: npm run smoke:commerce-operational-bottlenecks
Post-import smoke: npm run smoke:bling-orders-post-import
Detection smoke: npm run smoke:commerce-bottlenecks
Behavior smoke: npm run smoke:commerce-behavior-events
Exception smoke: npm run smoke:commerce-exception-center
```
