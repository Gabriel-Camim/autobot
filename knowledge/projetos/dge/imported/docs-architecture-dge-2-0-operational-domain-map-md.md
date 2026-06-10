---
title: DGE fonte - DGE 2.0 Operational Domain Map
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-operational-domain-map.md.'
source_path: docs/architecture/dge-2.0-operational-domain-map.md
---

# DGE 2.0 Operational Domain Map

Fonte original DGE 2.0: `docs/architecture/dge-2.0-operational-domain-map.md`.

---

# DGE 2.0 Operational Domain Map

## Financial Operations Cycle: Active

The operational financial cycle is implemented as a managerial subledger:

```txt
operational fact
-> idempotent command
-> title and installments
-> balanced journal
-> observed settlement
-> statement import
-> mandatory human reconciliation review
-> reconciled cash
-> budget and financial variance preview
```

The DGE keeps official bookkeeping, official tax assessment and external fiscal issuance outside this boundary.

## Tese

A DGE 2.0 nao e apenas ERP, BI, automacao ou projection engine. Ela e uma camada de inteligencia operacional auditavel que conecta fatos fisicos, comerciais, fiscais e financeiros a KPIs, gargalos e reforecast governado.

Este mapa registra dominios ativos, parciais e futuros antes de novos runtimes. Ele nao autoriza schema placeholder nem antecipa implementacao.

## Quatro Ciclos Conectados

```txt
Ciclo comercial:
pedido -> pagamento -> fulfillment -> expedicao -> pos-venda -> liquidacao -> KPI -> reforecast

Ciclo fisico:
compra -> recebimento -> staging/distribuicao -> estoque fisico -> transferencia -> consignacao -> sell-out ou retorno

Ciclo fiscal:
classificacao -> solicitacao documental -> emissao externa -> autorizacao/rejeicao -> cancelamento/devolucao -> evidencia

Ciclo financeiro:
titulo -> vencimento -> liquidacao -> conciliacao -> caixa -> centro de custo -> margem realizada -> projecao
```

## Fronteiras Oficiais

### Financeiro Operacional

A DGE tera subledger operacional proprio:

- contas a pagar;
- contas a receber;
- caixa;
- liquidacoes;
- conciliacao;
- centros de custo;
- lancamentos gerenciais.

O atual `Scenario & Finance Engine` continua sendo motor projetivo. Ele calcula cenarios e payback; nao substitui o subledger operacional.

### Contabilidade E Fiscal Oficial

A DGE classifica operacoes, preserva lineage, cria requests, bloqueia fluxos quando necessario e reconcilia evidencias. Contador e provedores externos continuam responsaveis por:

- escrituracao fiscal oficial;
- apuracao tributaria;
- emissao final de documentos;
- autorizacao, rejeicao e cancelamento externos.

### Franquias

Para a Galpao, consignacao e a politica prioritaria:

```txt
estoque enviado para franquia
-> posse fisica na unidade
-> propriedade patrimonial permanece da marca
-> sell-out entra via Bling/PDV reconciliado
-> baixa consignacao
-> gera recebivel, comissao ou repasse conforme contrato
```

Consignacao, transferencia interna, remessa e venda B2B nao sao sinonimos. A arquitetura permanece configuravel por operacao.

## Dominios

| Dominio | Estado | Proximo runtime |
| --- | --- | --- |
| Commercial Order Cycle | `partial` | financeiro, carrier runtime e ecommerce real |
| Physical Inventory Cycle | `partial` | hardening, planejamento e consignacao |
| Fiscal Document Cycle | `partial` | provider lifecycle e XML/NF-e assistido |
| Financial Operations Cycle | `skeleton` | subledger operacional |
| Franchise Consignment Cycle | `skeleton` | ledger consignado e sell-out reconciliado |
| Inventory Planning & Replenishment | `skeleton` | giro, cobertura, lead time e sugestoes |
| DGE Master Architecture Inventory | `active` | ERP Core Pre-Closure Hardening |
| Integration Reliability Cycle | `skeleton` | inbox, outbox, retry, replay e dead-letter |
| Production Readiness Plane | `partial` | runtime de observabilidade, retencao, segredos e rate limit ativo; faltam restore drill isolado verificado e entrypoint backend exclusivo DGE 2.0 |
| Official Accounting Boundary | `external_boundary` | integracao com contador/provedor |

## Invariantes

- CDD tem estoque fisico proprio.
- Hub oferece capacidade de reposicao; nao vira soma virtual do CDD.
- Estoque disponivel e estoque futuro permanecem separados.
- Estoque consignado pode estar na franquia e continuar patrimonialmente pertencendo a marca.
- Sell-out reconciliado baixa consignacao antes de gerar recebivel, comissao ou repasse.
- Transferencia, consignacao, venda B2B e remessa nao sao sinonimos.
- Movimento de estoque, documento fiscal, receita realizada e margem gerencial permanecem separados.
- Reembolso de pos-venda conecta estoque, financeiro e fiscal.
- APIs externas entram por contrato, idempotencia, inbox/outbox, retry e replay.
- n8n orquestra; DGE decide regra, estado e aprovacao.
- IA le fatos auditados e recomenda; nao liquida, paga, emite documento ou aprova acao final.

## Ordem Oficial

1. Heavy Backend Hardening v2. `completed`
2. Production Readiness Plane v1. `next_runtime`
3. Financial Operations Runtime Core v1.
4. Inventory Planning & Replenishment v1.
5. Franchise Consignment Network v1.
6. Caos Lab Service Desk v1.
7. DGE Master Architecture Inventory.
8. ERP Core Pre-Closure Hardening.
9. Service Desk / Error / Intelligence Hardening.
10. Fulfillment/Freight + n8n Readiness Alignment.
11. ERP Core Kernel Closure.
12. Backend Nucleus Migration Batches.
13. DGE Backend Kernel Closure.
14. Integration Reliability Plane + n8n Control Plane.
15. BI/Superset Semantic Foundation.
16. Fiscal Document Provider Lifecycle + XML/NF-e Assisted Import.
17. Freight/Frenet/Loggi Runtime.
18. Bling Live Controlled Run.
19. Full end-to-end simulation.
20. IA/RAI Operational Intelligence.
21. Next.js UX/UI + frontend final.
22. Homologacao.
23. Producao.

## Isolamento Absoluto Do Piloto

O piloto e prova de conceito historica congelada. Ele nao participa dos ciclos operacionais acima e nao pode ser tratado como dependencia tecnica, auth surface, readiness surface ou frontend transitorio da DGE 2.0.

Divida temporaria:

- `pilot_dge2_runtime_mount_coupling`: resolvido por `dge-2.0/server/index.js`; o piloto permanece congelado em `5173/8787` e a DGE 2.0 opera exclusivamente em `8788`.
- `backup_restore_drill_missing`: resolvido por restore drill Docker efemero com evidencia auditavel, RPO `24h` e RTO `4h`.

## Contratos Declarativos

- `operational.domain_map.v1`
- `operational.roadmap_dependency_graph.v1`
- `operational.production_readiness_map.v1`

Endpoints:

- `GET /api/operations/domain-map`
- `GET /api/operations/roadmap-dependency-graph`
- `GET /api/operations/production-readiness-map`
# Checkpoint: abastecimento preventivo ativo

O ciclo fisico agora inclui planejamento preventivo auditavel: saldo fisico, demanda observada, uplift projetivo aprovado, cobertura, safety stock, inbound confirmado, alternativas e dupla aprovacao. A logistica continua executando `ship` e `receive`; ela nao substitui a aprovacao de estoque nem a aprovacao financeira.

# Checkpoint: rede franqueada consignada ativa

O ciclo franqueado agora possui ledger patrimonial proprio. `ship` registra transito consignado; `receive` libera saldo disponivel na franquia; sell-out reconciliado baixa consignacao; fechamento diario aprovado pelo financeiro gera recebivel. Retorno, avaria, perda, divergencia e fallback CDD permanecem fluxos distintos e governados.

Proximo runtime oficial: `Caos Lab Service Desk v1`.
## Repository Layer E Operadores

Antes do Service Desk, a DGE 2.0 fecha duas fundacoes:

```txt
Repository Layer Migration v1
→ ERP Operator Directory + Workforce Identity & Behavior Trace v1
→ Caos Lab Service Desk v1
```

Services coordenam regras; repositories locais ao dominio encapsulam SQL e locks. O ERP registra a pessoa operacional, Governance registra autenticacao e autorizacao, e o Behavior Trace conecta acoes auditadas sem copiar estoque, dinheiro ou decisoes dos ledgers proprietarios.

BI permanece com views live. Materialized views serao avaliadas apenas no `BI/Superset Semantic Foundation`, dataset por dataset.

## ERP Operational Kernel Reset E Master Architecture Inventory

O dominio `ERP Operational Kernel Reset` nao libera mais `Integration Reliability Plane + n8n Control Plane` diretamente. Antes disso, a DGE executa `DGE Master Architecture Inventory`, `ERP Core Pre-Closure Hardening`, `Service Desk / Error / Intelligence Hardening` e `Fulfillment/Freight + n8n Readiness Alignment`.

Estado: `active`.

Entidades declarativas:

- `erp_operational_nucleus`;
- `legacy_quarantine_source`;
- `nucleus_equivalence_map`;
- `crm_consent_policy`;
- `n8n_readiness_intent`.

Invariantes:

- kernel novo nasce em paralelo;
- demo atual e migravel;
- legado so fica como fonte temporaria de equivalencia;
- adapter temporario exige prazo e check de remocao;
- cada nucleo precisa cobrir cadastro, operacao, consulta, automacao readiness, auditoria, BI e inteligencia;
- materialized views continuam adiadas.

O `DGE Master Architecture Inventory` separa tres closures:

- `ERP Core Kernel Closure`;
- `DGE Backend Kernel Closure`;
- `Production/Frontend Readiness Closure`.

Superset, IA/RAI, cloud/lakehouse, Next.js, n8n, Bling live, Freight/Frenet/Loggi, lineage, snapshots, banco de auditoria, logs para Service Desk, homologacao e producao precisam estar classificados como entregue, readiness, blueprint futuro, blocker, boundary externo ou fora de escopo.

Batch 3 material:

- `catalog_nucleus`: `migrated`;
- `pricing_promotion_nucleus`: `migrated`;
- `supplier_purchase_nucleus`: `migrated`, com supplier master, supplier variant terms, PO, receipt, inbound distribution, confirmacao e custo de entrada migrados;
- `inventory_nucleus`: `migrated`, com locations, movements, balances, reservations, stock counts, transfers, snapshot diario, PDV/store sale, reconciliacao commerce e exception material resolution migrados;
- `intelligence_nucleus`: `migrated`, com operational context, workflow control, exception center, exception resolution orchestration e KPI derivation migrados;
- `erp.repository.js`: aposentado no Batch 4; nao deve voltar ao facade ERP.

Ordem atualizada:

1. Heavy Backend Hardening v2. `completed`
2. Production Readiness Plane v1. `completed`
3. Financial Operations Runtime Core v1. `completed`
4. Inventory Planning & Replenishment v1. `completed`
5. Franchise Consignment Network v1. `completed`
6. Repository Layer Migration v1. `completed`
7. ERP Operator Directory + Workforce Identity & Behavior Trace v1. `completed`
8. Caos Lab Service Desk v1. `completed`
9. ERP Operational Kernel Reset v2. `completed`
10. DGE Master Architecture Inventory. `completed`
11. ERP Core Pre-Closure Hardening. `completed`
12. Service Desk / Error / Intelligence Hardening. `completed`
13. Fulfillment/Freight + n8n Readiness Alignment. `next_runtime`
14. ERP Core Kernel Closure.
15. Backend Nucleus Migration Batches.
16. DGE Backend Kernel Closure.
17. Integration Reliability Plane + n8n Control Plane.
