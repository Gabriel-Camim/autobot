---
title: DGE fonte - DGE 2.0 Integration Directive
category: projetos
tags:
- dge
- fonte-original
- contratos
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/contracts/dge-2.0-integration-directive.md.'
source_path: docs/contracts/dge-2.0-integration-directive.md
---

# DGE 2.0 Integration Directive

Fonte original DGE 2.0: `docs/contracts/dge-2.0-integration-directive.md`.

---

# DGE 2.0 Integration Directive

## Purpose

This directive defines how manual operators, n8n, Bling, ecommerce, Frenet, and future agents should interact with the DGE backend.

## Manual vs Automation

Manual and automated sources use the same canonical endpoints.

Manual example:

```json
{
  "source": "manual",
  "automationLevel": "manual",
  "submittedBy": "unit_operator_sp"
}
```

Automation example:

```json
{
  "source": "api",
  "automationLevel": "automated",
  "submittedBy": "system_automation_n8n"
}
```

## Required Scope

Every operational fact should include scope.

Preferred field:

```json
{
  "nodeKey": "store-sp"
}
```

Fallback fields:

```txt
nodeId
operationalNodeId
operationalNodeKey
storeKey
unitKey
metadata.requiredScope
metadata.nodeKey
```

## Governance Workflow Selection

Use these workflow keys:

```txt
manual_daily_kpi_approval -> daily KPI snapshots
inventory_snapshot_approval -> inventory availability snapshots
erp_import_audit -> Bling or ERP import runs
monthly_close_approval -> monthly KPI traces
adaptive_projection_approval -> adaptive projection runs
```

When the data must be audited, include:

```json
{
  "governanceRequired": true,
  "approvalWorkflowKey": "erp_import_audit"
}
```

## Automation Actor Rule

Use:

```txt
system_automation_n8n
```

for n8n-submitted runs, imports, reminders, and report dispatches.

Do not use `system_automation_n8n` for final approval decisions.

## Retry And Idempotency

n8n and other orchestrators may retry.

Required behavior:

```txt
record webhook event first
use stable payload or payloadHash
link webhook to automation run when possible
avoid creating duplicate canonical facts
let approval requests and exceptions remain traceable
```

For webhook events:

```txt
project_id + provider + payload_hash is unique
```

## Error Registration

When an automation fails, register:

```json
{
  "automationKey": "bling_inventory_daily_import",
  "status": "failed",
  "errorCode": "bling_timeout",
  "errorMessage": "Bling API did not respond within expected window.",
  "metadata": {
    "retryable": true,
    "nodeKey": "store-sp"
  }
}
```

Then add a failed step:

```json
{
  "stepKey": "fetch_payload",
  "status": "failed",
  "errorCode": "bling_timeout",
  "errorMessage": "Timeout while fetching inventory payload."
}
```

## Do Not Bypass The Backbone

Integrations must not write directly to internal tables.

Allowed path:

```txt
raw payload
  -> automation_webhook_events
  -> automation_runs
  -> normalized canonical write endpoint
  -> approval request
  -> obligation/audit/exception/report read models
```

## Future Integration Contracts

Specific Bling, ecommerce, and Frenet payload contracts should be built as adapters into these canonical write contracts.

Do not create a Bling-only operational truth table unless the data cannot be represented canonically.

## Integration Readiness Lock

Before any real external connector is promoted, it must pass `integration.readiness_lock.v1`.

Canonical endpoints:

```txt
GET /api/integrations/provider-registry
GET /api/integrations/readiness-lock
GET /api/integrations/readiness-lock/:providerKey
POST /api/integrations/readiness-lock/:providerKey/check
POST /api/integrations/readiness-lock/:providerKey/dry-run
```

Official providers v1:

```txt
bling
frenet
loggi
n8n
ecommerce
payment_gateway
```

The lock checks:

- declared contract;
- normalizer or payload contract;
- dry-run;
- Data Intake coverage;
- Exception Hub mapping;
- audit trail;
- idempotency policy;
- BI dataset;
- manual fallback;
- credential/config presence without exposing secret values.

Readiness levels:

```txt
not_configured
contract_declared
local_dry_run_ready
assisted_import_ready
automation_trace_ready
live_api_probe_ready
production_ready
blocked
```

V1 is deterministic and local by default. Bling v1.5 is the first provider with an explicit opt-in live probe; it remains read-only and cannot import automatically.

Credential policy:

```txt
store/return only presence, env key name and missing status
never store/return token, secret, password or raw credential value
```

Promotion rule:

```txt
No provider reaches production_ready without dry-run, exception mapping, Data Intake fallback, BI visibility, idempotency and credential/live-probe gate.
```

## Bling Real Connector Gate v1.5

Bling is an auxiliary source for sales, invoices, product references and observed inventory reconciliation.

Active gates:

```txt
POST /api/integrations/readiness-lock/bling/live-probe
POST /api/integrations/bling/orders/fetch-preview
POST /api/integrations/bling/inventory/fetch-preview
POST /api/integrations/bling/invoices/fetch-preview
POST /api/integrations/bling/webhooks
GET /api/integrations/bling/mappings
POST /api/integrations/bling/mappings
```

Rules:

- `BLING_ACCESS_TOKEN` can enable live probe, but the value is never returned or stored.
- Live probe is read-only and requires `allowExternalProbe=true`.
- Fetch preview does not create canonical records.
- Import from live/webhook source requires preview/hash guard.
- Bling inventory is never canonical ERP stock.
- Webhook events are trace/import suggestions, not automatic imports.
