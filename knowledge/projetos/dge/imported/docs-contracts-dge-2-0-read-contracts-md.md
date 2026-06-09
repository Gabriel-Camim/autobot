---
title: DGE fonte - DGE 2.0 Read Contracts
category: projetos
tags:
- dge
- fonte-original
- contratos
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/contracts/dge-2.0-read-contracts.md.'
source_path: docs/contracts/dge-2.0-read-contracts.md
---

# DGE 2.0 Read Contracts

Fonte original DGE 2.0: `docs/contracts/dge-2.0-read-contracts.md`.

---

# DGE 2.0 Read Contracts

## Daily Obligations

Endpoint:

```txt
GET /api/governance/daily-obligations
```

Purpose:

```txt
Show what operational facts are expected for a date and node.
```

Query fields:

```txt
date
nodeKey
includeDefinitions
```

Response sections:

```txt
obligations
summary
filters
automationActor
definitions
```

Consumers:

```txt
cockpit
n8n
operations manager
AI operational analyst
```

## Daily Audit Queue

Endpoint:

```txt
GET /api/governance/daily-audit-queue
```

Purpose:

```txt
Show approval requests that are actionable for a user.
```

Query fields:

```txt
userKey
date
status
workflowKey
limit
```

When `userKey` is provided, the backend returns only items the user can act on by role, responsibility, and scope.

## Audit Status

Endpoint:

```txt
GET /api/governance/audit-status
```

Purpose:

```txt
Aggregate approval request status by date, workflow, entity, and scope.
```

Query fields:

```txt
date
status
workflowKey
limit
```

## Operational Exceptions

Endpoint:

```txt
GET /api/governance/operational-exceptions
```

Purpose:

```txt
Detect current operational exceptions from daily obligations.
```

Query fields:

```txt
date
nodeKey
severity
```

Response sections:

```txt
exceptions
summary
filters
```

## Operational Health

Endpoint:

```txt
GET /api/governance/operational-health
```

Purpose:

```txt
Aggregate materialized exception recurrence and resolution.
```

Query fields:

```txt
days
nodeKey
exceptionType
```

Response sections:

```txt
health
exceptions
filters
```

Health fields:

```txt
totalExceptions
openExceptions
resolvedExceptions
resolutionRate
averageResolutionDays
topProblemNode
topExceptionType
byNode
byType
bySeverity
```

## Operational Report

Endpoint:

```txt
GET /api/governance/operational-report
```

Purpose:

```txt
Return a consolidated cockpit report for UI, n8n notifications, or AI narrative.
```

Query fields:

```txt
period
date
nodeKey
userKey
includeItems
```

Supported periods:

```txt
daily
weekly
monthly
```

Response sections:

```txt
report.summary
report.obligationStatus
report.auditQueue
report.auditStatus
report.exceptions
report.health
report.automationReadiness
report.recommendedActions
report.trace
filters
```

Recommended consumer:

```txt
future cockpit frontend
n8n daily report dispatch
AI executive report agent
operations manager
```

## Automation Registry

Endpoint:

```txt
GET /api/automations/registry
```

Purpose:

```txt
List expected automations and their owner/cadence/executor.
```

Query fields:

```txt
status
```

## Automation Runs

Endpoint:

```txt
GET /api/automations/runs
```

Purpose:

```txt
List automation execution traces.
```

Query fields:

```txt
automationKey
status
limit
```

## Automation Webhook Events

Endpoint:

```txt
GET /api/automations/webhook-events
```

Purpose:

```txt
List webhook payload traces received from n8n or other orchestrators.
```

Query fields:

```txt
provider
limit
```

## Timeline Event Registry

Endpoint:

```txt
GET /api/timeline/event-registry
```

Purpose:

```txt
List allowed timeline event types and metadata expectations.
```

Use this before adding new event types or new automation materialization routines.
