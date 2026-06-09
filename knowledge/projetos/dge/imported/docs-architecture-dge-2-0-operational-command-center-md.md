---
title: DGE fonte - DGE 2.0 Operational Command Center
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-operational-command-center.md.'
source_path: docs/architecture/dge-2.0-operational-command-center.md
---

# DGE 2.0 Operational Command Center

Fonte original DGE 2.0: `docs/architecture/dge-2.0-operational-command-center.md`.

---

# DGE 2.0 Operational Command Center

## Purpose

The Operational Command Center is a backend-only aggregation layer for the future cockpit.

It does not create facts, mutate projections, approve data, or execute automations. It answers one operational question:

```txt
What is the current operational state of DGE?
```

## Endpoint

```txt
GET /api/operations/command-center
```

Query params:

- `referenceDate`;
- `lookbackDays`;
- `limit`.

## Sections

The response aggregates:

- daily KPI snapshots;
- latest bottleneck detection runs;
- external integration runs;
- automation runs;
- pending approvals;
- recent timeline events;
- module registry summary;
- computed health status.
- intelligence layer.

## Intelligence Layer

Command Center Intelligence v1 adds:

- `priorityQueue`: ranked operational issues from bottlenecks, health, approvals, integrations, and automations;
- `domainScorecards`: status and score by domain;
- `recommendations`: deduplicated next actions from the priority queue;
- `dataFreshnessMap`: freshness of KPI snapshots, integrations, and automations;
- `automationReadiness`: whether the backbone is still manual/partial or ready to expand automation;
- `projectionImpactPreview`: non-official impact preview for future projection analysis.

The projection preview maps operational pressure to possible projection families and formulas. It does not recalculate, mutate, or approve official projections.

## Health Contract

The health object is intentionally simple in v1:

- `stable`;
- `watch`;
- `attention_required`.

It considers:

- active bottleneck signals;
- pending approvals;
- failed integrations;
- failed automations;
- missing/stale KPI snapshots.

## Guarantees

```txt
readOnly: true
createsOperationalFacts: false
officialProjectionMutation: false
frontendCoupling: false
projectionImpactPreviewOnly: true
```

This endpoint is the bridge between backend architecture and future cockpit UI. It should remain a read model.

## Current Implementation Status

```txt
Status: v1 implemented with intelligence layer
Smoke: npm run smoke:command-center
```
