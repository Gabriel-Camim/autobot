---
title: DGE fonte - DGE 2.0 Adaptive Projection Engine
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-adaptive-projection-engine.md.'
source_path: docs/architecture/dge-2.0-adaptive-projection-engine.md
---

# DGE 2.0 Adaptive Projection Engine

Fonte original DGE 2.0: `docs/architecture/dge-2.0-adaptive-projection-engine.md`.

---

# DGE 2.0 Adaptive Projection Engine

## Architectural Status

Status: implemented v1, but conceptually in transition.

The current module remains useful as a conservative adjustment/simulation mechanism, but it should not become the long-term orchestrator of reforecast.

Target direction:

```txt
Adaptive Projection Engine
-> Reforecast Intelligence Layer
```

This means adaptive logic should eventually operate inside a reforecast case created by Forecast Reconciliation.

It should not independently decide that official reforecast is needed.

Current directive:

```txt
Adaptive Projection Engine is transitional.
Reforecast Intelligence is the target decision layer.
Adaptive suggestions may be reused only inside a reforecast case and preview flow.
```

Guardrail:

```txt
No adaptive endpoint should create an official reforecast or bypass Forecast Reconciliation.
```

## Purpose

The Adaptive Projection Engine turns observed KPI history into traceable projection adjustment suggestions.

It does not mutate official projections automatically.

## Core Rule

```txt
Observed KPI history -> persistent variance -> suggested assumption adjustment -> human approval -> future reforecast.
```

Future core rule:

```txt
Forecast Reconciliation
-> reforecast case
-> Reforecast Intelligence adjustment policy
-> governed preview
-> human approval
-> projection version
```

The first version is conservative:

- reads `monthly_kpi_traces`;
- reads `observed_projection_variances`;
- requires minimum data quality;
- detects persistent variance by KPI;
- creates suggested assumption adjustments;
- links affected formulas and projection families;
- preserves the original official scenario.

Known limitation:

- it reads variance history, but does not fully consume bottleneck causal evidence;
- it is tied to `scenario_snapshot_id` more than `projection_version_id`;
- it can suggest adjustment before the system has created a case-level interpretation;
- it should be reformulated so adjustment suggestions are attached to reforecast cases.

## Relationship With Bottlenecks

Bottlenecks should not be treated as a side signal.

They are causal evidence.

```txt
Variance = what deviated.
Bottleneck = why it may have deviated.
Adaptive/Reforecast Intelligence = what assumption or preview may need to change.
```

Future Reforecast Intelligence should consume:

```txt
observed_projection_variances
bottleneck_detection_runs
projection_impact_traces
monthly_kpi_traces
projection_versions
```

This avoids a blind adjustment that sees only the KPI gap but not the operational cause.

## Active Now

```txt
POST /api/projections/adaptive/analyze
GET /api/projections/adaptive/adjustments
POST /api/projections/adaptive/simulate
```

The analysis endpoint creates an `adaptive_projection_run` and zero or more `projection_assumption_adjustments`.
The simulation endpoint creates an `adaptive_projection_run` with mode `simulate_projection`, using approved adjustments only.

## Tables

```txt
adaptive_projection_runs
projection_assumption_adjustments
```

## Adjustment Status

```txt
suggested
approved
rejected
expired
```

Only `suggested` is created automatically in v1. Human/operator governance moves a suggestion to `approved`, `rejected`, or `expired`.

## Decision Endpoints

```txt
POST /api/projections/adaptive/adjustments/:id/approve
POST /api/projections/adaptive/adjustments/:id/reject
POST /api/projections/adaptive/adjustments/:id/expire
```

Each decision stores:

- decision;
- decision reason;
- decided by;
- decided at;
- official projection mutation flag.

Each decision also creates a timeline event:

```txt
projection_adjustment_approved
projection_adjustment_rejected
projection_adjustment_expired
```

Approval does not recalculate the official scenario. It only marks the suggestion as eligible for a later controlled simulation or reforecast.

## Simulation

Adaptive simulation converts approved adjustments into an impact package.

It records:

- adjustment id;
- KPI key;
- assumption key;
- old value;
- suggested value;
- numeric delta;
- percentage delta;
- impacted formulas;
- impacted projection families;
- readiness for review.

Simulation is still non-mutating:

```txt
approved adjustment -> simulate_projection run -> human review -> future reforecast
```

## Simulation Decision

Simulation runs can be governed before any reforecast exists:

```txt
POST /api/projections/adaptive/simulations/:id/review
POST /api/projections/adaptive/simulations/:id/approve-for-reforecast
POST /api/projections/adaptive/simulations/:id/reject
```

Decision events:

```txt
adaptive_simulation_reviewed
adaptive_simulation_approved_for_reforecast
adaptive_simulation_rejected
```

`approve-for-reforecast` means the simulation may be used by a future reforecast workflow. It still does not create a new official scenario snapshot.

## Detection Policy

Default thresholds:

- minimum periods: 2;
- minimum absolute variance: 10%;
- minimum monthly quality score: 0.60;
- maximum suggestions per run: 20.

The endpoint may override these thresholds for analysis, but the thresholds are recorded in run metadata.

## Trace Metadata

Each suggestion records:

- KPI key;
- assumption key;
- observed average;
- projected average;
- suggested value;
- average variance;
- evidence window;
- evidence rows;
- impacted formula keys;
- impacted projection families;
- reason code;
- confidence;
- status.

## Non-Negotiable Guardrail

```txt
Adaptive analysis can suggest a future assumption.
It cannot overwrite the official scenario or projection.
```

Approval and controlled reforecast are later stages.

Additional guardrail:

```txt
Adaptive logic cannot bypass Forecast Reconciliation.
Persistent variance plus bottleneck evidence should become a reforecast case before it becomes an official reforecast proposal.
```
