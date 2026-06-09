---
title: Arquitetura da DGE
category: projetos
tags:
- dge
- arquitetura
- postgresql
- multitenant
- api
- backend
visibility: public
priority: 1
updated_at: '2026-06-09'
summary: Resumo técnico da arquitetura da DGE e dos módulos documentados.
---

# Arquitetura da DGE

A DGE separa ERP Core da camada de inteligência operacional. O ERP registra cadastros, estoque e operação; a DGE cruza esses dados com KPIs, projeções, fórmulas, reforecast, canais, logística, compras, exceções e governança.

## Pilares técnicos

- Backend modular com contratos de domínio.
- Banco relacional em PostgreSQL com modelagem de schemas.
- Estrutura multitenant, autenticação e permissões.
- APIs internas para módulos de produto, SKU, pedidos, canais, compras, estoque, frete, BI e exceções.
- Registros de lineage, snapshots, versões e estados.
- Smokes/checks para validar módulos e contratos.
- Roadmap Debt Register para diferenciar capacidade ativa, parcial, planejada e bloqueada.

## Módulos documentados na base DGE 2.0

A base de referência inclui documentação para Activation and KPI History, Adaptive Projection Engine, After Sales Claims Backbone, Automation Backbone, BI Semantic Layer, Bling ERP Connector, Channel Intelligence, Commerce Operational Events, Commerce Orders and Identity, Core Schema, Data Contracts, ERP Intelligence Integration, Event Registry, Forecast Reconciliation, Freight Economics, Fulfillment Control Tower, Inventory Capacity, KPI Intelligence, Marketplace Fulfillment Pools, Metric and Formula Registry, ML/Fine-tuning, Module Registry, Operational Cockpit, Operational Command Center, Operational Governance, Operational Nervous System, Projection Engine, Projection Impact Analyzer, Tenant Access and Responsibility e contratos de integração.

## Decisão arquitetural importante

A DGE evita esconder regra de negócio no frontend. A interface é uma superfície futura; a base real é o backend, onde vivem validações, contratos, cálculos, estados e auditoria.
