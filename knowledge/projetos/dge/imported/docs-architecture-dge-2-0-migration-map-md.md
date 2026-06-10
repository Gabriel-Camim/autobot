---
title: DGE fonte - DGE 2.0 Migration Map
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-migration-map.md.'
source_path: docs/architecture/dge-2.0-migration-map.md
---

# DGE 2.0 Migration Map

Fonte original DGE 2.0: `docs/architecture/dge-2.0-migration-map.md`.

---

# DGE 2.0 Migration Map

## Migration Strategy

DGE 2.0 should be built through vertical slices. A vertical slice starts with a user/domain event, crosses backend truth, persists official memory, and returns normalized data to the UI.

This avoids a risky rewrite and prevents empty architecture work that does not improve the product.

## Priority Table

| Order | Domain | Current Risk | DGE 2.0 Target | First Deliverable |
| --- | --- | --- | --- | --- |
| 1 | Scenario + Finance + Formula Trace | Contracts and reports still depend on frontend-calculated data and implicit formulas | Backend owns official calculations, snapshots, formula registry, and execution traces | `POST /api/scenarios/calculate` |
| 2 | Reports | Report generation shares context and accepts fragile KPI payloads | Report service consumes official snapshot and normalized retrieval context | `modules/reports/report.service.js` |
| 3 | Contracts | Contract generation depends on frontend package state and AI failure can be hard to diagnose | Contract service consumes official snapshot and stores package/version memory | `modules/contracts/contract.service.js` |
| 4 | Sprint Memory | Old and new records coexist | Sprint service normalizes and persists all records through one contract | `modules/memory/sprintMemory.service.js` |
| 5 | Documents | Local documents, generated docs, Blob, and future Postgres service overlap | Document service owns metadata, versions, status, and storage references | `modules/documents/document.service.js` |
| 6 | Retrieval Context | Legacy RAG index and Postgres retrieval are both present | Retrieval service assembles traceable context from official sources | `modules/memory/retrieval.service.js` |
| 7 | Activation + KPI Intelligence | Activation and observed KPIs are not yet a full intelligence layer | Contract activation starts daily snapshots; KPI Intelligence aggregates, compares, detects bottlenecks and feeds RAI | `modules/kpis/monthlyTrace.service.js` |
| 8 | Assistant | Conversation, report, and contract flows still share conceptual paths | Assistant service records conversations and AI traces separately from generation workflows | `modules/ai/assistant.service.js` |
| 9 | Frontend Shell | `App.jsx` still concentrates too many responsibilities | App shell composes feature pages with normalized data only | `src/app/AppShell.jsx` |

## Slice 1: Scenario + Finance

### Why First

Scenario + finance is the base of the DGE. Reports, contracts, annexes, payback, KPIs, and decision traces all depend on it.

If this slice is official, every other AI or document flow becomes more reliable.

### Current Sources

- `src/calculations.js`
- `src/dataModel.js`
- `src/domain/finance/financeEngine.js`
- `src/features/scenarios/scenario.helpers.js`
- `src/features/projections/projection.viewModel.js`
- `server/reporting.js`
- `server/memoryRepository.js`
- `server/postgresAdapter.js`
- `server/localJsonAdapter.js`

### Target Backend Files

```txt
server/contracts/scenario.contract.js
server/contracts/kpi.contract.js
server/contracts/premise.contract.js
server/contracts/formula.contract.js
server/contracts/timeline.contract.js
server/modules/metrics/metricCatalog.js
server/modules/finance/projectionEngine.js
server/modules/finance/formulaRegistry.js
server/modules/finance/calculationTrace.js
server/modules/finance/scenarioValidator.js
server/modules/scenarios/scenario.normalizer.js
server/modules/scenarios/scenario.service.js
server/modules/scenarios/scenario.routes.js
```

### Target API

```txt
POST /api/scenarios/calculate
```

Input:

```txt
scenarioId
scenarioLabel
premises
options
source
```

Output:

```txt
scenarioSnapshot
calculationRun
formulaTraces
kpis
projections
derivedMetrics
timelineEvent
memory
warnings
```

### Rules

- Frontend may continue doing temporary preview calculations.
- Official report and contract generation must use backend snapshot.
- Backend must normalize incomplete scenario data.
- Backend must return warnings instead of throwing for recoverable missing optional fields.
- Fatal validation failures must return structured errors.
- Every official calculated KPI must point to a formula key and formula version.
- Formula traces can be summarized in the main response and fetched in full later.

## Slice 2: Reports

### Target

Report generation should accept an official scenario snapshot ID or a normalized snapshot payload, never arbitrary UI state.

### Required Contract

```txt
ReportRequest
ReportResponse
RetrievalContext
AiTrace
```

### Rules

- No fake local AI fallback.
- OpenAI failures return real diagnostic errors.
- Report response is normalized before UI render.
- AI trace must link to scenario snapshot and directives used.

## Slice 3: Contracts

### Target

Contract generation should be a backend workflow that consumes:

- official scenario snapshot;
- normalized KPI snapshot;
- selected directive context;
- contract template options.

### Rules

- Contract package must remain navigable if one annex fails.
- Contract activation dates must be normalized.
- Contract memory must store package, documents, version, status, and trace relation.
- No contract fallback should look like a successful AI output.

## Slice 4: Documents

### Target

Document Service becomes the official owner of generated and uploaded documents.

### Storage Rule

```txt
Postgres stores metadata and searchable text.
Blob stores heavy files.
Local filesystem is development or migration support.
```

### Required Contract

```txt
DocumentRecord
DocumentVersion
DocumentStorageRef
DocumentStatus
```

## Slice 5: Frontend Shell Extraction

### Rule

Do not start frontend extraction by moving JSX randomly.

Extract pages only after their data contracts exist.

### First Candidates

```txt
ScenarioPage
ReportsPage
ContractsPage
SprintMemoryPage
AssistantPage
DocumentsPage
```

### Frontend API Pattern

Each feature should own an API file:

```txt
src/features/scenarios/scenario.api.js
src/features/reports/reports.api.js
src/features/contracts/contracts.api.js
```

Those API files should call shared HTTP helpers and normalize responses before exposing data to components.

## Guardrails

### Never Migrate Without

- contract;
- normalizer;
- structured error;
- local adapter compatibility;
- Postgres target;
- validation command.

### Avoid

- moving large JSX blocks without changing data boundaries;
- adding new features during core migration;
- making localStorage official;
- letting AI generation swallow backend errors;
- making Postgres optional in production without a visible degraded state.

## Immediate Next Implementation Step

Create the first backend slice:

```txt
POST /api/scenarios/calculate
```

Minimum implementation:

1. accept current frontend scenario payload;
2. normalize it through a backend contract;
3. reuse existing calculation logic safely;
4. map premises and KPIs through the metric catalog;
5. emit formula execution traces for headline calculations;
6. save an official scenario snapshot through `memoryRepository`;
7. return normalized KPIs, projections, calculation run, and timeline event;
8. expose structured warnings.

This endpoint becomes the first real DGE 2.0 spine.
