---
title: DGE fonte - DGE 2.0 Module Registry
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-module-registry.md.'
source_path: docs/architecture/dge-2.0-module-registry.md
---

# DGE 2.0 Module Registry

Fonte original DGE 2.0: `docs/architecture/dge-2.0-module-registry.md`.

---

# DGE 2.0 Module Registry

## Financial Operations Runtime Core v1

Status: `active`

The runtime provides BRL operational subledger, double-entry managerial journals, receivables, payables, installments, observed settlements, assisted CSV/OFX statement import, mandatory human reconciliation review, reconciled cash, budget versions, financial intelligence and versioned accounting export packages.

It is intentionally distinct from the projected scenario finance engine and from official external bookkeeping.

## Purpose

The Module Registry is the architectural map of DGE 2.0.

It prevents the backbone from becoming a loose set of tables, endpoints, and future ideas.

Every major module must declare:

- status;
- maturity;
- domain;
- dependencies;
- exposed endpoints;
- tables read;
- tables written;
- next actions;
- risks.

## Statuses

```txt
active
skeleton
blueprint
```

Definitions:

- `active`: implemented enough to be used by the current backend.
- `skeleton`: intentionally prepared, but not a full operational source yet.
- `blueprint`: documented future direction, not current execution surface.

## Endpoint

```txt
GET /api/registry/modules
GET /api/registry/modules with status=active
GET /api/registry/modules with domain=projections
```

## Current Direction

Active backbone:

- scenario and finance engine;
- activation and timeline;
- Data Intake Layer;
- monthly KPI intelligence;
- adaptive projection engine;
- channel intelligence runtime inside projection core;
- official reforecast engine;
- commerce orders, behavior trace and exception center;
- ERP ecommerce-first operating core;
- configurable fulfillment pools, CDD distribution plans and location master;
- Operational Exception Nervous System;
- Backend Auth/Tenant Hardening;
- RAI agent backbone.

Skeleton:

- Backbone Truth & Flow Registry;
- ERP Completeness Audit;
- ERP Operational Debt Register;
- CDD Stock Semantics + Supplier Inbound Distribution;
- ERP Fiscal & Accounting Distribution Layer;
- Caos Lab Service Desk;
- n8n Automation Control Plane;
- BI/Superset Semantic Foundation;
- direct carrier/runtime connectors for Frenet and Loggi.

Blueprint:

- ecommerce real backend;
- frontend contract pack / final cockpit UI;
- external auth provider;
- enterprise context backbone.

## 20x Readiness Direction

The official 20x readiness roadmap lives in:

```txt
dge-2.0/docs/architecture/dge-2.0-roadmap-20x-readiness.md
```

The current priority is backend completeness before frontend:

```txt
fluxos claros
estados explicitos
contratos estaveis
ERP completo
Service Desk humano
n8n governado
Superset semantico
frete/logistica pronta
IA/RAI alimentada por fatos auditados
frontend renderizando view models
```

Pre-20x cycles:

1. Backbone Truth & ERP Completeness Audit.
2. Caos Lab Service Desk & Resolution Workflow.
3. n8n Control Plane + BI/Superset Semantic Foundation.

Newly registered roadmap blockers:

- `ERP Operational Debt Register`: exposes gaps and blockers through `GET /api/operations/roadmap-debt-register`, `bi_roadmap_blocker_dataset` and `bi_erp_operational_debt_dataset`.
- `CDD Stock Semantics + Supplier Inbound Distribution`: active v1 runtime that keeps CDD own stock separate from hub replenishment capacity and distributes purchase receipt items by physical destination.
- `ERP Fiscal & Accounting Distribution Layer`: active v2 runtime that separates stock movement, fiscal request, realized revenue and managerial margin; enforces fiscal clearance and patrimonial cost lineage without issuing NF-e directly.

Post-20x acceleration:

1. Heavy Backend Hardening v2.
2. Freight/Frenet/Loggi Runtime.
3. Superset real.
4. Bling live data controlled run.
5. Full end-to-end simulation.
6. IA/RAI operacional.
7. Ecommerce real backend.
8. UX/UI prototyping.
9. Frontend cockpit.

## ABCDEF Expansion Queue

This queue records the current safest order for expanding the operational backbone.

### A. Current Closed Spine

Governance, Data Intake Layer, ERP operating core, Commerce trace/exception center, automation traces, post-import KPI publication, bottleneck detection and the Operational Exception Nervous System are the current active spine. Data Intake now includes `data.intake.routing.v1`, `data.intake.submission.v1` and `data.intake.coverage_lock.v1`, exposing collector-to-endpoint routing, governed submission, modular dispatch and coverage auditing for frontend/n8n without creating a universal submit endpoint.

`integration_readiness_lock` is now the gate before real external integrations. Bling, Frenet, Loggi, n8n, ecommerce real and payment gateway must declare provider capabilities, dry-run/normalizer status, Data Intake fallback, Exception Hub mapping, BI visibility, idempotency and credential presence before production promotion. V1 does not call external APIs by default and never stores raw secrets.

`bling_erp_connector` is now active in v1.5 live-gate mode. It supports read-only live probe, fetch-preview traces, webhook trace/idempotency, mappings, assisted imports and reconciliation summaries. Bling remains auxiliary: sales/orders can feed Commerce/ERP reconciliation, invoices are fiscal context, and inventory is observed evidence only, never canonical DGE stock.

`fulfillment_distribution_core` is active as an ERP-configurable policy layer. A channel/pool can require exclusive CDD fulfillment for Galpao-style operations through `cddExclusiveFulfillment=true`, `allowDirectStoreShipment=false`, and `allowInternalTransferToCdd=true`, but this is not hardcoded globally. Other tenants can later model ship-from-store, pickup, regional distribution or hybrid operations by changing pool policy instead of rewriting the system. CDDs are physical ERP locations, marketplaces are channels/providers, and online stock mutation must happen through the physical location chosen by the pool policy.

CDD stock semantics are now explicitly corrected in the roadmap: CDD own stock is physical inventory in the CDD location, while eligible hub stock is replenishment capacity. A pool must not treat hub stock as a virtual sum of CDD stock unless a future sell-before-replenishment policy explicitly allows that promise.

### A1. Channel Runtime Consolidation

Before opening another large backbone, the next safe step is to consolidate the channelized projection runtime that now lives inside the projection core.

This consolidation block must:

- formalize `projection.channelRuntime.v1` as an explicit output contract;
- create an isolated smoke for channelized `runProjectionCore`, independent from the full reforecast workflow;
- expose `channelRuntime`, `channelFinancialImpact`, and `ownVsMarketplaceDeltas` through BI-ready datasets;
- update channel bottlenecks to read projection runtime evidence, not only daily facts and preview traces;
- keep Shopee and Mercado Livre as comparative/projection benchmarks only;
- document how audited channel evidence overrides aggregate assumptions;
- preserve official forecast/reforecast governance: preview first, approval later, official version only through the existing governed flow.

This block is intentionally a consolidation step, not a new feature family. It prevents the new channel runtime from becoming disconnected from BI, bottlenecks, governance, and future reforecast officialization.

Implementation markers:

- contract: `projection.channelRuntime.v1`;
- BI dataset: `bi_projection_channel_runtime_dataset`;
- smoke: `smoke:projection-core-channel-runtime`;
- smoke: `smoke:channel-runtime-bottlenecks`;
- smoke: `smoke:official-channel-reforecast`;
- bottleneck source: `daily_kpi_snapshots + bi_projection_channel_runtime_dataset`.

### A2. Official Channel Reforecast

Depois da consolidacao A1, o canal runtime pode passar pelo fluxo oficial completo sem criar motor paralelo.

O bloco A2 fecha:

- channel variance como evidencia oficial;
- candidate e case governados;
- reforecast preview com `projection.channelRuntime.v1`;
- review e proposta formal;
- aprovacao oficial por `owner` ou `admin`;
- criacao de `projection_version` oficial filha;
- lineage parent-child preservado;
- active reference atualizado;
- diff vs parent expondo `ownChannelGMV`, `monthlyProfit`, `projectedFreightCost`, `channelMarketplaceLeakage` e deltas own vs marketplace;
- BI lendo a versao oficial por `bi_projection_channel_runtime_dataset`.

Regra de fronteira:

```txt
own_channel pode gerar inteligencia operacional.
Shopee e Mercado Livre continuam apenas benchmark comparativo/projetivo.
```

### A3. Reforecast Active State And Dependency Control

Depois que reforecast oficial existe, a DGE precisa controlar o estado vivo da tese projetiva.

Este bloco adiciona:

- `projection.active_state.v1`;
- `reforecast.dependency_control.v1`;
- `official.reforecast.explainability.v2`;
- fila logica de cases por prioridade e dependencia;
- bloqueio de approval oficial quando a proposal nasceu contra baseline obsoleta;
- override apenas para alta hierarquia com justificativa;
- revalidacao de cases/proposals pendentes apos nova official version;
- explicabilidade oficial reutilizavel para reforecasts, com diff mensal baseline vs official, evidence ledger, active state aftermath e especializacao completa para `channel_runtime`;
- classificacao de familias reais de reforecast, incluindo `formula_reforecast`, `freight_reforecast`, `mixed_reforecast` e fallback geral;
- datasets BI para active state, dependency queue e explainability.
- endpoint de leitura `GET /api/projections/versions/:id/explainability`.

Regra operacional:

```txt
active reference define a versao oficial usada pelo BI.
active state define se essa versao esta saudavel ou possui pendencias.
dependency queue define qual case deve ser resolvido primeiro.
explainability define por que a versao oficial existe, o que mudou, quais evidencias sustentaram e quais pendencias sobraram.
```

### B. Operational Nervous System

Antes de abrir novas integracoes reais, a DGE deve manter ativo o sistema nervoso operacional:

- `operational.exception_hub.v1`;
- `operational.exception_graph.v1`;
- `operational.exception_impact.v1`;
- `operational.resolution_policy.v1`;
- `data.intake.coverage_lock.v1`.

Este bloco ja esta ativo e conecta Data Intake, ERP, Commerce, pagamentos, checkout, approvals, bottlenecks, stale reforecast, integrations e automations.

Regra:

```txt
evento -> excecao -> causa -> impacto -> responsavel -> SLA -> resolucao -> evidencia -> BI -> RAI futuro
```

Novos modulos devem entrar no hub como fonte normalizada de excecao e no coverage lock como endpoint coberto, runtime direto permitido, integracao assistida, fora de escopo ou bloqueado por falta de routing.

### C. Commerce Orders, Behavior Trace And Exception Center

Commerce deixou de ser skeleton. A camada ativa inclui:

- `commerce_orders`;
- `commerce_order_items`;
- `commerce_operational_events`;
- `commerce_behavior_events`;
- `commerce_exception_resolutions`;
- behavior trace minimo por `customer_hash`;
- payment failure trace;
- checkout friction;
- commerce exception center.

O escopo atual ainda nao e CDP completo e nao executa contato, cupom, email ou cobranca. A DGE observa, rastreia, diagnostica, governa excecoes e alimenta BI/RAI futuro.

### D. Bling Sales/Orders Normalizer

After the commerce identity and orders tables exist, Bling sales/orders can become canonical facts instead of temporary integration summaries.

This block should normalize:

- customer identity;
- order header;
- order items;
- payments;
- operational lifecycle events;
- channel;
- node mapping;
- status and payment status.

### E. Fulfillment Control Tower And Logistics Intelligence

Frenet, Loggi, pickup, and hub logic should come after commerce orders because fulfillment intelligence needs order context.

This block must respect the DGE vs ecommerce responsibility contract:

```txt
Ecommerce executes the customer promise.
DGE audits, learns, recommends, governs, and explains the operation.
```

Minimum dependencies:

- order id;
- order items;
- destination;
- origin node;
- fulfillment method;
- provider;
- package dimensions or estimated package profile;
- quoted freight;
- chosen freight;
- realized freight;
- shipment status.

Delivery methods:

- carrier shipping;
- local delivery;
- store pickup;
- split shipping;
- internal transfer then shipping;
- manual review.

Do not make DGE the checkout runtime in this block.

### F. Commerce Behavior Events Expansion

Behavior trace minimo ja existe. Depois que a superficie real de ecommerce/app estiver clara, behavior events podem expandir a inteligencia de funil:

- product view;
- search;
- add to cart;
- checkout started;
- purchase completed;
- app goal completed;
- campaign touch.

This layer should feed cohorts, conversion bottlenecks, migration to own channel, and LTV projections.

### G. Advanced Commerce Intelligence

Only after orders, customers, logistics, and behavior events are stable should DGE 2.0 expand into:

- LTV;
- CAC payback;
- cohort retention;
- repeat purchase probability;
- customer segmentation;
- own-channel migration projection;
- logistics margin leakage;
- GMV lost by stockout or freight friction.

## Rule

No major new DGE module should be implemented without first being classified in the registry.

## Operational Domain Map Expansion

O registry tambem passa a declarar os proximos dominios estruturais como `skeleton`, sem antecipar runtime ou schema:

- `heavy_backend_hardening_v2`;
- `production_readiness_plane`;
- `integration_reliability_plane`;
- `financial_operations_runtime`;
- `inventory_planning_replenishment`;
- `franchise_consignment_network`;
- `fiscal_document_lifecycle`.

O mapa oficial vive em:

```txt
docs/architecture/dge-2.0-operational-domain-map.md
```

Regras:

- o motor financeiro atual e projetivo; o subledger operacional ainda e futuro;
- consignacao franqueada nao e transferencia interna comum;
- emissao e escrituracao fiscal oficial permanecem na fronteira contador/provedor;
- `Heavy Backend Hardening v2` foi promovido para fundacao ativa; `Production Readiness Plane v1` e o proximo runtime.

## Isolamento Absoluto Do Piloto

O piloto/DGE 1.0 e uma prova de conceito historica congelada. Ele nao integra o Module Registry da DGE 2.0, nao recebe features novas e nao define compatibilidade obrigatoria.

O mount temporario foi removido. O piloto permanece congelado em `5173/8787`; o backend DGE 2.0 opera exclusivamente em `8788`. Nenhum modulo novo pode depender de `src/**`, rotas raiz de documentos/memoria ou services historicos do piloto.
# Runtime ativo: Inventory Planning & Replenishment v1

`inventory_planning_replenishment` esta ativo. Ele calcula risco de ruptura e materializa PO ou transferencia somente apos `inventory_owner_review -> finance_manager_final`. O proximo modulo declarativo da sequencia e `franchise_consignment_network`.

# Runtime ativo: Franchise Consignment Network v1

`franchise_consignment_network` esta ativo. Ele preserva propriedade patrimonial da marca durante consignacao, exige dupla aprovacao para movimento material, reconcilia sell-out antes da baixa e cria recebivel somente depois do fechamento diario aprovado pelo financeiro.

O proximo modulo declarativo da sequencia e `repository_layer_migration`.

# Runtime ativo: Repository Layer Migration + ERP Operator Directory v1

`repository_layer_migration` esta ativo. Services operacionais coordenam regra; repositories locais ao dominio encapsulam persistencia. `check:repository-boundary` bloqueia novo SQL em service.

`erp_operator_directory`, `operator_workforce_identity` e `operator_behavior_trace` tambem estao ativos. O ERP registra a pessoa operacional, Governance registra autenticacao e autorizacao, e links comportamentais conectam fatos sem duplicar os ledgers materiais.

O proximo modulo declarativo da sequencia e `caos_lab_service_desk`.

# Runtime arquitetural ativo: ERP Operational Kernel Reset v2

`erp_operational_kernel_reset` esta ativo como gate arquitetural. Ele nao cria frontend, integracao externa, executor n8n ou materialized views. Ele define a nova fundacao do ERP por nucleos operacionais e impede que novas regras sejam empilhadas fora do dono de nucleus.

O modulo publica `GET /api/operations/erp-operational-kernel` com:

- 12 nucleos oficiais;
- envelope operacional comum;
- mapa demo migravel;
- fontes legadas aposentadas;
- politica CRM/ICP com consentimento LGPD;
- readiness n8n por nucleo.

Batch 3 material concluido:

- `catalog_nucleus` migrou produtos, SKUs, variantes, categorias, kits, midia, fitment e readiness de publicacao para repositories/services do kernel;
- `pricing_promotion_nucleus` migrou price lists/books, bindings canal/location, preco efetivo, promocoes e cupons;
- `supplier_purchase_nucleus` virou `migrated`: fornecedores, supplier variant terms, PO, receipt, inbound distribution, confirmacao e custo de entrada sairam do monolito;
- `inventory_nucleus` virou `migrated`: locations, movements, balances, reservations, stock counts, stock transfers, snapshot diario, PDV/store sale, reconciliacao commerce material e exception material resolution sairam do monolito;
- SKU ativo/publicavel sem `costAmount` ou `supplierCostReference` bloqueia no cadastro com `sku_cost_required_for_active_variant`;
- datasets BI permanecem como views live; materialized views seguem adiadas para `BI/Superset Semantic Foundation`.

# Runtime arquitetural ativo: DGE Master Architecture Inventory

`dge_master_architecture_inventory` esta ativo como gate arquitetural antes de qualquer closure. Ele registra ERP, commerce, Bling, fulfillment, freight, finance, fiscal, Service Desk, operations, BI, Superset, IA/RAI, projections, snapshots, lineage, logs, cloud, banco, repository/service layer, cockpit, control plane, health status, UX/UI, frontend, homologacao e producao.

O modelo de fechamento passa a ter tres closures distintas:

- `erp_core_kernel_closure`;
- `dge_backend_kernel_closure`;
- `production_frontend_readiness_closure`.

`ERP Core Pre-Closure Hardening` tambem esta ativo/concluido como gate: publica `GET /api/operations/erp-core-preclosure`, valida CRUD/API, rotas finas, actionAvailability, error codes, BI ownership, auditabilidade e estabilidade da API publica por nucleo.

O `Service Desk / Error / Intelligence Hardening` tambem esta ativo/concluido como gate: publica formulario rico, dominios, politica L1/L2/L3 e `GET /api/operations/service-de[SECRET_REDACTED]`; valida erro seguro, fechamento auditavel, anexos com metadata, memoria de trabalho e boundary manual de ticket.

O proximo runtime oficial depois desse hardening e `Fulfillment/Freight + n8n Readiness Alignment`, nao Integration Reliability + n8n. Integration Reliability + n8n continua essencial, mas so deve entrar depois do ERP core closure e dos batches de backend nucleus restantes.

Batch 4 operational intelligence concluido:

- `intelligence_nucleus` virou `migrated` para contexto operacional ERP, workflow control, exception center, orquestracao de resolucao e KPI derivado;
- `erp.repository.js` foi aposentado como runtime e nao deve voltar ao facade ERP;
- Service Desk nao recebe criacao automatica de tickets por esse corte; excecoes continuam fatos operacionais delegados aos dominios proprietarios.

Regra de qualidade:

```txt
legado so pode ser removido apos equivalencia por smoke/check;
adapter temporario precisa de prazo e check de remocao;
runtime real nao volta para mega-repository ou service raiz.
```

O proximo modulo declarativo da sequencia e `fulfillment_freight_n8n_readiness_alignment`.
