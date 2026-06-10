---
title: DGE fonte - DGE 2.0 Marketplace Fulfillment Pools
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-marketplace-fulfillment-pools.md.'
source_path: docs/architecture/dge-2.0-marketplace-fulfillment-pools.md
---

# DGE 2.0 Marketplace Fulfillment Pools

Fonte original DGE 2.0: `docs/architecture/dge-2.0-marketplace-fulfillment-pools.md`.

---

# DGE 2.0 Marketplace Fulfillment Pools

## Core Rule

Mercado Livre and Shopee are not physical inventory hubs.

They are sales channels/providers that generate demand. The DGE resolves that demand into a physical fulfillment location through a fulfillment pool before any ERP reservation or stock movement can happen.

Canonical flow:

1. Marketplace, PDV or ecommerce creates a sale.
2. DGE resolves provider and channel.
3. DGE resolves the fulfillment pool and its channel policy.
4. DGE allocates a physical hub/location, or the configured CDD when the pool requires it.
5. ERP creates reservation or stock movement on the physical location allowed by policy.
6. Exception Hub captures allocation, SKU mapping or stock failures.
7. Cockpit and BI expose operational impact.

## Boundaries

Physical stock lives only in:

- `erp_inventory_locations`
- `erp_inventory_balances`
- `erp_inventory_reservations`
- `erp_inventory_movements`

Marketplaces live as channels, mappings and allocation records:

- `commerce_orders`
- `sales_channels`
- `marketplace_listing_mappings`
- `fulfillment_pools`
- `fulfillment_pool_locations`
- `marketplace_order_allocations`
- `marketplace_inventory_publication_suggestions`

## Pool Capacity

Pool availability is calculated from eligible physical hubs:

```text
pool_available_qty =
  sum(available_qty from eligible physical hubs)
  - safety_buffer_qty
  - pending marketplace allocations
  - pending internal transfer pressure
```

V1 calculates capacity as a read model. It does not publish stock back to Mercado Livre or Shopee.

## Configurable CDD Policy

CDD-exclusive fulfillment is a Galpao policy, not a global DGE hardcode.

Pool policy controls this behavior:

- `cddExclusiveFulfillment`: online orders must ship from the configured distribution center.
- `allowDirectStoreShipment`: a tenant can later enable ship-from-store without changing the core.
- `allowInternalTransferToCdd`: missing CDD stock can create hub-to-CDD replenishment transfer plans.

When `cddExclusiveFulfillment=true`, pool locations represent replenishment sources for the CDD, not final online shipment origins. Brand-owned hubs are preferred, franchisee-owned hubs are last-resort sources and require reimbursement policy. When the flag is false, the same architecture can support regionalized fulfillment, pickup or hybrid operations.

CDD is always a physical ERP location with `locationType=distribution_center` and `onlineFulfillmentRole=primary_cdd`. Mercado Livre and Shopee never become `erp_inventory_location` rows.

## Allocation Status

Marketplace allocations use explicit operational states:

- `pending`
- `allocated`
- `reservation_created`
- `stock_deducted`
- `failed`
- `manual_review`
- `cancelled`
- `released`

The allocation layer separates marketplace sale intake from final stock mutation. Paid or confirmed marketplace orders can move to `stock_deducted`; otherwise the system can stop at reservation.

## Listing Mapping

Marketplace listing mapping does not assume SKU is always enough. The mapping supports:

- provider;
- channel;
- external listing id;
- external variation id;
- external SKU;
- internal SKU;
- ERP product variant;
- conversion factor;
- kit policy;
- status.

Missing or ambiguous mapping must create an exception instead of inventing stock behavior.

## Bling Boundary

Bling can provide orders, invoices, observed products and observed stock. It remains auxiliary.

Rules:

- Bling PDV sales must resolve a physical hub.
- Bling marketplace orders must go through fulfillment allocation.
- Bling observed stock is reconciliation evidence only.
- Bling does not overwrite DGE canonical stock.

## Data Intake Boundary

Data Intake remains the operational fallback and audit layer:

- daily inventory confirmation by hub;
- stock count and manual adjustment review;
- marketplace listing mapping review;
- fulfillment pool review;
- import fallback;
- divergence audit;
- exception resolution.

Marketplace daily facts are scheduled review or contingency once connectors/imports are active, not a broad daily manual obligation.
