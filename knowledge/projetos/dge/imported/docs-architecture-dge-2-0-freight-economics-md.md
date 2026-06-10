---
title: DGE fonte - DGE 2.0 Freight Economics
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-freight-economics.md.'
source_path: docs/architecture/dge-2.0-freight-economics.md
---

# DGE 2.0 Freight Economics

Fonte original DGE 2.0: `docs/architecture/dge-2.0-freight-economics.md`.

---

# DGE 2.0 Freight Economics

## Purpose

Freight Economics turns the DGE 1 freight percentage converter into a canonical, auditable backend layer.

It does not issue labels, reserve stock, or execute Frenet/Loggi.

## Endpoints

```txt
POST /api/logistics/freight-facts
GET /api/logistics/freight-kpis
POST /api/logistics/freight-kpis/publish-daily-snapshot
POST /api/kpis/bottlenecks/freight/run
```

## Canonical Facts

`freight_economic_facts` stores one economic freight fact per order/provider/method.

Important fields:

```txt
quoted_amount
charged_to_customer_amount
paid_to_carrier_amount
subsidy_amount
quote_vs_paid_delta_amount
order_gross_amount
order_net_amount
freight_paid_percent_of_order_net
freight_charged_percent_of_order_net
freight_paid_percent_of_order_gross
free_shipping
```

## Formula Registry

Current formulas:

```txt
freight_subsidy_amount = paid_to_carrier_amount - charged_to_customer_amount
freight_paid_percent_of_order_net = paid_to_carrier_amount / order_net_amount * 100
freight_charged_percent_of_order_net = charged_to_customer_amount / order_net_amount * 100
freight_paid_percent_of_order_gross = paid_to_carrier_amount / order_gross_amount * 100
quote_vs_paid_delta_amount = paid_to_carrier_amount - quoted_amount
freight_paid_percent_of_global_gmv = total_paid_to_carrier / total_net_gmv * 100
freight_charged_percent_of_global_gmv = total_charged_to_customer / total_net_gmv * 100
```

## Derived KPIs

```txt
freight_fact_count
freight_total_paid_to_carrier
freight_total_charged_to_customer
freight_total_subsidy_amount
freight_total_quote_vs_paid_delta
freight_paid_percent_of_global_gmv
freight_charged_percent_of_global_gmv
freight_avg_paid_percent_of_order_net
freight_avg_charged_percent_of_order_net
freight_free_shipping_order_count
```

## Boundary

This layer is economic intelligence only.

It must preserve:

```txt
officialProjectionMutation=false
```

Frenet, Loggi, labels, delivery events, pickup events, and reverse logistics should be built as later operational fact layers.

## Bottleneck Detection

Current signals:

```txt
freight_burden_high
freight_subsidy_high
freight_order_percent_high
freight_quote_paid_delta_high
free_shipping_pressure
```

The detector reads daily KPI snapshots and supports:

```txt
daily
weekly
monthly
```

## Smoke

```txt
npm run smoke:freight-economics
npm run smoke:freight-bottlenecks
```
