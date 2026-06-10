---
title: DGE fonte - DGE 2.0 Automation Backbone
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-automation-backbone.md.'
source_path: docs/architecture/dge-2.0-automation-backbone.md
---

# DGE 2.0 Automation Backbone

Fonte original DGE 2.0: `docs/architecture/dge-2.0-automation-backbone.md`.

---

# DGE 2.0 Automation Backbone

## Purpose

The automation backbone records what automations exist, when they run, what they processed, which steps happened, and which webhook payloads arrived.

n8n may orchestrate outside the DGE, but the DGE keeps the official trace.

## Active Tables

```txt
automation_registry
automation_runs
automation_run_steps
automation_webhook_events
```

## Active Endpoints

```txt
GET /api/automations/registry
POST /api/automations/runs
GET /api/automations/runs
POST /api/automations/runs/:id/steps
POST /api/automations/webhook-events
GET /api/automations/webhook-events
```

## Seeded Automations

```txt
daily_kpi_manual_reminder
bling_inventory_daily_import
bling_sales_daily_import
daily_operational_report_dispatch
exception_alert_dispatch
weekly_health_report
monthly_operational_close
```

## Canonical Executor

```txt
system_automation_n8n
```

The automation actor can submit or import facts. It should not replace final human approval.

## Run Trace

Automation runs should record:

```txt
automation_key
run_date
status
started_by
records_processed
facts_created
approval_requests_created
exceptions_created
error_code
error_message
metadata
```

Run steps should record canonical stages such as:

```txt
fetch_payload
normalize_payload
persist_fact
create_approval
materialize_exception
dispatch_report
```

## Webhook Events

Webhook events are idempotent by:

```txt
project_id + provider + payload_hash
```

This allows n8n to retry safely without duplicating the DGE trace.
