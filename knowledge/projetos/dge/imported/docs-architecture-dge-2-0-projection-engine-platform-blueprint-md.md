---
title: DGE fonte - DGE 2.0 - Projection Engine Platform Blueprint
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-projection-engine-platform-blueprint.md.'
source_path: docs/architecture/dge-2.0-projection-engine-platform-blueprint.md
---

# DGE 2.0 - Projection Engine Platform Blueprint

Fonte original DGE 2.0: `docs/architecture/dge-2.0-projection-engine-platform-blueprint.md`.

---

# DGE 2.0 - Projection Engine Platform Blueprint

## Decisao Central

A DGE 2.0 nao deve apenas reescrever o motor de calculo da DGE 1.0 em outro diretorio.

O objetivo e criar uma plataforma de projecao expansivel, auditavel, versionada e preparada para:

- forecast oficial;
- reforecast governado;
- simulacoes;
- previews de impacto;
- variancias projetado vs observado;
- restricoes operacionais;
- explicacoes tecnicas;
- suporte/SLA;
- RAI traces;
- aprendizado futuro com dados curados.

Regra:

> O calculo deve nascer rastreavel. Trace nao e camada posterior; trace e parte do proprio runtime.

## Anti-Divida Tecnica

A engine nao deve:

- depender de `src/calculations.js`;
- assumir um unico formato plano de scenario;
- hardcodar uma unica cronologia mensal;
- misturar formula, persistencia, narrativa e governanca no mesmo arquivo;
- sobrescrever projeções oficiais;
- recalibrar premissas automaticamente sem proposta e aprovacao;
- tratar todo dado observado como confiavel;
- impedir expansao por estoque, frete, hubs, ecommerce behavior, marketing, lojas e franquias.

## Arquitetura Em Camadas

```txt
Projection Request
  -> Projection Contract Layer
  -> Assumption Graph
  -> Formula Execution Graph
  -> Temporal Projection Engine
  -> Operational Constraint Layer
  -> Variance & Calibration Layer
  -> Projection Versioning Layer
  -> Explainability & RAI Layer
  -> Persistence Layer
```

## 1. Projection Contract Layer

Responsabilidade:

- definir entrada e saida estaveis da engine;
- normalizar unidades, escopos, status, datas e contexto;
- impedir que os modulos chamem a engine com JSON solto.

Entrada conceitual:

```txt
scenario
baselineCollection
observedKpis
operationalContext
constraints
simulationOptions
projectionVersionContext
requestMetadata
```

Saida conceitual:

```txt
projectionVersion
calculationRun
formulaTraces
projectionStates
projectionKpiOutputs
varianceFindings
explainabilityPacks
warnings
quality
```

Campos obrigatorios de request:

- `projectionMode`: `official_initial`, `simulation`, `preview`, `reforecast_proposal`, `approved_reforecast`;
- `projectionType`: `projection`, `forecast`, `reforecast`;
- `horizon`;
- `granularity`;
- `scope`;
- `source`;
- `requestedBy`;
- `governancePolicy`.

## 2. Assumption Graph

Premissas nao devem ser tratadas como objeto plano. Devem formar grafo versionado.

Cada premissa deve ter:

- `key`;
- `label`;
- `domain`;
- `unit`;
- `value`;
- `source`;
- `confidence`;
- `scopeType`;
- `scopeKey`;
- `periodStart`;
- `periodEnd`;
- `originType`: `baseline`, `manual_override`, `adaptive_suggestion`, `reforecast`, `system_default`;
- `validityStatus`;
- `dependsOn`;
- `impactsFormulaKeys`;
- `impactsKpiKeys`;
- `metadata`.

Beneficios:

- permite comparar premissas entre versoes;
- permite saber qual premissa causou mudanca no reforecast;
- permite recalibracao futura sem reescrever a engine;
- permite RAI explicar o peso de cada premissa.

## 3. Formula Execution Graph

Cada formula deve ser uma unidade executavel e registrada.

Contrato da formula:

```txt
key
version
domain
inputKeys
outputKey
unit
execute(context)
dependencies
confidencePolicy
variancePolicy
fallbackPolicy
limitations
maturity
reverseCalibration
```

Responsabilidades do graph:

- resolver ordem de execucao;
- validar inputs ausentes;
- aplicar defaults aprovados;
- calcular outputs;
- gerar formula trace;
- registrar warnings;
- impedir ciclos de dependencia;
- permitir substituicao versionada de formula.

Maturidade:

- `active`;
- `beta`;
- `blueprint`;
- `future`;
- `disabled`.

## 4. Temporal Projection Engine

A cronologia deve ser uma camada propria.

Granularidades futuras:

- daily;
- weekly;
- monthly;
- quarterly.

Componentes temporais:

- horizon;
- activation events;
- ramp curves;
- growth curves;
- decay;
- lag effects;
- seasonality;
- cohort effects;
- manual milestones;
- observed-driven recalibration.

Ramp curves suportadas:

- `linear`;
- `logistic`;
- `step`;
- `manual`;
- `observed_driven`;

Exemplos:

- migracao de canal proprio pode usar rampa linear no inicio;
- retencao pode ter lag de cohorts;
- estoque pode limitar GMV projetado por periodo;
- frete pode ter sazonalidade e efeito de mix regional.

## 5. Operational Constraint Layer

O motor deve separar potencial teorico de potencial viavel.

Restricoes previstas:

- estoque disponivel;
- cobertura por SKU;
- hubs disponiveis;
- estoque descentralizado;
- capacidade de separacao;
- capacidade de postagem;
- SLA logistico;
- custo de frete;
- limite de subsidio;
- limite de investimento;
- limite de time;
- qualidade de dados;
- aprovacoes pendentes;
- falha de integracao;
- ruptura operacional.

Saida esperada:

```txt
unconstrainedProjection
constraintsApplied
constrainedProjection
gmvAtRisk
marginAtRisk
slaRisk
confidenceImpact
```

## 6. Projection Families

Familias suportadas pela plataforma:

- `financial_projection`;
- `channel_migration_projection`;
- `commerce_growth_projection`;
- `inventory_resilience_projection`;
- `fulfillment_capacity_projection`;
- `freight_margin_projection`;
- `logistics_sla_projection`;
- `crm_retention_projection`;
- `marketing_efficiency_projection`;
- `unit_expansion_projection`;
- `franchise_projection`;
- `cashflow_projection`;
- `operational_risk_projection`.

Cada familia deve declarar:

- formulas principais;
- KPIs projetados;
- KPIs observaveis equivalentes;
- tolerancias;
- restricoes aplicaveis;
- trace packs;
- maturidade;
- extensoes futuras.

## 7. Variance & Calibration Layer

Cada KPI projetado deve poder ser comparado com KPI observado.

Contrato de variancia:

```txt
projectedKpiKey
observedKpiKey
period
projectedValue
observedValue
varianceAbsolute
variancePercent
qualityScore
confidence
reasonCode
classification
suggestedAction
impactedAssumptions
impactedFormulaKeys
impactedProjectionFamilies
```

Tipos de variancia:

- `volume_variance`;
- `margin_variance`;
- `conversion_variance`;
- `freight_variance`;
- `fulfillment_variance`;
- `inventory_variance`;
- `sla_variance`;
- `cac_ltv_variance`;
- `timing_variance`;
- `mix_variance`;
- `seasonality_variance`;
- `data_quality_variance`;
- `approval_delay_variance`;
- `integration_failure_variance`;
- `stockout_variance`;
- `hub_capacity_variance`;
- `payment_failure_variance`.

Cada regra de variancia deve declarar:

- tolerancia minima;
- numero minimo de periodos;
- qualidade minima dos dados;
- acao sugerida;
- premissas que podem ser recalibradas;
- formulas impactadas;
- se pode gerar reforecast proposal.

### Progressive Formula Variance

Nem toda variancia deve ser comparada contra a premissa final.

Formulas progressivas devem expor:

```txt
base_value
curve_factor
effective_projected_value
observed_value
variance_vs_effective
variance_vs_final_target
curve_position
curve_interpretation
```

Exemplo:

```txt
conversao_final_alvo = 2.0%
conversao_efetiva_periodo = 0.67%
conversao_observada = 1.8%
```

Nesse caso, a operacao ainda pode estar abaixo do alvo final, mas muito acima da curva esperada do periodo.

Reforecast deve diferenciar:

- ajuste de premissa final;
- aceleracao/desaceleracao de curva;
- mudanca de data de ativacao;
- outlier;
- baixa maturidade observada.

Blueprint detalhado:

```txt
dge-2.0/docs/architecture/dge-2.0-progressive-projection-transparency-blueprint.md
```

Implementacao atual:

```txt
dge-2.0/server/modules/finance/progressiveFormulaRegistry.js
projectionStates[].outputs.progressiveFormulas
projectionStates[].drivers.curveDrivers
```

O primeiro corte ja expoe as curvas progressivas no payload mensal, sem criar tabela dedicada.
Reforecast Preview deve consumir esse contrato antes de sugerir alteracao de premissa final.

## 8. Reforecast Governance

Reforecast nao e recalculo automatico.

Fluxo:

```txt
Observed KPIs
  -> Variance Detection
  -> Drift Classification
  -> Adaptive Suggestion
  -> Reforecast Proposal
  -> Human Review
  -> Approval / Rejection
  -> Official Reforecast Version
  -> Historical Timeline
```

Estados de projection version:

- `draft`;
- `preview`;
- `simulation`;
- `official`;
- `reforecast_proposal`;
- `approved_reforecast`;
- `superseded`;
- `revocation_requested`;
- `revoked`;
- `restored`.

Nenhuma versao oficial deve ser sobrescrita.

## 9. Projection Support, Review, Revocation And SLA

A engine deve conversar com a camada de suporte.

Solicitacoes:

- `projection_review_request`;
- `reforecast_revocation_request`;
- `technical_explanation_request`;
- `projection_correction_request`;
- `assumption_dispute_request`;
- `sla_support_request`.

Cada solicitacao deve conseguir apontar para:

- projection version;
- reforecast proposal;
- calculation run;
- formula traces;
- projection states;
- variance findings;
- user/requester;
- SLA;
- technical response;
- final decision.

Revogacao:

- nunca apaga versao;
- marca reforecast como `revoked`;
- restaura versao anterior ou cria nova versao corrigida;
- registra timeline e audit log.

## 10. Explainability & RAI Layer

Toda resposta da engine deve ser explicavel.

Niveis de explicacao:

- executivo;
- tecnico;
- formula-level;
- month-level;
- variance-level;
- support/SLA-level;
- RAI trace.

Perguntas que a engine deve responder:

- o que foi calculado?
- por que foi calculado assim?
- quais premissas pesaram mais?
- quais formulas entraram?
- quais restricoes limitaram a projecao?
- quais dados reais podem mudar a projecao?
- qual qualidade/confiança do resultado?
- qual seria a proxima coleta mais importante?
- qual mudanca exigiria reforecast?

## 11. Persistence Layer

Persistencia minima:

- scenario snapshot;
- scenario premises;
- scenario KPIs;
- projection version;
- projection assumptions;
- projection KPI outputs;
- calculation run;
- formula traces;
- projection states;
- trace packs;
- variance findings;
- support requests;
- technical explanations;
- timeline events;
- audit logs.

## 12. Implementacao Recomendada

Ordem de construcao:

1. `projection.contract.js`;
2. `assumptionGraph.js`;
3. `formulaExecutor.js`;
4. `projectionFormulaCatalog.js`;
5. `temporalModel.js`;
6. `constraintEngine.js`;
7. `varianceEngine.js`;
8. `projectionVersion.service.js`;
9. `projectionEngine.js` como orquestrador;
10. integracao com `scenario.service.js`.

## 13. Primeiro Corte Tecnico

O primeiro corte deve remover a dependencia de `src/calculations.js` sem reduzir capacidade futura.

Escopo minimo:

- criar formula executor;
- portar formulas ativas como funcoes executaveis DGE 2.0;
- gerar traces nativamente;
- gerar outputs equivalentes aos necessarios para os modulos atuais;
- manter projection states e trace packs;
- preservar contrato atual de `/api/scenarios/calculate`.

Fora do primeiro corte:

- estoque constraint real;
- reforecast oficial;
- suporte/SLA runtime;
- ML/fine-tuning;
- frontend.

Esses pontos ja devem estar previstos nos contratos, mas nao precisam ser executados no primeiro corte.
