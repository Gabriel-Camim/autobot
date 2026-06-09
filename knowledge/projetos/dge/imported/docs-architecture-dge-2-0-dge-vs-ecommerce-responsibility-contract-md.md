---
title: DGE fonte - DGE 2.0 vs Ecommerce Responsibility Contract
category: projetos
tags:
- dge
- fonte-original
- arquitetura
- contratos
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-dge-vs-ecommerce-responsibility-contract.md.'
source_path: docs/architecture/dge-2.0-dge-vs-ecommerce-responsibility-contract.md
---

# DGE 2.0 vs Ecommerce Responsibility Contract

Fonte original DGE 2.0: `docs/architecture/dge-2.0-dge-vs-ecommerce-responsibility-contract.md`.

---

# DGE 2.0 vs Ecommerce Responsibility Contract

## Purpose

This contract prevents DGE 2.0 from becoming a checkout, ecommerce runtime, WMS, TMS, or label issuing system by accident.

DGE 2.0 is the operational intelligence, audit, governance, and control tower layer.

The ecommerce is the transactional buying experience and customer-facing runtime.

## Core Rule

```txt
Ecommerce executes the customer promise.
DGE audits, learns, recommends, governs, and explains the operation.
```

## Ecommerce Responsibilities

The ecommerce owns the real-time customer journey:

- storefront;
- product browsing;
- customer login;
- cart;
- checkout;
- customer-facing freight quotes;
- customer-facing store pickup options;
- payment;
- order creation;
- order confirmation;
- customer-facing order status;
- customer notifications;
- checkout-time stock promise;
- runtime rules required to complete the sale.

The ecommerce can use approved DGE recommendations in future phases, but it should not depend on DGE as the first-phase blocking runtime for checkout.

## DGE Responsibilities

DGE owns operational intelligence and internal governance:

- ingest commerce orders, items, payments, customers, inventory, freight, pickup, and delivery events;
- audit whether ecommerce, Bling, Frenet, Loggi, stores, and hubs produced consistent facts;
- calculate freight percent per order;
- calculate freight percent over global GMV;
- detect freight subsidy, leakage, split shipment pressure, and decentralized stock bottlenecks;
- recommend origin hub, pickup availability policy, freight rules, and operational review actions;
- register internal cockpit queues for logistics and stock teams;
- preserve timeline events and approval traces;
- generate daily, weekly, and monthly operational reports;
- feed KPI intelligence, projections, and RAI agents with traceable facts.

DGE should not silently mutate ecommerce rules or official projections.

## Reforecast And Future Mitigation Boundary

Reforecast belongs to DGE as governance and projection versioning.

Operational mitigation with product pricing, SKU-specific recommendations, category strategy, coupons, ecommerce behavior, product margin, or social action should not be implemented as a standalone DGE module before ecommerce, ERP, stock, margin, and behavior context exist.

Current DGE scope:

- detect projected vs actual variance;
- classify materiality;
- attribute probable cause;
- open reforecast cases;
- store future mitigation readiness;
- identify missing contexts;
- govern forecast/reforecast decisions.

Future integrated scope:

- AI may suggest pricing, product mix, inventory, freight, marketing, coupon, or social-action strategies only when real ecommerce, ERP, product, stock, margin, coupon, and behavior context is available.

Executive rule:

```txt
social_action mitigation scope is restricted to executive, owner, admin, or equivalent high-authority tenant roles.
```

Detailed blueprint:

```txt
dge-2.0/docs/architecture/dge-2.0-forecast-reconciliation-and-reforecast-readiness-blueprint.md
```

## Integration Boundary

Phase 1:

```txt
Ecommerce/Bling/Frenet/Loggi execute.
DGE receives facts and audits.
```

Phase 2:

```txt
DGE generates recommendations and rulesets.
Humans approve.
Ecommerce can optionally consume approved recommendations.
```

Phase 3:

```txt
Ecommerce uses approved DGE rulesets as decision support.
Ecommerce remains the transactional runtime.
DGE remains the control tower and audit memory.
```

## Fulfillment Control Tower Scope

DGE may model fulfillment options, but this is analysis and cockpit intelligence unless a later approved phase explicitly promotes it to runtime integration.

Allowed DGE facts:

- `fulfillment_analysis`;
- `fulfillment_recommendations`;
- `fulfillment_exceptions`;
- `shipping_cost_analysis`;
- `pickup_operational_status`;
- `shipment_events`;
- `label_events`;
- `return_events`;
- `internal_transfer_recommendations`.

Not first-phase DGE responsibilities:

- reserve stock during checkout;
- block checkout;
- create cart promises;
- charge payment;
- issue invoice as source of truth;
- issue label as the operational source of truth;
- notify customer as the primary channel;
- decide in real time what the customer can buy.

## Hubs And Decentralized Stock

DGE should detect and explain hub-level stock behavior:

- which hubs had the ordered SKUs;
- whether a single hub could fulfill all order items;
- whether stock was decentralized across hubs;
- whether split shipping would create multiple labels;
- whether internal transfer would reduce customer-facing freight cost;
- whether the case requires human review.

Official states:

```txt
single_hub_fulfillable
decentralized_order_stock
multi_hub_split_required
internal_transfer_recommended
partial_stock_available
unfulfillable
manual_review_required
```

These states are operational intelligence states. They do not automatically rewrite ecommerce checkout logic.

## Delivery Methods

DGE should track and compare all delivery methods as facts:

```txt
carrier_shipping
local_delivery
store_pickup
split_shipping
internal_transfer_then_shipping
manual_review
```

Providers:

```txt
frenet
loggi
store_pickup
internal_transfer
manual
```

## Store Pickup

The ecommerce owns the customer-facing pickup option.

DGE audits pickup operations:

- pickup hub/store;
- pickup window;
- picking status;
- ready for pickup status;
- pickup deadline;
- pickup confirmation;
- expiration;
- cancellation;
- no-show;
- operational exceptions.

Relevant events:

```txt
pickup_ready
picked_up
pickup_expired
pickup_cancelled
pickup_failed_stock_location
```

## Loggi

The ecommerce/logistics stack owns the operational Loggi execution.

DGE tracks and analyzes:

- local delivery quote;
- selected delivery method;
- pickup scheduled;
- collected;
- in transit;
- delivered;
- delivery failed;
- cancelled;
- cost vs order;
- cost vs global GMV;
- SLA promised vs realized.

## Frenet

Frenet should enter DGE as freight/logistics facts:

- quoted freight;
- selected freight;
- label event;
- carrier;
- promised SLA;
- realized SLA;
- tracking status;
- freight paid to carrier;
- freight charged to customer;
- subsidy;
- difference between quoted and realized freight.

## Cockpit Principle

The future cockpit is internal and operational.

It should help stock/logistics teams answer:

- Which orders need origin review?
- Which orders have decentralized stock?
- Which orders may create multiple labels?
- Which pickup orders are waiting for separation?
- Which labels are missing?
- Which orders are late?
- Which returns/reverse logistics cases are open?
- Which hubs are creating cost, SLA, or stock bottlenecks?

## Non-Negotiable Boundary

No DGE module should be named or designed as if it owns checkout execution unless the architecture is explicitly revised.

Preferred naming:

```txt
Fulfillment Control Tower
Fulfillment Intelligence
Logistics Intelligence
Operational Cockpit
```

Avoid first-phase naming:

```txt
Checkout Engine
Fulfillment Runtime
Shipping Execution Engine
Stock Reservation Engine
```
