---
title: DGE fonte - DGE 2.0 Activation And KPI History
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-activation-and-kpi-history.md.'
source_path: docs/architecture/dge-2.0-activation-and-kpi-history.md
---

# DGE 2.0 Activation And KPI History

Fonte original DGE 2.0: `docs/architecture/dge-2.0-activation-and-kpi-history.md`.

---

# DGE 2.0 Activation And KPI History

## Purpose

DGE 2.0 must keep operating after the contract is activated.

The system should stop being only a projection layer and become a living operational memory that records daily KPI snapshots, monthly traces, and chronological events.

## Two Major Activation Events

### 1. DGE Initial Activation

This happens when the contract is officially activated.

From this point forward, the DGE must start daily operational tracking even if the ecommerce is not live yet.

Meaning:

- the partnership is active;
- the baseline scenario becomes official;
- the first operational timeline starts;
- daily KPI snapshot routine starts;
- manual KPI collection is allowed and expected;
- projection vs observed comparison can begin with partial data.

### 2. Ecommerce Activation

This happens when the ecommerce/own channel goes live.

From this point forward, the DGE continues daily KPI collection, but the KPI set expands.

Meaning:

- own-channel KPIs become active;
- funnel, checkout, cart, traffic, CRM, and logistics data start gaining more weight;
- the original DGE activation history remains intact;
- projection vs observed comparison becomes more operationally precise.

## Core Rule

```txt
DGE activation starts the tracking routine.
Ecommerce activation expands the tracking surface.
Neither event resets history.
```

The DGE should preserve one continuous chronological history.

## Daily KPI Snapshot Routine

Every active DGE project should produce a daily KPI snapshot.

The snapshot can be:

- manually entered;
- imported from a spreadsheet;
- imported from ecommerce;
- imported from ERP;
- imported from logistics tools;
- imported from CRM;
- inferred by AI and marked as pending confirmation.

Manual collection remains valid after ecommerce activation. It is not a temporary workaround; it is an official data source with lower automation level.

## Daily Snapshot Shape

```js
{
  id: 'daily-kpi-snapshot-...',
  projectId: '...',
  contractActivationId: '...',
  ecommerceActivationId: null,
  snapshotDate: '2026-05-13',
  periodType: 'daily',
  source: 'manual',
  automationLevel: 'manual',
  status: 'confirmed',
  kpis: [
    {
      key: 'actual_monthly_gmv',
      label: 'GMV real',
      value: 125000,
      unit: 'BRL',
      source: 'manual',
      confidence: 'manual',
      observedAt: '2026-05-13T12:00:00.000Z'
    }
  ],
  notes: 'Coleta manual antes do ecommerce estar ativo.',
  createdAt: '2026-05-13T12:00:00.000Z'
}
```

## Monthly Trace From Daily Snapshots

The monthly trace is not a separate guess. It is assembled from daily snapshots.

For each month, DGE should compute:

- daily snapshots received;
- missing days;
- confirmed vs estimated values;
- averages;
- totals;
- min/max;
- trend;
- variance versus projection;
- operational notes;
- formula versions used for comparisons.

Example:

```js
{
  month: '2026-05',
  dailySnapshotCount: 31,
  missingDays: [],
  projectedKpis: [],
  observedKpis: [],
  variance: [],
  timelineEvents: [],
  confidence: 'partial | complete | estimated',
  generatedAt: '...'
}
```

## Chronological History

DGE should preserve a timeline of every meaningful event:

- contract activated;
- DGE initial tracking started;
- daily KPI snapshot created;
- ecommerce activated;
- KPI imported;
- KPI manually corrected;
- report generated;
- projection recalculated;
- formula version changed;
- observed variance detected;
- monthly trace closed.

## Timeline Event Shape

```js
{
  id: 'timeline-event-...',
  projectId: '...',
  type: 'contract_activated',
  title: 'Contrato ativado',
  summary: 'A DGE iniciou rotina diaria de coleta de KPIs.',
  occurredAt: '2026-05-13T12:00:00.000Z',
  relatedIds: {
    contractActivationId: '...',
    scenarioSnapshotId: '...',
    calculationRunId: '...'
  },
  kpiKeys: [],
  status: 'confirmed'
}
```

## Activation Event Types

```txt
contract_activated
dge_tracking_started
daily_kpi_snapshot_created
daily_kpi_snapshot_corrected
ecommerce_activated
ecommerce_tracking_expanded
monthly_trace_closed
projection_recalculated
observed_variance_detected
formula_version_changed
```

## Pre-Ecommerce Daily KPIs

Before ecommerce activation, collect what can be observed manually or from existing systems:

- total GMV;
- marketplace GMV;
- orders;
- average ticket;
- marketplace fees;
- cancellations;
- returns/warranty;
- delivery cost;
- delivery SLA;
- customer contact capture;
- operational notes;
- contract status;
- implementation progress.

## Post-Ecommerce Daily KPIs

After ecommerce activation, continue all previous KPIs and add:

- own-channel GMV;
- own-channel orders;
- traffic;
- conversion rate;
- cart abandonment;
- cart recovery;
- checkout approval;
- payment failures;
- CRM opt-in;
- repeat purchase;
- ecommerce freight;
- pickup in store;
- app usage when available;
- campaign performance.

## Projection Vs Observed

Once daily snapshots exist, every monthly projection should be able to compare:

```txt
projected value
observed daily aggregation
variance
variance reason
confidence
action recommendation
```

This is where DGE 2.0 becomes a feedback system:

```txt
Project -> Activate -> Observe -> Compare -> Learn -> Reproject
```

## Storage Direction

Recommended Postgres tables:

```txt
activation_events
daily_kpi_snapshots
daily_kpi_values
monthly_kpi_traces
timeline_events
observed_projection_variances
```

The current `contract_activations`, `scenario_snapshots`, and `kpi_snapshots` should be reused and extended where possible.

Initial SQL skeleton:

```txt
dge-2.0/db/schema-dge-2.sql
```

This schema extends the current Build 1 database instead of replacing it.

## Automation Strategy

### Phase 1: Manual Routine

After DGE activation:

- daily manual KPI entry;
- daily snapshot saved;
- timeline event created;
- monthly trace assembled.

### Phase 2: Assisted Collection

- spreadsheets/imports;
- AI-assisted extraction from reports;
- validation against required KPI checklist.

### Phase 3: Ecommerce Integrations

- ecommerce platform;
- checkout;
- CRM;
- logistics;
- ERP/Bling;
- warehouse/stock.

### Phase 4: Adaptive Projection

- compare observed vs projected;
- detect recurring variance;
- recommend premise changes;
- create a new official scenario snapshot without deleting the original.

## Non-Negotiable Rule

Activation starts memory.

Every day after activation should either have:

- a confirmed daily KPI snapshot;
- a missing-data event explaining why it is absent.
