---
title: DGE fonte - DGE 2.0 Data Intake Layer Protocol
category: projetos
tags:
- dge
- fonte-original
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/operations/dge-2.0-manual-kpi-collection.md.'
source_path: docs/operations/dge-2.0-manual-kpi-collection.md
---

# DGE 2.0 Data Intake Layer Protocol

Fonte original DGE 2.0: `docs/operations/dge-2.0-manual-kpi-collection.md`.

---

# DGE 2.0 Data Intake Layer Protocol

## Purpose

Data Intake Layer is the official DGE 2.0 operating layer for governed data entry during development, implementation, early ecommerce activation, assisted imports, future automations, audit, SLA and contingency.

Manual KPI collection is one source mode inside Data Intake. It is not the module identity anymore, and it is not a temporary workaround.

The goal is to preserve daily operational memory even before integrations are ready.

Legacy contract aliases remain valid:

- `manual.kpi.collection_blueprint.v1` is the compatibility alias for `data.intake.blueprint.v1`;
- `manual.kpi.collection_obligation.v1` is the compatibility alias for `data.intake.obligation.v1`.
- `manual.kpi.collectors.read.v1` and `manual.kpi.collector.detail.v1` remain compatibility aliases for the canonical Data Intake read endpoints.

## Submission Routing v1

Data Intake now exposes a canonical read-only routing layer:

```txt
GET /api/operations/data-intake
GET /api/operations/data-intake/:collectorKey
GET /api/operations/data-intake/:collectorKey/routing
GET /api/operations/data-intake/coverage-lock
```

Routing contract:

```txt
data.intake.routing.v1
```

Each collector declares:

- target endpoint and HTTP method;
- target contract;
- required and optional payload fields;
- example payload;
- entry, review and final audit roles;
- approval workflow;
- snapshot target;
- BI datasets and projection families impacted;
- automation readiness;
- audit and idempotency policy;
- guardrail `noUniversalSubmitEndpoint = true`.

The legacy endpoints remain valid:

```txt
GET /api/operations/manual-collectors
GET /api/operations/manual-collectors/:collectorKey
```

They now include the canonical routing block, but keep the legacy response root for compatibility.

## Coverage Lock

Data Intake now owns a coverage lock for operational write paths.

Contract:

```txt
data.intake.coverage_lock.v1
```

The lock classifies each mutable endpoint as:

- covered by collector;
- allowed as direct system runtime;
- assisted external integration;
- out of scope for v1;
- blocked by missing routing.

The goal is not to force every write through a universal form. The goal is to prevent new modules from entering the DGE without an explicit operational door, audit policy, role, SLA and future automation path.

Integration Readiness Lock extends this rule to external providers.

Before Bling real, Frenet, Loggi, n8n, ecommerce webhooks or payment gateway are promoted, `integration.readiness_lock.v1` must confirm:

- Data Intake collector/fallback exists;
- dry-run exists when the provider can write operational facts;
- Exception Hub mapping exists;
- BI datasets exist;
- idempotency is declared;
- no secret value is stored or returned.

Manual remains a `sourceMode` and contingency. It is not the module identity.

## Core Rule

```txt
Every day after DGE activation must have either:
- a daily KPI snapshot;
- or a missing-snapshot event with a reason.
```

No silent gaps.

## Governance Contract

Data Intake follows a strict contract:

1. a confirmed daily snapshot must include every required KPI for its current stage;
2. incomplete snapshots are rejected unless explicitly submitted as an incomplete tracked exception;
3. every snapshot receives a collection assessment in metadata: checklist version, stage, required count, provided count, missing keys, coverage, and SLA status;
4. missing days must be registered as timeline events with a reason code;
5. monthly close is blocked when required-day coverage is below policy or when required missing days are unexplained;
6. a forced partial close must be explicit and remains traceable in the monthly trace metadata.

## Obligation Engine

The cockpit must not require data before the operation is expected to produce it.

For every calendar day, DGE resolves:

- whether DGE tracking was active;
- whether ecommerce was active;
- which collection stage applies;
- whether collection is required, future, or not applicable;
- which KPI checklist is mandatory;
- the SLA due date.

Two modes exist:

- `monitoring`: month-in-progress view. Future days are not required yet.
- `closing`: official monthly close view. All required days after activation are evaluated.

## Collection Stages

### initial_dge

Starts when the contract is activated and the DGE begins operational tracking.

Minimum daily KPIs:

- total GMV;
- marketplace GMV;
- orders;
- average ticket;
- freight average;
- cancellations;
- returns/warranty;
- customers with direct contact;
- implementation progress;
- operational note.

### ecommerce

Starts when the own-channel ecommerce goes live.

Continue all `initial_dge` KPIs and add:

- ecommerce GMV;
- ecommerce orders;
- sessions/traffic;
- conversion rate;
- cart abandonment;
- cart recovery;
- checkout approval;
- payment failures;
- ecommerce freight;
- pickup in store;
- CRM opt-in;
- repeat purchase.

## Daily Routine

Recommended collection window:

```txt
End of business day or next morning before 10:00.
```

For each day:

1. collect required KPIs for current stage;
2. record optional notes;
3. mark source as `manual`;
4. mark confidence/source mode as `manual` when applicable;
5. save daily snapshot;
6. review timeline event.

## Missing Snapshot Routine

If data cannot be collected:

1. register missing snapshot;
2. include reason;
3. mark whether it can be recovered later;
4. create timeline event;
5. allow later correction with a real snapshot.

Reason examples:

- responsible unavailable;
- data source unavailable;
- ecommerce not live yet;
- operational report delayed;
- holiday or no operation;
- migration/import issue;
- unknown.

## Correction Rule

If a missing day is later filled:

- save a normal daily snapshot for that date;
- keep the missing event in timeline;
- create a correction timeline event;
- monthly close should prefer confirmed KPI snapshot over missing event.

## Quality Impacts

Manual data is valid, but quality should reflect:

- manual-only period;
- missing days;
- corrected days;
- mixed sources;
- estimated values;
- confirmed values.

## Endpoints

```txt
GET /api/kpis/manual-checklist with stage=initial_dge
GET /api/kpis/manual-checklist with stage=ecommerce
POST /api/kpis/daily-snapshots
POST /api/kpis/missing-snapshot
GET /api/kpis/collection-status with monthKey=YYYY-MM
GET /api/kpis/manual-dashboard with monthKey=YYYY-MM
POST /api/kpis/monthly-traces/close
```

Monthly close policy:

- default minimum coverage: 80%;
- all required missing days must have either a daily snapshot or a missing snapshot timeline event;
- use `forcePartialClose=true` only for an explicit exception.

The manual dashboard endpoint is the preferred read model for future frontend screens. It returns checklist, daily rows, activation milestones, monitoring status, closing status, latest monthly trace, and next actions.

## Future Submission Workflow

## Submission Workflow v1

Data Intake now has a governed submission workflow:

```txt
POST /api/operations/data-intake/:collectorKey/submissions
GET /api/operations/data-intake/submissions
GET /api/operations/data-intake/submissions/:id
POST /api/operations/data-intake/submissions/:id/review
POST /api/operations/data-intake/submissions/:id/final-audit
```

Contract:

```txt
data.intake.submission.v1
```

The workflow uses the routing contract to validate payload, role, endpoint, audit policy and SLA. It creates a traceable submission before any modular write.

Status lifecycle:

```txt
submitted -> pending_review -> pending_final_audit -> approved_for_dispatch -> audited_operational_fact_created
```

Failure states:

```txt
validation_failed
review_rejected
audit_rejected
module_write_failed
```

V1 dispatch is intentionally conservative, but now supports the core operational write modules:

- `POST /api/channels/daily-facts`;
- `POST /api/erp/products`;
- `POST /api/erp/price-lists`;
- `POST /api/erp/promotions`;
- `POST /api/erp/inventory/stock-counts`;
- `POST /api/erp/inventory/movements`;
- `POST /api/erp/inventory/transfers`;
- `POST /api/erp/store-sales`;
- `POST /api/commerce/orders`;
- `POST /api/logistics/freight-facts`;
- `POST /api/after-sales/cases`;
- `POST /api/integrations/runs`;
- `POST /api/operations/nodes`;
- `POST /api/governance/tenant-users`;
- `POST /api/commerce/behavior-events`;
- `POST /api/commerce/exceptions/:id/resolve`;
- `POST /api/erp/exceptions/:id/resolve`;
- `GET` collectors remain read-models and do not create writes;
- Bling import and monthly close remain dedicated future workflows;
- other collectors can be submitted, reviewed and audited, but unsupported dispatch is recorded as `module_write_failed`;
- no `POST /api/operations/data-intake/submit` exists;
- Data Intake never writes around the target module contract.

## Frequency Semantics

Data Intake is not the same thing as daily collection. The official frequency model is:

- `daily`: recurring operational facts that create a daily obligation;
- `monthly`: recurring monthly close or governance obligation;
- `scheduled_review`: periodic review, but not a daily fact;
- `event_driven`: master data or operational setup that appears only when created, imported or changed;
- `exception_driven`: adjustment, divergence or failure that appears only when there is an exception.

ERP master data is event-driven:

- `erp_product_catalog_review`;
- `erp_price_list_review`;
- `erp_promotion_review`;
- `erp_hub_location_review`;
- `tenant_actor_review`;
- `erp_stock_transfer_review`.

ERP operational facts remain daily when they represent daily movement or audit:

- `erp_inventory_daily_count`;
- `erp_store_sale_daily`;
- `erp_order_stock_reconciliation`.

ERP exceptions are not daily obligations:

- `erp_inventory_adjustment_review`.

Exception and observability collectors are also `exception_driven` or `event_driven`, not daily obligations:

- `commerce_behavior_event_review`;
- `commerce_payment_failure_review`;
- `commerce_exception_resolution_review`;
- `erp_exception_resolution_review`;
- `automation_exception_review`;
- `bling_import_exception_review`;
- `reforecast_stale_baseline_review`.

The cockpit exposes this separation through `dailyIntakeDesk`, `erpMasterDataDesk` and `exceptionIntakeDesk`, while `manualCollectionDesk` remains only as a legacy-compatible field.

## Operational Exception Hub Link

Data Intake submissions that fail validation, miss SLA, wait for audit or fail modular dispatch now appear in the Operational Exception Hub. The hub is the cross-module queue for:

- Data Intake failures;
- ERP exceptions;
- Commerce/payment/checkout exceptions;
- approval delays;
- bottleneck signals;
- stale reforecast items;
- integration and automation issues.

Data Intake remains the portaria of operational data. The Exception Hub is the nervous system that explains impact, duplicate relationships, root cause, responsible role and resolution delegation.

BI datasets:

- `bi_data_intake_submissions_dataset`;
- `bi_data_intake_submission_audit_dataset`;
- `bi_data_intake_sla_dataset`.
- `bi_data_intake_coverage_lock_dataset`.

## Owner

The DGE operator or implementation lead owns daily collection until automated integrations are active.
