---
title: DGE fonte - DGE 2.0 KPI Intelligence Module
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-kpi-intelligence-module.md.'
source_path: docs/architecture/dge-2.0-kpi-intelligence-module.md
---

# DGE 2.0 KPI Intelligence Module

Fonte original DGE 2.0: `docs/architecture/dge-2.0-kpi-intelligence-module.md`.

---

# DGE 2.0 KPI Intelligence Module

## Purpose

The KPI Intelligence Module is one of the hearts of DGE 2.0.

It transforms operational data into a living intelligence layer that can compare, analyze, project, explain, detect bottlenecks, recommend action, and feed RAI agents.

It is not only a monthly closing module.

## Core Mission

```txt
Collect daily operational truth.
Aggregate it into periods.
Compare observed vs projected.
Detect variance and bottlenecks.
Explain what changed.
Recommend what to do.
Preserve history for RAI and future fine-tuning.
```

## What This Module Must Answer

- What changed since DGE activation?
- What changed since ecommerce activation?
- Which KPI deviated most from projection?
- Which operational driver explains the deviation?
- Is the issue commercial, inventory, logistics, CRM, marketing, pricing, or capacity?
- Is data complete enough to trust the conclusion?
- Did projected payback move?
- Which premise should be reviewed?
- Which formula or projection family was impacted?
- Which RAI agent should analyze the case?

## Module Layers

### 1. Collection Layer

Receives daily KPI snapshots from multiple sources.

Sources:

- manual input;
- spreadsheet imports;
- ecommerce platform;
- ERP/Bling;
- logistics providers;
- CRM;
- app events;
- AI-assisted extraction;
- future webhooks.

Responsibilities:

- normalize payloads;
- validate KPI keys;
- attach source and confidence;
- preserve raw import metadata safely;
- create timeline events;
- mark missing data explicitly.

### 2. Data Quality Layer

Scores whether a period can be trusted.

Signals:

- missing days;
- duplicated source;
- manual-only data;
- mixed-source data;
- imported data not reconciled;
- outlier values;
- zero values where operation should exist;
- stale snapshot;
- low-confidence AI extraction.

Quality statuses:

```txt
complete
partial
manual_only
mixed_sources
missing_days
low_confidence
stale
inconsistent
```

### 3. Aggregation Layer

Turns daily snapshots into weekly, monthly, quarterly, or custom-period traces.

Aggregation strategies:

- sum;
- average;
- weighted average;
- min/max;
- last value;
- first value;
- count;
- ratio;
- derived formula.

Examples:

- GMV: sum;
- orders: sum;
- average ticket: GMV / orders;
- conversion: orders / sessions;
- freight average: weighted average by orders;
- stockout rate: average or weighted by SKU exposure;
- SLA: ratio of on-time deliveries.

### 4. Projection Comparison Layer

Compares observed KPI aggregates against:

- original projection;
- latest projection;
- baseline before DGE activation;
- baseline before ecommerce activation;
- previous period;
- same weekday/month when available;
- scenario objective target.

Outputs:

- absolute variance;
- percentage variance;
- trend;
- confidence;
- reason hypothesis;
- affected formulas;
- affected projection families;
- possible payback impact.

### 5. Bottleneck Detection Layer

Detects operational constraints and failure patterns.

Bottleneck domains:

```txt
commercial
marketplace
own_channel
checkout
pricing
marketing
crm
inventory
operations
logistics
hubs
finance
data_quality
contract_governance
```

Example detections:

- traffic up, conversion down -> funnel/conversion bottleneck;
- orders up, fulfillment delay up -> operations capacity bottleneck;
- commerce order count missing -> commerce data or demand bottleneck;
- commerce AOV below minimum -> ticket/mix/discount bottleneck;
- commerce repeat rate low -> CRM/retention bottleneck;
- GMV below projection, stockout high -> inventory bottleneck;
- freight cost above projection -> logistics cost bottleneck;
- paid GMV up, margin down -> marketing efficiency bottleneck;
- repeat purchase below projection -> CRM/retention bottleneck;
- own-channel GMV below ramp -> channel migration bottleneck;
- missing daily snapshots -> data quality bottleneck.

### 6. Diagnosis Layer

Transforms detected signals into a structured diagnosis.

Diagnosis shape:

```js
{
  domain: 'inventory',
  severity: 'high',
  confidence: 'partial',
  title: 'Ruptura pode estar limitando GMV observado',
  evidence: [],
  affectedKpis: [],
  affectedProjectionFamilies: [],
  likelyDrivers: [],
  recommendedActions: [],
  needsHumanReview: true
}
```

### 7. Recommendation Layer

Suggests actions without automatically changing official projections.

Examples:

- review freight premise;
- verify top SKUs with rupture;
- recheck marketplace fee assumptions;
- open revised scenario;
- request missing KPI days;
- inspect checkout approval;
- compare before/after ecommerce activation;
- ask RAI agent to produce operational diagnosis.

### 8. Reprojection Layer

Creates controlled re-projections when observed variance is persistent.

Rules:

- never mutate original scenario snapshot;
- generate a new official scenario snapshot;
- link it to observed variance;
- preserve original projection for comparison;
- mark why reprojection happened.

### 9. RAI Memory Layer

Feeds RAI agents with structured operational memory:

- daily KPI snapshots;
- monthly traces;
- variance records;
- bottleneck detections;
- timeline events;
- recommended actions;
- human review decisions.

This lets agents answer:

- "Why did payback move?"
- "What bottleneck is most likely?"
- "What changed after ecommerce activation?"
- "Which KPI needs manual review?"

## Proposed Backend Structure

```txt
server/modules/kpis/
  dailyKpi.service.js
  manualCollectionChecklist.js
  missingSnapshot.service.js
  kpiAggregation.service.js
  monthlyTrace.service.js
  variance.service.js
  kpiQuality.service.js
  bottleneckDetection.service.js
  diagnosis.service.js
  recommendation.service.js
  reprojection.service.js
  kpiNarrative.service.js
  kpi.routes.js
```

## Proposed Contracts

```txt
DailyKpiSnapshot
DailyKpiValue
KpiAggregationRule
KpiPeriodTrace
KpiQualityScore
ObservedProjectionVariance
BottleneckSignal
OperationalDiagnosis
Recommendation
ReprojectionRequest
KpiNarrative
```

## Proposed Tables

Already planned in `dge-2.0/db/schema-dge-2.sql`:

```txt
daily_kpi_snapshots
daily_kpi_values
monthly_kpi_traces
observed_projection_variances
timeline_events
```

Recommended future tables:

```txt
kpi_aggregation_rules
kpi_quality_scores
bottleneck_signals
operational_diagnoses
recommendations
reprojection_requests
```

## Bottleneck Signal Shape

```js
{
  key: 'inventory_stockout_gmv_risk',
  domain: 'inventory',
  severity: 'high',
  confidence: 'partial',
  detectedAt: '...',
  period: '2026-05',
  evidence: [
    { kpiKey: 'actual_stockout_rate_percent', observed: 18, threshold: 8 },
    { kpiKey: 'actual_monthly_gmv', variancePercent: -14 }
  ],
  affectedKpis: ['actual_monthly_gmv', 'actual_orders'],
  affectedProjectionFamilies: ['channel_migration_projection', 'financial_projection'],
  recommendedActions: [
    'Auditar SKUs de curva A com ruptura.',
    'Comparar GMV perdido por categoria.',
    'Recalibrar premissa de estoque antes de reprojetar.'
  ]
}
```

## Data Quality Score Shape

```js
{
  period: '2026-05',
  status: 'partial',
  score: 0.72,
  dailySnapshotCount: 22,
  expectedDays: 31,
  missingDays: [2, 7, 19],
  sourceMix: {
    manual: 22,
    ecommerce: 0
  },
  warnings: [
    'Dados ainda manuais.',
    '3 dias sem snapshot.'
  ]
}
```

## Variance Reason Codes

```txt
data_missing
traffic_below_projection
conversion_below_projection
ticket_below_projection
orders_below_projection
freight_above_projection
stockout_above_threshold
returns_above_projection
cancellation_above_projection
cac_above_projection
crm_retention_below_projection
hub_capacity_limit
operational_delay
formula_assumption_drift
unknown
```

## Detection Maturity Levels

### Level 1: Rule-Based

Simple thresholds and variance rules.

### Level 2: Multi-KPI Heuristics

Combines multiple KPI movements into likely causes.

### Level 3: RAI-Assisted Diagnosis

RAI agent generates diagnosis from structured facts, traces, and timeline.

### Level 4: Observed Learning

Persistent variance suggests premise updates and new scenario snapshots.

### Level 5: Predictive Detection

Forecasts bottlenecks before the month closes.

## First Build Slice

Do not start with all detections.

Start with:

1. aggregation rules;
2. monthly trace closure;
3. data quality score;
4. observed vs projected variance;
5. simple bottleneck signals;
6. timeline event;
7. narrative summary.

## Manual Collection Endpoints

Initial implementation:

```txt
GET /api/kpis/manual-checklist with stage=initial_dge
GET /api/kpis/manual-checklist with stage=ecommerce
POST /api/kpis/missing-snapshot
GET /api/kpis/collection-status with monthKey=YYYY-MM
GET /api/kpis/manual-dashboard with monthKey=YYYY-MM
```

The missing snapshot endpoint must create a timeline event instead of leaving a silent operational gap.
The collection status endpoint is the monthly close gate: it exposes coverage, unexplained missing days, known missing days, blocking reasons, and whether the month can be closed.
The manual dashboard endpoint is the frontend-facing read model for the collection cockpit: checklist, day-by-day status, latest monthly trace, summary, and next actions.

## Collection Obligation Engine

The cockpit must evaluate expected data by operational obligation, not by raw calendar month.

Rules:

- before DGE activation: no daily KPI collection is required;
- after DGE activation: `initial_dge` checklist applies;
- after ecommerce activation: `ecommerce` checklist applies;
- in monitoring mode: future days are not required yet;
- in closing mode: all required days after activation are evaluated;
- monthly close uses required days, not total calendar days.

This prevents false data-quality failures while preserving a strict close gate.

## Non-Negotiable Rule

The module should never only say "KPI changed".

It must move toward:

```txt
KPI changed -> possible driver -> evidence -> confidence -> action.
```
