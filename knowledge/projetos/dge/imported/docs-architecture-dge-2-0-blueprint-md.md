---
title: DGE fonte - DGE 2.0 Architecture Blueprint
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-blueprint.md.'
source_path: docs/architecture/dge-2.0-blueprint.md
---

# DGE 2.0 Architecture Blueprint

Fonte original DGE 2.0: `docs/architecture/dge-2.0-blueprint.md`.

---

# DGE 2.0 Architecture Blueprint

## Financial Operations Runtime Core v1

The DGE 2.0 now has an operational managerial subledger. It explicitly separates DGE projection, approved budget, financial obligation, observed settlement, human-reviewed reconciliation, reconciled cash and official external bookkeeping.

The runtime uses BRL-only double-entry journals, idempotent financial commands, titles with installments, statement preview for CSV/OFX, mandatory human review for every reconciliation match, governed monthly close, accounting export packages and financial projection-impact previews. It does not issue fiscal documents or replace the accountant.

## Purpose

DGE 2.0 is the new operational growth intelligence system for Galpao. The historical pilot proved the product thesis, but it is not the runtime foundation of this product.

The DGE 2.0 is not an incremental refactor of the pilot. It is built as a new system with its own backend, contracts, database and future frontend. The pilot may inform product decisions, but it must not become a technical dependency, compatibility requirement or source of operational debt.

## North Star

```txt
Frontend presents, guides, and orchestrates experience.
Backend validates, calculates, generates, registers, and audits.
Postgres preserves official memory.
AI reasons only from traceable context and returns explicit errors when it fails.
```

## 20x Readiness Doctrine

DGE 2.0 is no longer only a projection migration. It is now an operational backbone with ERP, Data Intake, Bling assisted import, Commerce, fulfillment pools/CDD, Exception Hub, auth/tenant hardening, reforecast, BI datasets, logistics facts and automation traces.

The next product milestone is backend completeness before frontend polish:

```txt
Backend owns truth.
ERP owns catalog/stock/price.
Data Intake owns human fallback/audit/intake.
Exception Hub owns cross-module risk.
Service Desk owns human resolution.
BI/Superset owns semantic analytics.
Frontend renders stable contracts.
20x accelerates execution, not architectural chaos.
```

Frontend final is intentionally blocked until the backend has enough flow, state, contract, exception, BI, human resolution and auth coverage. The official roadmap lives in:

```txt
dge-2.0/docs/architecture/dge-2.0-roadmap-20x-readiness.md
```

## ERP Operational Debt Register

The roadmap must record real blockers as operational debt, not informal planning notes.

Canonical contracts:

- `operational.roadmap_debt_register.v1`
- `erp.operational_gap_register.v1`

Canonical endpoint:

- `GET /api/operations/roadmap-debt-register`

Canonical BI datasets:

- `bi_roadmap_blocker_dataset`
- `bi_erp_operational_debt_dataset`

Current registered blockers include location ownership gaps, location fulfillment policy gaps, channel price gaps, channel setting gaps, missing suppliers, BI/service gap formula divergence, CDD stock semantic correction, and the missing fiscal/accounting distribution layer.

## CDD And Distribution Semantics

CDD-exclusive fulfillment is a Galpao policy, not a global DGE hardcode. The architecture must support other tenants later through pool/channel policy fields such as `cddExclusiveFulfillment`, `allowDirectStoreShipment`, `allowInternalTransferToCdd`, `allowSellBeforeCddReplenishment`, `maxReplenishmentPromiseQty`, `maxReplenishmentLeadTimeHours`, and `readyToShipOnlyByDefault`.

Correct stock semantics:

```txt
CDD tem estoque fisico proprio.
Hub tem estoque fisico proprio.
Pool calcula capacidade de reposicao, nao soma virtual do CDD.

cdd_ready_to_ship_qty = estoque fisico disponivel no CDD
cdd_replenishable_qty = estoque transferivel de hubs elegiveis para o CDD
online_publishable_qty = politica configuravel, nao verdade fixa
```

Active runtime block:

- `CDD Stock Semantics + Supplier Inbound Distribution v1`

Target flow:

```txt
purchase receipt / invoice
-> item recebido
-> distribuicao por destino fisico
-> movement direto ou staging + transferencia
-> estoque fica disponivel somente quando destino e movement forem validos
```

Supplier inbound distribution must support item-level allocation across CDDs, hubs, stores and franchise locations. Undistributed received quantity stays pending/staging and must not become channel-available automatically.

## Fiscal And Accounting Distribution

The DGE must separate physical movement, fiscal documentation, realized revenue and managerial margin:

```txt
Movimento de estoque != documento fiscal != receita realizada != margem gerencial.
```

Active runtime block:

- `ERP Fiscal & Accounting Distribution Layer v2`

Rules:

- DGE does not issue NF-e in this version.
- DGE classifies the operation and creates fiscal document requests.
- Fiscal rules are configurable and accountant-governed.
- Same-owner transfers do not become sales revenue by default.
- Franchisee flows are never treated as internal transfers without explicit fiscal rule.
- Missing fiscal operation rule blocks finalization when the movement crosses legal/fiscal boundaries.
- Commercial tax profiles reduce contribution margin with estimated sales taxes, channel commission, subsidized freight and configured variable expenses.
- Transfer receipt preserves patrimonial cost from the origin and updates the destination moving average without pretending it is a new purchase.
- Fiscal requests use an explicit audited lifecycle and block shipment while clearance is pending.

## Why This Exists

The current DGE already contains the right product intelligence:

- scenario simulation;
- financial projections;
- KPI interpretation;
- AI assistant;
- report generation;
- contract and annex generation;
- sprint memory;
- directive memory;
- document memory;
- Postgres backbone;
- retrieval-ready context.

The current risk is architectural, not conceptual. Too many domains still share large frontend state, partial payloads, legacy JSON, localStorage, and API responses without mandatory normalization.

DGE 2.0 exists to make those boundaries explicit before adding more features.

## Architectural Principles

### 1. Contracts Before Components

Every important object must have a normalized shape before it reaches UI components, AI prompts, report generation, contract generation, or persistence.

Minimum official contracts:

- `ScenarioSnapshot`;
- `ScenarioPremise`;
- `KpiSnapshot`;
- `ReportRequest`;
- `ReportResponse`;
- `ContractRequest`;
- `ContractResponse`;
- `ContractPackage`;
- `ContractActivation`;
- `DocumentRecord`;
- `DocumentVersion`;
- `SprintMemory`;
- `AiTrace`;
- `DirectiveDocument`;
- `RetrievalContext`;
- `MetricDefinition`;
- `FormulaDefinition`;
- `CalculationRun`;
- `FormulaExecutionTrace`;
- `TimelineEvent`;
- `ActivationEvent`;
- `DailyKpiSnapshot`;
- `MonthlyKpiTrace`;
- `ObservedProjectionVariance`.

No component should render raw API, Postgres, localStorage, or AI output directly.

### 2. Backend Owns Truth

Frontend can simulate for fast interaction, but official decisions must come from backend services.

Backend ownership:

- scenario validation;
- official financial calculation;
- snapshot creation;
- report generation;
- contract generation;
- annex generation;
- AI trace storage;
- memory retrieval;
- document versioning;
- audit metadata.

### 3. Postgres Is Canonical

Postgres is the official memory layer. Local JSON and `localStorage` can exist only as:

- migration source;
- development fallback;
- draft cache;
- UI convenience;
- import/export bridge.

Any production-grade DGE 2.0 flow must be able to explain where its official data is stored in Postgres.

### 4. AI Must Be Traceable

AI output is not a hidden magic layer. Every meaningful AI generation must record:

- input;
- normalized scenario used;
- directives used;
- retrieval context used;
- model;
- status;
- error code when applicable;
- output;
- timestamp;
- relation to report, contract, sprint, or decision.

No local fallback should pretend to be a successful AI answer.

### 5. Error Boundaries Are Product Features

Black screens are not acceptable in DGE 2.0.

Every failure should identify:

- failing layer;
- failing operation;
- whether official memory was affected;
- whether AI generated a real response;
- next recoverable action.

### 6. Formulas Are Official Records

DGE 2.0 must not trust its own calculations blindly.

Every official calculation must be traceable to:

- formula key;
- formula version;
- input metrics;
- intermediate values;
- output metric;
- engine version;
- scenario snapshot;
- calculation run;
- timestamp.

No official DGE 2.0 calculation should exist without a registered formula and version.

### 7. Activation Starts Operational Memory

DGE 2.0 has two major activation events:

- initial DGE activation, when the contract is officially activated;
- ecommerce activation, when the own-channel ecommerce goes live.

Daily KPI tracking starts at initial DGE activation. Ecommerce activation expands the tracking surface but does not reset history.

Every day after activation should either have a confirmed KPI snapshot or a missing-data timeline event.

### 8. Ecommerce Owns The Customer Promise

DGE 2.0 must not accidentally become the ecommerce checkout runtime.

Responsibility contract:

```txt
docs/architecture/dge-2.0-dge-vs-ecommerce-responsibility-contract.md
```

Rule:

```txt
Ecommerce executes the customer promise.
DGE audits, learns, recommends, governs, and explains the operation.
```

Freight, pickup, Loggi, Frenet, hub selection, and decentralized stock should enter DGE first as operational facts, recommendations, exceptions, KPIs, and cockpit queues.

DGE may recommend rulesets in later phases, but it should not block checkout, reserve stock, charge payment, or own the customer-facing promise in the first fulfillment/logistics phase.

## Target Backend Shape

```txt
server/
  app/
    createServer.js
    routes.js
    errors.js
  contracts/
    scenario.contract.js
    kpi.contract.js
    premise.contract.js
    metric.contract.js
    formula.contract.js
    timeline.contract.js
    report.contract.js
    contract.contract.js
    document.contract.js
    sprint.contract.js
    aiTrace.contract.js
    activation.contract.js
    dailyKpiSnapshot.contract.js
    monthlyKpiTrace.contract.js
  modules/
    scenarios/
      scenario.routes.js
      scenario.service.js
      scenario.repository.js
      scenario.normalizer.js
    finance/
      finance.service.js
      projectionEngine.js
      formulaRegistry.js
      calculationTrace.js
      scenarioValidator.js
    metrics/
      metricCatalog.js
      metric.service.js
    reports/
      report.routes.js
      report.service.js
      report.prompt.js
    contracts/
      contract.routes.js
      contract.service.js
      annex.service.js
    memory/
      memory.routes.js
      memory.service.js
      retrieval.service.js
      timeline.service.js
    kpis/
      dailyKpi.service.js
      kpiAggregation.service.js
      monthlyTrace.service.js
      variance.service.js
      kpiQuality.service.js
      bottleneckDetection.service.js
      diagnosis.service.js
      recommendation.service.js
      reprojection.service.js
      kpiNarrative.service.js
    documents/
      document.routes.js
      document.service.js
      document.repository.js
    ai/
      aiClient.js
      aiTrace.service.js
      aiErrors.js
    agents/
      agentRegistry.service.js
      agentRun.service.js
      raiTrace.service.js
  repositories/
    postgres/
    local/
  db/
    migrations/
    seeds/
```

The historical root `server/index.js` serves only the frozen pilot backend. The DGE 2.0 backend has its own entrypoint at `dge-2.0/server/index.js`, its own runtime surface, and port `8788`. Pilot compatibility is not a DGE 2.0 requirement.

## Target Frontend Shape

```txt
src/
  app/
    AppShell.jsx
    routes.js
    ErrorBoundary.jsx
  shared/
    api/
    ui/
    formatters/
    errors/
  domain/
    contracts/
    scenario/
    finance/
    documents/
  features/
    scenarios/
      ScenarioPage.jsx
      scenario.api.js
      scenario.viewmodel.js
    assistant/
      AssistantPage.jsx
      assistant.api.js
      assistant.viewmodel.js
    reports/
      ReportsPage.jsx
      reports.api.js
    contracts/
      ContractsPage.jsx
      contracts.api.js
    sprintMemory/
      SprintMemoryPage.jsx
      sprintMemory.api.js
    documents/
      DocumentsPage.jsx
      documents.api.js
```

The historical `src/App.jsx` belongs to the frozen pilot. The future DGE 2.0 frontend will be designed separately after backend contracts are stable.

## DGE 2.0 Migration Rule

Each migration step must satisfy five checks:

1. It has an explicit data contract.
2. It has a normalizer at every boundary.
3. It has a backend service or a clear reason why it is frontend-only.
4. It preserves DGE 2.0 contracts already declared as supported.
5. It passes `npm run validate`.

Contract directive:

```txt
docs/architecture/dge-2.0-data-contracts-directive.md
```

No DGE 2.0 route should write raw payloads to Postgres. Every input, persistence shape, and output must pass through a contract/normalizer.

## First Vertical Slice

The cleanest first DGE 2.0 slice is:

```txt
Scenario input -> backend calculation -> official snapshot -> report generation -> AI trace -> Postgres memory
```

This slice matters because contracts, reports, KPIs, and decisions all depend on the scenario being official.

## Not In The First Slice

Avoid starting with:

- full visual redesign;
- authentication;
- ecommerce integrations;
- Bling/Frenet/Loggi real integrations;
- pgvector;
- multi-tenant permissions;
- replacing every document flow at once;
- complete `App.jsx` rewrite.

These are valuable, but they should come after the core data spine is stable.

## Definition Of Ready For A Migrated Domain

A domain is ready to migrate when it has:

- current behavior mapped;
- source files identified;
- official contract drafted;
- API inputs and outputs listed;
- persistence destination defined;
- known legacy payloads listed;
- UI failure states defined.

## Definition Of Done For A Migrated Domain

A domain is migrated when:

- UI receives normalized data only;
- backend validates and owns official state;
- Postgres is the canonical destination when configured;
- local adapter remains compatible for development;
- errors are structured;
- AI traces are recorded when AI is involved;
- docs are updated;
- `npm run validate` passes.

## Operating Cadence

DGE 2.0 should advance by vertical slices, not by folder shuffling. The old migration cadence below remains historical context for the first backend extraction, but the current 20x-readiness cadence is:

Recommended order:

1. Backbone Truth & ERP Completeness Audit;
2. ERP Economic/Fiscal Runtime Hardening + Blueprint Truth Sync;
3. DGE Operational Domain Map + Roadmap Expansion;
4. Heavy Backend Hardening v2;
5. Production Readiness Plane;
6. Financial Operations Runtime Core;
7. Inventory Planning & Replenishment;
8. Franchise Consignment Network;
9. Caos Lab Service Desk;
10. Integration Reliability Plane + n8n Control Plane;
11. BI/Superset Semantic Foundation;
12. Fiscal Document Provider Lifecycle + XML/NF-e Assisted Import;
13. Freight/Frenet/Loggi Runtime;
14. Bling live data controlled run;
15. full backend end-to-end simulation;
16. IA/RAI operacional;
17. ecommerce real, UX/UI prototyping e frontend final.

## DGE 2.0 SQL Skeleton

The additive SQL skeleton lives in:

```txt
dge-2.0/db/schema-dge-2.sql
```

It extends the Build 1 schema with:

- metric and formula registries;
- calculation runs and formula execution traces;
- projection states and trace packs;
- activation events;
- daily KPI snapshots and values;
- monthly KPI traces;
- operational timeline events;
- observed vs projected variances;
- modular AI agents;
- RAI traces and structured cognitive path steps;
- fine-tuning candidate examples.

RAI cognitive paths should store structured summaries, source usage, verification steps, and decision paths. They should not depend on private raw model reasoning.

## KPI Intelligence Module

The KPI Intelligence Module is documented in:

```txt
docs/architecture/dge-2.0-kpi-intelligence-module.md
```

It is responsible for daily KPI collection, data quality, aggregation, observed vs projected variance, bottleneck detection, recommendations, controlled reprojection, and RAI-ready operational memory.

## Operational Domain Map

O mapa oficial dos dominios operacionais vive em:

```txt
docs/architecture/dge-2.0-operational-domain-map.md
```

Ele registra quatro ciclos conectados:

```txt
comercial -> fisico -> fiscal -> financeiro -> KPI -> reforecast
```

Regras:

- o `Scenario & Finance Engine` calcula projecoes; ele nao substitui o futuro subledger financeiro operacional;
- estoque consignado pode estar fisicamente na franquia e continuar patrimonialmente pertencendo a marca;
- sell-out reconciliado baixa consignacao e pode gerar recebivel, comissao ou repasse conforme contrato;
- transferencia, consignacao, venda B2B e remessa nao sao sinonimos;
- reembolso de pos-venda deve conectar estoque, financeiro e fiscal;
- APIs externas devem entrar por inbox/outbox, idempotencia, retry e replay;
- n8n orquestra; DGE decide regra, estado e aprovacao;
- IA le fatos auditados e recomenda; nao liquida, paga, emite documento ou aprova acao final.

`Heavy Backend Hardening v2` e `Production Readiness Plane v1` foram concluidos. O proximo runtime oficial e `Financial Operations Runtime Core v1`.

### Heavy Backend Hardening v2 entregue

- mutacoes materiais de estoque passam por command ledger idempotente;
- retries com a mesma chave e payload retornam o resultado anterior;
- a mesma chave com payload divergente bloqueia a operacao;
- balances recebem locks ordenados e invariantes de saldo nao negativo;
- reserva e baixa online/marketplace podem ocorrer em lote atomico;
- transferencias preservam custo patrimonial e evitam duplicacao em replay;
- precisao financeira, triggers de `updated_at` e schema drift possuem checks executaveis.

### Production Readiness Plane v1 concluido

- requests recebem `x-request-id` e trace tecnico sanitizado;
- health separa liveness de readiness;
- o piloto historico permanece congelado em `5173/8787`, fora da superficie de readiness DGE 2.0;
- o backend exclusivo DGE 2.0 responde em `8788`;
- rate limit PostgreSQL produz evidencia auditavel;
- retencao LGPD limpa apenas traces efemeros por CLI governada;
- ledgers materiais permanecem preservados;
- backup e restore usam PostgreSQL Docker efemero, recusam o banco canonico como destino e removem o container temporario;
- recovery policy inicial registra RPO `24h` e RTO `4h`.

O restore drill isolado registra evidencia sanitizada com status `verified`. Integracoes externas continuam bloqueadas pelo futuro `Integration Reliability Plane`.

## ERP Operational Kernel Reset v2

A DGE 2.0 agora possui um kernel operacional declarativo para o ERP. O objetivo e impedir que o ERP continue crescendo como acumulado de cadastros, endpoints e repositories grandes.

Cada nucleo do ERP deve obedecer ao envelope:

```txt
cadastro -> operacao -> consulta -> automacao readiness -> auditoria -> BI -> inteligencia
```

O kernel oficial vive em `erp.operational_kernel.v2` e e exposto por `GET /api/operations/erp-operational-kernel`.

Decisoes:

- reset agressivo com kernel novo em paralelo;
- demo migravel, sem descartar smokes e seeds atuais;
- cobertura total sempre;
- fontes legadas de runtime real devem ser migradas para o nucleus correspondente antes do closure;
- adapters temporarios exigem dono, nucleo substituto e check de remocao;
- CRM/ICP exige consentimento para perfil identificado e campanha nominal;
- behavior pre-consentimento permanece pseudonimizado;
- materialized views ficam adiadas para `BI/Superset Semantic Foundation`;
- n8n orquestra apenas depois de readiness declarado por nucleo.

O proximo runtime oficial nao e mais `Integration Reliability Plane + n8n Control Plane`. A DGE ja passou pelo `DGE Master Architecture Inventory`, pelo `ERP Core Pre-Closure Hardening` e pelo `Service Desk / Error / Intelligence Hardening`; antes do ERP Core Kernel Closure ainda precisa passar pelo alinhamento de Fulfillment/Freight + n8n readiness.

Batch 4 do kernel ERP aposentou o monolito `erp.repository.js` sem mudar o contrato publico das rotas `/api/erp/*`. `catalog_nucleus`, `pricing_promotion_nucleus`, `supplier_purchase_nucleus`, `inventory_nucleus` e `intelligence_nucleus` ja operam por repositories/services/adapters proprios em `server/modules/erp/nuclei/`. PDV/store sale, reconciliacao material de commerce e resolucao material de excecoes continuam no `inventory_nucleus`; contexto operacional, workflow control, exception center, orquestracao de resolucao e KPI derivado ERP passam ao `intelligence_nucleus`. SKU ativo/publicavel sem custo segue bloqueando na origem com `sku_cost_required_for_active_variant`, e `check:erp-completeness` deve permanecer com `totalGaps = 0`. BI continua em views live.

`ERP Core Pre-Closure Hardening` criou `erp.core_preclosure.v1` e `GET /api/operations/erp-core-preclosure`. O gate valida que cada nucleo ERP possui owner, CRUD/API, rota publica mapeada, facade fina, actionAvailability, auth roles, error codes, BI live datasets, audit/lineage/snapshot e cockpit lane. Isso deixa o ERP core pronto para os hardenings seguintes, mas nao declara o kernel fechado.
# Inventory Planning & Replenishment v1 checkpoint

O runtime preventivo de abastecimento esta ativo. A DGE 2.0 calcula demanda observada ponderada em 7, 30 e 90 dias, aplica fatores sazonais e projetivos aprovados, explode demanda de kits nos componentes fisicos, separa disponibilidade atual de inbound confirmado e cria alternativas auditaveis de compra, redistribuicao ou plano hibrido.

Nenhuma sugestao cria efeito material automaticamente. A execucao exige, sempre e sem limite minimo de valor, aprovacao sequencial do responsavel de estoque e do responsavel financeiro. Apos as duas aprovacoes, a DGE cria PO ou transferencia usando os runtimes canonicos existentes. O proximo runtime oficial e `Franchise Consignment Network v1`.

# Franchise Consignment Network v1 checkpoint

O runtime patrimonial e financeiro da rede franqueada esta ativo. Estoque enviado para franquia permanece pertencendo patrimonialmente a marca: `ship` registra transito consignado e somente `receive` libera saldo consignado disponivel na unidade. Sell-out entra por API interna governada ou contingencia Data Intake, exige reconciliacao humana e somente entao reduz o saldo.

O fechamento diario cria draft idempotente, resolve reembolso por SKU no price book contratual, calcula taxas configuraveis e exige aprovacao financeira antes de postar recebivel. Retorno, avaria, perda, divergencia e fallback franquia -> CDD preservam evidencia e dupla aprovacao. Integracoes Bling/PDV live continuam fora deste runtime.

Proximo corte oficial: `DGE Master Architecture Inventory`. O closure passa a ter sobrenome: `ERP Core Kernel Closure`, `DGE Backend Kernel Closure` e `Production/Frontend Readiness Closure`. Superset, IA/RAI, cloud/lakehouse, Next.js, n8n, Bling live, Freight/Frenet/Loggi e materialized views continuam posicionados como readiness ou blueprint futuro ate seus macros proprios.
