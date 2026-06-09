---
title: DGE fonte - DGE 2.0 - Forecast Reconciliation And Reforecast Readiness Blueprint
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-forecast-reconciliation-and-reforecast-readiness-blueprint.md.'
source_path: docs/architecture/dge-2.0-forecast-reconciliation-and-reforecast-readiness-blueprint.md
---

# DGE 2.0 - Forecast Reconciliation And Reforecast Readiness Blueprint

Fonte original DGE 2.0: `docs/architecture/dge-2.0-forecast-reconciliation-and-reforecast-readiness-blueprint.md`.

---

# DGE 2.0 - Forecast Reconciliation And Reforecast Readiness Blueprint

## Purpose

This blueprint defines the missing middle layer between official forecasts and future operational mitigation.

The DGE 2.0 should not treat reforecast as a simple recalculation. Reforecast must be born from reconciled evidence:

```txt
official forecast
-> audited actuals
-> projected vs actual reconciliation
-> variance classification
-> bottleneck causal evidence
-> probable cause attribution
-> reforecast case
-> governed preview
-> approval
-> new projection version
```

The current phase prepares the DGE to detect and explain when the digital operation is diverging from the forecast thesis.

It does not implement deep operational mitigation plans yet.

## Core Decision

Operational mitigation with AI, product pricing, SKU-level stock, coupons, social actions, category strategy, product margin, and ecommerce behavior must not be implemented as an isolated DGE module now.

That layer must be born integrated with:

- ecommerce orders;
- ecommerce customers;
- ecommerce product catalog;
- ecommerce behavior events;
- product and category margin;
- SKU-level stock;
- Bling/ERP facts;
- freight actuals;
- coupon attribution;
- user behavior and funnel context.

Until these contexts exist, reforecast should only store readiness, required context, allowed future mitigation scopes, restricted scopes, and executive notes.

## Non-Negotiable Boundary

```txt
DGE 2.0 detects, reconciles, explains, governs, and versions.
Ecommerce executes customer-facing commerce, pricing, coupons, checkout, and behavior capture.
ERP/Bling owns operational product, stock, invoice, and cost facts.
n8n may orchestrate approved automations later.
```

The DGE must not silently change ecommerce pricing, coupons, catalog, stock promises, freight policy, or checkout behavior.

Future DGE recommendations may become approved rulesets, but ecommerce remains the runtime.

## What Is Reforecast

Reforecast is a governed revision of a projection version because the official forecast thesis no longer matches audited operational reality.

It may happen because:

- observed KPIs diverged from projected KPIs;
- the divergence persisted long enough to stop being noise;
- the divergence affects financial, operational, channel, logistics, inventory, or commerce assumptions;
- a structural event changed the operating context;
- an executive decision changed contract, channel, pricing, ecommerce, hub, freight, or stock strategy.

Reforecast is not:

- every new KPI snapshot;
- every daily variance;
- every adaptive simulation;
- an automatic overwrite of the official forecast;
- an action plan;
- a campaign plan;
- a pricing engine;
- a stock purchasing engine.

## Forecast Reconciliation Layer

Forecast reconciliation answers:

```txt
What did the official forecast expect?
What actually happened?
Was the difference relevant?
Was it noise, trend, structural variance, or critical break?
What caused it?
What projection families and formulas were affected?
Does this require monitoring, audit, explanation, reforecast preview, or executive decision?
```

This layer is the reason DGE becomes necessary as digital operation monitoring, not just as initial projection software.

It must not duplicate the current KPI intelligence stack.

It consumes and interprets existing facts:

```txt
projection_versions
projection_kpi_outputs
monthly_kpi_traces
observed_projection_variances
bottleneck_detection_runs
projection_impact_traces
daily_kpi_snapshots
approval/audit status
```

Rule:

```txt
Variance Engine calculates the numeric gap.
Bottleneck Detection explains operational symptoms.
Projection Impact Analyzer maps operational pressure to projection families/formulas.
Forecast Reconciliation gives semantic meaning and opens governed cases.
```

## Relationship With Existing Modules

The DGE already has pieces of the intelligence chain. Forecast Reconciliation should unify them, not replace them.

```txt
Projection Version
-> official projected outputs

Monthly KPI Trace
-> monthly observed aggregate and quality

Observed Projection Variance
-> projected vs actual numeric gap

Bottleneck Detection
-> operational symptom and probable causal evidence

Projection Impact Analyzer
-> affected projection families/formulas from cockpit pressure

Forecast Reconciliation
-> case-level interpretation, materiality, cause attribution, readiness, and next decision

Reforecast Intelligence
-> adjustment policy and preview generation inside a case
```

## Official Reforecast Explainability v2

Every official reforecast must generate deterministic explainability.

The explainability layer answers:

```txt
Why does this official version exist?
Which baseline was preserved?
Which child version was created?
Which evidence supported the change?
Which assumptions changed?
Which monthly outputs changed?
Who approved the mutation?
Which pending cases were resolved or made stale?
What is the active projection health after the new version?
```

The canonical contract is `official.reforecast.explainability.v2`.

It includes:

- executive and technical narratives;
- primary reason;
- evidence ledger;
- baseline vs official diff;
- monthly impact timeline;
- assumption diff ledger;
- family explainer;
- governance and approval trace;
- active state aftermath;
- dependency impact summary;
- risk and confidence;
- RAI readiness.

The first complete family explainer is `channel_runtime`.

The family explainability layer also covers:

- `formula_reforecast`, for formula swaps, formula previews, runtime policy and blocked/planned formula contexts;
- `freight_reforecast`, for freight cost, freight burden, logistics formulas and future Frenet/Loggi/Bling/hub context;
- `inventory_product_capacity`, for ERP stock/capacity constraints, stockout, GMV at risk, hub pressure and aggregated inventory runtime;
- `mixed_reforecast`, for cases where more than one material family influences the official version.

For channel reforecast it must explain:

- own channel vs marketplace aggregate;
- Shopee and Mercado Livre as comparative/projection benchmark only;
- GMV, take rate, margin, freight burden, leakage and customer data coverage;
- why marketplace does not receive direct operational intelligence;
- which metrics must be monitored after officialization.

Fallback explainers exist for formula, freight and general reforecast until those families receive specialized contracts.

Family classification rule:

```txt
channel_runtime = channel evidence only
freight_reforecast = freight/logistics evidence dominates, even when freight formula previews are attached
formula_reforecast = non-freight formula swap or formula evidence dominates
mixed_reforecast = multiple material families are present
general_reforecast = fallback for approved assumption changes without specialized family
```

## Official Inventory Capacity Reforecast

Inventory capacity reforecast follows the same official governance rail. It is not a separate engine.

Accepted flow:

```txt
erp.bottleneck_signal.v1
-> reforecast_case triggerType=erp_inventory_capacity_variance
-> reforecast preview with projection.inventoryRuntime.v1
-> preview review
-> formal proposal
-> official approval
-> official child projection_version
-> explainability family inventory_product_capacity
```

When the evidence family is `inventory_product_capacity`, the formal proposal and official version plan must declare:

```txt
reforecastFamily = inventory_product_capacity
inventoryRuntimeContractVersion = projection.inventoryRuntime.v1
inventoryBoundary = aggregated_capacity_runtime
rawSkuRuntimeBoundary = false
```

Official approval must block the flow if:

- the preview did not apply `inventoryRuntime`;
- inventory evidence is missing;
- `stockoutRatePercent`, `gmvAtRiskAmount` or `capacityFactor` is absent;
- the proposal baseline is stale without owner/admin override;
- the actor is not owner/admin or tenant_owner/tenant_admin.

This preserves the thesis:

```txt
DGE can officialize an inventory-constrained forecast thesis.
DGE cannot inject raw SKU rows into projection core.
DGE cannot execute purchase, transfer or manual stock adjustment as part of reforecast.
Bling remains auxiliary evidence, not canonical inventory owner.
```

### Variance Vs Bottleneck

These are not the same object.

```txt
Variance = what deviated.
Bottleneck = why it may have deviated.
Reconciliation = what the deviation means for the official forecast thesis.
```

Example:

```txt
Variance:
actual_monthly_gmv is -18% versus projected GMV.

Bottleneck evidence:
inventory_stockout_gmv_risk
fulfillment_decentralized_order_stock
freight_cost_above_projection

Reconciliation:
The forecast thesis is at risk because inventory/logistics are constraining the projected channel migration.
```

### Adaptive Projection Reformulation

The current Adaptive Projection Engine should be treated as a transition module.

It should not remain the primary orchestrator of reforecast logic.

Target reformulation:

```txt
Adaptive Projection Engine
-> Reforecast Intelligence Layer
```

The useful parts should be preserved:

- KPI-to-assumption mappings;
- assumption adjustment suggestions;
- evidence windows;
- impact simulation;
- approval/rejection traces.

But they should run inside a reforecast case created by Forecast Reconciliation.

Future rule:

```txt
Adaptive logic does not decide alone that reforecast is needed.
Forecast Reconciliation creates or updates the case.
Reforecast Intelligence suggests the adjustment and preview inside that case.
```

## Forecast Thesis

Every official forecast should be interpreted as a thesis.

Examples:

- own channel migration will reach a target percentage after ramp-up;
- freight cost will improve with hubs, pickup, or better logistics mix;
- ecommerce conversion will sustain the modeled rate;
- app/CRM will increase repeat purchase and LTV;
- inventory and fulfillment will support the projected demand;
- contribution margin will stay inside modeled limits;
- payback will occur inside the approved horizon.

The DGE should monitor whether the thesis is still alive.

## Projected Vs Actual Ledger

The projected vs actual ledger should not be rebuilt as a redundant table if the existing KPI intelligence tables can be evolved cleanly.

Current base:

```txt
monthly_kpi_traces
observed_projection_variances
projection_kpi_outputs
```

Needed evolution:

```txt
observed_projection_variances.projection_version_id
observed_projection_variances.projection_kpi_output_id
observed_projection_variances.actual_snapshot_id or monthly_kpi_trace_id
```

The reconciliation view should eventually expose, per projection version, period, and KPI:

```txt
projection_version_id
projection_kpi_output_id
period_key
kpi_key
projected_value
actual_value
variance_abs
variance_percent
variance_direction
projection_family_key
formula_key
source_snapshot_id
actual_audit_status
actual_quality_score
reconciliation_status
classification
probable_causes
metadata
```

This ledger becomes the factual base for:

- reforecast cases;
- executive cockpit health;
- RAI explanations;
- future ML/fine-tuning;
- post-reforecast learning.

Implementation rule:

```txt
Do not create a second variance ledger before evaluating whether observed_projection_variances can be extended.
```

## Variance Classification

Recommended classification:

```txt
within_expected_range
noise
watch
material_variance
structural_variance
critical_break
data_quality_blocked
```

Example policy:

```txt
< 5% variance = within_expected_range
5% to 15% = watch
> 15% for enough periods = material_variance
> 25% with payback/margin impact = structural_variance
contract/ecommerce/hub activation changed = critical_break
actual data not audited = data_quality_blocked
```

Thresholds should be configurable by KPI and projection family.

## Curve-Aware Reconciliation

Progressive formulas require reconciliation against the effective value of the period, not only against the final target.

For every progressive KPI, reconciliation should eventually compare:

```txt
observed_value vs period_effective_projected_value
observed_value vs final_target_value
observed_position vs expected_curve_position
```

Example:

```txt
Final conversion target: 2.0%
Period 2 effective conversion by ramp: 0.67%
Observed conversion: 1.8%
```

This should not automatically mean "raise final conversion target".

It may mean:

```txt
accelerate_curve
shorten_ramp_duration
mark_campaign_outlier
wait_more_data
raise_final_target
```

Rule:

```txt
Forecast Reconciliation must check curve variance before recommending final assumption recalibration.
```

Detailed blueprint:

```txt
dge-2.0/docs/architecture/dge-2.0-progressive-projection-transparency-blueprint.md
```

Current implementation base:

```txt
projectionStates[].outputs.progressiveFormulas
projectionStates[].drivers.curveDrivers
```

Forecast Reconciliation should use these values before opening a final-target reforecast.
If observed conversion, GMV, freight, delivery or payback differs from the forecast, the first question is:

```txt
Did the operation miss the period-effective curve, or only differ from the final target?
```

Current runtime behavior:

```txt
observed_projection_variances
-> matched projection_states.outputs.progressiveFormulas
-> curveVariance
-> reforecast case evidence
```

When a progressive formula exists, materiality classification should use variance against the period-effective value.
The original variance remains available, but the case must show whether the operation is ahead of curve, behind curve, or on curve.

## Reforecast Intelligence Preflight

Before Reforecast Preview v1, the DGE must separate three registries:

```txt
curveVarianceRegistry
- maps observed KPI keys to progressive formulas;
- declares whether lower value is better;
- classifies ahead/on/behind curve.

reforecastIntelligenceRegistry
- reads curve variance, materiality, probable causes and data quality;
- decides preview readiness;
- recommends curve, assumption, activation, mixed, audit, or monitoring path.

reforecastPreview.contract
- defines preview envelope;
- guarantees no official projection mutation;
- separates preview from proposal and approved reforecast version.
```

Preview policy examples:

```txt
ahead_of_curve + below final target
-> curve_reforecast / accelerate_curve

ahead_of_curve + above final target
-> mixed_reforecast / accelerate_curve + raise_final_target

behind_curve + operational cause
-> mixed_reforecast / operationally constrained preview

behind_curve + low data quality
-> data_audit_required

on_curve
-> monitoring / wait_more_data
```

This prevents Reforecast Preview from becoming a clone of Adaptive Projection.
Adaptive Projection remains a transitional suggestion layer and should be absorbed into Reforecast Intelligence policies.

## Probable Cause Attribution

The DGE should not only say that numbers changed. It should classify probable causes.

Bottleneck signals are the main causal evidence source.

They should be linked to reforecast cases as:

```txt
bottleneck_run_id
bottleneck_signal_key
domain
severity
evidence_json
affected_kpis
recommended_actions
```

Initial cause taxonomy:

```txt
conversion_gap
freight_cost_gap
stockout_gap
decentralized_inventory_gap
fulfillment_delay_gap
payment_failure_gap
traffic_quality_gap
cac_gap
margin_gap
ticket_gap
channel_migration_gap
activation_delay_gap
data_quality_gap
commerce_behavior_gap
product_mix_gap
category_margin_gap
coupon_attribution_gap
pricing_gap
```

Each cause should carry:

```txt
confidence
evidence
affected_kpis
affected_formulas
affected_projection_families
recommended_next_step
```

## Reforecast Case

Before there is a reforecast proposal, there should be a reforecast case.

The case is the governed investigation object.

Suggested fields:

```txt
case_id
baseline_projection_version_id
scope_type
scope_key
status
severity
trigger_type
trigger_source
affected_kpis
affected_formulas
affected_projection_families
probable_causes
evidence_json
recommendation
requires_human_review
requires_data_audit
requires_technical_explanation
future_mitigation_readiness
created_by
assigned_to
decision_notes
metadata
```

Suggested statuses:

```txt
open
watching
data_audit_required
ready_for_preview
preview_generated
pending_approval
approved_for_reforecast
rejected
closed_no_action
closed_mitigated
closed_superseded
```

## Reforecast Proposal

A reforecast proposal should only be created after a case is mature enough.

The proposal should reference:

- baseline projection version;
- proposed projection version;
- reforecast case;
- changed assumptions;
- projected impact;
- evidence;
- approval chain;
- decision log.

Official forecast mutation only happens after approval.

## Official Channel Reforecast

Channel reforecast follows the same official governance rail. It is not a separate engine.

The accepted flow is:

```txt
channel_projection_variance
-> channel_reforecast_candidate
-> reforecast_case
-> reforecast preview
-> preview review
-> formal proposal
-> official approval
-> official child projection_version
```

When the evidence family is `channel_projection_variance`, the formal proposal and official version plan must declare:

```txt
reforecastFamily = channel_runtime
channelRuntimeContractVersion = projection.channelRuntime.v1
marketplaceBoundary = comparative_projection_only
ownChannelBoundary = operational_intelligence_allowed
```

Official approval must block the flow if:

- the preview did not apply `channelRuntime`;
- channel evidence is missing;
- `ownChannelGMV` or `marketplaceGMV` is missing from active overrides;
- marketplace operational intelligence is not explicitly false;
- the actor is not `owner` or `admin`;
- required acknowledgements are incomplete.

This preserves the thesis:

```txt
DGE can officialize a channelized reforecast.
DGE cannot operate Shopee or Mercado Livre as intelligent operational domains.
```

BI and lineage must continue reading the official child version through the same projection version tables and `bi_projection_channel_runtime_dataset`.

## Active State And Dependency Control

The active projection is still the latest official, non-revoked projection version.

However, the active projection can be unhealthy.

Current v1 contracts:

```txt
projection.active_state.v1
reforecast.dependency_control.v1
official.reforecast.explainability.v1
```

Rules:

- every official approval checks whether the proposal baseline is still the active projection;
- stale baseline approval is blocked by default;
- owner/admin or tenant_owner/tenant_admin may override stale baseline only with an explicit reason;
- after a new official version is created, pending cases and proposals are revalidated;
- cases can be marked as `needs_preview_regeneration`, `still_required`, `blocked_by_dependency`, `blocked_by_data_quality`, or `resolved_by_new_reforecast`;
- the active state tells the cockpit whether the projection is `current`, `pending_review`, `has_stale_previews`, `has_pending_official_approval`, `has_blocking_cases`, or `data_quality_blocked`.

Default dependency order:

```txt
data_quality_audit
structural_baseline_activation
channel_gmv_revenue
inventory_product_capacity
fulfillment_logistics_freight
after_sales_reverse_logistics
formula_curve_ramp
future_mitigation_ai_campaigns
```

This prevents a reforecast proposal calculated against an older baseline from being approved blindly after a newer official reforecast has already changed the active thesis.

## Mitigation Readiness Only

The current DGE phase should prepare for future mitigation, not implement it.

A reforecast case may store:

```json
{
  "mitigationContextAvailable": false,
  "mitigationRecommended": true,
  "requiresCommerceContext": true,
  "requiresProductMarginContext": true,
  "requiresStockContext": true,
  "requiresUserBehaviorContext": true,
  "allowedFutureScopes": [
    "pricing",
    "inventory",
    "freight",
    "marketing",
    "product_mix",
    "category_strategy",
    "social_action"
  ],
  "restrictedFutureScopes": [
    {
      "scope": "social_action",
      "minTenantLevel": "executive"
    }
  ],
  "futureMitigationNotes": "Mitigation planning depends on ecommerce, ERP, margin, stock, coupon, and behavior context."
}
```

This lets the DGE say:

```txt
The forecast thesis is at risk.
A mitigation discussion may be useful.
But deep mitigation cannot be safely recommended until commerce and product context are available.
```

## Future AI Context Window

Future IA analysis should open from a reforecast case, not from a generic chat.

The future context window should include:

- baseline projection version;
- forecast thesis;
- projected vs actual ledger;
- variance classifications;
- probable causes;
- affected formulas;
- affected projection families;
- audited KPI snapshots;
- ecommerce orders and product performance;
- SKU-level stock and cost;
- product margin;
- category behavior;
- coupon attribution;
- freight actuals;
- user behavior events;
- tenant scope and permission level.

Output from AI should be advisory and governable:

```txt
suggested_mitigation_angles
pricing_risk_notes
inventory_risk_notes
coupon_attribution_plan
expected_kpi_impact
required_data
confidence
human_decision_required
```

No AI output should directly mutate official forecasts, ecommerce prices, coupons, stock strategy, or campaign execution.

## Future Mitigation Scopes

Allowed future scopes:

```txt
pricing
category_strategy
product_mix
inventory
stock_reallocation
sku_purchase
freight_policy
marketing
crm_campaign
coupon_strategy
social_action
checkout_fix
payment_recovery
fulfillment_process
data_audit
technical_fix
```

These scopes are future-ready metadata now.

They are not active execution modules in the current phase.

## Social Actions

Social actions are restricted to high tenant levels.

Reason:

- they affect brand strategy;
- they may use public-facing campaigns;
- they may require executive budget;
- they may use coupon attribution;
- they can alter strategic reading of ecommerce performance;
- they should not be created by routine operational users.

Rule:

```txt
social_action scope requires executive, owner, admin, or equivalent high-authority tenant role.
```

Future social action analysis should depend on:

- coupon code;
- campaign window;
- ecommerce attribution;
- cost of action;
- orders attributed;
- GMV attributed;
- margin after discount;
- new vs returning customers;
- repeat purchase after campaign;
- LTV estimate;
- projection impact.

Current phase:

```txt
Store social_action only as restricted future mitigation scope.
Do not implement social action planning yet.
```

## Tenant Model

Initial authority model:

```txt
operator
- can see local reconciliation signals if authorized;
- cannot approve reforecast;
- cannot request social action strategy.

unit_manager
- can review local variance;
- can request human review;
- cannot approve official reforecast globally.

regional_manager
- can review multi-unit variance;
- can submit case for executive approval;
- may approve regional analysis depending on policy.

executive
- receives official reforecast readings;
- can request technical explanation;
- can approve/reject reforecast proposals;
- can authorize social_action scope.

admin / owner
- can govern official forecast, reforecast, revocation, and restricted future scopes.

caos_lab_support
- can add technical explanation and RAI analysis;
- cannot approve official mutation unless explicitly assigned that role.

automation_tenant
- can detect, suggest, collect, and create draft cases;
- cannot approve official reforecast or social action.
```

## Visualization Requirements

Projection page should eventually show:

```txt
Official forecast version
Forecast Thesis Score
Projected vs actual summary
Risk by projection family
Open reforecast cases
Reforecast readiness
Future mitigation context status
Restricted executive-only scopes
```

Case page should show:

```txt
Why this case exists
Which KPIs diverged
How long the divergence persisted
What caused the divergence
Which formulas/families are affected
Whether data was audited
Whether reforecast is recommended
Whether mitigation context is available
Which future contexts are missing
Who can approve the next step
```

Diff visualization should show:

```txt
baseline forecast
actual observed
variance
proposed reforecast preview
impact on payback, margin, GMV, freight, stock, conversion
affected formulas
decision history
```

## First Implementable Cut

Recommended next technical cut:

```txt
Forecast Reconciliation v1
```

Scope:

- no mitigation plans;
- no AI action planner;
- no pricing recommendations;
- no coupon/social action execution;
- no ecommerce runtime mutation.

Build:

- reconciliation contract;
- materiality policy registry;
- service to compare official projection version outputs against audited KPI snapshots;
- reforecast case skeleton;
- endpoints to run/list reconciliation and cases;
- readiness metadata for future mitigation;
- tenant guardrails for restricted scopes.

Smoke should prove:

- official projection version exists;
- audited actual KPI is compared against projected KPI;
- variance item is created;
- material variance can open a reforecast case;
- case stores future mitigation readiness;
- social_action appears only as restricted future scope;
- official projection version remains unchanged.

## Architecture Rule

Do not build Operational Mitigation Planning as a standalone DGE module before ecommerce/ERP/product/stock/margin/behavior context exists.

The current DGE should prepare the evidence and governance rail.

The future integrated system should decide whether pricing, inventory, social action, coupons, product mix, freight policy, or marketing action is the right mitigation.

## Reforecast Temporal Cutoff Policy

Reforecast must not rewrite the past.

When a case is generated on a date inside the operating horizon, the preview should separate:

```txt
locked actuals
-> already observed and audited data

current period remainder
-> prorated/blended preview from effectiveFrom

future periods
-> full reforecast preview
```

Example:

```txt
case created: 2026-05-10
lockedActualsThrough: 2026-05-10
effectiveFrom: 2026-05-11
currentPeriodPolicy: prorated_reforecast
futurePeriodPolicy: full_reforecast
closedPeriodPolicy: preserve_audited_actuals
```

Current runtime:

```txt
dailyReforecastRuntime: false
monthlyPreviewRuntime: true
intraPeriodBlendDeclared: true
```

This means the first preview runtime still recalculates with a monthly engine, but the preview contract explicitly declares the temporal cutoff and guardrails.

Future daily/weekly engine should use this same policy to blend actuals and forecast precisely.

## Reforecast Adjustment Model

Reforecast must not be limited to assumption changes.

The preview layer should distinguish:

```txt
assumption_reforecast
- changes an assumption value;
- active in preview v1 through assumptionOverrides.

curve_reforecast
- changes ramp/growth/activation curve behavior;
- declared in preview v1.

formula_reforecast
- changes formula version, policy or data composition;
- declared in preview v1.

activation_reforecast
- changes activation timing or milestone;
- declared in preview v1.

mixed_reforecast
- combines multiple layers;
- active_partial in preview v1.
```

Formula reforecast must always be versioned.

Example:

```txt
formulaKey: logistics.effective_freight_cost
formulaVersionFrom: 1.0.0
formulaVersionTo: 1.1.0
formulaPolicyFrom: proxy_pickup_adjusted_freight_scaled_by_ramp
formulaPolicyTo: weighted_frenet_loggi_erp_hub_mix_when_integrations_are_mature
runtimeSupport: declared
```

This lets the DGE state that a future reforecast may require changing the calculation logic itself, not only changing a numeric premise.
