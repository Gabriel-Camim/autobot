---
title: DGE fonte - DGE 2.0 - Progressive Projection Transparency Blueprint
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-progressive-projection-transparency-blueprint.md.'
source_path: docs/architecture/dge-2.0-progressive-projection-transparency-blueprint.md
---

# DGE 2.0 - Progressive Projection Transparency Blueprint

Fonte original DGE 2.0: `docs/architecture/dge-2.0-progressive-projection-transparency-blueprint.md`.

---

# DGE 2.0 - Progressive Projection Transparency Blueprint

## Purpose

This blueprint defines how DGE 2.0 should expose, persist, and reconcile progressive formulas.

Progressive formulas are formulas whose projected value changes across time because of ramp-up, growth, activation, payback, operational learning, freight/logistics improvement, or staged adoption.

The goal is to prevent projections from showing only final monthly numbers while hiding the temporal logic that produced them.

## Core Problem

A fixed premise is not enough.

Example:

```txt
Final conversion target: 2.0%
Ramp curve: linear over 3 periods
Period 2 expected effective conversion: 0.67%
Observed conversion: 1.8%
```

If DGE compares only observed conversion against the final 2.0% target, it may say the operation is still below target.

If DGE compares observed conversion against the period-effective curve value, it sees the operation is far above the expected ramp position.

This distinction changes the meaning of reforecast.

## Required Separation

Every progressive formula should separate:

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

This lets the DGE answer:

- what was the final target?
- what was expected for this period?
- what actually happened?
- is the operation ahead of curve, behind curve, or noisy?
- should the system adjust the final target or recalibrate the curve?

## Progressive Formula Registry

The first registry should include:

```txt
projection.ramp
projection.growth_factor
own_channel.effective_conversion
own_channel.effective_gmv
own_channel.effective_incremental_gmv
own_channel.effective_cart_recovery_gmv
logistics.effective_delivery_days
logistics.effective_freight_cost
financial.effective_monthly_profit
financial.accumulated_cash
financial.payback_progress
participation.post_payback_rate
crm.effective_retention_upside
```

Each registry item should declare:

```txt
formula_key
label
projection_family
curve_type
base_value_key
effective_output_key
observed_kpi_key
final_target_key
curve_driver_keys
confidence_policy
recalibration_modes
owner_boundary
explanation_levels
```

## Current Progressive Formulas In Projection Core

Current formulas already implicit in `projectionCore.js`:

```txt
projection.ramp
- activationPeriod
- implementationPeriods
- rampFactor
- rampPercent
- channelActive

projection.growth_factor
- monthlyGrowth
- growthFactor
- repurchaseIncreasePercent
- appRepurchaseIncreasePercent
- appLTVIncreasePercent

own_channel.effective_gmv
- ownChannelGMV * rampFactor * growthFactor

own_channel.effective_incremental_gmv
- incrementalGMV * rampFactor * growthFactor

own_channel.effective_cart_recovery_gmv
- cartRecoveryGMV * rampFactor * growthFactor

own_channel.effective_conversion
- ownChannelConversionRatePercent * rampFactor * logisticsModifier

logistics.effective_delivery_days
- currentDeliveryDays minus expected improvement scaled by rampFactor

logistics.effective_freight_cost
- pickupAdjustedFreight scaled by ramp/activity assumptions

financial.effective_monthly_profit
- margin/logistics/app upside scaled by ramp/growth minus ramped costs

financial.accumulated_cash
- previousAccumulatedCash + monthlyProfit - periodInvestment

financial.payback_progress
- accumulatedCash versus totalInvestment and payback milestone

participation.post_payback_rate
- dualCortexParticipationPercent activates only after payback
```

## Curve Variance Types

KPI variance is not enough for progressive formulas.

DGE needs curve variance:

```txt
variance_vs_period_effective_value
variance_vs_final_target
variance_vs_curve_position
```

Example:

```txt
target_conversion = 2.0%
period_effective_conversion = 0.67%
observed_conversion = 1.8%

variance_vs_effective = +168.6%
variance_vs_final_target = -10%
curve_position = ahead_of_curve
```

## Curve Interpretation

Suggested values:

```txt
on_curve
ahead_of_curve
behind_curve
accelerating
decelerating
temporary_spike
temporary_drop
insufficient_maturity
data_quality_blocked
outlier
```

## Recalibration Modes

Reforecast should not only change final premises.

Supported future recalibration modes:

```txt
accelerate_curve
decelerate_curve
raise_final_target
lower_final_target
shift_activation_date
extend_ramp_duration
shorten_ramp_duration
change_curve_type
mark_outlier
wait_more_data
request_data_audit
```

Examples:

```txt
assumption_reforecast:
final conversion target changes from 2.0% to 2.6%.

curve_reforecast:
final conversion target remains 2.0%, but ramp duration changes from 3 periods to 2 periods.

activation_reforecast:
activation period shifts because ecommerce went live earlier/later than planned.
```

## Observed Maturity

Observed data should not recalibrate curves automatically.

Each curve-aware observation should carry maturity:

```txt
sample_size
period_count
stability_score
seasonality_flag
campaign_flag
outlier_flag
data_quality_score
audit_status
observed_maturity_score
```

Interpretation:

```txt
observed above curve + low maturity = monitor
observed above curve + high maturity = suggest curve acceleration
observed below curve + high maturity = suggest deceleration or target review
observed with campaign flag = do not recalibrate without attribution
```

## Curve Confidence

Each curve should expose confidence:

```txt
modeled
partial
low
blocked
observed_validated
```

Examples:

```txt
ramp curve confidence = modeled
growth curve confidence = partial until repeated observed periods
freight curve confidence = low until Frenet/Loggi actuals
inventory curve confidence = blocked until SKU-level stock
conversion curve confidence = partial until ecommerce behavior events mature
```

## Outlier Handling

Before reforecast, DGE should identify possible outliers:

```txt
launch_spike
campaign_spike
social_action_spike
stockout_shock
integration_failure
manual_data_error
seasonal_event
one_off_bulk_order
coupon_spike
payment_gateway_incident
```

Outlier rule:

```txt
An outlier can create a case, but should not automatically recalibrate the curve.
```

## Explanation Levels

Progressive formulas should be explainable at multiple levels.

```txt
executive_summary
operator_reason
technical_formula_trace
reforecast_relevance
support_sla_detail
rai_training_detail
```

Example:

```txt
Executive:
Conversion is ahead of the expected ramp for this period.

Operator:
The channel is performing above the curve, but sample maturity and campaign effects must be checked.

Technical:
effective_conversion = target_conversion * ramp_factor * logistics_modifier.

Reforecast:
This may require curve acceleration instead of changing final conversion target.
```

## Ownership Boundary

DGE owns:

- curve modeling;
- effective projected values;
- projected vs observed curve comparison;
- curve explanation;
- recalibration recommendation;
- governance and versioning.

Ecommerce owns:

- actual conversion;
- sessions;
- product views;
- cart behavior;
- coupon usage;
- checkout behavior;
- customer behavior events.

ERP/Bling owns:

- SKU stock;
- product cost;
- product status;
- invoice/order operational facts.

Frenet/Loggi/logistics stack owns:

- freight actuals;
- labels;
- shipping SLA;
- logistics events.

## Future Counterfactual Baseline

For future campaigns, coupons, social actions, pricing changes, and inventory actions, DGE will need:

```txt
actual outcome
vs
expected outcome without action
```

This is not implemented now.

It should be reserved for the future ecommerce-integrated mitigation module.

## Persistence Strategy

Do not create new tables in the first cut.

First cut should enrich existing projection state payloads:

```txt
projection_states.outputs_json.progressiveFormulas
projection_states.drivers_json.curveDrivers
projection_state_trace_packs.metadata.progressiveFormulaKeys
projection_kpi_outputs.metadata.progressiveFormulaKey
projection_kpi_outputs.metadata.effectiveValueContext
```

Only create dedicated tables later if:

- reconciliation needs high-volume curve variance queries;
- multiple observed curves need historical comparison;
- ML/fine-tuning requires normalized curve observations.

## Relationship With Reforecast

Reforecast Preview must eventually support:

```txt
assumption_reforecast
curve_reforecast
activation_reforecast
mixed_reforecast
```

Forecast Reconciliation should not recommend a final-target adjustment when the evidence only proves curve acceleration/deceleration.

Rule:

```txt
If observed value differs from period-effective value, check curve variance before changing final assumption.
```

## First Implementable Cut

Recommended next technical cut:

```txt
Progressive Projection Transparency v1
```

Scope:

- create progressive formula registry;
- make `projectionCore` emit `progressiveFormulas` per projection state;
- include base value, curve factor, effective projected value, final target, formula key, curve type, confidence, and reforecast relevance;
- persist inside existing `projection_states.outputs_json`;
- expose in existing scenario calculate response through `result.projectionStates`;
- smoke validates ramp, conversion, GMV, delivery days, monthly profit, accumulated cash, and payback progress.

Out of scope:

- curve-aware reforecast preview;
- dedicated curve tables;
- AI mitigation planner;
- ecommerce behavior integration;
- automatic curve recalibration.

## Validation Expectations

Smoke should prove:

```txt
projectionState[period].outputs.progressiveFormulas exists
projection.ramp exposes rampFactor/rampPercent
own_channel.effective_conversion exposes target conversion and period-effective conversion
own_channel.effective_gmv exposes target GMV and effective GMV
logistics.effective_delivery_days exposes current, target, and effective delivery days
financial.accumulated_cash exposes previous, monthly profit, investment, and accumulated cash
financial.payback_progress exposes payback status and accumulated progress
officialProjectionMutation remains false
```

This prepares Forecast Reconciliation to compare observed actuals against the right period-effective value.
