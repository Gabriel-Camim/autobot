---
title: DGE fonte - DGE 2.0 Operational Cockpit Backbone
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-operational-cockpit-backbone.md.'
source_path: docs/architecture/dge-2.0-operational-cockpit-backbone.md
---

# DGE 2.0 Operational Cockpit Backbone

Fonte original DGE 2.0: `docs/architecture/dge-2.0-operational-cockpit-backbone.md`.

---

# DGE 2.0 Operational Cockpit Backbone

## Papel

O cockpit operacional e o read model oficial da operacao DGE 2.0. Ele nao substitui Superset e nao vira frontend nesta etapa: ele entrega contratos backend para que o futuro cockpit renderize filas, status, pendencias, SLA, TMA, reforecast e Data Intake sem decidir regra de negocio na tela.

## Contrato principal

- `GET /api/operations/cockpit`
- contrato: `dge.operational_cockpit.v2`
- modo: read-only
- sem criacao de fato operacional
- sem mutation de projection version
- sem inteligencia operacional direta em Shopee/Mercado Livre

O payload centraliza:

- Command Center executivo;
- Control Plane operacional;
- tickets normalizados;
- fluxo de cases de reforecast;
- active state e dependency queue;
- pendencias por role, actor e hub;
- SLA, TMA e aging;
- Data Intake Layer;
- freshness de dados;
- readiness de automacoes;
- datasets BI para Superset.
- Operational Exception Hub;
- Data Intake Coverage Lock.

## Lanes operacionais

As lanes sao estaveis para o futuro frontend:

- `executive_overview`
- `daily_manual_collection`
- `approval_audit`
- `reforecast_control`
- `channel_intelligence`
- `inventory_hubs`
- `commerce_orders`
- `fulfillment_logistics`
- `freight_economics`
- `after_sales_reverse_logistics`
- `integrations_automations`
- `bi_reporting`
- `rai_observability`

Cada lane carrega status, pendencias, criticidade, overdue, roles donas, roles visiveis, top tickets, endpoints e datasets ligados.

## Tickets operacionais

O cockpit normaliza aprovacoes, gargalos, cases, shipments, automacoes, integracoes, reforecast e coletores faltantes como `operational.ticket.v1`.

Campos centrais:

- `ticketKey`
- `ticketType`
- `domain`
- `lane`
- `assignedRole`
- `assignedActorKey`
- `hubKey`
- `channelKey`
- `slaStatus`
- `ageHours`
- `timeInCurrentStepHours`
- `tmaTargetHours`
- `nextRequiredAction`

## Operational Exception Hub

O cockpit agora consome o `Operational Exception Hub` como sistema nervoso operacional da DGE.

Interfaces:

- `GET /api/operations/exception-hub`
- `GET /api/operations/exception-hub/:exceptionKey`
- `POST /api/operations/exception-hub/:exceptionKey/link`
- `POST /api/operations/exception-hub/:exceptionKey/resolve`
- `GET /api/operations/exception-impact`

Contratos:

- `operational.exception_hub.v1`
- `operational.exception_graph.v1`
- `operational.exception_impact.v1`
- `operational.resolution_policy.v1`

O hub unifica Data Intake, ERP, Commerce, pagamentos, checkout, approvals, bottlenecks, stale reforecast, integration runs, automation issues e excecoes operacionais antigas. Ele nao substitui os exception centers de dominio: ele conecta, deduplica, prioriza, calcula impacto e delega resolucao para o servico correto.

O cockpit expoe:

- `operationalExceptionHubDesk`;
- `exceptionGraphDesk`;
- `dataIntakeCoverageDesk`.

Com isso, a mesa operacional responde por que uma pendencia esta no topo da fila, qual causa provavel, qual entidade afeta, qual role deve agir, se bloqueia BI/projecao/auditoria, e se a resolucao depende de outro modulo.

Guardrails:

- o hub nao escreve em tabelas canonicas ignorando servicos modulares;
- `system_integration` nao resolve excecao final;
- marketplaces continuam benchmark/projecao;
- nenhuma cobranca, cupom, email, contato externo ou projection version nasce do hub.

## Data Intake Layer

Data Intake Layer e a portaria operacional de dados da DGE. Ela governa dados manuais, importacoes assistidas, automacoes futuras, auditoria, SLA, obrigacoes por role/hub/canal e contingencia.

O antigo Manual KPI Collector fica como compatibilidade historica. `manual` passa a ser apenas um `sourceMode`, nao o nome do modulo.

Data Intake nasce como blueprint renderizavel e checklist operacional vivo. Ela nao e formulario universal: a entrada real continua nos endpoints modulares existentes.

Interfaces:

- `GET /api/operations/data-intake`
- `GET /api/operations/data-intake/:collectorKey`
- `GET /api/operations/data-intake/:collectorKey/routing`
- `GET /api/operations/manual-collectors`
- `GET /api/operations/manual-collectors/:collectorKey`
- contrato canonico: `data.intake.blueprint.v1`
- contrato canonico: `data.intake.obligation.v1`
- contrato de roteamento: `data.intake.routing.v1`
- aliases legados: `manual.kpi.collection_blueprint.v1` e `manual.kpi.collection_obligation.v1`
- campo canonico no cockpit: `dataIntakeDesk`
- campo compativel atual no cockpit: `manualCollectionDesk`
- desks especializados: `dailyIntakeDesk`, `erpMasterDataDesk`, `exceptionIntakeDesk`

O `dataIntakeDesk` inclui `routingReadiness`, `byEndpoint`, `bySourceMode`, `needsApproval`, `automationCandidates`, `manualContingencyCollectors` e `missingRouting`. Isso permite ao futuro frontend e ao n8n renderizarem/rotearem coletores sem decidir regra de negocio.

O cockpit nao cobra cadastro estrutural como rotina diaria. Produtos, SKUs, listas de preco, promocoes, hubs e atores tenant aparecem no `erpMasterDataDesk` como entradas `event_driven`. Ajustes de estoque aparecem no `exceptionIntakeDesk`. Somente fatos recorrentes, como KPIs de canal, contagem diaria, venda PDV diaria, frete, pos-venda e integracoes, aparecem no `dailyIntakeDesk` como obrigacoes por data.

## Data Intake Submission Workflow

O cockpit tambem le submissões governadas da Data Intake:

- `POST /api/operations/data-intake/:collectorKey/submissions`;
- `GET /api/operations/data-intake/submissions`;
- `GET /api/operations/data-intake/submissions/:id`;
- `POST /api/operations/data-intake/submissions/:id/review`;
- `POST /api/operations/data-intake/submissions/:id/final-audit`.

Contrato:

```txt
data.intake.submission.v1
```

O workflow nao cria um submit universal. Cada collector continua apontando para endpoint modular proprio, e a Data Intake governa validacao, revisao, auditoria final, SLA/TMA, audit trail e dispatch.

Dispatch ativo v1:

- `POST /api/channels/daily-facts`.
- `POST /api/erp/products`.
- `POST /api/erp/price-lists`.
- `POST /api/erp/promotions`.
- `POST /api/erp/inventory/stock-counts`.
- `POST /api/erp/inventory/movements`.
- `POST /api/erp/inventory/transfers`.
- `POST /api/erp/store-sales`.
- `POST /api/commerce/orders`.
- `POST /api/logistics/freight-facts`.
- `POST /api/after-sales/cases`.
- `POST /api/integrations/runs`.
- `POST /api/operations/nodes`.
- `POST /api/governance/tenant-users`.
- `POST /api/commerce/behavior-events`.
- `POST /api/commerce/exceptions/:id/resolve`.
- `POST /api/erp/exceptions/:id/resolve`.

Collectors `GET`, Bling import e monthly close ficam rastreaveis, mas nao viram escrita generica neste bloco.

O ERP Operating Core tambem aparece no `erpDesk` do cockpit:

- SKUs ativos sem preco ecommerce;
- promocoes ativas por campanha/lista/canal;
- transferencias entre hubs pendentes;
- vendas PDV/loja fisica recentes por hub;
- excecoes de venda sem baixa de estoque;
- datasets de preco, promocao, transferencia e venda fisica ligados ao BI.

O `erpDesk` tambem inclui `ERP Workflow Control`:

- `workflowSummary`;
- `masterDataWorkflow`;
- `inventoryWorkflow`;
- `salesWorkflow`;
- `exceptionWorkflow`.

Isso permite que o cockpit mostre o fluxo completo de cada entidade ERP, incluindo origem Data Intake, approval, status operacional, SLA/TMA, role responsavel, hub, SKU e proxima acao.

Collectors v1:

- macro business daily;
- own channel daily;
- Shopee daily;
- Mercado Livre daily;
- inventory hub daily;
- commerce orders daily;
- fulfillment daily;
- freight/logistics daily;
- after-sales daily;
- integrations/automations daily;
- ERP inventory daily count;
- ERP store sale daily;
- ERP order stock reconciliation;
- monthly close;
- data quality audit.

Collectors ERP master data:

- ERP product catalog review;
- ERP price list review;
- ERP promotion review;
- ERP hub/location review;
- tenant actor review.

Collectors ERP event/exception:

- ERP stock transfer review, event-driven;
- ERP inventory adjustment review, exception-driven.

Collectors de excecao/observabilidade cross-module:

- commerce behavior event review;
- commerce payment failure review;
- commerce exception resolution review;
- ERP exception resolution review;
- automation exception review;
- Bling import exception review futuro;
- reforecast stale baseline review.

Marketplaces continuam como benchmark comparativo/projetivo. O unico canal elegivel para acao operacional direta da DGE e o canal proprio.

O cockpit infere o status da obrigacao olhando dados reais:

- `daily_kpi_snapshots`
- `channel_daily_facts`
- `inventory_availability_snapshots`
- `commerce_orders`
- `freight_economic_facts`
- `after_sales_cases`
- `approval_requests`

Estados operacionais:

- `pending_entry`
- `submitted`
- `pending_review`
- `pending_final_audit`
- `approved_audited`
- `rejected`
- `stale`
- `manual_contingency`
- `automation_replaced`

Com isso, a DGE consegue responder: quem deveria preencher hoje, qual canal/hub esta pendente, qual role precisa agir, qual dado ja pode virar snapshot, qual coleta ja foi auditada e qual excecao entrou pelo hub operacional.

## Data Intake Coverage Lock

O `Data Intake Coverage Lock` verifica se cada endpoint mutavel importante esta:

- coberto por collector;
- liberado como runtime sistemico direto;
- coberto por integracao assistida;
- fora do escopo v1;
- ou bloqueado por falta de routing.

Interface:

- `GET /api/operations/data-intake/coverage-lock`

Contrato:

- `data.intake.coverage_lock.v1`

A regra de arquitetura e simples: modulos novos nao devem criar uma porta lateral de entrada operacional. Antes de entrar em Frenet, Loggi, Bling real, n8n ou frontend, o endpoint precisa estar explicado pela Data Intake, por runtime sistemico direto ou por uma excecao documentada.

## Reforecast no cockpit

O cockpit incorpora:

- active projection state;
- dependency queue;
- stale baseline guardrail;
- fluxo completo por case;
- official explainability;
- family explainability;
- channel runtime;
- formula/freight/mixed reforecasts.

O endpoint `GET /api/projections/reforecast-cases/:id/flow` devolve a timeline operacional de cada case, com etapas, responsaveis, SLA, TMA, proposal, official version e explainability.

## Superset

Superset continua como camada BI analitica. O cockpit e a mesa operacional.

Datasets adicionados:

- `bi_operational_cockpit_ticket_queue_dataset`
- `bi_cockpit_role_actor_hub_pendency_dataset`
- `bi_reforecast_case_flow_dataset`
- `bi_manual_kpi_collection_blueprint_dataset`
- `bi_manual_collection_obligations_dataset`
- `bi_manual_collection_status_dataset`
- `bi_manual_collection_role_queue_dataset`
- `bi_data_intake_routing_dataset`
- `bi_data_intake_endpoint_map_dataset`
- `bi_data_intake_automation_readiness_dataset`
- `bi_command_center_operational_status_dataset`
- `bi_sla_tma_ticket_dataset`
- `bi_data_freshness_dataset`
- `bi_approval_audit_queue_dataset`
- `bi_automation_readiness_dataset`
- `bi_operational_exception_hub_dataset`
- `bi_operational_exception_graph_dataset`
- `bi_exception_root_cause_unified_dataset`
- `bi_exception_resolution_sla_unified_dataset`
- `bi_data_intake_coverage_lock_dataset`
- `bi_exception_projection_impact_dataset`
- `bi_integration_readiness_lock_dataset`
- `bi_integration_provider_capabilities_dataset`
- `bi_integration_readiness_checks_dataset`
- `bi_integration_exception_mapping_dataset`
- `bi_automation_orchestration_readiness_dataset`

## Fronteiras

- DGE opera canal proprio.
- Shopee e Mercado Livre sao comparativos/projetivos.
- Cockpit nao cria versao oficial.
- Cockpit nao cria fatos.
- Automacoes futuras entram por contratos e normalizadores existentes.
- Manual permanece como contingencia/sourceMode mesmo apos n8n/Bling/Frenet/Loggi.
- `integrationReadinessDesk` mostra gates de Bling, Frenet, Loggi, n8n, ecommerce real e payment gateway antes de qualquer runtime externo real.
