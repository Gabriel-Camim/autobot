---
title: DGE fonte - DGE 2.0 Projection Impact Analyzer
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-projection-impact-analyzer.md.'
source_path: docs/architecture/dge-2.0-projection-impact-analyzer.md
---

# DGE 2.0 Projection Impact Analyzer

Fonte original DGE 2.0: `docs/architecture/dge-2.0-projection-impact-analyzer.md`.

---

# DGE 2.0 Projection Impact Analyzer

## Purpose

Projection Impact Analyzer v1 turns operational cockpit intelligence into a traceable, non-official projection impact preview.

It does not recalculate official scenarios, create assumption adjustments, or approve reforecast. Its job is to answer:

```txt
Which projection families and formulas may be affected by the current operational state?
```

## Endpoints

```txt
GET /api/projections/impact-preview
GET /api/projections/impact-traces
```

`impact-preview` reads the Operational Command Center, extracts `projectionImpactPreview`, persists a `projection_impact_trace`, and creates a timeline event.

## Table

```txt
projection_impact_traces
```

Stores:

- reference date and period;
- source payload from command center;
- impact preview JSON;
- recommendations;
- impacted formula keys;
- impacted projection families;
- guarantees;
- summary.

## Guarantees

```txt
previewOnly: true
officialProjectionMutation: false
createsProjectionAdjustment: false
createsOfficialReforecast: false
requiresHumanApprovalForOfficialUse: true
```

## Relationship With Forecast Reconciliation

The analyzer is upstream evidence for Forecast Reconciliation.

Current flow:

```txt
Command Center Intelligence
-> Projection Impact Analyzer
-> projection_impact_traces
-> Forecast Reconciliation
-> reforecast case / monitoring decision
```

Projection impact traces explain operational pressure before any official adjustment or reforecast proposal is created.

They should be combined with:

- observed projection variances;
- monthly KPI traces;
- bottleneck detection runs;
- projection versions;
- approval/audit status.

Adaptive projection v1 may still suggest assumption adjustments, but the target architecture reformulates it into a Reforecast Intelligence layer that operates inside a reconciliation case.

## Current Implementation Status

```txt
Status: v1 implemented
Smoke: npm run smoke:projection-impact
```
