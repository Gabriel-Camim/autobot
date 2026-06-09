---
title: DGE fonte - DGE 2.0 - Development Doctrine
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-development-doctrine.md.'
source_path: docs/architecture/dge-2.0-development-doctrine.md
---

# DGE 2.0 - Development Doctrine

Fonte original DGE 2.0: `docs/architecture/dge-2.0-development-doctrine.md`.

---

# DGE 2.0 - Development Doctrine

## Financial Operations Doctrine

- DGE projection is not approved budget, obligation, settlement, reconciled cash or official bookkeeping.
- Posted financial ledgers are immutable. Corrections use reversals.
- Settlement observation does not infer reconciled cash.
- Every reconciliation match requires human review in Core v1.
- Official accounting and official tax assessment remain external boundaries.

## Principio Central

A DGE 2.0 deve ser desenvolvida como sistema novo, limpo e expansivel.

A DGE 1.0 e prototipo historico preservado. Ela pode inspirar decisoes de produto, mas nao deve ser dependencia tecnica, fonte oficial de dados ou base de runtime.

## Isolamento Absoluto Do Piloto

O piloto/DGE 1.0 e somente uma prova de conceito historica. A DGE 2.0 nao e uma refatoracao incremental do piloto: ela nasce como produto novo, com backend, contratos, banco e futuro frontend proprios.

Regra:

```txt
Piloto = referencia visual e historica.
DGE 2.0 = produto novo, com arquitetura propria.
Nenhuma evolucao da DGE 2.0 deve exigir manutencao do piloto.
```

Diretrizes:

- nao implementar features novas no piloto;
- nao migrar mutations, login visual, documentos ou memoria do piloto para `tenant/auth`;
- nao incluir rotas raiz legadas em auditorias de auth, readiness ou cobertura da DGE 2.0;
- nao tratar compatibilidade com `src/App.jsx` como requisito da DGE 2.0;
- consultar o piloto somente como referencia de tese, narrativa, experiencia e aprendizados;
- exigir decisao arquitetural explicita antes de qualquer reutilizacao futura;
- manter `server/index.js` restrito ao piloto congelado e `dge-2.0/server/index.js` como entrypoint exclusivo do produto novo.

## Forma De Agir

Quando houver dois caminhos:

1. caminho simples, rapido, mas com risco de divida tecnica;
2. caminho mais complexo, mas arquiteturalmente mais correto;

a DGE 2.0 deve favorecer o caminho mais correto, desde que ele seja justificavel para a expansao futura do sistema.

## Regras

- Nao esconder mudancas estruturais importantes atras de adaptadores ambiguos.
- Nao criar ponte permanente com DGE 1.0.
- Nao copiar codigo legado apenas para trocar o problema de lugar.
- Nao manter contrato ruim so porque ja existe.
- Reformular contratos quando eles virarem gargalo real.
- Manter compatibilidade temporaria apenas quando explicitamente declarada, com destino claro de remocao.
- Preferir contratos versionados a payloads soltos.
- Preferir repositories e services explicitos a stores genericos.
- Preferir engine modular e trace-first a calculos hardcoded.
- Preferir schema fundacional proprio a dependencia em tabelas legadas.
- Toda decisao estrutural deve ser registrada em blueprint ou plano de migracao.

## Arquitetura Antes De Execucao

Antes de implementar uma camada central, a DGE 2.0 deve primeiro definir:

- responsabilidade da camada;
- contrato de entrada;
- contrato de saida;
- persistencia;
- rastreabilidade;
- governanca;
- qualidade;
- extensoes futuras;
- riscos de acoplamento;
- criterio de validacao.

## Contratos

Endpoints e services centrais devem expor contratos versionados.

Exemplo:

```txt
scenario.calculate.v2
```

Um contrato pode manter campos temporarios de compatibilidade, mas deve declarar isso explicitamente:

```txt
compatibility.legacyTopLevelFields = true
```

Compatibilidade temporaria nao e licenca para divida tecnica permanente.

### Gargalo De Contrato

Quando um contrato central virar gargalo para a arquitetura futura, a DGE 2.0 deve tratar isso como problema de desenho do sistema, nao como detalhe de implementacao.

Diretriz:

- explorar o contrato antes de plugar novas engines;
- redesenhar o contrato quando ele estiver limitando rastreabilidade, governanca, versionamento, reforecast, suporte/SLA, RAI ou expansao operacional;
- evitar adaptadores que apenas embrulham um contrato ruim;
- aceitar um caminho mais complexo quando ele deixa o sistema mais limpo, explicavel e expansivel;
- manter compatibilidade apenas de forma explicita, versionada e removivel;
- validar o novo contrato com smoke tests antes de conectar modulos centrais.

Aplicacao pratica:

```txt
Se /api/scenarios/calculate nao comportar o futuro da DGE 2.0,
o contrato deve evoluir para um envelope versionado, rastreavel e governado,
em vez de receber uma camada de compatibilidade silenciosa.
```

## Engines

Engines centrais devem ser plataformas expansivas, nao arquivos monoliticos.

Exemplo para Projection Engine:

```txt
Projection Contract
  -> Assumption Graph
  -> Formula Execution Graph
  -> Temporal Model
  -> Constraint Layer
  -> Variance Layer
  -> Versioning
  -> Explainability
  -> Persistence
```

Trace nao deve ser camada posterior. O calculo deve nascer rastreavel.

## Boundary Doctrine

Tudo dentro de `dge-2.0/` deve evitar imports da DGE 1.0.

O check oficial e:

```txt
npm run check:dge2-boundary
```

Violacoes conhecidas devem ser tratadas como bloqueios arquiteturais, nao como estado aceitavel.

## Decisao Operacional

Se uma decisao parecer mais demorada agora, mas evitar reescrita futura da engine, do schema, dos contratos ou da governanca, ela deve ser considerada seriamente como caminho preferencial.

O objetivo nao e andar rapido hoje e pagar depois. O objetivo e construir a DGE 2.0 para nao precisar ser reconstruida quando entrarem:

- estoque;
- hubs;
- ecommerce behavior;
- frete;
- fulfillment;
- reforecast;
- suporte/SLA;
- RAI;
- ML/fine-tuning.

## 20x Acceleration Doctrine

O Pro 20x deve acelerar execucao de arquitetura governada, nao multiplicar drift.

Regra:

```txt
20x mais capacidade so e vantagem se houver 20x mais disciplina de contrato, smoke, estado, BI, excecao e auditoria.
```

Antes do frontend final, a DGE deve ter:

- fluxos principais registrados em `operational.flow_registry.v1`;
- estados criticos registrados em `operational.state_machine_registry.v1`;
- writes criticos cobertos por auth/role/scope;
- action availability exposta para o futuro frontend;
- Service Desk conectando Exception Hub a resolucao humana;
- BI/Superset semanticamente certificado;
- ERP completeness audit para catalogo, preco, estoque, fornecedor, compra, canal e CDD;
- n8n governado por promotion gates, idempotencia e dead-letter;
- IA/RAI consumindo contextos auditados, sem executar acao final.

Frontend nao deve ser usado para esconder falta de regra de negocio no backend. A UI renderiza view models e acoes permitidas; ela nao decide permissao, transicao, preco, estoque, reforecast, ticket ou excecao.

## Service Desk Doctrine

Exception Hub detecta e prioriza. Service Desk organiza resolucao.

Toda excecao critica deve poder virar ticket idempotente, linkado a entidade operacional, com SLA, actor responsavel, playbook, evidencia e outcome.

Sem ticket, a DGE apenas aponta problema. Com ticket, a DGE vira operacao executavel.

## n8n Doctrine

n8n pode orquestrar, repetir, agendar e encaminhar. A DGE continua dona de:

- contrato;
- estado;
- idempotencia;
- auditoria;
- fallback manual;
- Exception Hub;
- aprovacao final.

`system_integration` e automacoes podem submeter traces, previews, drafts e runs. Eles nao podem aprovar final, resolver excecao final, publicar versao oficial, sobrescrever estoque canonico ou executar ajuste material sem gate humano.

## Operational Domain Map Doctrine

Antes de abrir um novo runtime, classificar seu lugar nos ciclos comercial, fisico, fiscal e financeiro descritos em:

```txt
docs/architecture/dge-2.0-operational-domain-map.md
```

Diretrizes:

- nao criar schema placeholder apenas para antecipar dominio futuro;
- distinguir motor financeiro projetivo de subledger financeiro operacional;
- tratar consignacao franqueada como relacao patrimonial propria, nao como transferencia interna comum;
- manter escrituracao fiscal oficial na fronteira contador/provedor;
- fechar invariantes de banco e readiness de producao antes de ampliar integracoes reais;
- registrar novos blockers no debt register com macro afetada e owner.

## Reforecast E Mitigacao Futura

Reforecast deve nascer de reconciliacao entre projetado e realizado, nao de recalculo solto.

A DGE 2.0 deve preparar readiness para mitigacao operacional futura, mas nao deve implementar plano de mitigacao profundo antes de existir contexto real de ecommerce, ERP, estoque, margem por produto, cupons, frete real e comportamento do usuario.

Regra:

- DGE detecta, compara, explica, governa e versiona;
- ecommerce executa experiencia, preco, cupom, checkout e comportamento;
- ERP/Bling fornece fatos de produto, custo, estoque, nota e pedido;
- IA futura pode sugerir mitigacoes somente com contexto integrado e aprovacao humana;
- `social_action` e escopo executivo/restrito, nao operacional comum.

## ERP Operational Kernel Doctrine

O ERP da DGE 2.0 nao deve crescer por remendos em repositories grandes. Toda nova evolucao operacional deve declarar seu nucleo antes de criar schema, endpoint ou automacao.

Envelope obrigatorio por nucleo:

```txt
cadastro -> operacao -> consulta -> automacao readiness -> auditoria -> BI -> inteligencia
```

Regras:

- nao adicionar nova regra de negocio em mega-repositories ou services raiz;
- usar fonte legada apenas como equivalencia temporaria declarada;
- remover legado somente apos smoke/check equivalente verde;
- todo adapter temporario exige `expiresAt`, `replacedByNucleus` e `removalCheck`;
- CRM identificado, ICP nominal e campanhas exigem consentimento LGPD valido;
- behavior antes do aceite deve permanecer pseudonimizado;
- n8n pode orquestrar somente depois de readiness declarado pelo nucleo;
- materialized views continuam adiadas para o macro `BI/Superset Semantic Foundation`.
