---
title: DGE fonte - DGE 2.0 Financial Operations Runtime Core v1
category: projetos
tags:
- dge
- fonte-original
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/operations/dge-2.0-financial-operations-runbook.md.'
source_path: docs/operations/dge-2.0-financial-operations-runbook.md
---

# DGE 2.0 Financial Operations Runtime Core v1

Fonte original DGE 2.0: `docs/operations/dge-2.0-financial-operations-runbook.md`.

---

# DGE 2.0 Financial Operations Runtime Core v1

## Boundary

The DGE financial runtime is an operational managerial subledger. It records obligations, installments, observed settlements, human-reviewed reconciliation, reconciled cash, budgets and financial intelligence. It does not replace official accounting, official tax assessment or an external fiscal provider.

## Core Invariants

- A confirmed order may create a receivable. It does not create bank cash.
- An observed payment creates a pending settlement. It does not create reconciled cash.
- Every accepted reconciliation match requires human review and evidence.
- Every posted managerial journal balances debit and credit.
- Posted ledger entries are immutable. Corrections use reversal journals.
- Closed monthly periods reject silent retroactive writes.
- Financial writes use an idempotent `commandKey`.
- `system_integration` may submit governed facts and drafts. It cannot accept reconciliation matches, close periods, reverse journals or write off debt.

## Main Flow

```txt
operational fact
-> idempotent command
-> title
-> installments
-> balanced managerial journal
-> observed settlement
-> imported statement preview
-> normalized statement lines
-> scored reconciliation candidates
-> mandatory human review
-> reconciled cash
-> financial KPI and projection-impact preview
```

## Statement Imports

CSV and OFX imports use route-scoped memory uploads. The raw file is not stored. The runtime persists SHA-256, sanitized preview, normalized lines, actor and audit metadata. Reusing the same content hash is blocked.

## Monthly Close

`POST /api/finance/periods/:monthKey/close` closes a managerial period. Any later correction must reverse the original posting and create a new journal in an open period.

## Accounting Export

`POST /api/finance/exports/accounting-package` generates a versioned JSON package with journals, ledger entries, titles, installments, settlements, reviewed matches and source links. This package is evidence for an accountant or future provider adapter; it is not official bookkeeping.
