---
title: DGE fonte - DGE 2.0 Tenant Access & Responsibility Model
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-tenant-access-and-responsibility.md.'
source_path: docs/architecture/dge-2.0-tenant-access-and-responsibility.md
---

# DGE 2.0 Tenant Access & Responsibility Model

Fonte original DGE 2.0: `docs/architecture/dge-2.0-tenant-access-and-responsibility.md`.

---

# DGE 2.0 Tenant Access & Responsibility Model

## Purpose

Approval workflows need real responsibility context.

The current governance skeleton accepts `submittedBy` and `decidedBy` as text. That is enough for early smoke tests, but real operation needs users, roles, units, and scopes.

## Core Model

```txt
tenant user
  -> assigned roles
  -> assigned operational nodes
  -> assigned responsibilities
  -> allowed workflow decisions
```

## User Levels

Initial role keys:

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
system_integration
```

Seeded automation actor:

```txt
system_automation_n8n
```

This actor has `system_integration` role, entry/import responsibilities, and global scope. It is allowed to submit operational facts for audit, not to replace final human approval.

## Responsibilities

Initial responsibility keys:

```txt
daily_kpi_entry
daily_kpi_review
inventory_entry
inventory_review
erp_import_review
monthly_close_review
adaptive_projection_review
campaign_approval
automation_review
```

## Unit Scope

Users may be scoped to:

- one operational node;
- multiple operational nodes;
- a region;
- the whole tenant/project.

Examples:

```txt
unit_operator -> Loja SP
unit_manager -> Loja SP
regional_manager -> Sudeste
tenant_auditor -> all nodes
tenant_owner -> all nodes
```

## Workflow Enforcement

Approval workflow steps already declare `requiredRole`.
They also declare `requiredResponsibility`.

Decision enforcement checks:

```txt
decidedBy user exists
user has required role
user scope covers entity/unit
user responsibility covers workflow
```

Only then a decision should be accepted.
When an approval request includes `requiredScope`, `operationalScope`, or `scope` in metadata, the actor must have a matching node, region, project, tenant, global, or all scope.

Operational modules should not require the operator to type approval scope manually. KPI, inventory, and integration writes derive `requiredScope` from the payload or metadata whenever a node/unit/store key is present.

## Proposed Tables

```txt
tenant_users
tenant_user_roles
tenant_user_node_assignments
tenant_user_responsibilities
```

## Active Endpoints

```txt
GET /api/governance/access-definitions
POST /api/governance/tenant-users
GET /api/governance/tenant-users
```

`POST /api/governance/tenant-users` accepts:

```json
{
  "userKey": "unit_manager_sp",
  "displayName": "Unit Manager SP",
  "email": "unit.manager@example.com",
  "roles": ["unit_manager"],
  "responsibilities": ["daily_kpi_review", "inventory_review"],
  "nodeAssignments": [
    { "scopeType": "node", "scopeKey": "store-sp" }
  ]
}
```

Roles and responsibilities are rejected when they do not exist in the registry.

## Status

This model should become active before:

- required daily audit rollout;
- n8n automation approval flows;
- ecommerce campaign automation;
- official reforecast approval.

## Guardrail

No automated or manual action should be considered audited only because it was executed. It becomes audited only when the responsible user chain approves it within scope.
