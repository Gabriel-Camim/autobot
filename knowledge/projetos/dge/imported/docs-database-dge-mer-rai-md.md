---
title: DGE fonte - DGE MER RAI-ready
category: projetos
tags:
- dge
- fonte-original
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/database/dge-mer-rai.md.'
source_path: docs/database/dge-mer-rai.md
---

# DGE MER RAI-ready

Fonte original DGE 2.0: `docs/database/dge-mer-rai.md`.

---

# DGE MER RAI-ready

Este documento define o esqueleto de banco da DGE para a Build 1 e para a camada futura de RAI.

Neste projeto, RAI significa Retrieval-Augmented Intelligence: inteligencia aumentada por recuperacao seletiva, versionada e auditavel de contexto.

RAI nao e apenas RAG tradicional. RAG busca trechos e responde. RAI, na DGE, recupera documentos, diretrizes, cenarios, KPIs, contratos, sprints e trilhas autorizadas, monta um contexto rastreavel e registra quais fontes sustentaram cada resposta.

## Principio Central

Frontend mostra, simula e orienta.
Backend valida, calcula, gera, registra e audita.
Postgres preserva a memoria oficial.
RAI recupera contexto confiavel para aumentar a inteligencia da IA.

## Camadas Do MER

```txt
tenant
  -> project
    -> scenario_snapshot
      -> scenario_premise
      -> kpi_snapshot
    -> ai_conversation
      -> ai_message
      -> ai_trace
        -> ai_trace_sources
    -> sprint
      -> sprint_item
    -> document
      -> document_version
    -> contract
      -> contract_annex
      -> contract_activation
    -> retrieval_index
      -> retrieval_source
      -> retrieval_chunk
      -> retrieval_query
      -> retrieval_context
    -> future commerce / erp / logistics / crm
```

## Core Build 1

### tenants

| Campo | Tipo | Chave | Descricao |
| --- | --- | --- | --- |
| id | uuid | pk | Organizacao dona dos dados |
| name | varchar(160) |  | Nome do tenant |
| slug | varchar(120) | unique | Identificador amigavel |
| status | varchar(40) |  | active, paused, archived |
| metadata | jsonb |  | Configuracoes futuras |
| created_at | timestamptz |  | Criacao |
| updated_at | timestamptz |  | Atualizacao |

### projects

| Campo | Tipo | Chave | Descricao |
| --- | --- | --- | --- |
| id | uuid | pk | Projeto operacional |
| tenant_id | uuid | fk tenants.id | Tenant dono |
| name | varchar(160) |  | Nome |
| slug | varchar(120) |  | Identificador |
| status | varchar(40) |  | active, paused, archived |
| metadata | jsonb |  | Configuracoes |
| created_at | timestamptz |  | Criacao |
| updated_at | timestamptz |  | Atualizacao |

### scenario_snapshots

Snapshot imutavel do estado de um cenario em um momento. Contratos, relatorios e respostas de IA devem apontar para snapshots, nao para valores soltos vindos do navegador.

| Campo | Tipo | Chave | Descricao |
| --- | --- | --- | --- |
| id | uuid | pk | Snapshot imutavel |
| tenant_id | uuid | fk tenants.id | Tenant |
| project_id | uuid | fk projects.id | Projeto |
| name | varchar(160) |  | Nome |
| scenario_type | varchar(60) |  | conservador, moderado, agressivo, personalizado |
| source | varchar(80) |  | ui, ai, import, migration |
| assumptions_json | jsonb |  | Premissas completas |
| calculations_json | jsonb |  | Calculos oficiais |
| projection_json | jsonb |  | Projecoes oficiais |
| calculation_version | varchar(80) |  | Versao do motor financeiro |
| input_hash | varchar(160) |  | Hash de auditoria |
| created_by | uuid | nullable | Usuario futuro |
| created_at | timestamptz |  | Criacao |

### scenario_premises

Premissas atomizadas para consulta, filtro e recuperacao contextual.

| Campo | Tipo | Chave | Descricao |
| --- | --- | --- | --- |
| id | uuid | pk | Premissa |
| tenant_id | uuid | fk tenants.id | Tenant |
| project_id | uuid | fk projects.id | Projeto |
| scenario_snapshot_id | uuid | fk scenario_snapshots.id | Snapshot |
| group_key | varchar(100) |  | marketplace, canal, logistica |
| key | varchar(120) |  | Chave tecnica |
| label | varchar(180) |  | Rotulo humano |
| value_numeric | numeric | nullable | Valor numerico |
| value_text | text | nullable | Valor textual |
| unit | varchar(40) |  | percent, currency, month, count |
| data_type | varchar(40) |  | percent, currency, integer, text, boolean |
| metadata | jsonb |  | Contexto |
| created_at | timestamptz |  | Criacao |

### kpis e kpi_snapshots

`kpis` define o indicador. `kpi_snapshots` registra a leitura do indicador em um cenario e momento especifico.

Exemplos: vazamento mensal, taxa total marketplace, lucro incremental, payback, ROI, GMV proprio, frete subsidiado.

### documents e document_versions

`documents` representa o documento conceitual. `document_versions` representa conteudo, arquivo, versao e status.

Relacoes:

| Relacao | Descricao |
| --- | --- |
| documents 1:n document_versions | Um documento pode ter muitas versoes |
| documents n:n ai_traces | Via ai_trace_sources |
| documents n:n retrieval_sources | Documento entra em um indice de recuperacao |
| documents 1:n contract_annexes | Anexos sao documentos versionaveis |

### ai_conversations, ai_messages e ai_traces

Conversas sao threads. Mensagens sao entradas e saidas. Traces registram a decisao, o contexto recuperado, as fontes usadas e a confiabilidade.

`ai_trace_sources` e a ponte entre a resposta da IA e as fontes:

- document_id;
- document_version_id;
- scenario_snapshot_id;
- kpi_snapshot_id;
- sprint_id;
- contract_id;
- retrieval_context_id.

### sprints

Sprint Memory e a memoria cronologica da evolucao sistemica. Ela precisa ser recuperavel pela IA para explicar por que a DGE evoluiu em determinada direcao.

### contracts, contract_annexes e contract_activations

Contrato sem snapshot e texto. Contrato com snapshot versionado vira instrumento de governanca.

| Relacao | Descricao |
| --- | --- |
| contracts n:1 scenario_snapshots | Contrato herda premissas e KPIs oficiais |
| contract_annexes n:1 contracts | Anexos filhos em cascata |
| contract_annexes n:1 documents | Anexo tambem e documento versionavel |
| contract_activations n:1 contracts | Ativacao final do pacote |

## Camada RAI: Retrieval-Augmented Intelligence

### retrieval_indexes

Define um indice logico de recuperacao.

Exemplos:

- diretrizes_dge;
- memoria_sprints;
- contratos_e_anexos;
- cenarios_e_kpis;
- ia_traces_autorizadas;
- ecommerce_futuro.

### retrieval_sources

Fonte original indexada.

Pode apontar para:

- documento;
- versao de documento;
- sprint;
- contrato;
- snapshot de cenario;
- trace de IA;
- futuro pedido, produto, cliente ou estoque.

### retrieval_chunks

Trechos recuperaveis. Na Build 1 podem ser textuais, com hash e metadata. Embeddings ficam preparados para futuro com pgvector, mas nao precisam ser implementados agora.

### retrieval_queries e retrieval_results

Registram o que foi buscado, quais chunks foram encontrados, score, ranking e quais foram selecionados para contexto.

### retrieval_contexts

Registra o contexto final montado para a IA. Isso permite auditar:

```txt
Pergunta X
-> consulta Y
-> chunks A/B/C
-> contexto Z
-> resposta R
```

## Futuro Ecommerce/ERP/Logistica/CRM

Essas entidades ficam desenhadas, mas nao entram na Build 1:

- sales_channels
- customers
- products
- product_categories
- product_applications
- orders
- order_items
- carts
- cart_items
- erp_integrations
- erp_sync_runs
- inventory_locations
- inventory_balances
- invoices
- shipping_quotes
- shipments
- shipment_events
- hubs
- crm_segments
- campaigns
- campaign_events
- financial_events
- marketplace_fee_snapshots

## Regra De Implantacao

Build 1 implementa a coluna vertebral, memoria oficial e retrieval auditavel. Entidades de ecommerce, ERP, logistica e CRM entram depois, sem refazer o banco.

## Extensao DGE 2.0

A extensao incremental da modelagem fica em:

```txt
dge-2.0/db/schema-dge-2.sql
```

Ela adiciona:

- catalogo de metricas;
- registro versionado de formulas;
- execucoes de calculo;
- traces de formulas;
- estados mensais de projecao;
- trace packs de projecao;
- eventos de ativacao;
- snapshots diarios de KPIs;
- fechamento mensal de KPIs;
- timeline operacional;
- variancia observado vs projetado;
- agentes IA modularizados;
- RAI traces com caminho cognitivo estruturado;
- candidatos de fine-tuning revisaveis.

O caminho cognitivo do RAI deve ser salvo como trilha estruturada de decisao, fontes, verificacoes e resumo operacional. Ele nao deve depender de raciocinio bruto privado do modelo.
