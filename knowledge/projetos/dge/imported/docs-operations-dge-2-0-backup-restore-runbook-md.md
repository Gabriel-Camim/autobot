---
title: DGE fonte - DGE 2.0 Backup And Restore Drill Runbook
category: projetos
tags:
- dge
- fonte-original
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/operations/dge-2.0-backup-restore-runbook.md.'
source_path: docs/operations/dge-2.0-backup-restore-runbook.md
---

# DGE 2.0 Backup And Restore Drill Runbook

Fonte original DGE 2.0: `docs/operations/dge-2.0-backup-restore-runbook.md`.

---

# DGE 2.0 Backup And Restore Drill Runbook

## Scope

This runbook applies only to the exclusive DGE 2.0 backend and its PostgreSQL database. The frozen pilot is outside this readiness surface.

Initial controlled-pilot recovery target:

```txt
RPO: 24 hours
RTO: 4 hours
```

RPO is the maximum acceptable data interval between backups. RTO is the maximum acceptable time to restore an isolated usable database.

## Docker Ephemeral Drill

The default adapter uses `pgvector/pgvector:pg16`, because the DGE 2.0 database requires the `vector` PostgreSQL extension. It creates a real dump, restores into a temporary PostgreSQL container, verifies invariants and critical counts, records sanitized evidence, and removes the container.

```powershell
npm run backup:create:dge2
npm run backup:restore-drill:dge2
npm run smoke:docker-restore-drill-verified
```

Required configuration:

```txt
DGE_BACKUP_ADAPTER=docker_postgres_ephemeral
DGE_DOCKER_POSTGRES_IMAGE=pgvector/pgvector:pg16
DGE_BACKUP_DIR=.local/dge-backups
DGE_RECOVERY_RPO_HOURS=24
DGE_RECOVERY_RTO_HOURS=4
```

## Verification

A drill is `verified` only when:

- the temporary database differs from the canonical database;
- migrations and checksums match;
- inventory invariants remain green;
- critical table counts match;
- duration stays within RTO;
- the temporary container is removed.

Evidence never stores raw DSNs or passwords.

## Failure Codes

- `docker_unavailable`
- `backup_create_failed`
- `restore_container_start_failed`
- `restore_failed`
- `restore_verification_failed`
- `restore_cleanup_failed`
- `restore_drill_canonical_database_refused`

Any failed drill remains an explicit production-readiness blocker until a later drill is verified.
