---
title: DGE fonte - DGE 2.0 Projection Engine
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-projection-engine.md.'
source_path: docs/architecture/dge-2.0-projection-engine.md
---

# DGE 2.0 Projection Engine

Fonte original DGE 2.0: `docs/architecture/dge-2.0-projection-engine.md`.

---

# DGE 2.0 Projection Engine

## Purpose

DGE 2.0 projections must explain operational evolution, not only show numbers increasing over time.

Every projection should answer:

- what is being projected;
- which objective it serves;
- which formulas and drivers were used;
- why the curve grows, stabilizes, or falls;
- which assumptions are strongest;
- which operational constraints can cap the result;
- how future observed KPIs can validate or challenge the projection.

## Core Rule

```txt
Projection rows are not just output rows.
Projection rows are monthly calculation states.
```

Each projected month should be able to expose:

- active formulas;
- ramp factor;
- growth factor;
- channel activation status;
- migration progress;
- operational constraints;
- financial impact;
- logistics impact;
- CRM/app impact;
- variance versus previous month;
- relation to the final target.

## Projection Families

DGE 2.0 should support multiple projection families instead of one generic table.

### 1. Financial Projection

Objective:

- understand cash, profit, payback, ROI, and participation rules.

Core outputs:

- monthly profit;
- investment by month;
- accumulated cash;
- payback month;
- ROI by month;
- participation start month;
- post-payback economics.

Key drivers:

- setup;
- monthly fee;
- margin recovered;
- logistics savings;
- app retention upside;
- freight subsidy;
- CAC burden;
- operational extra cost;
- post-payback participation.

### 2. Channel Migration Projection

Objective:

- explain how marketplace GMV migrates into own channel over time.

Core outputs:

- target own-channel migrated GMV;
- monthly ramp percentage;
- active migrated GMV by month;
- incremental GMV by month;
- recovered cart GMV by month;
- channel mix over time.

Key drivers:

- target migration percentage;
- implementation months;
- activation month;
- conversion factor;
- review factor;
- freight friction factor;
- CRM/LTV factor;
- monthly growth factor.

This is where the DGE must explain:

```txt
Why month 1 is not 100% of the target.
Why the ramp starts after activation.
Why the target migration is reached gradually.
Why growth continues after the ramp completes.
```

### 3. Operational Capacity Projection

Objective:

- verify whether projected demand can be fulfilled.

Core outputs:

- projected orders;
- own-channel orders;
- orders per day;
- required operator capacity;
- hub capacity usage;
- bottleneck flags;
- SLA risk.

Key drivers:

- monthly orders;
- average ticket;
- hub count;
- hub capacity;
- picking/packing time;
- operational error rate;
- current delivery SLA;
- expected hub SLA.

### 4. Logistics Projection

Objective:

- estimate delivery cost, speed, subsidy, hub leverage, and reverse logistics.

Core outputs:

- blended freight;
- pickup-adjusted freight;
- freight subsidy cost;
- delivery-day reduction;
- logistics savings;
- reverse logistics exposure;
- hub-routable order share.

Key drivers:

- SP/outside SP mix;
- motoboy/Loggi cost;
- carrier cost;
- pickup-in-store percentage;
- subsidized freight percentage;
- current delivery days;
- expected delivery days with hubs;
- failed delivery and reverse logistics rates.

### 5. CRM And Retention Projection

Objective:

- estimate how owned customer relationship increases LTV, frequency, and repeat purchase.

Core outputs:

- active identified base;
- recurring customers;
- repeat purchase uplift;
- LTV uplift;
- campaign contribution;
- CRM-attributed GMV;
- retention upside.

Key drivers:

- identified customer percentage;
- app recurring users;
- campaign frequency;
- app usage frequency;
- app LTV increase;
- app repurchase increase;
- opt-in rate;
- CAC/LTV ratio.

### 6. Inventory And Product Projection

Objective:

- connect sales projection to stock reality.

Core outputs:

- projected stock coverage;
- rupture risk;
- GMV at risk from stockout;
- SKU/category bottlenecks;
- capital tied in stock;
- replenishment timing.

Key drivers:

- stock available;
- inventory turnover;
- replenishment lead time;
- stockout rate;
- category mix;
- projected orders;
- product margin.

### 7. Marketing Efficiency Projection

Objective:

- test whether growth requires paid acquisition or can be driven by CRM/organic gains.

Core outputs:

- CAC by channel;
- blended CAC;
- ROAS;
- paid GMV contribution;
- margin after media;
- payback of acquisition.

Key drivers:

- media budget;
- paid media CAC;
- ROAS;
- CRM campaign budget;
- conversion rate;
- average ticket;
- gross margin.

### 8. Scenario Comparison Projection

Objective:

- compare conservative, moderate, aggressive, and custom paths.

Core outputs:

- payback comparison;
- ROI comparison;
- leakage reduction;
- GMV recovered;
- margin recovered;
- operational risk score;
- best/worst drivers.

Key drivers:

- all scenario assumptions;
- formula versions;
- objective weights.

## Monthly Projection State

Every projected month should eventually be represented like this:

```js
{
  month: 6,
  objective: 'channel_migration',
  formulasUsed: [
    'projection.ramp',
    'projection.growth_factor',
    'projection.own_channel_gmv',
    'projection.monthly_profit'
  ],
  drivers: {
    activationMonth: 6,
    implementationMonths: 5,
    rampMonths: 1,
    rampFactor: 0.2,
    growthFactor: 1,
    targetMigrationPercent: 8
  },
  outputs: {
    ownChannelGMV: 123000,
    incrementalGMV: 32000,
    recoveredCartGMV: 9000,
    monthlyProfit: 18000,
    accumulatedCash: -42000
  },
  explanation: {
    summary: 'Primeiro mes ativo do canal proprio. A rampa usa 20% do potencial porque a implantacao prevista tem 5 meses.',
    constraints: ['Canal ainda em rampa operacional.'],
    confidence: 'modeled'
  },
  tracePacks: [
    {
      key: 'channel_migration_trace_pack',
      label: 'Rastreio de migracao de canal',
      objective: 'channel_migration',
      formulaKeys: [
        'projection.ramp',
        'projection.growth_factor',
        'own_channel.adjusted_gmv'
      ],
      drivers: {
        rampFactor: 0.2,
        growthFactor: 1,
        targetMigrationPercent: 8
      },
      outputs: {
        ownChannelGMV: 123000,
        incrementalGMV: 32000
      },
      status: 'modeled',
      summary: 'Canal ativo com 20% da rampa e fator de crescimento 1.'
    }
  ],
  monthlyFormulaTraces: [
    {
      formulaKey: 'projection.ramp',
      outputValue: 0.2,
      inputs: [
        { key: 'month', value: 6, unit: 'month' },
        { key: 'activation_month', value: 6, unit: 'month' },
        { key: 'implementation_months', value: 5, unit: 'month' }
      ]
    },
    {
      formulaKey: 'projection.active_own_channel_gmv',
      outputValue: 123000
    }
  ]
}
```

## Ramp-Up Rule

The current model uses:

```txt
activationMonth = implementationMonths + 1
rampMonths = max(month - activationMonth + 1, 0)
ramp = channelActive ? min(rampMonths / implementationMonths, 1) : 0
```

Meaning:

- before activation, the channel contributes 0%;
- in the first active month, it contributes `1 / implementationMonths`;
- it reaches 100% of target after the implementation window;
- after reaching target, growth can continue through the monthly growth factor.

DGE 2.0 must expose this as a traceable projection mechanism, not bury it inside a table.

Current implementation note:

`POST /api/scenarios/calculate` returns `projectionStates` with this ramp-up logic already expanded for each month. The first implementation focuses on channel migration, cash return, and margin recovery; future iterations should add operational capacity, inventory, logistics, CRM, and marketing-specific states.

Adaptive projection analysis is separated from official scenario calculation. `POST /api/projections/adaptive/analyze` can suggest assumption adjustments from observed variance history, but it does not mutate the official projection.

`projectionStates.tracePacks` is also implemented. The first active packs are:

- `channel_migration_trace_pack`;
- `financial_return_trace_pack`;
- `payback_trace_pack`;
- `logistics_trace_pack`;
- `crm_retention_trace_pack`.

`projectionStates.monthlyFormulaTraces` is implemented for the first monthly projection formulas:

- `projection.ramp`;
- `projection.growth_factor`;
- `projection.active_own_channel_gmv`;
- `projection.active_incremental_gmv`;
- `projection.active_cart_recovery_gmv`;
- `projection.monthly_profit`;
- `projection.accumulated_cash`.

Future reserved packs:

- `operational_capacity_trace_pack`;
- `inventory_trace_pack`;
- `marketing_trace_pack`.

## Formula Description Metadata

Each formula must support rich explanation metadata:

```js
{
  description: 'What the formula calculates in business language.',
  rationale: 'Why DGE uses this formula.',
  consideredFactors: ['Which variables were considered.'],
  excludedFactors: ['Which variables are not yet included.'],
  limitations: ['Where this formula can be wrong or incomplete.'],
  interpretation: 'How a human should read the result.',
  futureExpansion: ['How this formula can evolve.'],
  auditNotes: ['Internal notes for governance and review.']
}
```

The goal is not only transparency. It also lets future AI, reports, contracts, and dashboards explain calculations consistently.

## Projection Objectives

Each projection run should declare one or more objectives:

```txt
cash_return
channel_migration
margin_recovery
operational_capacity
logistics_efficiency
crm_retention
inventory_resilience
marketing_efficiency
scenario_comparison
contract_viability
```

Different objectives can use the same base scenario but emphasize different outputs and explanations.

## Expansion Strategy

Projection formulas should evolve in layers:

### Layer 1: Current Deterministic Model

Uses current DGE formulas and static assumptions.

### Layer 2: Driver Trace Model

Adds formula traces for ramp, growth, monthly profit, logistics, CRM, and projection rows.

### Layer 3: Operational Constraint Model

Adds capacity, inventory, SLA, stockout, hub, and team constraints.

### Layer 4: Observed Variance Model

Compares projected KPIs with observed KPIs after real data imports.

### Layer 5: Adaptive Forecast Model

Recalibrates future projections based on observed variance while preserving original scenario history.

## Non-Negotiable Rule

A projection number is incomplete until it can explain its drivers.
