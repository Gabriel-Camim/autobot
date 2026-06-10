---
title: DGE fonte - DGE 2.0 ERP Ecommerce-First Backbone
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-erp-ecommerce-first-backbone.md.'
source_path: docs/architecture/dge-2.0-erp-ecommerce-first-backbone.md
---

# DGE 2.0 ERP Ecommerce-First Backbone

Fonte original DGE 2.0: `docs/architecture/dge-2.0-erp-ecommerce-first-backbone.md`.

---

# DGE 2.0 ERP Ecommerce-First Backbone

## Decisao

A DGE passa a ser o source of truth operacional para catalogo ecommerce, SKUs, estoque por hub, movimentos, reservas e contagens. O Bling deixa de ser operador primario de ERP e passa a fonte auxiliar de vendas/notas/importacao.

## Contratos

- `erp.product_catalog.v1`
- `erp.inventory_ledger.v1`
- `erp.transactional_runtime.v1`

## Interfaces

- `POST /api/erp/products`
- `GET /api/erp/products`
- `GET /api/erp/products/:id`
- `POST /api/erp/products/:id/variants`
- `POST /api/erp/products/:id/prices`
- `POST /api/erp/price-lists`
- `GET /api/erp/price-lists`
- `GET /api/erp/prices/effective`
- `POST /api/erp/promotions`
- `GET /api/erp/promotions`
- `GET /api/erp/catalog`
- `POST /api/erp/inventory/movements`
- `GET /api/erp/inventory/movements`
- `GET /api/erp/inventory/balances`
- `POST /api/erp/inventory/reservations`
- `POST /api/erp/inventory/reservations/:id/release`
- `POST /api/erp/inventory/stock-counts`
- `POST /api/erp/inventory/stock-counts/:id/approve`
- `POST /api/erp/inventory/transfers`
- `POST /api/erp/inventory/transfers/:id/ship`
- `POST /api/erp/inventory/transfers/:id/receive`
- `POST /api/erp/store-sales`
- `GET /api/erp/store-sales`
- `POST /api/erp/inventory/publish-daily-snapshot`

## Modelo Operacional

O estoque canonico nasce do ledger:

```txt
produto/variante -> hub/location -> movimento -> saldo -> reserva -> snapshot auditado -> KPI/BI/projecao
```

O ERP Operating Core v1 amplia esse fluxo para:

```txt
SKU -> hub -> estoque -> movimento -> preco -> promocao -> venda -> auditoria -> BI/projecao
```

Regras:

- nenhuma movimentacao de estoque existe sem SKU cadastrado;
- listas de preco oficiais incluem `varejo`, `atacado`, `revenda`, `ecommerce`, `marketplace_benchmark` e `promotional`;
- a lista `ecommerce` e a fonte canonica para preco operacional do ecommerce;
- promocao calcula preco efetivo por vigencia sem sobrescrever preco base;
- transferencia entre hubs e fluxo composto: solicitacao, envio, transito, recebimento e reconciliacao;
- venda PDV/loja fisica por hub baixa estoque quando SKU esta mapeado;
- venda marketplace segue benchmark/projecao, nao inteligencia operacional direta.

Snapshots antigos (`inventory_availability_snapshots`) continuam existindo como fotografia auditavel e compatibilidade com KPI/cockpit. Eles nao sao mais a fonte primaria quando o ledger ERP estiver disponivel.

## Bling

Bling deve entrar como:

- importador auxiliar de pedidos/vendas;
- fonte de nota/status fiscal quando disponivel;
- contingencia/importacao assistida para estoque;
- nunca overwrite automatico do saldo canonico da DGE.

Conflitos Bling vs DGE viram excecao, ticket, approval ou reconciliation, nao atualizacao silenciosa.

## BI

Datasets:

- `bi_erp_product_catalog_dataset`
- `bi_erp_price_orchestration_dataset`
- `bi_erp_promotions_dataset`
- `bi_erp_inventory_balances_dataset`
- `bi_erp_inventory_movements_dataset`
- `bi_erp_inventory_reservations_dataset`
- `bi_erp_stock_counts_dataset`
- `bi_erp_stock_transfers_dataset`
- `bi_erp_store_sales_dataset`
- `bi_erp_inventory_reconciliation_dataset`

## Data Intake E Cockpit

A Data Intake Layer passa a incluir collectors ERP. O antigo nome Manual KPI Collector permanece apenas como compatibilidade de contrato/endpoints.

- `erp_product_catalog_review`
- `erp_price_list_review`
- `erp_promotion_review`
- `erp_hub_location_review`
- `tenant_actor_review`
- `erp_inventory_daily_count`
- `erp_inventory_adjustment_review`
- `erp_stock_transfer_review`
- `erp_store_sale_daily`
- `erp_order_stock_reconciliation`
- `bling_sales_import_audit`

Esses collectors apontam para endpoints modulares do ERP/Bling, carregam role de entrada/revisao/auditoria, SLA, BI impactado e modo de contingencia. A camada nao cria formulario universal nesta etapa.

Separacao de frequencia:

- produtos, SKUs, listas de preco, promocoes, hubs e atores sao master data `event_driven`;
- transferencia entre hubs e evento operacional governado, nao rotina diaria;
- ajuste de estoque e `exception_driven`;
- contagem de estoque, venda PDV diaria e reconciliacao pedido/estoque continuam `daily`.

Essa separacao impede que o cockpit cobre cadastro de produto ou preco todos os dias, mas continua mostrando pendencias quando um SKU ativo esta sem preco ecommerce, uma promocao esta ativa/vencendo, uma transferencia esta aberta ou um ajuste exige auditoria.

## ERP Workflow Control

O ERP deixa de ser apenas endpoints de cadastro/ledger e passa a expor um read model operacional:

```txt
GET /api/erp/workflows
```

Contrato:

```txt
erp.workflow_control.v1
```

O workflow consolida:

- `erp_master_data`: produto/SKU, lista de preco, promocao, hub/location e tenant actor;
- `erp_inventory_flow`: contagem, ajuste, movimento, reserva e transferencia;
- `erp_sales_flow`: venda PDV, pedido ecommerce e importacao/venda auxiliar;
- `erp_exception_flow`: SKU sem preco ecommerce, venda sem baixa, movimento com approval, transferencia aberta e divergencia de contagem.

O endpoint e read-only. Ele nao cria movimento, nao aprova cadastro e nao substitui Data Intake. Ele explica o estado operacional depois que Data Intake, endpoints ERP e approvals geram dados reais.

## ERP Transactional Runtime

O runtime transacional padroniza toda operacao que altera estoque, venda ou preco aplicado:

```txt
Data Intake/endpoint -> SKU -> preco efetivo -> estoque/reserva -> movimento -> excecao -> workflow/BI
```

Fluxos cobertos:

- venda PDV registra a venda mesmo quando um item falha, baixa estoque apenas para SKU/hub validos e marca `completed_with_exceptions` quando houver SKU desconhecido ou saldo insuficiente;
- pedido ecommerce preserva o contrato commerce e anexa `erpReconciliation` com `erp.transactional_runtime.v1`;
- cancelamento de pedido cria compensacao `sale_cancellation`;
- preco efetivo usa lista `ecommerce` e promocao ativa sem sobrescrever preco base;
- promocao por SKU tem precedencia sobre promocao por categoria;
- transferencia entre hubs registra saida, transito, entrada e divergencia de recebimento como reconciliacao pendente.

Datasets BI adicionais:

- `bi_erp_transactional_runtime_dataset`;
- `bi_erp_store_sale_reconciliation_dataset`;
- `bi_erp_commerce_order_stock_reconciliation_dataset`;
- `bi_erp_price_effective_audit_dataset`;
- `bi_erp_transfer_reconciliation_dataset`.

Datasets BI:

- `bi_erp_workflow_control_dataset`;
- `bi_erp_master_data_governance_dataset`;
- `bi_erp_exception_queue_dataset`.

## ERP Exception Intelligence & Resolution Center

O centro de excecoes transforma pendencias do ERP em casos operacionais resolviveis, com diagnostico e rastro de decisao:

```txt
excecao -> causa provavel -> impacto -> responsavel -> acao permitida -> runtime modular -> resolucao auditavel
```

Contratos:

- `erp.exception_case.v1`
- `erp.reconciliation_resolution.v1`

Endpoints:

- `GET /api/erp/exceptions`
- `GET /api/erp/exceptions/:id`
- `POST /api/erp/exceptions/:id/resolve`
- `POST /api/erp/exceptions/:id/retry`
- `POST /api/erp/exceptions/:id/escalate`

Casos cobertos na v1:

- venda PDV com SKU nao mapeado ou baixa pendente;
- pedido ecommerce/commerce com reconciliacao ERP incompleta;
- transferencia entre hubs recebida com divergencia;
- pendencias de master data que afetam preco, estoque ou operacao.

Guardrails:

- resolucao usa servicos modulares do ERP, nao escrita direta em saldo canonico;
- `system_integration` pode criar evidencia, mas nao resolve/audita excecao;
- toda resolucao exige ator, papel e justificativa;
- marketplaces seguem comparativos/projetivos e nao geram inteligencia operacional direta;
- cada acao gera registro em `erp_exception_resolutions` e timeline.

As excecoes ERP tambem entram no Operational Exception Hub como fonte de dominio. O ERP continua sendo source of truth de catalogo, preco e estoque; o hub faz dedupe, grafo, impacto, SLA unificado e resolucao delegada.

Interfaces cross-module:

- `GET /api/operations/exception-hub`
- `GET /api/operations/exception-impact`
- `POST /api/operations/exception-hub/:exceptionKey/resolve`

Datasets BI:

- `bi_erp_exception_cases_dataset`;
- `bi_erp_exception_resolution_dataset`;
- `bi_erp_exception_financial_impact_dataset`;
- `bi_erp_exception_root_cause_dataset`;
- `bi_erp_resolution_sla_dataset`.

O roteamento canonico fica em `data.intake.routing.v1` e pode ser lido por:

- `GET /api/operations/data-intake`
- `GET /api/operations/data-intake/:collectorKey`
- `GET /api/operations/data-intake/:collectorKey/routing`

Para ERP, isso garante que catalogo, contagem, movimentos, reconciliacao e importacao Bling sejam direcionados para contratos modulares sem transformar Data Intake em um endpoint generico de escrita.

## Guardrails

- DGE e fonte canonica de catalogo e estoque.
- Ecommerce continua runtime de checkout/cliente.
- Bling e fonte auxiliar.
- Ajustes materiais precisam de actor, role, motivo e approval.
- Marketplaces seguem comparativos/projetivos.
