---
title: DGE fonte - DGE 2.0 Operational Governance
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-operational-governance.md.'
source_path: docs/architecture/dge-2.0-operational-governance.md
---

# DGE 2.0 Operational Governance

Fonte original DGE 2.0: `docs/architecture/dge-2.0-operational-governance.md`.

---

# DGE 2.0 Operational Governance

## Purpose

Operational governance controls how manual KPI entries, ERP imports, inventory snapshots, monthly closes, and adaptive projections become audited data.

Automation reduces manual entry, but it does not remove daily audit responsibility.

The legacy governance exception endpoints remain valid, but they now act as a domain source for the Operational Exception Hub. Governance still materializes and resolves obligation-level exceptions; the hub provides the cross-module queue, impact score, graph links, dedupe and resolution delegation.

## Core Flow

```txt
registered
  -> submitted
  -> reviewed by superior
  -> final tenant audit
  -> approved/audited
  -> eligible for official DGE use
```

## Active Skeleton

Tables:

```txt
approval_workflows
approval_requests
approval_decisions
tenant_users
tenant_user_roles
tenant_user_node_assignments
tenant_user_responsibilities
```

Endpoints:

```txt
GET /api/governance/workflows
GET /api/governance/access-definitions
GET /api/governance/daily-audit-queue
GET /api/governance/audit-status
GET /api/governance/daily-obligations
GET /api/governance/operational-exceptions
POST /api/governance/operational-exceptions/materialize
POST /api/governance/operational-exceptions/resolve
GET /api/operations/exception-hub
GET /api/operations/exception-impact
GET /api/governance/operational-health
GET /api/governance/operational-report
POST /api/governance/tenant-users
GET /api/governance/tenant-users
POST /api/governance/approvals
GET /api/governance/approvals
GET /api/governance/entity-status
POST /api/governance/approvals/:id/decision
```

## Seeded Workflows

```txt
manual_daily_kpi_approval
inventory_snapshot_approval
erp_import_audit
monthly_close_approval
adaptive_projection_approval
```

## User Levels To Model Later

```txt
unit_operator
unit_manager
regional_manager
operations_manager
finance_manager
integration_operator
inventory_owner
tenant_auditor
tenant_owner
tenant_admin
```

Access definitions are exposed by:

```txt
GET /api/governance/access-definitions
```

Tenant users can now be registered with roles, responsibilities, and operational scope:

```json
{
  "userKey": "unit_manager_sp",
  "displayName": "Unit Manager SP",
  "roles": ["unit_manager"],
  "responsibilities": ["daily_kpi_review", "inventory_review"],
  "nodeAssignments": [
    { "scopeType": "node", "scopeKey": "store-sp" }
  ]
}
```

Role and responsibility keys must exist in the access registry.

## Guardrails

- Registered data is not automatically audited data.
- Automation should create reviewable facts, not bypass audit.
- Manual entry becomes contingency once integrations mature.
- Daily audit remains mandatory even when Bling/ecommerce automations are active.
- Approval workflow is intentionally generic so it can wrap many entity types.

## Next Steps

- Enforce workflow decision authorization using tenant user role, responsibility, and node scope.
- Block monthly close from using unaudited data when governance becomes active.

## Linked Entry Points

Governance can now be attached at write time by sending `approvalWorkflowKey`.

Supported entry points:

```txt
POST /api/kpis/daily-snapshots
POST /api/operations/inventory-availability
POST /api/operations/inventory-kpis/publish-daily-snapshot
POST /api/integrations/runs
```

Examples:

```json
{
  "approvalWorkflowKey": "manual_daily_kpi_approval",
  "submittedBy": "unit_operator_1"
}
```

This creates an `approval_request` linked to the saved entity, but it does not block legacy flows yet.

Approval decisions are enforced against tenant access:

```txt
decidedBy must be an active tenant user
current workflow step requiredRole must be present in user roles
current workflow step requiredResponsibility must be present in user responsibilities
approval metadata scope must be covered by user node assignments when scope is provided
```

Operational write flows should attach scope automatically to their approval requests. The active helper derives `requiredScope` from explicit scope metadata, `nodeId`, `operationalNodeId`, `nodeKey`, `operationalNodeKey`, `storeKey`, or `unitKey`.

Active automatic scope entry points:

```txt
POST /api/kpis/daily-snapshots
POST /api/operations/inventory-availability
POST /api/operations/inventory-kpis/publish-daily-snapshot
POST /api/integrations/runs
```

## Daily Audit Cockpit

The first cockpit layer is read-model based. It does not create new facts; it organizes active `approval_requests` into an operational queue.

```txt
GET /api/governance/daily-audit-queue
GET /api/governance/audit-status
```

`daily-audit-queue` can filter by user key, date, status, and workflow. When `userKey` is provided, it returns only approval requests that the user can act on based on role, responsibility, and scope.

`audit-status` returns aggregate counts by status, workflow, entity type, scope, actionable items, open items, and late items.

## Daily Operational Obligations

The obligations layer answers what should exist even before a fact is submitted.

```txt
GET /api/governance/daily-obligations
```

Initial obligation types:

```txt
daily_kpi_snapshot
inventory_availability_snapshot
erp_inventory_import
```

Each obligation is independent from its executor. It can be fulfilled by manual entry today or by automation later. The canonical automation actor is:

```txt
system_automation_n8n
```

Automation can submit or import facts, but final approval still belongs to the human governance chain.

Automation execution itself is traced by the automation backbone:

```txt
GET /api/automations/registry
POST /api/automations/runs
POST /api/automations/webhook-events
```

## Operational Exceptions

Operational exceptions convert obligation gaps into alertable facts.

```txt
GET /api/governance/operational-exceptions
POST /api/governance/operational-exceptions/materialize
```

Current exception types:

```txt
missing_daily_kpi
missing_inventory_snapshot
missing_erp_inventory_import
received_unaudited
approval_pending
audit_overdue
correction_requested
audit_rejected
```

`materialize` creates `timeline_events` with `event_type = operational_exception`. It is idempotent by `exceptionKey`, so the same date/unit/obligation/type does not create duplicate timeline events.

Timeline event definitions are governed by the event registry:

```txt
GET /api/timeline/event-registry
```

Exceptions can be resolved with:

```txt
POST /api/governance/operational-exceptions/resolve
```

Resolution types:

```txt
fact_submitted
approval_completed
waived
false_positive
manual_override
```

Resolution closes the original exception event and creates an `operational_exception_resolved` event with `resolvedBy`, `resolutionType`, notes, and timestamp.

Operational health is exposed by:

```txt
GET /api/governance/operational-health
```

It aggregates exception recurrence, open vs resolved exceptions, resolution rate, average resolution days, top problem node, and top exception type.

## Operational Report

The consolidated operational report is the read model intended for cockpit UI, n8n notifications, and future AI-generated executive narratives.

```txt
GET /api/governance/operational-report
```

Supported query fields:

```txt
period=daily|weekly|monthly
date=YYYY-MM-DD
nodeKey=all or node key
userKey=optional tenant user key
includeItems=true|false
```

The report combines:

```txt
daily obligations
daily audit queue
audit status
operational exceptions
operational health
automation readiness
recommended actions
trace metadata
```

## Required Governance On Entry

Write endpoints can opt into strict entry governance with:

```json
{ "governanceRequired": true }
```

When enabled, the request must include `approvalWorkflowKey` or it fails with `approval_workflow_required`.

Supported entry points:

```txt
POST /api/kpis/daily-snapshots
POST /api/operations/inventory-availability
POST /api/operations/inventory-kpis/publish-daily-snapshot
POST /api/integrations/runs
```

## Enforcement Mode

Critical flows can opt into enforcement with:

```json
{ "governanceEnforced": true }
```

Initial enforced flow:

```txt
POST /api/kpis/monthly-traces/close
```

When enabled, monthly close requires all included `daily_kpi_snapshot` entities to have final approval. If not, it returns `approval_workflow_failed`.
