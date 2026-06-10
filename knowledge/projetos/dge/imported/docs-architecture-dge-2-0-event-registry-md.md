---
title: DGE fonte - DGE 2.0 Event Registry
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-event-registry.md.'
source_path: docs/architecture/dge-2.0-event-registry.md
---

# DGE 2.0 Event Registry

Fonte original DGE 2.0: `docs/architecture/dge-2.0-event-registry.md`.

---

# DGE 2.0 Event Registry

## Purpose

The timeline is the official chronological trace of DGE facts, decisions, exceptions, and resolutions.

The event registry defines which event types exist, which module owns them, which metadata is expected, and which events may be materialized idempotently by jobs or automations.

## Active Endpoint

```txt
GET /api/timeline/event-registry
```

## Registry Fields

```txt
key
domain
description
sourceModule
defaultSeverity
materializable
idempotencyKey
expectedMetadata
```

## Materializable Events

Materializable events can be created by system routines, smoke scripts, n8n jobs, or future internal automation without creating duplicate noise.

Current materializable examples:

```txt
daily_kpi_snapshot_missing
operational_exception
operational_exception_resolved
```

## Guardrails

- New timeline event types must be added to the registry before use.
- Materialized events should define an idempotency key.
- Generic `timeline_event` is allowed only for modules that do not yet have a specialized event type.
- Automation should create facts and traces; human governance still approves audited operational truth.
