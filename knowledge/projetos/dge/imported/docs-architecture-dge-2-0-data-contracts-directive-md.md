---
title: DGE fonte - DGE 2.0 Data Contracts Directive
category: projetos
tags:
- dge
- fonte-original
- arquitetura
- contratos
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-data-contracts-directive.md.'
source_path: docs/architecture/dge-2.0-data-contracts-directive.md
---

# DGE 2.0 Data Contracts Directive

Fonte original DGE 2.0: `docs/architecture/dge-2.0-data-contracts-directive.md`.

---

# DGE 2.0 Data Contracts Directive

## Purpose

DGE 2.0 must not persist or render raw payloads.

Every boundary must normalize data before it becomes official memory, UI state, AI context, formula input, KPI history, timeline event, or training candidate.

## Non-Negotiable Rule

```txt
No DGE 2.0 route writes raw payloads to Postgres.
No DGE 2.0 UI component should render raw API payloads.
No RAI agent should consume unnormalized operational memory.
```

## Contract Layers

### Input Contract

Normalizes external input before service logic.

Examples:

- API request body;
- imported spreadsheet row;
- ecommerce webhook payload;
- AI extracted value;
- manual KPI entry.

### Persistence Contract

Shapes data before insertion or update in Postgres.

Examples:

- nullable IDs become `null`;
- arrays are always arrays;
- metadata is always an object;
- dates become ISO/date strings;
- unrecognized status values fall back to safe defaults.

### Output Contract

Normalizes service responses before UI or AI consumption.

Examples:

- timeline event response;
- daily KPI snapshot response;
- RAI trace response;
- monthly trace response.

## Required Normalizers

DGE 2.0 must maintain normalizers for:

- `ActivationEvent`;
- `DailyKpiSnapshot`;
- `DailyKpiValue`;
- `TimelineEvent`;
- `MonthlyKpiTrace`;
- `ObservedProjectionVariance`;
- `AiAgent`;
- `AiAgentRun`;
- `RaiTrace`;
- `RaiTraceStep`;
- `TrainingExample`;
- `CalculationRun`;
- `FormulaExecutionTrace`;
- `ProjectionState`;
- `ProjectionTracePack`.

## Shared Constants

Shared constants must define allowed values for:

- activation stages;
- activation event types;
- timeline event types;
- KPI sources;
- automation levels;
- confidence statuses;
- record statuses;
- agent types;
- agent run types;
- RAI trace types;
- RAI step types;
- fine-tuning statuses.

## Safe Defaults

Defaulting is allowed when it prevents fragile payloads, but defaults must not hide operational truth.

Examples:

- missing metadata -> `{}`;
- missing KPI list -> `[]`;
- missing status -> `draft` or `confirmed`, depending on context;
- invalid source -> `manual`;
- invalid confidence -> `unknown`;
- invalid date -> current date only when the event is being created now.

## Rejection Rules

Some data should be rejected, not defaulted:

- daily KPI value without `key`;
- activation event without event type;
- formula trace without formula key;
- RAI trace step without step type;
- monthly trace without month key;
- training example without input/output JSON.

## Metadata Rule

Unknown fields should be preserved in `metadata` only when useful for audit or migration.

They should not leak into official top-level contracts unless explicitly promoted.

## RAI Cognitive Path Rule

RAI traces should store structured cognitive paths:

- source plan;
- selected context;
- decision path summary;
- verification steps;
- confidence status;
- output contract status.

They should not store or depend on private raw model reasoning.

## Evolution Rule

When a contract changes:

1. add or update constants;
2. update normalizer;
3. update SQL if persistence shape changes;
4. update API/service;
5. update docs;
6. run validation.
# Data Intake Routing

`data.intake.routing.v1` is the canonical contract for collector-to-module routing.

Rules:

- Data Intake routing is read-only, while `data.intake.submission.v1` governs writes through modular dispatch.
- `manual.kpi.*` contracts remain compatibility aliases only.
- each collector must declare target endpoint, target contract, payload shape, validation rules, roles, approval workflow, SLA, audit policy, BI impact and projection families impacted;
- frontend and n8n must consume routing instead of hardcoding endpoint decisions;
- no `POST /api/operations/data-intake/submit` exists in v1;
- governed submissions must call supported module services instead of writing directly to canonical tables;
- Shopee and Mercado Livre collectors remain benchmark/projection only and cannot create direct operational intelligence.
