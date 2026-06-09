---
title: DGE fonte - DGE 2.0 - Directory Boundary and Migration Plan
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-directory-boundary-and-migration-plan.md.'
source_path: docs/architecture/dge-2.0-directory-boundary-and-migration-plan.md
---

# DGE 2.0 - Directory Boundary and Migration Plan

Fonte original DGE 2.0: `docs/architecture/dge-2.0-directory-boundary-and-migration-plan.md`.

---

# DGE 2.0 - Directory Boundary and Migration Plan

## Problema

Os artefatos da DGE 2.0 foram criados nos mesmos diretorios historicos da DGE 1.0:

- `docs/architecture`
- `docs/contracts`
- `docs/operations`
- `docs/database`
- `db`
- `server/contracts`
- `server/modules`
- `scripts`
- `docs/deliverables`

Isso cria risco de confusao entre legado, runtime atual, backbone novo, contratos de dados e entregaveis executivos.

## Decisao

A partir deste ponto, a DGE 2.0 deve ter diretorio exclusivo:

- `dge-2.0/`

A DGE 1.0 deve ser tratada como legado preservado:

- `dge-1.0-legacy/`

Novos artefatos da DGE 2.0 devem nascer dentro de `dge-2.0/`.

## Estrutura-Alvo

```txt
dge-2.0/
  docs/
    architecture/
    contracts/
    operations/
    database/
  db/
  server/
    contracts/
    modules/
  scripts/
  deliverables/

dge-1.0-legacy/
  README.md
  ai_contexts/
  api/
  src/
  docs/
  server/
```

## Regra de Migracao

Nao mover runtime executavel em massa sem ajuste de referencias.

Cada lote deve ter:

- origem;
- destino;
- tipo de arquivo;
- impacto esperado;
- imports ou scripts afetados;
- validacao minima;
- rollback simples.

## Classificacao Inicial

### DGE 2.0 - Candidatos a migracao documental imediata

- `docs/architecture/dge-2.0-*.md`
- `docs/contracts/dge-2.0-*.md`
- `docs/operations/dge-2.0-*.md`
- `docs/database/postgres-backbone-rai-plan.md`
- `docs/database/dge-mer-rai.md`
- `docs/deliverables/DGE-2.0-*`
- `docs/deliverables/build_dge_technical_document.py`

### DGE 2.0 - Candidatos a migracao tecnica controlada

- `dge-2.0/db/schema-dge-2.sql`
- `dge-2.0/db/setup-dge-2.js`
- `server/contracts/*`
- `server/modules/*`
- `server/dataContracts.js`
- `scripts/smoke-*.js` relacionados aos modulos DGE 2.0

Esses arquivos devem ser migrados junto com ajustes em:

- `package.json`
- `server/index.js`
- imports internos dos modulos;
- smoke tests;
- documentacao de setup.

### DGE 1.0 - Legado a preservar

- `src/*`
- `api/*`
- `ai_contexts/*`
- `db/setup-postgres.js`
- `db/schema-retrieval.sql`
- documentos historicos que nao comecam com `dge-2.0`
- contratos e anexos gerados da DGE 1.0

## Ordem Recomendada

1. Criar fronteira fisica `dge-2.0/` e `dge-1.0-legacy/`.
2. Migrar apenas documentacao DGE 2.0 para `dge-2.0/docs`.
3. Atualizar referencias de docs e deliverables.
4. Migrar `db/schema-dge-2.sql` e `db/setup-dge-2.js` para `dge-2.0/db`. Concluido no Lote 2.
5. Ajustar scripts npm para apontar para os novos caminhos.
6. Migrar smoke tests DGE 2.0 para `dge-2.0/scripts`.
7. Migrar `server/contracts` e `server/modules` para `dge-2.0/server`.
8. Ajustar imports do backend.
9. Rodar `npm run smoke:backend`.
10. Somente depois mover legado DGE 1.0 para `dge-1.0-legacy/`.

## Status de Migracao

### Lote 1 - Documentacao e Entregaveis DGE 2.0

Status: parcialmente concluido.

Movido para `dge-2.0/`:

- documentacao `docs/architecture/dge-2.0-*.md`;
- contratos `docs/contracts/dge-2.0-*.md`;
- operacao `docs/operations/dge-2.0-*.md`;
- database docs `postgres-backbone-rai-plan.md` e `dge-mer-rai.md`;
- PDF final DGE 2.0;
- script de geracao do documento tecnico;
- relatorios de acessibilidade;
- assets e paginas renderizadas do documento tecnico.

Pendente:

- `docs/deliverables/DGE-2.0-arquitetura-tecnico-executiva-galpao.docx`

Motivo: arquivo bloqueado por outro processo no momento da migracao. Mover para `dge-2.0/deliverables/` quando o arquivo estiver fechado/desbloqueado.

### Lote 2 - Banco DGE 2.0

Status: concluido.

Movido para `dge-2.0/db/`:

- `schema-dge-2.sql`;
- `setup-dge-2.js`.

Ajustado:

- `package.json` agora executa `npm run db:setup:dge2` via `node dge-2.0/db/setup-dge-2.js`;
- imports do setup foram ajustados para continuar lendo os registries ainda localizados em `server/modules`.

Observacao: `server/modules` foi migrado no Lote 4.

### Lote 3 - Smoke Tests DGE 2.0

Status: concluido.

Movido para `dge-2.0/scripts/`:

- todos os arquivos `scripts/smoke-*.js`;
- `smoke-utils.js`.

Ajustado:

- scripts `smoke:*` em `package.json` agora executam via `node dge-2.0/scripts/...`.
- validado com `npm run smoke:command-center`.

Mantido na raiz historica:

- `scripts/check-stability.js`;
- `scripts/check-utf8-text.js`;
- `scripts/keep-dist.js`.

Motivo: esses arquivos ainda sao utilitarios gerais do projeto e nao pertencem exclusivamente ao backbone operacional da DGE 2.0.

### Lote 4 - Server Modules e Contracts DGE 2.0

Status: concluido.

Movido para `dge-2.0/server/`:

- `server/modules`;
- `server/contracts`.

Ajustado:

- `server/index.js` importa routers DGE 2.0 de `../dge-2.0/server/modules/...`;
- `dge-2.0/db/setup-dge-2.js` importa registries de `../server/modules/...`.
- dependencias temporarias do `scenario.service.js` e do antigo `projectionEngine.js` foram resolvidas nos lotes seguintes.

Validado:

- `node --check server/index.js`;
- `node --check dge-2.0/db/setup-dge-2.js`;
- `npm run db:setup:dge2`;
- servidor temporario na porta `8791`;
- `npm run smoke:command-center` com `DGE_API_URL=http://127.0.0.1:8791`.

Observacao: `server/index.js` continua na raiz historica por enquanto porque ainda concentra endpoints legados, documentos, memoria e frontend build. A migracao completa do servidor deve acontecer em lote separado.

## Boundary Doctrine

Status: ativo, sem violacoes atuais.

A partir deste ponto, a DGE 2.0 deve ser reconstruida como sistema proprio. A DGE 1.0 fica preservada como prototipo historico e referencia de produto, mas nao pode ser dependencia tecnica da DGE 2.0.

Check criado:

- `npm run check:dge2-boundary`

Violacoes historicas removidas:

- `dge-2.0/server/modules/finance/projectionEngine.js` importa `src/calculations.js`;
- `dge-2.0/server/modules/scenarios/scenario.service.js` importa `server/memoryRepository.js`.

Essas violacoes foram removidas pelos blocos:

1. `schema-dge-2-core.sql`;
2. repositories proprios DGE 2.0;
3. `scenario.service.js` puro;
4. `projectionCore.js` plugado no endpoint;
5. remocao do `projectionEngine.js` antigo.

Documento de referencia criado:

- `dge-2.0/docs/architecture/dge-2.0-core-schema-blueprint.md`

Decisao adicionada:

- o primeiro cenario oficial da DGE 2.0 nasce de `baseline_collection_runs/items/reviews`;
- a DGE 2.0 nao importa cenario da DGE 1.0;
- a DGE 1.0 e apenas prototipo historico preservado.

### Lote 5 - Core Schema DGE 2.0

Status: concluido.

Criado:

- `dge-2.0/db/schema-dge-2-core.sql`.

O core inclui:

- identidade operacional;
- tenant users, roles, responsabilidades e escopo;
- audit log;
- governanca e aprovacoes;
- data sources, ingestion batches e qualidade;
- baseline collection inicial;
- scenario foundation;
- projection versions;
- reforecast proposals/decisions;
- support requests, eventos e explicacoes tecnicas.

O setup `db:setup:dge2` agora aplica:

1. `schema-dge-2-core.sql`;
2. `schema-dge-2.sql`.

Tambem foram removidas referencias obrigatorias do schema DGE 2.0 para tabelas legadas `users` e `contract_activations`.

Validado:

- `node --check dge-2.0/db/setup-dge-2.js`;
- `npm run db:setup:dge2`;
- verificacao das novas tabelas core no Postgres.

### Lote 6 - Scenario Service Repositories DGE 2.0

Status: concluido.

Criado:

- `dge-2.0/server/repositories/scenarioSnapshot.repository.js`;
- `dge-2.0/server/repositories/calculationRun.repository.js`;
- `dge-2.0/server/repositories/formulaTrace.repository.js`;
- `dge-2.0/server/repositories/projectionState.repository.js`;
- `dge-2.0/server/repositories/timeline.repository.js`.

Ajustado:

- `dge-2.0/server/modules/scenarios/scenario.service.js` nao importa mais `server/memoryRepository.js`;
- o calculo de cenario agora persiste em transacao propria da DGE 2.0:
  - scenario snapshot;
  - premises;
  - scenario KPIs;
  - calculation run;
  - formula traces;
  - projection states;
  - projection state trace packs;
  - timeline event.

Validado:

- `node --check` nos repositories e no scenario service;
- `npm run db:setup:dge2`;
- POST real em `/api/scenarios/calculate` contra servidor temporario;
- persistencia confirmada no Postgres:
  - 15 premises;
  - 5 scenario KPIs;
  - 89 formula traces;
  - 12 projection states;
  - 60 trace packs;
  - 1 timeline event.

Boundary check:

- violacao removida: `scenario.service.js -> server/memoryRepository.js`;
- violacao restante naquele momento: `projectionEngine.js -> src/calculations.js`.

### Projection Engine Platform Blueprint

Status: concluido.

Criado:

- `dge-2.0/docs/architecture/dge-2.0-projection-engine-platform-blueprint.md`.

Decisao:

- nao copiar o motor da DGE 1.0 para dentro da DGE 2.0;
- criar uma Projection Engine Platform expansivel;
- calculo deve nascer trace-first;
- engine deve suportar assumption graph, formula execution graph, temporal model, constraints, variancias, reforecast, suporte/SLA e RAI;
- primeiro corte tecnico deve remover `src/calculations.js` preservando contrato atual de `/api/scenarios/calculate`.

### Development Doctrine

Status: ativo.

Criado:

- `dge-2.0/docs/architecture/dge-2.0-development-doctrine.md`.

Diretriz:

- favorecer arquitetura limpa e expansivel mesmo quando o caminho correto for mais complexo;
- evitar adaptadores ambiguos, pontes permanentes e compatibilidade silenciosa;
- reformular contratos quando eles virarem gargalo real;
- manter compatibilidade temporaria apenas quando declarada explicitamente;
- registrar decisoes estruturais antes da execucao.

Complemento registrado:

- antes de conectar uma engine central em contrato existente, revisar se o contrato ainda serve ao futuro da DGE 2.0;
- se o contrato for o gargalo, redesenhar o contrato como envelope versionado, rastreavel e governado;
- nao usar adaptador para esconder mudanca estrutural;
- preferir o caminho mais complexo quando ele evita divida tecnica, reescrita futura e acoplamento com legado.

### Lote 7 - Projection Engine Platform Skeleton

Status: concluido.

Criado:

- `dge-2.0/server/contracts/projection.contract.js`;
- `dge-2.0/server/modules/finance/assumptionGraph.js`;
- `dge-2.0/server/modules/finance/formulaExecutor.js`;
- `dge-2.0/server/modules/finance/temporalModel.js`;
- `dge-2.0/server/modules/finance/constraintEngine.js`;
- `dge-2.0/server/modules/finance/varianceEngine.js`.

Decisao:

- o esqueleto ainda nao substituia `projectionEngine.js` naquele lote;
- nenhum novo arquivo pode importar DGE 1.0;
- proximos passos podem portar formulas ativas para executor puro sem alterar o contrato externo da API.

Validado:

- `node --check` nos novos arquivos;
- naquele momento, `npm run check:dge2-boundary` ainda acusava apenas a violacao antiga `projectionEngine.js -> src/calculations.js`.

### Lote 8 - Projection Formula Catalog E Projection Core

Status: concluido.

Criado:

- `dge-2.0/server/modules/finance/projectionFormulaCatalog.js`;
- `dge-2.0/server/modules/finance/projectionCore.js`;
- `dge-2.0/server/modules/finance/projectionOutputBuilder.js`;
- `dge-2.0/server/modules/finance/projectionExplainability.js`;
- `dge-2.0/scripts/smoke-projection-core.js`.

Ajustado:

- `formulaExecutor.js` preserva metadados de dominio, familias, variance policy e calibration policy nos traces;
- `package.json` inclui `npm run smoke:projection-core`.

Capacidade entregue:

- catalogo executavel com formulas ativas de marketplace, canal proprio, margem, logistica, CRM/app e investimento;
- blueprints de formulas futuras para estoque, fulfillment, frete, marketing e restricoes operacionais;
- core puro que roda sem persistencia e sem API;
- outputs de calculo, KPIs, premissas, estados temporais e explicacao da engine.

Validado:

- `node --check` nos novos arquivos;
- `npm run smoke:projection-core`.

Resultado do smoke:

- 28 formula traces;
- 12 projection states;
- 5 KPIs principais;
- lucro incremental estimado calculado.

Observacao:

- naquele momento, `projectionCore.js` ainda nao substituia `projectionEngine.js`;
- a violacao restante no boundary foi resolvida no Lote 10.

### Lote 9 - Scenario Calculate Contract v2

Status: concluido.

Criado:

- `dge-2.0/server/contracts/scenarioCalculation.contract.js`;
- `dge-2.0/scripts/smoke-scenario-calculate-contract.js`.

Ajustado:

- `scenario.service.js` agora retorna envelope `scenario.calculate.v2`;
- resposta separa `result`, `traceability`, `persistence`, `governance`, `quality` e `compatibility`;
- campos top-level antigos continuam apenas como compatibilidade declarada;
- `package.json` inclui `npm run smoke:scenario-calculate-contract`.

Decisao:

- nao criar adaptador para esconder mudanca;
- formalizar contrato expansivel antes de plugar `projectionCore`;
- preparar o endpoint para projection version, reforecast, suporte/SLA e RAI.

Validado:

- `node --check` no contrato, service e smoke;
- `npm run db:setup:dge2`;
- servidor temporario na porta `8791`;
- `npm run smoke:scenario-calculate-contract`.

Resultado do smoke:

- `contractVersion = scenario.calculate.v2`;
- scenario snapshot persistido;
- calculation run persistido;
- formula traces retornados em `traceability`;
- projection states retornados em `result`.

### Lote 10 - Scenario Calculate Plugado No Projection Core

Status: concluido.

Ajustado:

- `scenario.service.js` deixou de importar `projectionEngine.js`;
- `/api/scenarios/calculate` passou a executar `runProjectionCore`;
- `projectionCore.js` passou a gerar trace packs mensais nativos;
- `smoke-scenario-calculate-contract.js` passou a validar trace packs persistidos;
- `projectionEngine.js` antigo foi removido do runtime da DGE 2.0.

Decisao:

- nao manter arquivo antigo dentro da DGE 2.0 se ele depende de `src/calculations.js`;
- nao criar adaptador para simular compatibilidade com a engine antiga;
- preservar o contrato `scenario.calculate.v2` e mover a execucao para a engine limpa;
- manter compatibilidade top-level apenas declarada pelo envelope, nao como base arquitetural.

Validado:

- `node --check` no service, core e smoke;
- `npm run db:setup:dge2`;
- servidor temporario na porta `8791`;
- `npm run smoke:scenario-calculate-contract`;
- `npm run smoke:projection-core`;
- `npm run check:dge2-boundary`.

Resultado:

- `formulaTraceCount = 28`;
- `tracePackCount = 60`;
- `projectionStateCount = 12`;
- boundary DGE 2.0 verde, sem imports para DGE 1.0.

### Lote 11 - Projection Version Lifecycle v1

Status: concluido.

Criado:

- `dge-2.0/server/repositories/projectionVersion.repository.js`;
- `dge-2.0/server/modules/projections/projectionLifecycle.service.js`;
- `dge-2.0/scripts/smoke-projection-version-lifecycle.js`.

Ajustado:

- `/api/scenarios/calculate` cria `projection_versions` oficiais;
- resposta `scenario.calculate.v2` passa a retornar `projectionVersion` e `persistence.projectionVersionId`;
- projection version congela assumptions em `projection_assumption_values`;
- projection version congela KPIs e outputs mensais em `projection_kpi_outputs`;
- `GET /api/projections/versions`;
- `GET /api/projections/versions/:id`;
- `GET /api/projections/timeline`;
- smoke do contrato principal exige `projectionVersionId`;
- `package.json` inclui `npm run smoke:projection-version-lifecycle`.

Decisao:

- projection version e a fonte oficial da cronologia de forecasts/reforecasts;
- calculate oficial nao deve apenas devolver numeros, deve criar uma versao governavel da projecao;
- labels de versao usam sequencia + sufixo temporal para evitar colisao em calculos concorrentes;
- reforecast, revogacao e suporte/SLA devem operar sobre `projectionVersionId`.

Validado:

- `node --check` no repository, service, routes, scenario service e smoke;
- `npm run db:setup:dge2`;
- `npm run check:dge2-boundary`;
- servidor temporario na porta `8791`;
- `npm run smoke:scenario-calculate-contract`;
- `npm run smoke:projection-version-lifecycle`.

Resultado do smoke lifecycle:

- projection version oficial criada;
- `projectionType = forecast`;
- assumptions congeladas: 42;
- KPI outputs congelados: 173;
- timeline retorna a versao criada.

### Lote 12 - Forecast Reconciliation And Reforecast Readiness Blueprint

Status: concluido.

Criado:

- `dge-2.0/docs/architecture/dge-2.0-forecast-reconciliation-and-reforecast-readiness-blueprint.md`.

Ajustado:

- `dge-2.0/docs/architecture/dge-2.0-dge-vs-ecommerce-responsibility-contract.md`;
- `dge-2.0/docs/architecture/dge-2.0-development-doctrine.md`.

Decisao:

- reforecast nao nasce de recalculo solto;
- reforecast nasce de reconciliacao entre projetado e realizado auditado;
- antes de proposta de reforecast deve existir um case com variancia, causa provavel, materialidade, evidencia e decisao governada;
- mitigacao operacional profunda com IA, preco, produto, categoria, estoque, cupom, margem e comportamento nao deve nascer isolada dentro da DGE agora;
- reforecast atual deve guardar readiness e contexto futuro necessario;
- `social_action` e escopo futuro restrito a alta camada de tenant, como executive, owner ou admin.

Primeiro corte tecnico recomendado:

- `Forecast Reconciliation v1`;
- comparar `projection_kpi_outputs` oficiais contra snapshots/KPIs auditados;
- classificar variancia;
- atribuir causa provavel;
- abrir skeleton de reforecast case;
- registrar readiness de mitigacao futura;
- garantir que projection version oficial nao muda.

### Lote 13 - Reforecast Intelligence, Variance E Bottleneck Boundary

Status: concluido.

Ajustado:

- `dge-2.0/docs/architecture/dge-2.0-forecast-reconciliation-and-reforecast-readiness-blueprint.md`;
- `dge-2.0/docs/architecture/dge-2.0-adaptive-projection-engine.md`;
- `dge-2.0/docs/architecture/dge-2.0-projection-impact-analyzer.md`.

Decisao:

- Forecast Reconciliation nao deve criar outra logica paralela de variancia;
- `monthly_kpi_traces`, `observed_projection_variances` e `projection_kpi_outputs` sao a base atual do projected vs actual;
- evolucao correta e conectar variancias a `projection_version_id` e `projection_kpi_output_id`;
- bottlenecks nao sao redundantes com variancia;
- variancia responde o que desviou;
- bottleneck responde por que provavelmente desviou;
- Projection Impact Analyzer traduz pressao operacional em familias/formulas afetadas;
- Forecast Reconciliation interpreta tudo em nivel de case;
- Adaptive Projection v1 passa a ser modulo em transicao;
- alvo conceitual: `Adaptive Projection Engine -> Reforecast Intelligence Layer`;
- Reforecast Intelligence deve operar dentro de reforecast case, nao decidir reforecast sozinho.

Primeiro corte tecnico recomendado atualizado:

- nao criar novo ledger redundante;
- estender ou envolver `observed_projection_variances`;
- criar reconciliation case consumindo:
  - `projection_versions`;
  - `projection_kpi_outputs`;
  - `monthly_kpi_traces`;
  - `observed_projection_variances`;
  - `bottleneck_detection_runs`;
  - `projection_impact_traces`;
- anexar bottleneck signals como evidencia causal;
- manter simulation/adjustment logic do Adaptive como policy/preview dentro do case.

### Lote 14 - Forecast Reconciliation Foundation v1

Status: concluido.

Criado:

- `dge-2.0/server/modules/projections/reconciliationPolicyRegistry.js`;
- `dge-2.0/server/modules/projections/forecastReconciliation.service.js`;
- `dge-2.0/server/repositories/forecastReconciliation.repository.js`;
- `dge-2.0/scripts/smoke-forecast-reconciliation.js`.

Ajustado:

- `schema-dge-2-core.sql` inclui `reforecast_cases` e `reforecast_case_events`;
- `schema-dge-2.sql` estende `observed_projection_variances` com:
  - `projection_version_id`;
  - `projection_kpi_output_id`;
  - `reconciliation_status`;
  - `materiality_classification`;
  - `probable_causes_json`;
  - `linked_bottleneck_run_ids`;
  - `linked_projection_impact_trace_ids`;
- `projection.routes.js` expõe:
  - `POST /api/projections/versions/:id/reconcile`;
  - `GET /api/projections/versions/:id/reconciliation`;
  - `GET /api/projections/reforecast-cases`;
- `package.json` inclui `npm run smoke:forecast-reconciliation`.

Decisao:

- reconciliation consome variancias existentes, bottleneck runs e projection impact traces;
- nao cria novo ledger paralelo de variancia;
- bottleneck signals entram como evidencia causal oficial do case;
- reconciliation pode criar case, mas nao cria reforecast proposal;
- reconciliation nao altera projection version oficial;
- readiness de mitigacao futura fica registrado no case, com `social_action` restrito a executive/owner/admin.

Validado:

- `node --check` nos novos arquivos;
- `npm run db:setup:dge2`;
- servidor temporario na porta `8791`;
- `npm run smoke:forecast-reconciliation`;
- `npm run smoke:scenario-calculate-contract`;
- `npm run smoke:projection-version-lifecycle`;
- `npm run check:dge2-boundary`.

Resultado do smoke:

- projection version oficial criada;
- variancia de frete real vs projetado vinculada a projection version;
- bottleneck de frete anexado como evidencia causal;
- reforecast case criado;
- classificacao: `critical_break`;
- recomendacao: `mandatory_reforecast_review`;
- causa provavel: `freight_cost_gap`;
- `officialProjectionMutation = false`.

### Lote 15 - Reforecast Case Detail v1

Status: concluido.

Ajustado:

- `forecastReconciliation.repository.js` adiciona:
  - detalhe de case;
  - eventos do case;
  - transicao de status;
  - criacao de `projection_support_requests` para explicacao tecnica;
- `forecastReconciliation.service.js` adiciona:
  - `GET` detalhado do case;
  - diff observado vs projetado;
  - separacao de evidencias por variancia, bottleneck e projection impact;
  - decision trail;
  - transicao governada;
  - request de explicacao tecnica;
- `projection.routes.js` expoe:
  - `GET /api/projections/reforecast-cases/:id`;
  - `POST /api/projections/reforecast-cases/:id/transition`;
  - `POST /api/projections/reforecast-cases/:id/request-technical-explanation`;
- `smoke-forecast-reconciliation.js` valida detalhe, transicao e request tecnico.

Decisao:

- case deve ser legivel antes de preview de reforecast;
- transicoes nao criam reforecast proposal;
- solicitacao tecnica usa suporte/SLA existente;
- nenhum fluxo altera projection version oficial.

Validado:

- `node --check` nos arquivos alterados;
- `npm run db:setup:dge2`;
- servidor temporario na porta `8791`;
- `npm run smoke:forecast-reconciliation`;
- `npm run smoke:scenario-calculate-contract`;
- `npm run check:dge2-boundary`.

Resultado do smoke:

- detalhe do case retorna diff observado vs projetado;
- evidencia de bottleneck aparece no detalhe;
- decision trail aparece no detalhe;
- status transita para `ready_for_reforecast_preview`;
- request tecnico cria `projection_support_request`;
- case passa para `technical_explanation_requested`;
- `officialProjectionMutation = false`.

### Lote 16 - Progressive Projection Transparency Blueprint

Status: concluido.

Criado:

- `dge-2.0/docs/architecture/dge-2.0-progressive-projection-transparency-blueprint.md`.

Ajustado:

- `dge-2.0/docs/architecture/dge-2.0-projection-engine-platform-blueprint.md`;
- `dge-2.0/docs/architecture/dge-2.0-forecast-reconciliation-and-reforecast-readiness-blueprint.md`.

Decisao:

- reforecast preview nao deve ser implementado antes de explicitar formulas progressivas;
- comparar observado apenas com premissa final e insuficiente;
- reconciliacao deve diferenciar:
  - variancia vs valor efetivo do periodo;
  - variancia vs alvo final;
  - posicao observada vs posicao esperada na curva;
- curvas podem exigir:
  - `accelerate_curve`;
  - `decelerate_curve`;
  - `raise_final_target`;
  - `lower_final_target`;
  - `shift_activation_date`;
  - `extend_ramp_duration`;
  - `shorten_ramp_duration`;
  - `mark_outlier`;
  - `wait_more_data`;
- primeiro corte nao cria tabelas novas;
- primeiro corte deve enriquecer `projectionStates.outputs.progressiveFormulas`.

Formulas progressivas identificadas no core atual:

- `projection.ramp`;
- `projection.growth_factor`;
- `own_channel.effective_conversion`;
- `own_channel.effective_gmv`;
- `own_channel.effective_incremental_gmv`;
- `own_channel.effective_cart_recovery_gmv`;
- `logistics.effective_delivery_days`;
- `logistics.effective_freight_cost`;
- `financial.effective_monthly_profit`;
- `financial.accumulated_cash`;
- `financial.payback_progress`;
- `participation.post_payback_rate`;
- `crm.effective_retention_upside`.

Primeiro corte tecnico recomendado:

- `Progressive Projection Transparency v1`;
- criar registry de formulas progressivas;
- fazer `projectionCore` emitir `progressiveFormulas` por periodo;
- persistir dentro de `projection_states.outputs_json`;
- validar em smoke ramp/conversao/GMV/prazo/lucro/acumulado/payback;
- manter fora do escopo reforecast preview, IA, mitigacao e recalibracao automatica.

### Lote 17 - Progressive Projection Transparency v1

Status: concluido.

Criado:

- `dge-2.0/server/modules/finance/progressiveFormulaRegistry.js`;
- `dge-2.0/scripts/smoke-progressive-projection-transparency.js`.

Ajustado:

- `projectionCore.js` agora emite `outputs.progressiveFormulas` em cada `projectionState`;
- `projectionCore.js` agora expõe `drivers.curveDrivers` com versao do registry, curva de rampa, modo de crescimento, periodo de ativacao e crescimento mensal;
- `stateOutputs` agora expõe `projectedFreightCost`, alem de conversao efetiva, prazo efetivo e caixa acumulado;
- `package.json` inclui `npm run smoke:progressive-projection`.

Capacidade entregue:

- formulas progressivas ficaram explicitas no payload mensal;
- cada formula declara valor base, fator de curva, valor efetivo do periodo, alvo final, KPI observado esperado, modos futuros de recalibragem, owner boundary e explicacao;
- a comparacao futura de observado vs projetado podera diferenciar:
  - variancia contra valor efetivo do periodo;
  - variancia contra meta final;
  - posicao na curva;
  - necessidade de acelerar/desacelerar curva versus alterar premissa final.

Formulas progressivas ativas:

- `projection.ramp`;
- `projection.growth_factor`;
- `own_channel.effective_conversion`;
- `own_channel.effective_gmv`;
- `own_channel.effective_incremental_gmv`;
- `own_channel.effective_cart_recovery_gmv`;
- `logistics.effective_delivery_days`;
- `logistics.effective_freight_cost`;
- `financial.effective_monthly_profit`;
- `financial.accumulated_cash`;
- `financial.payback_progress`;
- `participation.post_payback_rate`;
- `crm.effective_retention_upside`.

Decisao:

- nao criar tabela dedicada agora;
- persistir as formulas progressivas dentro de `projection_states.outputs_json`;
- preservar a projection version oficial sem mutacao;
- usar esta camada como prerequisito para Reforecast Preview v1.

Validado:

- `node --check` nos arquivos novos e alterados;
- `npm run smoke:projection-core`;
- `npm run smoke:progressive-projection`;
- `npm run check:dge2-boundary`.

Resultado do smoke:

- 13 formulas progressivas por projection state;
- mes 4 com conversao efetiva `0.706666%` contra meta final `2%`;
- prazo efetivo `4.333334` dias;
- payback ainda abaixo do threshold;
- `officialProjectionMutation = false`;
- boundary DGE 2.0 verde, sem imports para DGE 1.0.

### Lote 18 - Curve-Aware Forecast Reconciliation v1

Status: concluido.

Criado/ajustado:

- `forecastReconciliation.repository.js` agora lista `projection_states` da projection version;
- `forecastReconciliation.service.js` agora enriquece variancias com `curveVariance`;
- `smoke-forecast-reconciliation.js` agora exige leitura de curva progressiva no detalhe do case.

Capacidade entregue:

- Forecast Reconciliation deixa de depender apenas da variancia plana registrada;
- cada variancia pode ser comparada contra a formula progressiva efetiva do periodo;
- o case passa a carregar:
  - `effectiveProjectedValue`;
  - `finalTargetValue`;
  - `varianceVsEffective`;
  - `varianceVsEffectivePercent`;
  - `varianceVsFinalTarget`;
  - `varianceVsFinalTargetPercent`;
  - `curvePosition`;
  - `curveInterpretation`;
  - modos futuros de recalibragem;
  - regra `curve_variance_precedes_final_target_reforecast`.

Decisao:

- nao criar novo ledger;
- usar `projection_states.outputs_json.progressiveFormulas` como fonte da curva;
- manter `observed_projection_variances` como base factual de variancia;
- anexar contexto de curva ao evidence do reforecast case;
- classificar materialidade usando variancia vs valor efetivo do periodo quando a curva estiver disponivel.

Validado:

- `node --check` no service, repository e smoke;
- `npm run smoke:forecast-reconciliation`;
- `npm run check:dge2-boundary`.

Resultado do smoke:

- formula de curva usada: `logistics.effective_freight_cost`;
- posicao na curva: `behind_curve`;
- valor efetivo projetado do periodo: `14.474674`;
- variancia vs efetivo: `190.161975%`;
- projection version oficial nao sofreu mutacao.

### Lote 19 - Reforecast Intelligence Preflight

Status: concluido.

Criado:

- `dge-2.0/server/modules/projections/curveVarianceRegistry.js`;
- `dge-2.0/server/modules/projections/reforecastIntelligenceRegistry.js`;
- `dge-2.0/server/contracts/reforecastPreview.contract.js`;
- `dge-2.0/scripts/smoke-reforecast-intelligence.js`.

Ajustado:

- `forecastReconciliation.service.js` deixou de manter hardcode interno de KPI -> formula progressiva;
- `forecastReconciliation.service.js` agora retorna `reforecastIntelligence`;
- reforecast cases passam a registrar `reforecastIntelligence` em metadata;
- `moduleRegistry.js` reclassifica Adaptive Projection como transitional suggestion layer;
- `package.json` inclui `npm run smoke:reforecast-intelligence`;
- docs de Adaptive e Forecast Reconciliation foram atualizadas.

Capacidade entregue:

- mapeamento de KPI observado para formula progressiva virou registry reutilizavel;
- classificacao ahead/on/behind curve virou policy reutilizavel;
- Reforecast Intelligence agora decide readiness e tipo de preview:
  - `curve_reforecast`;
  - `assumption_reforecast`;
  - `activation_reforecast`;
  - `mixed_reforecast`;
  - `data_audit_required`;
  - `monitoring`;
- Reforecast Preview ganhou contrato v1 antes de existir runtime pesado;
- Adaptive Projection ficou formalmente impedido de competir com Forecast Reconciliation.

Decisao:

- Reforecast Preview v1 deve nascer a partir de reforecast case;
- preview nao cria projection version oficial;
- preview nao executa mitigacao;
- preview deve consumir:
  - `curveVariance`;
  - `probableCauses`;
  - `bottleneckEvidence`;
  - `projectionImpactEvidence`;
  - `reforecastIntelligence`;
  - `futureMitigationReadiness`.

Validado:

- `node --check` nos novos registries, contrato e services;
- `npm run smoke:reforecast-intelligence`;
- `npm run smoke:forecast-reconciliation`;
- `npm run smoke:scenario-calculate-contract`;
- `npm run check:dge2-boundary`.

Resultado do smoke:

- 14 mapeamentos KPI -> formula progressiva;
- frete atras da curva com causa operacional gera `mixed_reforecast`;
- acao primaria: `generate_operationally_constrained_preview`;
- contrato preparado: `reforecast.preview.v1`;
- `officialProjectionMutation = false`.

### Lote 20 - Reforecast Preview Runtime v1

Status: concluido.

Criado:

- `dge-2.0/server/repositories/reforecastPreview.repository.js`;
- `dge-2.0/server/modules/projections/reforecastPreview.service.js`;
- `dge-2.0/scripts/smoke-reforecast-preview.js`.

Ajustado:

- `projection.routes.js` expoe `POST /api/projections/reforecast-cases/:id/preview`;
- `package.json` inclui `npm run smoke:reforecast-preview`.

Capacidade entregue:

- preview nasce a partir de `reforecastCaseId`;
- carrega projection version baseline;
- reconstroi scenario a partir de `projection_assumption_values`;
- consome `reforecastIntelligence`;
- monta `adjustmentSet` rastreavel;
- roda `projectionCore` em modo `preview`;
- calcula `diffVsBaseline`;
- persiste `projection_reforecast_proposals` com:
  - `source = reforecast_preview_v1`;
  - `status = preview_generated`;
  - `proposed_projection_version_id = null`;
  - evidencias do case;
  - intelligence;
  - adjustmentSet;
  - diff;
  - garantias de nao mutacao oficial;
- registra evento `reforecast_preview_generated` no case.

Decisao:

- preview nao cria projection version oficial;
- preview nao aprova reforecast;
- preview nao executa mitigacao;
- preview e proposta tecnica preliminar governavel;
- approval/proposal formal e official reforecast version ficam para lote posterior.

Primeiro tipo suportado:

- `mixed_reforecast` para frete atras da curva com causa operacional;
- overrides iniciais:
  - `carrierCost`;
  - `averageFreightCost`.

Validado:

- `node --check` no repository, service, routes e smoke;
- `npm run smoke:reforecast-preview`;
- `npm run smoke:reforecast-intelligence`;
- `npm run smoke:forecast-reconciliation`;
- `npm run smoke:scenario-calculate-contract`;
- `npm run check:dge2-boundary`.

Resultado do smoke:

- proposal criada em `preview_generated`;
- tipo de preview: `mixed_reforecast`;
- overrides aplicados: `carrierCost`, `averageFreightCost`;
- diff de `projectedFreightCost`:
  - baseline `21.712`;
  - preview `25.392`;
  - delta `3.68`;
  - delta percentual `16.9491%`;
- `officialProjectionMutation = false`;
- `createsOfficialProjectionVersion = false`.

### Lote 21 - Reforecast Temporal Cutoff Policy v1

Status: concluido.

Ajustado:

- `reforecastPreview.contract.js` adiciona `buildTemporalCutoffPolicy`;
- `reforecastPreview.service.js` declara `temporalCutoff` em todo preview;
- `smoke-reforecast-preview.js` valida cutoff, effectiveFrom e guardrails;
- Forecast Reconciliation blueprint documenta a politica temporal.

Capacidade entregue:

- preview deixa explicito que nao sobrescreve passado auditado;
- `cutoffDate` define ate onde os dados reais ficam travados;
- `effectiveFrom` define quando o preview passa a valer;
- periodo corrente usa politica `prorated_reforecast`;
- periodos fechados usam `preserve_audited_actuals`;
- periodos futuros usam `full_reforecast`;
- contrato declara que a engine diaria ainda nao esta ativa:
  - `dailyReforecastRuntime = false`;
  - `monthlyPreviewRuntime = true`;
  - `intraPeriodBlendDeclared = true`.

Decisao:

- nao implementar engine diaria agora;
- nao fingir que o preview mensal resolve dias ja observados;
- registrar a regra temporal desde ja para evitar reforecast que reescreve o passado.

Validacao esperada:

- `cutoffDate = 2026-05-10`;
- `effectiveFrom = 2026-05-11`;
- `doesNotOverwriteClosedActuals = true`;
- `currentPeriodPolicy = prorated_reforecast`.

### Lote 22 - Reforecast Adjustment Model & Formula Readiness v1

Status: concluido.

Criado:

- `dge-2.0/server/contracts/reforecastAdjustment.contract.js`;
- `dge-2.0/server/modules/projections/reforecastAdjustmentRegistry.js`.

Ajustado:

- `reforecastPreview.service.js` passa a gerar `adjustmentSet.items` normalizados;
- `smoke-reforecast-preview.js` valida tipos ativos e declarados;
- Forecast Reconciliation blueprint documenta adjustment model e formula reforecast.

Capacidade entregue:

- reforecast deixa de ser apenas troca de premissa;
- tipos declarados:
  - `assumption_reforecast`;
  - `curve_reforecast`;
  - `formula_reforecast`;
  - `activation_reforecast`;
  - `mixed_reforecast`;
  - `data_audit_required`;
  - `monitoring`;
- suporte runtime separado:
  - `assumption_reforecast = active`;
  - `mixed_reforecast = active_partial`;
  - `curve_reforecast = declared`;
  - `formula_reforecast = declared`;
  - `activation_reforecast = declared`;
- formula reforecast passa a carregar:
  - `formulaVersionFrom`;
  - `formulaVersionTo`;
  - `formulaPolicyFrom`;
  - `formulaPolicyTo`;
  - `requiredContexts`;
  - `runtimeSupport`;
  - `previewRuntimeEffect`.

Primeiras formulas com readiness:

- `logistics.effective_freight_cost`;
- `own_channel.effective_conversion`.

Decisao:

- preview v1 executa apenas assumption overrides;
- formula/curve/activation reforecast ficam declarados e auditaveis;
- trocar versao de formula em runtime fica para lote futuro, depois de governance/review do preview.

### Lote 23 - Reforecast Preview Decision Form v1

Status: concluido.

Criado:

- `dge-2.0/server/contracts/reforecastPreviewDecision.contract.js`;
- `dge-2.0/server/modules/projections/reforecastPreviewDecision.service.js`.

Ajustado:

- `reforecastPreview.repository.js` agora lista/detalha previews, atualiza status e insere decisions;
- `projection.routes.js` expoe:
  - `GET /api/projections/reforecast-cases/:id/previews`;
  - `GET /api/projections/reforecast-previews/:id`;
  - `POST /api/projections/reforecast-previews/:id/review`;
  - `POST /api/projections/reforecast-previews/:id/approve-for-proposal`;
  - `POST /api/projections/reforecast-previews/:id/reject`;
  - `POST /api/projections/reforecast-previews/:id/expire`;
- `smoke-reforecast-preview.js` valida review e approval form completos.

Capacidade entregue:

- preview deixa de ser apenas status e passa a ter formulario decisorio;
- cada decisao salva `decision_payload` em `projection_reforecast_decisions`;
- formulario ancora snapshots:
  - `adjustmentSetSnapshot`;
  - `temporalCutoffSnapshot`;
  - `diffVsBaselineSnapshot`;
  - `reforecastIntelligenceSnapshot`;
  - `guaranteesSnapshot`;
- proposal registra `lastDecision` em metadata;
- case recebe eventos:
  - `reforecast_preview_reviewed`;
  - `reforecast_preview_approved_for_proposal`;
  - `reforecast_preview_rejected`;
  - `reforecast_preview_expired`.

Regras de validacao:

- `reviewed` exige ator, role, notes, cutoff acknowledgement, diff acknowledgement e active adjustments acknowledgement;
- `approved_for_proposal` exige role `executive`, `owner` ou `admin`;
- approval exige `approvalReadiness = ready_for_proposal`;
- approval exige acknowledgement de mutacao oficial, cutoff, diff, ajustes ativos;
- se houver declared adjustments, exige declared adjustments acknowledgement;
- se houver `formula_reforecast`, exige formula change acknowledgement;
- `rejected` exige reason code e notes.

Decisao:

- approve-for-proposal ainda nao cria proposta formal nova nem projection version oficial;
- decisions ficam ancoradas no preview e preparadas para viajar ate o reforecast oficial futuro;
- formulario e fonte de auditoria, suporte, RAI trace e revogacao futura.

Validado:

- `node --check` nos novos contratos/services/routes/smoke;
- `npm run smoke:reforecast-preview`;
- `npm run smoke:forecast-reconciliation`;
- `npm run smoke:scenario-calculate-contract`;
- `npm run check:dge2-boundary`.

Resultado do smoke:

- preview gerado;
- detail/list funcionando;
- review form salvo;
- approval form executivo salvo;
- status final `approved_for_proposal`;
- case event `reforecast_preview_approved_for_proposal`;
- `officialProjectionMutation = false`;
- `createsOfficialProjectionVersion = false`.

### Lote 24 - Formal Reforecast Proposal v1

Status: concluido.

Criado:

- `dge-2.0/server/contracts/reforecastProposal.contract.js`;
- `dge-2.0/server/modules/projections/reforecastProposal.service.js`.

Ajustado:

- `projection.routes.js` expoe `POST /api/projections/reforecast-previews/:id/create-formal-proposal`;
- `smoke-reforecast-preview.js` valida criacao de proposta formal depois do approval do preview.

Capacidade entregue:

- preview aprovado pode virar proposta formal governavel;
- proposal muda de `approved_for_proposal` para `formal_proposal_pending_approval`;
- pacote formal fica salvo em `metadata.formalProposal`;
- pacote formal ancora:
  - source preview proposal;
  - reforecast case;
  - baseline projection version;
  - executive summary;
  - business justification;
  - technical justification;
  - accepted adjustments;
  - required approvals;
  - preview snapshot;
  - formula reforecast readiness;
  - guarantees;
- decisao `formal_proposal_created` fica registrada em `projection_reforecast_decisions`;
- case recebe evento `formal_reforecast_proposal_created`.

Decisao:

- proposta formal ainda nao cria projection version oficial;
- `proposed_projection_version_id` permanece vazio;
- formula runtime swap continua inativo;
- official reforecast version fica para lote posterior, depois de aprovacao formal.

Validado:

- `node --check` no contrato, service, routes e smoke;
- `npm run smoke:reforecast-preview`;
- `npm run smoke:forecast-reconciliation`;
- `npm run smoke:scenario-calculate-contract`;
- `npm run check:dge2-boundary`.

Resultado do smoke:

- status final `formal_proposal_pending_approval`;
- required approvals: `executive`, `owner`;
- `runtimeFormulaSwapActive = false`;
- `proposedProjectionVersionLinked = false`;
- `officialProjectionMutation = false`;
- `createsOfficialProjectionVersion = false`.

### Lote 25 - Formula Reforecast Runtime v1

Status: concluido.

Criado:

- `dge-2.0/server/contracts/formulaReforecast.contract.js`;
- `dge-2.0/server/modules/finance/formulaReforecastRuntime.js`;
- `dge-2.0/scripts/smoke-formula-reforecast-runtime.js`.

Ajustado:

- `package.json` inclui `npm run smoke:formula-reforecast-runtime`.

Capacidade entregue:

- reforecast de formula passa a ter contrato proprio `formula.reforecast.v1`;
- runtime puro recebe serie de formulas progressivas emitida pelo Projection Core;
- compara valor observado contra valor efetivo da curva no periodo;
- classifica direcao da variancia:
  - `above_curve`;
  - `below_curve`;
  - `on_curve`;
- escolhe modo de recalibragem a partir do registry da formula:
  - `accelerate_curve`;
  - `decelerate_curve`;
  - `raise_final_target`;
  - `lower_final_target`;
  - `wait_more_data`;
- gera proposta de formula versionada:
  - `formulaVersionFrom`;
  - `formulaVersionTo`;
  - `formulaPolicyFrom`;
  - `formulaPolicyTo`;
  - parent formula version obrigatoria;
  - reversibilidade declarada;
- preserva periodos ate o cutoff;
- recalcula apenas periodos futuros;
- retorna impacto futuro por periodo e sumario acumulado;
- nao cria projection version oficial;
- nao muta registry oficial de formulas;
- nao sobrescreve passado auditado.

Decisao:

- reforecast oficial nao deve avancar completo enquanto formulas progressivas ainda forem apenas declaradas;
- este runtime e o primeiro corte limpo para substituir `exclude_from_runtime_v1` por formula reforecast executavel;
- formula reforecast nasce como preview governavel, nao como mudanca automatica;
- para `accelerate_curve`, a surpresa observada acima da curva pode carregar impacto para o futuro com decaimento ate o horizonte;
- para `decelerate_curve`, a regra equivalente deve reduzir o futuro sem aumentar baseline;
- approval oficial deve consumir este contrato antes de criar nova projection version.

Validado:

- `node --check` no contrato, runtime e smoke;
- `npm run smoke:formula-reforecast-runtime`;
- `npm run smoke:progressive-projection`;
- `npm run smoke:projection-core`;
- `npm run check:dge2-boundary`.

Resultado do smoke:

- formula testada: `own_channel.effective_conversion`;
- periodo observado: 4;
- variancia vs valor efetivo: `80%`;
- modo sugerido: `accelerate_curve`;
- periodos futuros afetados: 8;
- delta futuro total: `1.978665`;
- `officialProjectionMutation = false`;
- `overwritesAuditedPast = false`.

### Lote 26 - Formula Reforecast Preview Integration v1

Status: concluido.

Ajustado:

- `dge-2.0/server/modules/projections/reforecastPreview.service.js`;
- `dge-2.0/server/contracts/reforecastProposal.contract.js`;
- `dge-2.0/scripts/smoke-reforecast-preview.js`.

Capacidade entregue:

- Reforecast Preview passa a executar `buildFormulaReforecastPreview` para evidencias com `curveVariance` disponivel;
- `adjustmentSet` passa a carregar `formulaReforecastPreviews`;
- `formula_reforecast` deixa de ser apenas `declared` quando ha runtime de preview valido;
- nesses casos, o ajuste passa para:
  - `runtimeSupport = active_partial`;
  - `previewRuntimeEffect = formula_reforecast_preview`;
  - `metadata.formulaReforecastPreviewAvailable = true`;
- proposal formal passa a carregar:
  - `formulaReforecastReadiness.formulaReforecastPreviews`;
  - `runtimeFormulaSwapActive = true` para runtime de preview;
  - `officialFormulaSwapActive = false` para deixar claro que a versao oficial ainda nao troca formula automaticamente;
- gate oficial continua sem criar projection version oficial;
- gate oficial pode aprovar o caminho de versao oficial mantendo formula fora do runtime oficial v1 quando necessario.

Decisao:

- formula reforecast agora e executavel no preview, mas ainda nao altera a projection version oficial;
- `runtimeFormulaSwapActive` no pacote formal significa runtime de preview disponivel, nao swap oficial;
- `officialFormulaSwapActive` separa claramente a capacidade futura de criar versao oficial com troca real de formula;
- o proximo salto estrutural deve ser fazer a Official Reforecast Version consumir `formulaReforecastPreviews` aprovados antes de criar `projection_versions` filhas.

Validado:

- `node --check` nos arquivos alterados;
- servidor temporario na porta `8787`;
- `npm run smoke:reforecast-preview`;
- `npm run smoke:forecast-reconciliation`;
- `npm run smoke:scenario-calculate-contract`;
- `npm run smoke:formula-reforecast-runtime`;
- `npm run check:dge2-boundary`.

Resultado do smoke principal:

- proposal final: `approved_for_official_reforecast`;
- previewTypes: `mixed_reforecast`;
- adjustmentTypes: `assumption_reforecast`, `formula_reforecast`;
- formal proposal:
  - `runtimeFormulaSwapActive = true`;
  - `officialFormulaSwapActive = false`;
- official approval:
  - `formulaRuntimePolicy = exclude_from_runtime_v1`;
  - `readyForOfficialVersion = true`;
  - `createsOfficialProjectionVersion = false`;
- `officialProjectionMutation = false`.

### Lote 27 - Official Reforecast Version v1 E Horizonte De Exibicao BI

Status: concluido.

Criado:

- `dge-2.0/server/contracts/officialReforecastVersion.contract.js`;
- `dge-2.0/server/modules/projections/officialReforecastVersion.service.js`.

Ajustado:

- `dge-2.0/server/contracts/projection.contract.js`;
- `dge-2.0/server/modules/scenarios/scenario.service.js`;
- `dge-2.0/server/repositories/projectionVersion.repository.js`;
- `dge-2.0/server/repositories/reforecastPreview.repository.js`;
- `dge-2.0/server/modules/projections/projection.routes.js`;
- `dge-2.0/scripts/smoke-reforecast-preview.js`.

Capacidade entregue:

- endpoint `POST /api/projections/reforecast-proposals/:id/create-official-version`;
- cria nova `projection_versions` oficial do tipo `reforecast`;
- nova versao aponta para `parent_projection_version_id`;
- cria `projection_version_links` com `link_type = official_reforecast_child`;
- proposal passa para `official_reforecast_version_created`;
- proposal recebe `proposed_projection_version_id`;
- calculation run, formula traces, projection states, assumptions e KPI outputs sao persistidos para a versao filha;
- timeline event registra a criacao da versao oficial;
- case event registra `official_reforecast_version_created`.

Decisao estrutural sobre horizonte:

- reforecast oficial nao deve ser influenciado por filtro temporal do cockpit;
- filtro temporal do cockpit/Superset/BI e apenas camada de exibicao;
- `projectionViewContext` passa a declarar:
  - `displayOnly = true`;
  - `affectsRuntimeCalculation = false`;
- calculo e reforecast usam `modelHorizonMonths`;
- filtros de BI podem exibir 3, 6, 12 ou N meses sem alterar a versao oficial materializada;
- isso prepara a DGE para Superset, datasets controlados, exploracao livre, relatórios e BI com IA sem contaminar o motor de projecao.

Limite consciente do v1:

- se o gate oficial usa `exclude_from_runtime_v1`, a versao oficial executa apenas ajustes de premissa;
- `formulaReforecastPreviews` ficam anexados como evidencia rastreavel;
- `officialFormulaSwapActive = false`;
- formula swap oficial fica para lote futuro com runtime proprio de versao de formula.

Validado:

- `node --check` nos arquivos novos/alterados;
- servidor temporario na porta `8787`;
- `npm run smoke:reforecast-preview`;
- `npm run smoke:scenario-calculate-contract`;
- `npm run smoke:forecast-reconciliation`;
- `npm run smoke:formula-reforecast-runtime`;
- `npm run check:dge2-boundary`.

Resultado do smoke principal:

- proposal final: `official_reforecast_version_created`;
- projection version filha criada;
- parent projection version linkado;
- `modelHorizonMonths = 12`;
- `displayHorizonMonths = 6`;
- `displayAffectsRuntime = false`;
- projection states materializados: 12;
- `officialFormulaSwapActive = false`.

### Norte Pos-Lote 27 - Fechamento Do Ciclo De Reforecast E BI

Status: definido como direcao.

Ordem recomendada:

1. `Lineage + Diff Parent`
2. `Active Reference Policy`
3. `BI Dataset Views`
4. `Revocation Flow`
5. `Official Formula Swap`

Decisao:

- a official reforecast version nao fecha sozinha a tese de acompanhamento operacional;
- a versao filha precisa ser legivel cronologicamente, comparavel contra o parent e selecionavel como referencia ativa;
- o cockpit e o BI nao devem consultar tabelas cruas como fonte primaria;
- Superset deve consumir datasets/views controladas;
- filtros temporais do cockpit, Superset e BI sao apenas camada de exibicao;
- reforecast, projection engine e versao oficial continuam usando horizonte tecnico/modelado;
- revogacao e rollback precisam nascer como fluxo governado, nao como edicao manual de status;
- formula swap oficial so deve entrar depois que lineage, diff, active reference e datasets estiverem claros.

Bloco imediato:

- criar endpoint de linhagem de projection version;
- criar endpoint de diff parent vs child;
- definir policy de versao ativa para cockpit/BI;
- preparar primeiras views/datasets SQL para BI controlado.

Resultado esperado:

- qualquer stakeholder consegue ver qual versao nasceu de qual;
- qualquer reforecast oficial pode ser comparado com seu parent;
- cockpit e BI conseguem identificar a referencia oficial atual;
- Superset pode comecar a operar sobre views governadas;
- ciclo de reforecast fica auditavel antes de avancar para revogacao e formula swap oficial.

### Diretriz Futura - Frontend, Cockpit E Orchestration Layer

Status: definido como direcao futura.

Decisao:

- o roadmap atual e o roadmap macro do backend/backbone da DGE 2.0;
- frontend/cockpit deve ser norteado depois que os contratos centrais do backbone estiverem mais estaveis;
- o frontend nao deve consumir diretamente regras cruas do dominio;
- deve existir uma camada intermediaria de orchestration/BFF entre backend core e cockpit;
- essa camada deve compor dados, aplicar policies de permissao, preparar view models e reduzir acoplamento entre UI e motor;
- Superset/BI pode coexistir com o cockpit, mas ambos devem consumir datasets/views/contratos controlados.

Arquitetura-alvo:

```txt
Postgres / DGE Backend Core
  -> Domain Services / Engines
  -> Operational API
  -> Orchestration Layer / BFF
  -> Cockpit Frontend
  -> Superset / BI / Reports
```

Roadmap futuro de Frontend + Orchestration:

1. Design System Operacional
2. Tenant & Permission UI
3. Command Center
4. Projection Explorer
5. Operational Data Entry
6. BI Bridge
7. Automation Center
8. AI/RAI Workspace

Diretriz:

- nao construir tela definitiva em cima de contrato instavel;
- primeiro estabilizar backbone, contratos, versionamento, governanca e datasets;
- depois desenhar orchestration/BFF e cockpit por fluxos operacionais;
- manter regras de negocio no backend/domain services;
- manter composicao de experiencia, filtros, estados de tela e agregacoes de UI na orchestration layer;
- manter BI em datasets certificados, nao em tabelas cruas.

### Lote 28 - Projection Lineage, Diff Parent, Active Reference E BI Views v1

Status: concluido.

Criado/ajustado:

- `projectionLifecycle.service.js` adiciona:
  - `GET /api/projections/versions/active-reference`;
  - `GET /api/projections/versions/:id/lineage`;
  - `GET /api/projections/versions/:id/diff-parent`;
- `projectionVersion.repository.js` adiciona leitura de links, ancestors, children, assumptions, KPI outputs e active reference;
- `schema-dge-2.sql` adiciona views controladas para BI/Superset:
  - `bi_projection_versions_dataset`;
  - `bi_projection_monthly_outputs_dataset`;
  - `bi_reforecast_cases_dataset`;
  - `bi_official_reforecast_lineage_dataset`;
  - `bi_active_projection_reference_dataset`;
- `smoke-reforecast-preview.js` valida active reference, lineage e diff parent apos criar official reforecast version.

Capacidade entregue:

- versao oficial filha deixa de ser apenas persistencia e passa a ser navegavel;
- lineage mostra ancestors, children, links e active reference;
- diff parent compara child oficial contra parent baseline;
- diff separa outputs/KPIs alterados e premissas alteradas;
- active reference v1 define default para cockpit, BI e reports;
- Superset pode iniciar em views certificadas sem consultar tabelas cruas.

Active Reference Policy v1:

- policy: `latest_official_not_revoked_by_activated_at`;
- status obrigatorio: `official`;
- `revoked_at` deve ser null;
- ordenacao: `activated_at desc nulls last, created_at desc`;
- consumidores default:
  - cockpit;
  - BI;
  - reports.

Decisao:

- active reference v1 e derivada por policy, sem tabela nova;
- revogacao/rollback futuro podera alterar essa policy ou adicionar estado governado;
- diff detalhado fica completo em `kpiOutputDiff`;
- summary do diff fica executivo, por KPI importante no ultimo periodo materializado;
- BI deve usar views controladas como contrato inicial com Superset.

Validado:

- `node --check` nos arquivos alterados;
- `npm run db:setup:dge2`;
- servidor temporario na porta `8787`;
- `npm run smoke:reforecast-preview`;
- `npm run smoke:scenario-calculate-contract`;
- `npm run smoke:forecast-reconciliation`;
- `npm run smoke:formula-reforecast-runtime`;
- `npm run check:dge2-boundary`;
- consulta direta nas cinco views BI.

Resultado do smoke principal:

- active reference apontou para a official reforecast version mais recente;
- lineage retornou 1 ancestor para a versao filha;
- diff parent encontrou outputs e premissas alteradas;
- `displayAffectsRuntime = false`;
- boundary DGE 2.0 verde.

### Lote 29 - BI Semantic Layer Expansion v1

Status: concluido.

Criado:

- `dge-2.0/docs/architecture/dge-2.0-bi-semantic-layer-blueprint.md`;
- `dge-2.0/scripts/smoke-bi-datasets.js`.

Ajustado:

- `schema-dge-2.sql` amplia a camada de views BI/Superset;
- `package.json` adiciona `npm run smoke:bi-datasets`.

Views BI adicionadas/ampliadas:

- Projection BI:
  - `bi_projection_versions_dataset`;
  - `bi_projection_monthly_outputs_dataset`;
  - `bi_projection_states_dataset`;
  - `bi_progressive_formulas_dataset`;
  - `bi_projection_trace_packs_dataset`;
  - `bi_official_reforecast_lineage_dataset`;
  - `bi_active_projection_reference_dataset`;
- Formula/trace:
  - `bi_formula_registry_dataset`;
  - `bi_formula_execution_traces_dataset`;
- Observado/variancia/reforecast:
  - `bi_daily_kpi_values_dataset`;
  - `bi_monthly_kpi_traces_dataset`;
  - `bi_observed_projection_variances_dataset`;
  - `bi_reforecast_cases_dataset`;
  - `bi_reforecast_proposals_dataset`;
  - `bi_reforecast_decisions_dataset`;
- Gargalos/impacto:
  - `bi_bottleneck_signals_dataset`;
  - `bi_projection_impact_traces_dataset`;
- Governanca:
  - `bi_approval_flow_dataset`;
- Operacao/estoque/commerce/frete/logistica:
  - `bi_operational_nodes_dataset`;
  - `bi_products_dataset`;
  - `bi_inventory_availability_dataset`;
  - `bi_commerce_orders_dataset`;
  - `bi_commerce_order_items_dataset`;
  - `bi_freight_economics_dataset`;
  - `bi_fulfillment_options_dataset`;
  - `bi_logistics_shipments_dataset`;
  - `bi_logistics_events_dataset`;
- IA/RAI:
  - `bi_ai_agent_runs_dataset`;
  - `bi_rai_traces_dataset`;
  - `bi_rai_trace_steps_dataset`;
  - `bi_rai_training_examples_dataset`.

Decisao:

- BI passa a ser camada oficial da DGE 2.0;
- Superset, cockpit, relatorios e IA devem consumir views/datasets controlados;
- tabelas cruas nao sao contrato primario de BI;
- filtros temporais continuam sendo exibicao, sem alterar projection engine/reforecast;
- datasets vazios de IA/RAI sao aceitaveis enquanto agentes reais ainda nao executam.

Validado:

- `npm run db:setup:dge2`;
- `npm run smoke:bi-datasets`;
- 31 views BI obrigatorias encontradas;
- views principais de projection/formula/progressive formulas/active reference retornam dados.

### Lote 30 - Projection Revocation And Rollback v1

Status: concluido.

Criado:

- `dge-2.0/server/contracts/projectionRevocation.contract.js`.

Ajustado:

- `projectionVersion.repository.js` adiciona `updateProjectionVersionLifecycle`;
- `projectionLifecycle.service.js` adiciona:
  - `requestProjectionVersionRevocation`;
  - `approveProjectionVersionRevocation`;
- `projection.routes.js` expoe:
  - `POST /api/projections/versions/:id/request-revocation`;
  - `POST /api/projections/versions/:id/approve-revocation`;
- `smoke-reforecast-preview.js` valida request + approval de revogacao.

Capacidade entregue:

- projection version oficial pode receber solicitacao de revogacao;
- status muda para `revocation_requested`;
- active reference e recalculada e remove a versao contestada;
- parent version volta a ser referencia ativa quando aplicavel;
- owner/admin pode aprovar revogacao;
- status muda para `revoked`;
- `revoked_at` fica preenchido;
- projection version, outputs, traces, lineage e diff permanecem preservados;
- timeline events registram solicitacao e aprovacao de revogacao.

Decisao:

- revogacao nao apaga projection version;
- rollback v1 e governado por status + active reference policy;
- active reference v1 continua:
  - `latest_official_not_revoked_by_activated_at`;
- versoes `revocation_requested` e `revoked` ficam fora da referencia ativa;
- fluxo de revogacao deve existir antes do official formula swap.

Validado:

- `node --check` nos arquivos alterados;
- servidor temporario na porta `8787`;
- `npm run smoke:reforecast-preview`;
- `npm run smoke:bi-datasets`;
- `npm run smoke:scenario-calculate-contract`;
- `npm run smoke:formula-reforecast-runtime`;
- `npm run check:dge2-boundary`.

Resultado do smoke principal:

- official reforecast version criada como filha;
- active reference apontou para a filha;
- revocation request mudou status para `revocation_requested`;
- active reference voltou ao parent;
- revocation approval mudou status para `revoked`;
- `revokedAt` preenchido;
- parent permaneceu como active reference;
- `deletesProjectionVersion = false`.

### Lote 31 - Superset Integration Contract v1

Status: concluido.

Criado:

- `dge-2.0/server/modules/bi/biDatasetCatalog.js`;
- `dge-2.0/server/contracts/biDataset.contract.js`.

Ajustado:

- `dge-2.0/scripts/smoke-bi-datasets.js` passa a validar pelo catalogo oficial;
- `dge-2.0/docs/architecture/dge-2.0-bi-semantic-layer-blueprint.md` documenta o contrato de integracao Superset.

Capacidade entregue:

- catalogo versionado de datasets certificados;
- contrato `bi.dataset.contract.v1`;
- cada dataset declara:
  - view;
  - titulo;
  - dominio;
  - owner;
  - grain;
  - coluna temporal principal;
  - metricas;
  - dimensoes;
  - filtros recomendados;
  - audiences;
  - dashboards associados;
  - policy de refresh;
  - policy futura de RLS;
  - uso por IA;
- smoke valida que todas as views do catalogo existem;
- smoke valida que dashboards nao referenciam datasets inexistentes.

Dashboards iniciais:

1. Executive Overview
2. Projection Explorer
3. Reforecast Control
4. Operation Bottlenecks
5. Commerce & Freight
6. Inventory & Fulfillment
7. AI/RAI Observability

Decisao:

- Superset deve ser configurado a partir do catalogo certificado;
- views cruas nao entram como datasets oficiais sem catalogo;
- IA da DGE deve consultar datasets certificados e registrar fontes no RAI trace;
- RLS real fica para etapa posterior, mas `tenant_id` e `project_id` ja sao obrigatorios no contrato.

### Lote 32 - Official Formula Swap v1

Status: concluido.

Criado:

- `dge-2.0/scripts/smoke-official-formula-swap.js`;
- script `npm run smoke:official-formula-swap`.

Ajustado:

- `dge-2.0/server/contracts/reforecastOfficialApproval.contract.js`;
- `dge-2.0/server/contracts/officialReforecastVersion.contract.js`;
- `dge-2.0/server/modules/finance/projectionCore.js`;
- `dge-2.0/server/modules/projections/officialReforecastVersion.service.js`.

Capacidade entregue:

- policy oficial `execute_formula_reforecast_v1`;
- suporte oficial restrito a `own_channel.effective_conversion`;
- validacao bloqueia formula swap oficial para chaves nao suportadas;
- `projectionCore` aceita `simulationOptions.formulaReforecastPreviews`;
- periodos passados/cutoff continuam preservados;
- periodos futuros podem materializar `recalibratedSeries.proposedEffectiveValue`;
- `outputs.progressiveFormulas[]` expõe:
  - `runtimeOverrideActive`;
  - `runtimeOverride.runtimePolicy`;
  - `formulaVersionFrom`;
  - `formulaVersionTo`;
  - `formulaPolicyFrom`;
  - `formulaPolicyTo`;
  - `baselineEffectiveValue`;
  - `proposedEffectiveValue`;
  - `delta`;
  - `temporalPolicy`.

Decisao:

- formula swap oficial nao deve nascer como adaptador externo;
- a troca entra no proprio contrato de projection runtime;
- formulas ainda nao suportadas continuam como preview/evidencia;
- freight/logistics formula swap oficial fica para lote futuro, depois de amadurecer a semantica operacional.

Validado:

- `node --check` nos arquivos alterados;
- servidor temporario na porta `8787`;
- `npm run smoke:official-formula-swap`;
- `npm run smoke:formula-reforecast-runtime`;
- `npm run smoke:progressive-projection`;
- `npm run smoke:reforecast-preview`;
- `npm run smoke:bi-datasets`;
- `npm run smoke:scenario-calculate-contract`;
- `npm run check:dge2-boundary`.

### Lote 33 - Formula Swap Capability Matrix v1

Status: concluido.

Criado:

- `dge-2.0/server/modules/finance/officialFormulaSwapCapabilityRegistry.js`;
- `dge-2.0/scripts/smoke-official-formula-swap-capability.js`;
- script `npm run smoke:official-formula-swap-capability`.

Ajustado:

- `reforecastOfficialApproval.contract.js` passa a consultar a capability matrix;
- `officialReforecastVersion.contract.js` passa a consultar a capability matrix;
- contratos deixam de depender de lista local hardcoded de formulas suportadas.

Capacidade entregue:

- registry versionado `OFFICIAL_FORMULA_SWAP_CAPABILITY_REGISTRY_VERSION = 1.0.0`;
- cada formula declara:
  - `status`;
  - maturidade;
  - familia;
  - suporte runtime;
  - policies permitidas;
  - roles de aprovacao;
  - evidencias obrigatorias;
  - KPIs observados exigidos;
  - modos de recalibragem suportados;
  - politica temporal;
  - nivel de risco;
  - notas de expansao;
- `own_channel.effective_conversion` permanece `active`;
- frete, entrega, GMV, incremental GMV e retencao/app ficam `planned`;
- lucro mensal, caixa acumulado e payback ficam bloqueados como formulas compostas.

Decisao:

- expandir formula swap oficial exige primeiro mudar o status na capability matrix;
- formulas compostas nao devem ser alvo direto de swap oficial v1;
- formulas financeiras devem nascer como resultado de formulas dependentes recalculadas, nao como override isolado;
- frete/logistica sera a proxima familia natural, mas so depois do contrato operacional de frete/hub/shipment estar maduro.

### Lote 34 - Reforecast + Projection BI Readiness v1

Status: concluido.

Criado:

- view `bi_formula_runtime_overrides_dataset`;
- view `bi_reforecast_diff_summary_dataset`;
- view `bi_reforecast_version_timeline_dataset`.

Ajustado:

- `bi_progressive_formulas_dataset` passa a expor runtime override;
- `biDatasetCatalog.js` inclui os datasets novos;
- `biDatasetCatalog.js` inclui os dashboards:
  - `Formula Runtime Monitor`;
  - `Executive Version Timeline`;
- `smoke-bi-datasets.js` valida os novos datasets;
- `dge-2.0-bi-semantic-layer-blueprint.md` documenta os datasets novos.

Capacidade entregue:

- BI consegue separar projection oficial, preview, reforecast oficial, revogacao e formula swap;
- formula swaps materializados ficam consultaveis por periodo, formula, policy, versao e delta;
- diff baseline vs preview fica normalizado por metrica;
- timeline cronologica expõe cases, proposals, decisions, links parent-child e revogacoes;
- Superset ganha datasets prontos para Projection Explorer, Reforecast Control, Formula Runtime Monitor e Executive Version Timeline.

Decisao:

- BI e cockpit devem ler a narrativa de reforecast por datasets certificados;
- JSON rico continua disponivel nos datasets, mas métricas principais de diff e runtime override devem estar em colunas;
- filtros temporais do Superset continuam display-only e nao alteram runtime/model horizon.

### Lote 35 - Freight & Fulfillment Operational Contract Blueprint v1

Status: planejado/documentado.

Criado:

- `dge-2.0/docs/architecture/dge-2.0-freight-fulfillment-operational-contract-blueprint.md`.

Capacidade planejada:

- separacao clara entre responsabilidades de ecommerce, ERP/Bling, Frenet/Loggi/transportadoras e DGE;
- fluxo canonico de pedido, pagamento, nota, estoque por hub, fulfillment, frete, etiqueta, postagem e entrega;
- leitura explicita de hub unico, estoque descentralizado, split shipping, transferencia interna e retirada em loja;
- Loggi e Frenet delimitados como providers, nao como cerebro operacional da DGE;
- camada pos-entrega adicionada:
  - garantia;
  - troca;
  - avaria;
  - dano;
  - nao recebimento;
  - extravio;
  - reembolso;
  - reposicao;
  - reversa;
- KPIs e gargalos futuros para frete, fulfillment, logistica e pos-entrega;
- roadmap em lotes antes de liberar formula swap oficial de frete/logistica.

Decisao:

- frete/logistica devem amadurecer como contrato operacional antes de virar runtime de formula swap oficial;
- ocorrencias pos-entrega precisam entrar cedo porque afetam margem, reversa, transportadora, qualidade de produto, atendimento e recompra;
- a DGE deve consolidar, auditar, comparar, detectar e projetar impacto, sem assumir checkout runtime, reserva de estoque, emissao fiscal ou papel de transportadora.

## Regra de Ouro

Separar primeiro a intencao e os artefatos documentais; mover runtime depois, com teste a cada lote.

O objetivo nao e apenas organizar pastas. O objetivo e impedir que DGE 1.0 e DGE 2.0 virem um sistema ambiguo.

## Diretriz Posterior: Piloto Congelado

As etapas historicas de extracao descritas neste documento nao autorizam novas pontes com o piloto. A regra atual e mais estrita:

```txt
Piloto = prova de conceito historica congelada.
DGE 2.0 = produto novo com backend, contratos, banco e futuro frontend proprios.
```

O processo raiz compartilhado e apenas acoplamento temporario registrado como `pilot_dge2_runtime_mount_coupling`. O fechamento do Production Readiness Plane deve criar entrypoint backend exclusivo para a DGE 2.0.
