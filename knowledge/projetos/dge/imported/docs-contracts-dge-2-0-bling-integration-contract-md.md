---
title: DGE fonte - DGE 2.0 Bling Integration Contract
category: projetos
tags:
- dge
- fonte-original
- contratos
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/contracts/dge-2.0-bling-integration-contract.md.'
source_path: docs/contracts/dge-2.0-bling-integration-contract.md
---

# DGE 2.0 Bling Integration Contract

Fonte original DGE 2.0: `docs/contracts/dge-2.0-bling-integration-contract.md`.

---

# DGE 2.0 Bling Integration Contract

## Purpose

This contract defines how Bling data should enter the DGE without becoming a parallel source of truth.

Bling is now an auxiliary ERP/sales provider for DGE 2.0. The DGE ERP is the source of truth for catalog and inventory; Bling payloads are raw operational input that must be normalized into canonical DGE facts and reconciliation/audit flows.

## Integration Flow

```txt
Bling raw payload
  -> automation_webhook_events
  -> automation_runs
  -> automation_run_steps
  -> canonical DGE write endpoint
  -> approval request
  -> obligations, audit, exceptions, reports
```

## Automation Keys

Current automation registry keys:

```txt
bling_inventory_daily_import
bling_sales_daily_import
```

Expected executor:

```txt
system_automation_n8n
```

## Product Contract

Canonical endpoint:

```txt
POST /api/operations/products
```

Bling product fields should normalize into:

```txt
sku
name
category
brand
status
metadata.blingProductId
metadata.blingRawStatus
metadata.blingUpdatedAt
```

Example canonical payload:

```json
{
  "sku": "SKU-001",
  "name": "Produto exemplo",
  "category": "Camisetas",
  "brand": "Marca",
  "status": "active",
  "metadata": {
    "blingProductId": "123456",
    "blingRawStatus": "A",
    "blingUpdatedAt": "2026-05-14T10:00:00.000Z"
  }
}
```

Idempotency:

```txt
project_id + sku
metadata.blingProductId should remain stable for traceability
```

## Inventory Contract

Canonical endpoints:

```txt
POST /api/operations/inventory-availability
POST /api/integrations/runs
POST /api/automations/runs
POST /api/automations/runs/:id/steps
```

Bling warehouse/deposit must map to a DGE operational node or ERP inventory location:

```txt
blingWarehouseId -> operational_nodes.key or metadata mapping
```

Preferred canonical scope:

```json
{
  "nodeKey": "store-sp"
}
```

Canonical inventory payload:

```json
{
  "nodeKey": "store-sp",
  "snapshotDate": "2026-05-14",
  "source": "erp",
  "automationLevel": "automated",
  "approvalWorkflowKey": "inventory_snapshot_approval",
  "submittedBy": "system_automation_n8n",
  "items": [
    {
      "sku": "SKU-001",
      "onHandQty": 20,
      "reservedQty": 3,
      "availableQty": 17,
      "safetyStockQty": 5,
      "unitCost": 25.5,
      "metadata": {
        "blingProductId": "123456",
        "blingWarehouseId": "987",
        "rawAvailableQty": 17
      }
    }
  ],
  "metadata": {
    "provider": "bling",
    "operation": "inventory",
    "blingWarehouseId": "987"
  }
}
```

Availability status:

```txt
available -> availableQty above safety stock
low_stock -> availableQty above zero and below or equal safety stock
stockout -> availableQty less than or equal to zero
unknown -> payload insufficient
```

Inventory import run:

```json
{
  "provider": "bling",
  "operation": "inventory",
  "status": "confirmed",
  "source": "api",
  "recordsReceived": 100,
  "recordsNormalized": 98,
  "recordsFailed": 2,
  "submittedBy": "system_automation_n8n",
  "approvalWorkflowKey": "erp_import_audit",
  "metadata": {
    "nodeKey": "store-sp",
    "blingWarehouseId": "987",
    "automationKey": "bling_inventory_daily_import"
  }
}
```

Idempotency:

```txt
inventory snapshot: project_id + node_id + snapshot_date + source
webhook event: project_id + provider + payload_hash
integration run: trace each execution, do not use as canonical idempotency key
```

## Sales And Orders

Sales/orders are active canonical commerce facts and may trigger ERP reconciliation. They should not overwrite ERP inventory balances directly.

Future canonical entities:

```txt
commerce_customers
commerce_orders
commerce_order_items
commerce_payments
```

Expected normalized fields:

```txt
blingOrderId
orderNumber
orderDate
channel
nodeKey
customerHash
customerSource
customerAcquisitionChannel
grossAmount
discountAmount
shippingAmount
netAmount
status
paymentStatus
items[].sku
items[].quantity
items[].unitPrice
items[].discountAmount
```

Temporary registration before commerce tables exist:

```txt
POST /api/integrations/runs
provider=bling
operation=sales or orders
metadata.rawSummary
```

Treat sales import as auxiliary commerce input. The import can feed `commerce_orders`, but ERP stock effects must flow through reservations/movements and reconciliation, not direct inventory overwrite.

Customer identity rule:

```txt
Bling sales/order normalization should attempt to resolve or create commerce_customers before writing commerce_orders.
Orders may still be stored with customer_hash when customer matching is incomplete.
Raw personal data should not be required for canonical DGE facts.
```

## Orders Dry-Run And Import

Endpoints:

```txt
POST /api/integrations/bling/orders/normalize
POST /api/integrations/bling/orders/dry-run
POST /api/integrations/bling/orders/import
POST /api/integrations/bling/orders/post-import-actions
```

Purpose:

```txt
Normalize Bling sales/orders into canonical commerce customers, orders, items, and payments.
```

Rules:

```txt
dry-run always runs before import
confirmImport=true is required for persistence
orders persist through POST /api/commerce/orders service
customer identity is resolved or created through commerce order persistence
ERP reconciliation attempts to reserve/release/sell by SKU and hub when the SKU exists in the DGE ERP
unknown SKU or hub becomes reconciliation exception, not silent stock overwrite
integration run is created for ERP audit
automation run, steps, and webhook event are registered
no commerce projection is mutated automatically
```

Response sections:

```txt
dryRun.normalized.orders
dryRun.wouldPersist.customers
dryRun.wouldPersist.orders
dryRun.wouldAffectProjections
created.orders
created.customers
created.integrationRun
created.integrationApprovalRequest
created.automationRun
created.automationRunSteps
created.automationWebhookEvent
```

Post-import actions:

```txt
calculate commerce order KPIs
publish derived daily KPI snapshot
record automation run and steps
do not run commerce bottleneck detection yet
do not mutate official projection
```

Typical blockers:

```txt
orders_missing
order_items_missing
```

Typical warnings:

```txt
customer_hash_missing
node_key_missing
```

## Automation Run Pattern

Start run:

```json
{
  "automationKey": "bling_inventory_daily_import",
  "runDate": "2026-05-14",
  "status": "started",
  "startedBy": "system_automation_n8n",
  "metadata": {
    "provider": "bling",
    "nodeKey": "store-sp"
  }
}
```

Recommended steps:

```txt
fetch_payload
store_webhook_payload
normalize_payload
upsert_products
persist_inventory_snapshot
create_integration_run
create_approval
materialize_exceptions
finish_run
```

Complete run:

```json
{
  "automationKey": "bling_inventory_daily_import",
  "status": "completed",
  "recordsProcessed": 100,
  "factsCreated": 1,
  "approvalRequestsCreated": 2,
  "exceptionsCreated": 0
}
```

## Webhook Event Pattern

Endpoint:

```txt
POST /api/automations/webhook-events
```

Example:

```json
{
  "provider": "n8n",
  "eventType": "bling_inventory_daily_import.completed",
  "linkedRunId": "uuid",
  "normalizedStatus": "linked",
  "payload": {
    "executionId": "n8n-123",
    "provider": "bling",
    "operation": "inventory",
    "nodeKey": "store-sp",
    "blingWarehouseId": "987"
  }
}
```

## Error And Retry

When Bling fails:

```json
{
  "automationKey": "bling_inventory_daily_import",
  "runDate": "2026-05-14",
  "status": "failed",
  "startedBy": "system_automation_n8n",
  "errorCode": "bling_api_timeout",
  "errorMessage": "Bling API timeout while fetching inventory.",
  "metadata": {
    "provider": "bling",
    "nodeKey": "store-sp",
    "retryable": true
  }
}
```

Failed step:

```json
{
  "stepKey": "fetch_payload",
  "stepIndex": 1,
  "status": "failed",
  "errorCode": "bling_api_timeout",
  "errorMessage": "Bling API timeout while fetching inventory."
}
```

Retry rule:

```txt
n8n may retry webhook delivery.
automation_webhook_events is idempotent by provider + payload_hash.
canonical facts must still use their own idempotency rules.
```

## Governance Rule

Bling imports can create approval requests.

Bling automation must not final-approve:

```txt
system_automation_n8n can submit
integration_operator can review
tenant_auditor or responsible superior can final approve
```

## Current Status

```txt
Products -> active canonical endpoint exists
Inventory -> active canonical endpoint exists
Integration run -> active trace exists
Automation run -> active trace exists
Normalizer -> POST /api/integrations/bling/normalize
Orders/sales -> skeleton active through commerce canonical tables
Payments/customers -> skeleton active through commerce canonical tables
```

## Normalizer Endpoint

Endpoint:

```txt
POST /api/integrations/bling/normalize
```

Purpose:

```txt
Transform Bling-like raw payload into canonical DGE payloads without persistence.
```

Response sections:

```txt
normalized.products
normalized.inventorySnapshot
normalized.integrationRun
normalized.automationWebhookEvent
normalized.automationRun
persistence.enabled=false
```

The normalizer is safe for n8n dry runs because it does not write to the database.

## Inventory Dry-Run Endpoint

Endpoint:

```txt
POST /api/integrations/bling/inventory/dry-run
```

Purpose:

```txt
Simulate the complete Bling inventory import impact without persistence.
```

Response sections:

```txt
dryRun.valid
dryRun.persistenceEnabled=false
dryRun.normalized
dryRun.wouldPersist
dryRun.wouldCreateApprovals
dryRun.wouldAffectObligations
dryRun.wouldAffectExceptions
dryRun.warnings
dryRun.blockers
dryRun.trace
```

Use this endpoint before allowing n8n to call a future real import endpoint.

Typical blockers:

```txt
node_key_missing
inventory_items_missing
inventory_item_sku_missing
```

Typical warnings:

```txt
products_missing
stockout_items_detected
```

## Inventory Import Endpoint

Endpoint:

```txt
POST /api/integrations/bling/inventory/import
```

Purpose:

```txt
Persist a confirmed Bling inventory import through canonical DGE services.
```

Request shape:

```json
{
  "confirmImport": true,
  "payload": {
    "nodeKey": "store-sp",
    "snapshotDate": "2026-05-14",
    "produtos": []
  }
}
```

Rules:

```txt
dry-run always runs first
blockers stop import
confirmImport=true is required
products are upserted through POST /api/operations/products service
inventory snapshot is saved through canonical operations service
external integration run is saved through canonical integrations service
automation run, steps, and webhook event are registered
approval requests are created
no approval decision is made automatically
```

Response sections:

```txt
imported
dryRun
created.automationRun
created.automationRunSteps
created.automationWebhookEvent
created.products
created.inventorySnapshot
created.inventoryApprovalRequest
created.integrationRun
created.integrationApprovalRequest
impact.before
impact.after
```

Without `confirmImport=true`, the endpoint returns the dry-run result and does not persist.

## Inventory Post-Import Actions

Endpoint:

```txt
POST /api/integrations/bling/inventory/post-import-actions
```

Purpose:

```txt
Convert an imported inventory snapshot into derived daily KPIs and run daily inventory bottleneck detection.
```

Request shape:

```json
{
  "confirmPublish": true,
  "nodeKey": "store-sp",
  "snapshotDate": "2026-05-14",
  "submittedBy": "system_automation_n8n",
  "approvalWorkflowKey": "manual_daily_kpi_approval"
}
```

Rules:

```txt
preview always runs first
confirmPublish=true is required
inventory snapshot must exist for nodeKey and snapshotDate
derived inventory KPIs are published as daily KPI snapshot
approval request can be created for the derived KPI snapshot
daily inventory bottleneck detection runs after publish
automation run and steps are recorded
```

Response sections:

```txt
executed
reason
preview
created.automationRun
created.automationRunSteps
created.publishedDailySnapshot
created.bottleneckDetection
```

Without `confirmPublish=true`, the endpoint returns preview only and does not publish KPIs.
