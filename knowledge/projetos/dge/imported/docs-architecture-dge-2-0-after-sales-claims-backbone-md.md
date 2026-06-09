---
title: DGE fonte - DGE 2.0 - After-Sales, Claims & Reverse Logistics Backbone
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-after-sales-claims-backbone.md.'
source_path: docs/architecture/dge-2.0-after-sales-claims-backbone.md
---

# DGE 2.0 - After-Sales, Claims & Reverse Logistics Backbone

Fonte original DGE 2.0: `docs/architecture/dge-2.0-after-sales-claims-backbone.md`.

---

# DGE 2.0 - After-Sales, Claims & Reverse Logistics Backbone

## Decisao de arquitetura

A DGE nao deve tratar garantia, troca, avaria, dano, nao recebimento, extravio, reembolso e reposicao como simples `metadata` de logistica. Esses eventos afetam margem, SLA, reputacao, recompra, estoque, frete e suporte. Por isso eles passam a compor uma espinha propria de pos-venda:

`pedido -> shipment -> return/reversa -> after_sales_case -> eventos -> KPIs diarios -> bottlenecks -> BI`

## Responsabilidade por sistema

- Ecommerce/app/suporte: executam a interacao transacional com o cliente, coleta de evidencias, abertura do ticket e comunicacao.
- ERP/Bling: registra nota, produto, estoque, pedido e reconciliacao operacional quando aplicavel.
- Frenet/Loggi/transportadora: registra cotacao, etiqueta, tracking, entrega, insucesso, extravio e reversa.
- DGE: audita, normaliza, rastreia, calcula custo, publica KPI, detecta gargalo e alimenta BI/projecoes.

## Entidades canonicas

- `after_sales_cases`: case oficial de pos-venda por pedido/item/shipment, com tipo, motivo, status, severidade, custos, evidencias e vinculo operacional.
- `after_sales_case_events`: timeline do case, incluindo investigacao, garantia, troca, reembolso, reversa, reposicao e fechamento.
- `logistics_returns`: fluxo logistico de devolucao/reversa, mantido como entidade logistica ligada ao shipment.

## Tipos de case v1

- `warranty`: garantia.
- `exchange`: troca.
- `shipping_damage`: avaria no transporte.
- `product_damage`: dano/defeito de produto.
- `not_received`: cliente relata nao recebimento.
- `lost_package`: extravio confirmado ou provavel.
- `wrong_item`: produto errado.
- `missing_item`: item faltante.
- `return`: devolucao.
- `refund`: reembolso.
- `replacement`: reposicao.
- `customer_claim`: reclamacao generica ainda nao classificada.

## KPIs publicados

- `after_sales_case_count`
- `after_sales_affected_order_count`
- `after_sales_claim_rate_percent`
- `after_sales_warranty_case_count`
- `after_sales_exchange_case_count`
- `after_sales_damage_case_count`
- `after_sales_not_received_case_count`
- `after_sales_open_case_count`
- `after_sales_unresolved_high_severity_count`
- `after_sales_total_case_cost_amount`
- `after_sales_reverse_logistics_cost_amount`
- `after_sales_refund_amount`
- `after_sales_average_resolution_hours`

## Bottleneck detection

O dominio `after_sales` roda nas cadencias diaria, semanal e mensal. Os sinais v1 sao:

- `after_sales_claim_pressure`: volume/taxa de claims acima do patamar.
- `after_sales_damage_pressure`: avaria/dano recorrente.
- `after_sales_not_received_pressure`: nao recebimento/extravio.
- `after_sales_cost_pressure`: custo materializado em reembolso, reversa ou reposicao.
- `after_sales_resolution_sla_pressure`: fila aberta, severidade alta ou demora de resolucao.

## Datasets BI

- `bi_after_sales_cases_dataset`: visao analitica por case com pedido, SKU, custo, status, severidade e tempo de resolucao.
- `bi_after_sales_case_events_dataset`: timeline dos eventos de cada case.
- `bi_logistics_returns_dataset`: devolucoes e reversas logisticas por shipment.

## Fronteira operacional

A DGE 2.0 nao vira help desk nem motor de checkout. Ela registra a memoria operacional auditavel e produz leitura de impacto. A execucao transacional continua no ecommerce/app/suporte/ERP/transportadoras.

## Governanca, tenant e SLA

O pos-venda nasce governado pelo mesmo motor de aprovacoes da DGE:

- Workflow: `after_sales_case_approval`.
- Etapas: gestor de suporte, aprovacao financeira e auditoria final tenant.
- Roles: `support_operator`, `support_manager`, `logistics_operator`, `logistics_manager`, `finance_manager`, `tenant_auditor`.
- Responsabilidades: `after_sales_case_entry`, `after_sales_case_review`, `after_sales_financial_approval`, `after_sales_final_audit`.
- SLA: cada case recebe `sla_policy_key`, `sla_due_at` e `sla_status`.
- BI: datasets exibem `approval_status`, etapa atual, politica SLA e vencimento.

Cases com impacto financeiro, severidade alta/critica ou tipos sensiveis entram em aprovacao formal antes de serem considerados auditados.

## Expansoes futuras

- SLA por tenant, cargo, unidade e tipo de case.
- Plano de mitigacao assistido por IA quando um bottleneck de pos-venda acionar reforecast.
- Relacao de case com ajuste de preco, categoria, produto, estoque e margem quando ecommerce real estiver integrado.
- Relatorios periodicos automaticos por n8n e Superset.
- Fine-tuning com cases resolvidos, decisao humana e resultado observado.
