---
title: DGE fonte - DGE 2.0 Operational Data Contracts
category: projetos
tags:
- dge
- fonte-original
- contratos
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/contracts/dge-2.0-operational-data-contracts.md.'
source_path: docs/contracts/dge-2.0-operational-data-contracts.md
---

# DGE 2.0 Operational Data Contracts

Fonte original DGE 2.0: `docs/contracts/dge-2.0-operational-data-contracts.md`.

---

# DGE 2.0 Operational Data Contracts

## Purpose

This contract pack defines the official backend language for manual entry, n8n, Bling, ecommerce, future frontend views, and AI agents.

All operational facts should follow the same pattern:

```txt
source fact
  -> normalized payload
  -> canonical DGE write endpoint
  -> approval request when governance applies
  -> obligation/audit/exception/report read models
```

## Canonical Actors

```txt
manual operator: tenant user such as unit_operator_*
automation executor: system_automation_n8n
reviewer: user with required role, responsibility, and scope
final approver: tenant_auditor, tenant_owner, or workflow-specific superior
```

## Canonical Scope

Operational write payloads should include one of:

```txt
nodeKey
nodeId
operationalNodeId
operationalNodeKey
storeKey
unitKey
metadata.requiredScope
metadata.nodeKey
```

The backend derives `requiredScope` from these fields and attaches it to approval requests.

Recommended default:

```json
{
  "nodeKey": "store-sp"
}
```

## Canonical Governance Fields

Use these fields on write endpoints when the fact must enter the approval chain:

```json
{
  "approvalWorkflowKey": "manual_daily_kpi_approval",
  "submittedBy": "unit_operator_1",
  "governanceRequired": true
}
```

If `governanceRequired` is `true`, `approvalWorkflowKey` is mandatory.

## Canonical Automation Fields

Manual and automated facts use the same write endpoints. The distinction is metadata:

```json
{
  "source": "api",
  "automationLevel": "automated",
  "submittedBy": "system_automation_n8n"
}
```

Automation may submit facts, create runs, and trigger approval requests. It should not final-approve audited data.

## Idempotency Rules

Current idempotency rules:

```txt
inventory snapshot: project_id + node_id + snapshot_date + source
automation webhook: project_id + provider + payload_hash
operational exception: exceptionKey in timeline metadata
daily KPI snapshot: project_id + snapshot_date + source + scope_type + scope_key lookup
```

## Contract Files

```txt
docs/contracts/dge-2.0-write-contracts.md
docs/contracts/dge-2.0-read-contracts.md
docs/contracts/dge-2.0-integration-directive.md
docs/contracts/dge-2.0-bling-integration-contract.md
```

## Non-Negotiables

- Do not create operational truth without scope.
- Do not bypass approval for audited operational data.
- Do not let automation final-approve itself.
- Do not add new event types without the timeline event registry.
- Do not create integration-specific payloads that skip canonical DGE contracts.
