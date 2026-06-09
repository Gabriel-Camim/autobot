---
title: DGE fonte - DGE 2.0 Roadmap 20x Readiness
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-roadmap-20x-readiness.md.'
source_path: docs/architecture/dge-2.0-roadmap-20x-readiness.md
---

# DGE 2.0 Roadmap 20x Readiness

Fonte original DGE 2.0: `docs/architecture/dge-2.0-roadmap-20x-readiness.md`.

---

# DGE 2.0 Roadmap 20x Readiness

## Financial Operations Runtime Core v1 Completed

The operational finance macro is active. DGE 2.0 records idempotent financial commands, receivables, payables, installments, balanced managerial journals, observed settlements, assisted statement imports, human-reviewed reconciliation, reconciled cash, monthly budgets, financial variance previews and accounting export packages.

Resolved blockers:

- `financial_subledger_missing`
- `accounts_receivable_runtime_missing`
- `accounts_payable_runtime_missing`
- `cash_settlement_reconciliation_missing`
- `after_sales_financial_fiscal_link_missing`

The next runtime is **Inventory Planning & Replenishment v1**.

## Tese

A DGE 2.0 ja passou de motor de projecao para backbone operacional: ERP, Data Intake, Bling assisted import, Commerce, fulfillment pools/CDD, Exception Hub, auth/tenant, reforecast, BI datasets, logistics facts e automation traces existem em v1/v2.

O proximo objetivo nao e frontend bonito. O objetivo e fechar a DGE como plataforma operacional aceleravel:

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

Regra de direcao:

```txt
Frontend final fica bloqueado ate o backend ter fluxo, estado, contrato, excecao, BI, resolucao humana e auth suficientes.
20x acelera execucao; nao autoriza bagunca arquitetural.
```

## Estado Atual

### Active Spine

- ERP operating core, catalog v2, price lists, coupons, purchase receipt, stock ledger, transfers, CDD/pool policy.
- Data Intake Layer com routing, submission, modular dispatch e coverage lock.
- Bling assisted import v2 com previews, mappings, hash guard, reconciliation e estoque observado.
- Commerce orders, behavior trace, payment failure trace e exception center.
- Marketplace/CDD fulfillment pools e reconciliation gates.
- Operational Exception Hub, graph, impact e resolution delegation.
- Integration Readiness Lock para Bling, Frenet, Loggi, n8n, ecommerce real e payment gateway.
- Tenant Auth Hardening com `x-dge-user-key`, role/scope e bloqueio de `system_integration` para finais.
- BI datasets/Superset-ready views amplos.
- Reforecast oficial com active state, dependency queue, inventory/channel runtime e explainability.

### Needs Completion

- Action availability por item e auth coverage continuamente ampliada para novos writes.
- Heavy Backend Hardening v2 para transacoes, concorrencia de estoque, precisao financeira e schema drift.
- Production Readiness Plane para observabilidade, backup/restore, LGPD, segredos, rate limit e recuperacao.

### Checkpoint: Heavy Backend Hardening v2 concluido

O estoque canonico agora possui command ledger, idempotencia material, locks ordenados, invariantes no service e no banco, lote atomico para reserva/baixa online e marketplace, protecao contra contagem obsoleta, custo medio protegido em transacao, precisao numerica declarada, triggers de `updated_at` e manifesto de schema drift.

Com essa fundacao fechada, `Production Readiness Plane v1` passa a ser o proximo runtime oficial.
- Financial Operations Runtime com subledger operacional proprio: pagar, receber, caixa, liquidacao, conciliacao, centros de custo e lancamentos gerenciais.
- Inventory Planning & Replenishment para giro, cobertura, safety stock, lead time, sugestao de compra e redistribuicao preventiva.
- Franchise Consignment Network com posse fisica separada de propriedade patrimonial e sell-out via Bling/PDV reconciliado.
- Integration Reliability Plane com inbox/outbox, retry, replay e dead-letter.
- Fiscal Document Provider Lifecycle + XML/NF-e assisted import.
- Caos Lab Service Desk para transformar excecao em trabalho humano.
- n8n Automation Control Plane real: workflows, promotion gates, dead-letter e fallback.
- BI/Superset Semantic Foundation: dataset certification, metric catalog, dashboard families e freshness.
- Freight/Frenet/Loggi runtime: quote, label, tracking, reversa, custos e SLA.
- IA/RAI operacional com context packs curados e recomendacao governada.

### Later

- Frontend final.
- Ecommerce real runtime.
- External auth provider/JWT.
- ML/fine-tuning.

## Lacunas E Oportunidades

### Backbone / Hardening

Faltam tres mapas para a DGE crescer sem perder controle:

- `operational.flow_registry.v1`: fluxo -> contrato -> endpoints -> tabelas -> excecoes -> smokes.
- `operational.state_machine_registry.v1`: estados e transicoes permitidas por dominio.
- `operational.smoke_matrix.v1`: smoke -> fluxo validado -> risco coberto.

Checks necessarios:

- `check:flow-registry`
- `check:auth-coverage`
- `check:state-machine-coverage`
- `check:roadmap-truth`

Oportunidade: usar esses mapas como fonte do futuro Frontend Contract Pack e como contexto deterministico para RAI.

### ERP Completeness

O ERP ja tem catalogo, estoque, preco, cupons, kits, fornecedores, compras, locations, CDD, transfers e PDV. O que falta e o ERP dizer quando um cadastro esta realmente pronto para operar/publicar.

Completeness audit deve apontar:

- produto sem lifecycle correto;
- SKU sem categoria, fornecedor, custo, dimensoes de pacote ou midia principal;
- SKU ativo em canal sem price list/preco vigente;
- SKU sem channel settings para ecommerce, Shopee, Mercado Livre ou loja fisica relevante;
- produto sem ordenacao geral/categoria quando o canal exigir catalogo;
- produto com compatibilidade de moto ausente quando a categoria exigir;
- kit/bundle com componente sem estoque/preco;
- fornecedor sem dados minimos;
- purchase receipt sem custo, divergencia ou movement;
- CDD/hub sem actor/responsavel, capacity ou status operacional.

Oportunidade: o completeness audit vira a checklist oficial antes de ecommerce real, BI executivo e IA de recomendacao.

### ERP Operational Debt Register

O Ciclo 1 tambem passa a registrar dores reais como divida tecnica/bloqueio de avanco, nao como comentario solto de planejamento.

Contrato:

- `operational.roadmap_debt_register.v1`
- `erp.operational_gap_register.v1`

Endpoint:

- `GET /api/operations/roadmap-debt-register`

Datasets:

- `bi_roadmap_blocker_dataset`
- `bi_erp_operational_debt_dataset`

Dividas registradas e estado atual:

| Debt | Origem | Urgencia | Count | Status | Bloqueia |
| --- | --- | --- | ---: | --- | --- |
| `location_missing_actor_or_role` | `bi_erp_location_master_dataset` | high | 0 | `resolved_by_seed_backfill` | - |
| `location_missing_fulfillment_policy` | `bi_erp_location_master_dataset` | high | 0 | `resolved_by_seed_backfill` | - |
| `sku_active_channel_without_valid_price` | `bi_erp_catalog_publication_readiness_dataset` | high | 0 | `resolved_by_seed_backfill` | - |
| `sku_channel_settings_missing` | `bi_erp_catalog_publication_readiness_dataset` | medium | 0 | `resolved_by_seed_backfill` | - |
| `sku_missing_supplier` | `erp.catalog_completeness.v1` | medium | 0 | `resolved_by_seed_backfill` | - |
| `gap_formula_alignment` | BI + service audit | high | 0 delta | `resolved_by_formula_alignment` | - |
| `cdd_stock_semantics_correction` | architecture blueprint | critical | 0 | `resolved_by_runtime_gate` | - |
| `distribution_fiscal_accounting_layer_missing` | architecture blueprint | critical | 0 | `resolved_by_runtime_hardening` | - |
| `sales_tax_profile_not_applied` | economic runtime audit | critical | 0 | `resolved_by_runtime_hardening` | - |
| `transfer_cost_lineage_incomplete` | stock transfer runtime audit | critical | 0 | `resolved_by_runtime_hardening` | - |
| `fiscal_clearance_not_enforced` | fiscal request runtime audit | critical | 0 | `resolved_by_runtime_hardening` | - |
| `economic_fiscal_write_auth_missing` | auth coverage audit | high | 0 | `resolved_by_runtime_hardening` | - |
| `blueprint_runtime_status_drift` | roadmap truth audit | high | 0 | `resolved_by_truth_sync` | - |

Regra: uma divergencia entre service e BI deve reaparecer como `gap_formula_alignment`. O estado resolvido acima e validado pelos checks; nao e uma dispensa futura de auditoria.

Novos blockers estruturais estao registrados no runtime `operational.roadmap_debt_register.v1` por familia:

- hardening de banco;
- subledger financeiro;
- franquias e consignacao;
- planejamento de abastecimento;
- lifecycle fiscal externo;
- confiabilidade de integracoes;
- readiness de producao.

### Bling / Marketplace / Reconciliation

Bling assisted import existe, mas precisa de uma rodada controlada com dado real Galpao:

- live probe opt-in;
- fetch preview real;
- mapping governance real;
- import assistido de pedidos;
- estoque observado como reconciliation evidence;
- no canonical overwrite.

ML/Shopee continuam sem API direta. O estoque publicado futuro deve nascer como sugestao DGE por pool/CDD, nao como escrita automatica.

### n8n

Automation backbone registra runs, steps e webhooks. Falta controlar workflows externos.

`n8n Automation Control Plane v1` deve governar:

- workflow registry;
- trigger policy;
- endpoint allowlist;
- payload contract;
- idempotency key;
- retry/backoff;
- dead-letter;
- fallback manual/Data Intake;
- promotion gate: `draft -> dry_run -> supervised -> active`;
- Exception Hub e Service Desk para falha.

n8n executa orquestracao. A DGE decide contrato, estado, auditoria e aprovacao.

### Service Desk / Caos Lab

Exception Hub detecta, prioriza e delega, mas ainda nao governa a execucao humana.

`Caos Lab Service Desk & Resolution Workflow v1` deve criar:

- tickets linkados a exception, pedido, SKU, hub, CDD, transferencia, mapping, approval, BI dataset, automation run e integration run;
- SLA, assignment, comments, evidence, playbooks, escalation e outcome;
- idempotencia por exceptionKey + entity;
- filas por role/actor/hub/canal;
- reprocess action somente quando dominio permitir.

Sem Service Desk, a DGE aponta problema. Com Service Desk, ela organiza resolucao.

### BI / Superset

Ha muitos datasets. Falta certificacao semantica.

`BI/Superset Semantic Foundation v1` deve definir:

- dataset certification;
- metric definitions;
- common dimensions;
- ownership por dominio;
- freshness/SLA por dataset;
- sensitive fields policy;
- dashboard families oficiais.

Superset deve consumir views semanticas certificadas, nao tabelas cruas.

### Freight / Frenet / Loggi

Freight economics e logistics facts ja existem. Falta carrier runtime:

- quote request/response;
- comparacao Frenet/Loggi/motoboy/retirada;
- label lifecycle;
- tracking lifecycle;
- shipment exception;
- reverse logistics;
- custo cotado vs cobrado vs realizado;
- origem CDD/pool;
- impacto em margem/reforecast.

Frenet/Loggi entram depois de readiness lock, Service Desk e BI semantic minimo.

### IA / RAI

RAI backbone existe, mas ainda nao deve virar agente operacional autonomo.

Antes de IA operacional:

- context packs de Exception Hub, Service Desk, BI, ERP, Commerce e Reforecast;
- trace curation;
- evals;
- policy de recomendacao vs acao;
- proibicao de execucao final sem aprovacao.

IA recomenda playbook, causa provavel, prioridade e risco. Nao executa cobranca, cupom, compra, ajuste, aprovacao ou contato externo.

## Macros Do Roadmap

### Macro A: Backbone Truth & Flow Registry

Contratos:

- `operational.flow_registry.v1`
- `operational.state_machine_registry.v1`
- `operational.smoke_matrix.v1`

Interfaces planejadas:

- `GET /api/operations/flow-registry`
- `GET /api/operations/state-machines`

Cobrir: Data Intake, Bling, ERP, purchase receipt, stock count, transfers, marketplace allocation, CDD replenishment, commerce gates, Exception Hub e reforecast officialization.

### Macro B: ERP Completeness & Master Data Hardening

Contratos:

- `erp.catalog_completeness.v1`
- `erp.channel_publication.v1`
- `erp.vehicle_fitment.v1`
- `erp.supplier_purchase_flow.v1`
- `erp.price_list_governance.v1`
- `erp.coupon_policy.v1`

Interfaces planejadas:

- `GET /api/erp/catalog/completeness`
- `GET /api/erp/products/:id/publication-readiness`
- `GET /api/erp/skus/:sku/channel-readiness`
- `POST /api/erp/purchase-orders`
- `POST /api/erp/purchase-receipts`
- `POST /api/erp/vehicle-fitments`

### Macro B1: ERP Operational Debt Register

Objetivo: transformar gaps de cadastro, arquitetura e BI em divida rastreavel, agrupada por origem, urgencia, owner, status e macro bloqueada.

Contratos:

- `operational.roadmap_debt_register.v1`
- `erp.operational_gap_register.v1`

Interfaces:

- `GET /api/operations/roadmap-debt-register`

Datasets:

- `bi_roadmap_blocker_dataset`
- `bi_erp_operational_debt_dataset`

Check:

- `check:roadmap-debt-register`

### Macro B2: CDD Stock Semantics + Supplier Inbound Distribution

Status: `active_v1`.

Decisao implementada: CDD tem estoque fisico proprio. Hub tem estoque fisico proprio. Pool calcula capacidade de reposicao, nao soma virtual do CDD.

Formula de referencia:

```txt
cdd_ready_to_ship_qty = estoque fisico disponivel no CDD
cdd_replenishable_qty = estoque transferivel de hubs elegiveis para o CDD
online_publishable_qty = politica configuravel, nao verdade fixa
```

Politicas ativas de pool:

- `allowSellBeforeCddReplenishment`
- `maxReplenishmentPromiseQty`
- `maxReplenishmentLeadTimeHours`
- `readyToShipOnlyByDefault: true`

Contratos ativos:

- `erp.cdd_stock_semantics.v1`
- `erp.inbound_distribution_plan.v1`
- `erp.inbound_distribution_item.v1`
- `erp.purchase_receipt_distribution.v1`
- `erp.receiving_mode.v1`
- `erp.online_publishable_stock_policy.v1`

Datasets ativos:

- `bi_cdd_own_stock_dataset`
- `bi_cdd_replenishment_capacity_dataset`
- `bi_online_publishable_stock_policy_dataset`
- `bi_purchase_receipt_distribution_dataset`
- `bi_inbound_distribution_gap_dataset`
- `bi_supplier_inbound_allocation_dataset`

Fluxo alvo:

```txt
purchase receipt / invoice
-> item recebido
-> distribuicao por destino fisico
-> movement direto ou staging + transferencia
-> estoque disponivel somente quando destino e movement forem validos
```

### Macro B3: ERP Fiscal & Accounting Distribution Layer

Status: `active_v2_hardened`.

Regra:

```txt
Movimento de estoque != documento fiscal != receita realizada != margem gerencial.
```

Contratos ativos:

- `erp.distribution_accounting.v1`
- `erp.distribution_valuation.v1`
- `erp.fiscal_operation_rule.v1`
- `erp.fiscal_document_request.v1`
- `erp.nfe_requirement_check.v1`
- `erp.accounting_impact_summary.v1`

Regras arquiteturais:

- DGE nao emite NF-e nesta versao.
- DGE classifica operacao e cria solicitacao fiscal.
- Regra fiscal e configuravel e accountant-governed.
- Transferencia mesma titularidade nao vira receita por padrao.
- Fluxo para franqueado nunca e tratado como transferencia interna sem regra fiscal explicita.
- Falta de regra fiscal bloqueia finalizacao quando ha fronteira fiscal/legal.

Datasets ativos:

- `bi_distribution_accounting_dataset`
- `bi_distribution_valuation_dataset`
- `bi_fiscal_document_request_dataset`
- `bi_nfe_requirement_dataset`
- `bi_hub_distributed_value_dataset`
- `bi_franchisee_fiscal_flow_dataset`
- `bi_inventory_cost_flow_dataset`
- `bi_expected_margin_by_destination_dataset`

### Macro C: Caos Lab Service Desk & Resolution Workflow

Contratos:

- `service.ticket.v1`
- `service.ticket_event.v1`
- `service.ticket_playbook.v1`
- `service.ticket_sla.v1`
- `service.resolution_workflow.v1`

Interfaces planejadas:

- `POST /api/service-desk/tickets`
- `GET /api/service-desk/tickets`
- `POST /api/service-desk/tickets/:id/assign`
- `POST /api/service-desk/tickets/:id/events`
- `POST /api/service-desk/tickets/:id/resolve`
- `POST /api/operations/exception-hub/:exceptionKey/create-ticket`

### Macro D: n8n Automation Control Plane

Contratos:

- `automation.workflow_registry.v1`
- `automation.trigger_policy.v1`
- `automation.run_supervision.v1`
- `automation.dead_letter.v1`

Interfaces planejadas:

- `GET /api/automations/workflows`
- `POST /api/automations/workflows`
- `POST /api/automations/workflows/:id/check`
- `POST /api/automations/workflows/:id/promote`
- `GET /api/automations/dead-letter`
- `POST /api/automations/dead-letter/:id/retry`

### Macro E: BI/Superset Semantic Foundation

Contratos:

- `bi.semantic_catalog.v1`
- `bi.metric_definition.v1`
- `bi.dataset_certification.v1`
- `bi.dashboard_family.v1`

Interfaces planejadas:

- `GET /api/bi/semantic-catalog`
- `GET /api/bi/datasets/certification`

### Macro F: Freight/Frenet/Loggi Runtime

Contratos:

- `freight.quote_runtime.v1`
- `logistics.carrier_runtime.v1`
- `logistics.label_lifecycle.v1`
- `logistics.tracking_event.v1`
- `reverse_logistics.runtime.v1`

### Macro G: IA/RAI Operational Intelligence

Contratos:

- `rai.context_pack.v1`
- `rai.trace_curation.v1`
- `rai.operational_recommendation.v1`
- `rai.eval.v1`

### Macro H: Ecommerce Real Backend & Frontend Contract Pack

Entregas:

- ecommerce consumindo catalogo ERP, preco DGE, promocao/cupom, disponibilidade/pool/CDD e behavior trace;
- view models por tela;
- empty states;
- action availability por item;
- error codes;
- filtros/paginacao;
- escopo por usuario.

### Macro I: Operational Domain Map + Roadmap Dependency Graph

Status: `active_v1`.

Documento:

- `docs/architecture/dge-2.0-operational-domain-map.md`

Contratos:

- `operational.domain_map.v1`
- `operational.roadmap_dependency_graph.v1`
- `operational.production_readiness_map.v1`

Regra:

```txt
motor financeiro projetivo != subledger financeiro operacional
transferencia != consignacao != venda B2B != remessa
movimento fisico != documento fiscal != liquidacao financeira
```

## Checkpoint Dos Ciclos Pre-20x

O Ciclo 1 expandiu alem da auditoria inicial e entregou:

- Flow Registry, State Machine Registry, Smoke Matrix e Auth Coverage;
- ERP Completeness Audit e Operational Debt Register;
- CDD Stock Semantics + Supplier Inbound Distribution;
- ERP Fiscal & Accounting Distribution Layer;
- ERP Economic/Fiscal Runtime Hardening;
- Operational Domain Map + Roadmap Dependency Graph.

Com os novos fios explicitados, Service Desk e n8n continuam importantes, mas deixam de ser os proximos runtimes imediatos. A sequencia oficial passa a seguir invariantes, readiness de producao, financeiro operacional, planejamento de abastecimento e consignacao antes de ampliar automacao externa.

## Sequencia Oficial Expandida

1. Heavy Backend Hardening v2. `completed`
2. Production Readiness Plane v1. `next_runtime`
3. Financial Operations Runtime Core v1.
4. Inventory Planning & Replenishment v1.
5. Franchise Consignment Network v1.
6. Repository Layer Migration v1.
7. ERP Operator Directory + Workforce Identity & Behavior Trace v1.
8. Caos Lab Service Desk v1.
9. Integration Reliability Plane + n8n Control Plane.
10. BI/Superset Semantic Foundation.
11. Fiscal Document Provider Lifecycle + XML/NF-e Assisted Import.
12. Freight/Frenet/Loggi Runtime.
13. Bling Live Controlled Run.
14. Full end-to-end simulation.
15. IA/RAI Operational Intelligence.
16. Ecommerce real, UX/UI prototyping e frontend final.

### Checkpoint: Production Readiness Plane v1 implementado, evidencia de restore pendente

O runtime local e cloud-agnostic foi ativado com:

- request tracing estruturado e sanitizado;
- `GET /api/health/live` e `GET /api/health/ready`;
- token administrativo legado identificado como responsabilidade exclusiva do piloto, fora do readiness DGE 2.0;
- CORS por allowlist e payload global reduzido;
- rate limit PostgreSQL auditavel;
- secret readiness sem persistencia de valor bruto;
- politica LGPD de retencao executavel por CLI governada;
- backup e restore drill com recusa de banco canonico e evidencia auditavel.

O plano permanece `partial`, nao `completed`: o ambiente local ainda nao possui restore drill `verified` e a DGE 2.0 ainda compartilha temporariamente o processo raiz com o piloto. `DGE_ADMIN_TOKEN_SHA256` pertence ao legado e nao participa mais dos criterios de readiness DGE 2.0. O proximo runtime somente muda para `Financial Operations Runtime Core v1` depois do restore drill isolado e do entrypoint proprio.

## Isolamento Absoluto Do Piloto

O piloto e uma prova de conceito historica congelada. Ele pode continuar acessivel localmente para consulta e demonstracao, mas nao recebe features novas e nao define compatibilidade obrigatoria para a DGE 2.0.

```txt
Piloto = referencia visual e historica.
DGE 2.0 = produto novo, com arquitetura propria.
Nenhuma evolucao da DGE 2.0 deve exigir manutencao do piloto.
```

Divida temporaria registrada:

| Debt | Origem | Urgencia | Status | Target |
| --- | --- | --- | --- | --- |
| `pilot_dge2_runtime_mount_coupling` | `server/index.js` | high | `resolved_by_exclusive_entrypoint` | `Production Readiness Plane v1 Completion` |

## Production Readiness Plane V1 Completion

O piloto permanece congelado em `5173/8787`. A DGE 2.0 possui backend exclusivo em `8788`, com health, observabilidade, rate limit, segredos e recovery policy medidos somente nessa superficie.

O restore drill usa PostgreSQL Docker efemero, registra evidencia sanitizada e exige RPO inicial de `24h` e RTO inicial de `4h`. Com os dois blockers finais resolvidos, o proximo runtime oficial passa a ser `Financial Operations Runtime Core v1`.

Antes de promover readiness para verde, a DGE 2.0 deve ganhar entrypoint backend exclusivo. Health, observabilidade, rate limit, secrets e restore drill devem medir apenas essa superficie.

## Definition Of Backend Ready For Frontend

Antes do frontend final, a DGE precisa cumprir:

- `smoke:backend` verde;
- `check:dge2-boundary` verde;
- `check:roadmap-truth` verde;
- flow registry cobrindo os fluxos principais;
- auth coverage para writes criticos;
- action availability nos desks operacionais;
- ERP completeness audit retornando pendencias explicaveis;
- Service Desk conectado ao Exception Hub;
- Superset semantic catalog definido;
- n8n control plane com promotion gates;
- freight/logistics runtime pelo menos em dry-run/blueprint executavel;
- frontend contract pack com view models estaveis.
# Checkpoint: Inventory Planning & Replenishment v1

`Inventory Planning & Replenishment v1` foi concluido como runtime backend-only. O modulo cobre politicas por SKU/location, termos de fornecedor, snapshots de demanda e cobertura, recomendacao de safety stock, alternativas de compra/redistribuicao/hibrido, preview de impacto e execucao idempotente apos dupla aprovacao humana obrigatoria.

Proximo runtime oficial: `Franchise Consignment Network v1`.

# Checkpoint: Franchise Consignment Network v1

`Franchise Consignment Network v1` foi concluido como runtime backend-only. O modulo preserva propriedade patrimonial da marca durante a consignacao, separa transito de saldo disponivel, exige dupla aprovacao sem limite minimo, reconcilia sell-out antes da baixa e posta recebivel somente apos fechamento diario aprovado pelo financeiro.

Retorno, ajuste patrimonial e fallback franquia -> CDD permanecem governados. Integracoes Bling/PDV live continuam futuras.

Proximo runtime oficial: `Repository Layer Migration v1`.

# Checkpoint: Repository Layer Migration + ERP Operator Directory v1

Antes do Service Desk, a DGE 2.0 passou a separar coordenacao de regra e persistencia. Services operacionais nao executam SQL diretamente: repositories locais ao dominio encapsulam leitura, escrita e locks. O gate oficial e `check:repository-boundary`.

O ERP tambem passou a registrar operadores como pessoas operacionais canonicas, separadas do principal de autenticacao. Governance vincula identidade provider-agnostic sem guardar token OAuth bruto. Perfis pessoais ficam cifrados; a revelacao completa exige escopo, justificativa e evento auditavel. Alocacoes temporais, lifecycle, offboarding efetivo e handoffs preparam o Service Desk para trabalhar com responsaveis reais.

```txt
Franchise Consignment Network concluido
→ Repository Layer Migration v1
→ ERP Operator Directory + Workforce Identity & Behavior Trace v1
→ Caos Lab Service Desk v1
```

BI continua em views live. A decisao sobre materialized views foi adiada para `BI/Superset Semantic Foundation`, avaliada por dataset conforme volume, latencia, custo de query e SLA de freshness.

# Checkpoint: ERP Operational Kernel Reset v2

`ERP Operational Kernel Reset v2` foi concluido como gate arquitetural antes de novas integracoes. A DGE 2.0 deixa de tratar o ERP como soma de cadastros e runtimes acumulados: cada eixo passa a ser um nucleo operacional com o mesmo envelope obrigatorio.

```txt
cadastro -> operacao -> consulta -> automacao readiness -> auditoria -> BI -> inteligencia
```

Nucleos oficiais:

- `catalog_nucleus`;
- `supplier_purchase_nucleus`;
- `pricing_promotion_nucleus`;
- `inventory_nucleus`;
- `fulfillment_nucleus`;
- `finance_nucleus`;
- `fiscal_nucleus`;
- `franchise_nucleus`;
- `operator_nucleus`;
- `crm_icp_nucleus`;
- `intelligence_nucleus`;
- `automation_nucleus`.

O reset e agressivo no destino, mas controlado na execucao: a demo atual e migravel, a cobertura total permanece obrigatoria, e as fontes legadas que serviam como equivalencia temporaria foram migradas para os nucleos correspondentes antes do closure. Nenhum adapter temporario pode existir sem dono, substituto e check de remocao.

CRM/ICP passa a ter diretriz propria: behavior antes do aceite e apenas pseudonimizado; perfil identificado, segmentacao nominal e campanha exigem consentimento valido. Performance de campanha alimenta KPI, variancia, projection impact e possivel reforecast governado, nunca mutacao automatica da projecao oficial.

As materialized views ficam adiadas para `BI/Superset Semantic Foundation`.

## Batch 3 concluido: ERP Material + PDV/Commerce Adapter Split

O terceiro lote real do kernel saiu do monolito ERP sem alterar contrato publico. `supplier_purchase_nucleus` segue migrado para fornecedores, termos por SKU, PO, receipt, inbound distribution, confirmacao de receipt e custo de entrada. `inventory_nucleus` agora e runtime migrado para locations, movements, balances, reservations, batch reserve/deduct, stock counts, stock transfers, snapshot diario, PDV/store sale, reconciliacao material de commerce e resolucao material de excecoes.

Escopo migrado:

- catalogo: produtos, SKUs, variantes, categorias, kits, midia, fitment e publicacao;
- pricing/promocoes: price books/lists, precos por SKU, bindings por canal/location, cupons e promocoes;
- supplier purchase: fornecedores, supplier variant terms, pedidos de compra, receipts, inbound distribution, confirmacao e custo de entrada;
- inventory: locations, movements, balances, reservations, stock counts, transfers, snapshot diario, PDV/store sale, reconciliacao commerce e resolucao material de excecoes.

## Batch 4 concluido: ERP Operational Intelligence Split

O `erp.repository.js` foi aposentado como runtime. Contexto operacional, workflow control, exception center, resolucao orquestradora de excecoes e derivacao de KPI ERP passam a pertencer ao `intelligence_nucleus`, preservando o mesmo shape das rotas `/api/erp/operational-context`, `/api/erp/workflows`, `/api/erp/exceptions` e `/api/erp/kpis/publish-daily-snapshot`. A resolucao material continua delegada aos adapters do `inventory_nucleus`; nenhum ticket automatico de Service Desk e criado. Os checks `check:erp-operational-intelligence-boundary`, `check:erp-operational-intelligence-equivalence` e `check:erp-monolith-retired` impedem retorno do monolito. BI continua em live views; nenhuma materialized view foi criada neste batch.

## Full Migration Before Closure concluido

Antes do Kernel Closure, os runtimes reais restantes tambem foram migrados para seus donos de nucleus: `fulfillment_nucleus`, `finance_nucleus`, `fiscal_nucleus`, `franchise_nucleus`, `operator_nucleus`, complementos de `inventory_nucleus` e complementos de `intelligence_nucleus`.

As fontes `fulfillment.repository.js`, `bottleneckRun.repository.js`, `operationalCockpit.repository.js` e `reforecastPreview.repository.js` deixam de ser quarentena ativa e passam a constar como fontes aposentadas. O check `check:erp-kernel-closure-readiness` exige quarentena zerada, facades finas, runtime dentro de nucleus e BI ainda em live views.

## DGE Master Architecture Inventory

Antes de qualquer closure, a DGE 2.0 passa a usar o `DGE Master Architecture Register` como fonte de verdade para impedir fechamento por sensacao. Cada frente grande precisa estar classificada como `delivered`, `readiness`, `blueprint_future`, `blocker`, `external_boundary` ou `out_of_scope`.

O registro cobre ERP, commerce, Bling, fulfillment, freight, finance, fiscal, Service Desk, operations, BI, Superset, IA/RAI, projections, snapshots, lineage, logs, cloud, banco, repository/service layer, cockpit, control plane, health status, UX/UI, frontend, homologacao e producao.

Matriz obrigatoria por dominio:

- runtime atual;
- CRUD/API interna;
- schema/banco;
- repository/service;
- datasets BI;
- Superset readiness;
- cockpit/control plane;
- health/status;
- logs/Service Desk;
- idempotencia/hash/SHA-256;
- lineage/snapshots/auditoria;
- homologacao/producao;
- pendencia futura.

### Decisoes Travadas

- BI atual continua em live views.
- Superset sera camada exploratoria e certificada futura, com datasets, charts, dashboards e metric catalog.
- Materialized views ficam para decisao por dataset no `BI/Superset Semantic Foundation`.
- Lakehouse, Databricks, AWS analytics e cloud hosting entram como `analytics_platform_decision_record`, sem vendor lock nesta etapa.
- PostgreSQL continua sendo o banco canonico operacional.
- IA/RAI significa recuperacao auditavel de contexto, nao agente executor. IA recomenda, resume e prioriza; nao aprova, paga, emite documento, ajusta estoque ou fecha chamado.
- Next.js e o candidato natural para frontend real, mas apenas depois de frontend contract pack com view models, action availability, error codes, CRUD estavel e UX/UI.
- Service Desk registra logs/evidencias redigidas, tickets, fluxos de atendimento, multitenancy, SLA/TMA, anexos, comentarios e fechamento com outcome tecnico. Ticket nao corrige estoque, caixa, fiscal ou projecao diretamente.
- n8n orquestra; DGE decide regra, estado, auth, idempotencia e aprovacao.
- Bling live controlado depende de inbox/outbox, retry, dead-letter, hash guard e fallback manual.
- Fulfillment core cobre CDD, hubs, pools, allocation e publishable stock. Freight/Frenet/Loggi runtime futuro cobre quote, label, tracking, reversa, custo cotado vs realizado e SLA.
- Forecast, reforecast, variancia, bottlenecks, lineage, snapshots e auditoria alimentam o core inteligente; roadmap e reforecast oficial nunca sao recalculados automaticamente.

### Tres Closures Oficiais

```txt
ERP Core Kernel Closure
!= DGE Backend Kernel Closure
!= Production/Frontend Readiness Closure
```

`ERP Core Kernel Closure` fecha o ERP core como fundacao limpa. Ele nao declara que commerce, governance, projections, operations, integrations, BI/Superset, RAI, cloud, frontend ou lakehouse estao finalizados.

`DGE Backend Kernel Closure` so acontece depois dos batches de migracao dos runtimes backend restantes para nuclei/backlog honesto.

`Production/Frontend Readiness Closure` so acontece depois de Integration Reliability + n8n, BI/Superset Semantic Foundation, Fiscal Provider/XML, Freight/Frenet/Loggi, Bling Live Controlled Run, IA/RAI, frontend contract pack, homologacao e evidencia de producao.

```txt
DGE Master Architecture Inventory
-> ERP Core Pre-Closure Hardening
-> Service Desk / Error / Intelligence Hardening
-> Fulfillment/Freight + n8n Readiness Alignment
-> ERP Core Kernel Closure
-> Backend Nucleus Migration Batches
-> DGE Backend Kernel Closure
-> Integration Reliability Plane + n8n Control Plane
-> BI/Superset Semantic Foundation
-> Fiscal Provider/XML
-> Freight/Frenet/Loggi Runtime
-> Bling Live Controlled Run
-> IA/RAI Operational Intelligence
-> Next.js UX/UI + Frontend Final
-> Homologacao
-> Producao
```

### ERP Core Pre-Closure Hardening Concluido

`ERP Core Pre-Closure Hardening` adicionou o contrato `erp.core_preclosure.v1` e o endpoint read-only `GET /api/operations/erp-core-preclosure`.

O gate confirma que os nucleos ERP atuais possuem owner, CRUD/API, rota publica mapeada, facade fina, command policy, actionAvailability, auth roles, error codes, BI live datasets, audit/lineage/snapshot e cockpit lane.

Essa conclusao resolve somente `erp_core_preclosure_hardening_missing`. Ela nao fecha o ERP Core Kernel.

### Service Desk / Error / Intelligence Hardening Concluido

`Service Desk / Error / Intelligence Hardening` adicionou o contrato `service_desk.error_intelligence_hardening.v1`, o formulario rico `service.ticket_form.v1`, a politica `service.routing_policy.v1` e os endpoints:

- `GET /api/service-desk/ticket-form`;
- `GET /api/service-desk/domains`;
- `GET /api/service-desk/routing-policy`;
- `GET /api/operations/service-de[SECRET_REDACTED]`.

O gate confirma formulario unico rico, dominios de atendimento, roteamento L1/L2/L3 por dominio, anexos com metadata segura, memoria de trabalho, fechamento auditavel, resposta tecnica sanitizada com `requestId`, criacao de ticket apenas por acao humana explicita e inteligencia sem recalculo automatico de roadmap, forecast ou reforecast oficial.

Essa conclusao resolve somente `service_desk_error_intelligence_hardening_missing`. Ela nao fecha o ERP Core Kernel. Antes do closure ainda faltam:

- `Fulfillment/Freight + n8n Readiness Alignment`;
- `ERP Core Kernel Closure`.
