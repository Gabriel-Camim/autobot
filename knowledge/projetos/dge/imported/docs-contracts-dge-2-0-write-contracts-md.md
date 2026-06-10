---
title: DGE fonte - DGE 2.0 Write Contracts
category: projetos
tags:
- dge
- fonte-original
- contratos
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/contracts/dge-2.0-write-contracts.md.'
source_path: docs/contracts/dge-2.0-write-contracts.md
---

# DGE 2.0 Write Contracts

Fonte original DGE 2.0: `docs/contracts/dge-2.0-write-contracts.md`.

---

# DGE 2.0 Write Contracts

## Daily KPI Snapshot

Endpoint:

```txt
POST /api/kpis/daily-snapshots
```

Purpose:

```txt
Register daily operational KPIs by date and scope.
```

Required fields:

```txt
snapshotDate
kpis
```

Recommended fields:

```txt
nodeKey
source
automationLevel
status
approvalWorkflowKey
submittedBy
```

Example:

```json
{
  "snapshotDate": "2026-05-14",
  "nodeKey": "store-sp",
  "source": "manual",
  "automationLevel": "manual",
  "status": "draft",
  "allowIncomplete": true,
  "approvalWorkflowKey": "manual_daily_kpi_approval",
  "submittedBy": "unit_operator_sp",
  "kpis": [
    {
      "key": "daily_store_revenue",
      "label": "Receita diaria da unidade",
      "value": 1200,
      "unit": "BRL"
    }
  ]
}
```

Response shape:

```txt
snapshot
collectionAssessment
timelineEvent
approvalRequest
```

Common errors:

```txt
approval_workflow_required
daily_kpi_collection_contract_failed
```

## Inventory Availability Snapshot

Endpoint:

```txt
POST /api/operations/inventory-availability
```

Purpose:

```txt
Register SKU availability for an operational node and date.
```

Required fields:

```txt
nodeKey or nodeId
snapshotDate
items
```

Example:

```json
{
  "nodeKey": "store-sp",
  "snapshotDate": "2026-05-14",
  "source": "manual",
  "automationLevel": "manual",
  "approvalWorkflowKey": "inventory_snapshot_approval",
  "submittedBy": "inventory_owner_sp",
  "items": [
    {
      "sku": "SKU-001",
      "onHandQty": 10,
      "reservedQty": 2,
      "availableQty": 8,
      "safetyStockQty": 3,
      "unitCost": 25
    }
  ]
}
```

Response shape:

```txt
snapshot
summary
timelineEvent
approvalRequest
```

## External Integration Run

Endpoint:

```txt
POST /api/integrations/runs
```

Purpose:

```txt
Register a Bling, ERP, ecommerce, Frenet, or manual import run.
```

Required fields:

```txt
provider
operation
status
```

Example:

```json
{
  "provider": "bling",
  "operation": "inventory",
  "status": "confirmed",
  "source": "api",
  "recordsReceived": 50,
  "recordsNormalized": 49,
  "recordsFailed": 1,
  "submittedBy": "system_automation_n8n",
  "approvalWorkflowKey": "erp_import_audit",
  "metadata": {
    "nodeKey": "store-sp"
  }
}
```

Response shape:

```txt
integrationRun
approvalRequest
```

## Approval Decision

Endpoint:

```txt
POST /api/governance/approvals/:id/decision
```

Purpose:

```txt
Approve, reject, or request correction for the current workflow step.
```

Required fields:

```txt
decision
decidedBy
```

Example:

```json
{
  "decision": "approved",
  "decidedBy": "unit_manager_sp",
  "notes": "Valores conferidos contra fechamento da loja."
}
```

Accepted decisions:

```txt
approved
rejected
correction_requested
```

Governance enforcement:

```txt
decidedBy must be active tenant user
user must have current step requiredRole
user must have current step requiredResponsibility
user must cover requiredScope when scope exists
```

## Operational Exception Resolution

Endpoint:

```txt
POST /api/governance/operational-exceptions/resolve
```

Purpose:

```txt
Close a materialized operational exception and create a resolution timeline event.
```

Required fields:

```txt
exceptionKey
resolvedBy
resolutionType
```

Example:

```json
{
  "exceptionKey": "operational_exception:2026-05-14:store-sp:daily_kpi_snapshot:missing_daily_kpi",
  "resolvedBy": "tenant_auditor_1",
  "resolutionType": "fact_submitted",
  "notes": "KPI enviado e aprovado apos cobranca."
}
```

Resolution types:

```txt
fact_submitted
approval_completed
waived
false_positive
manual_override
```

## Automation Run

Endpoint:

```txt
POST /api/automations/runs
```

Purpose:

```txt
Register an automation execution.
```

Example:

```json
{
  "automationKey": "bling_inventory_daily_import",
  "runDate": "2026-05-14",
  "status": "completed",
  "startedBy": "system_automation_n8n",
  "recordsProcessed": 50,
  "factsCreated": 1,
  "approvalRequestsCreated": 1,
  "exceptionsCreated": 0
}
```

## Automation Run Step

Endpoint:

```txt
POST /api/automations/runs/:id/steps
```

Example:

```json
{
  "stepKey": "persist_fact",
  "stepIndex": 3,
  "status": "completed",
  "recordsProcessed": 50
}
```

## Automation Webhook Event

Endpoint:

```txt
POST /api/automations/webhook-events
```

Purpose:

```txt
Record a webhook payload received from n8n or another orchestrator.
```

Example:

```json
{
  "provider": "n8n",
  "eventType": "bling_inventory_daily_import.completed",
  "normalizedStatus": "linked",
  "linkedRunId": "uuid",
  "payload": {
    "executionId": "n8n-123",
    "automationKey": "bling_inventory_daily_import",
    "nodeKey": "store-sp"
  }
}
```

Idempotency:

```txt
payload_hash is derived from payload when not provided.
project_id + provider + payload_hash is unique.
```
