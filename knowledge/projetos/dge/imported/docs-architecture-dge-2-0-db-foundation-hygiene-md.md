---
title: DGE fonte - DGE 2.0 DB Foundation Hygiene
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-db-foundation-hygiene.md.'
source_path: docs/architecture/dge-2.0-db-foundation-hygiene.md
---

# DGE 2.0 DB Foundation Hygiene

Fonte original DGE 2.0: `docs/architecture/dge-2.0-db-foundation-hygiene.md`.

---

# DGE 2.0 DB Foundation Hygiene

## Migration Order

Official setup order:

1. Core foundation schema.
2. Retrieval and auxiliary schemas.
3. Operational schema.
4. Indexes, constraints and updated_at triggers.
5. BI semantic views.
6. Module registry and seed data.

`schema-dge-2.sql` remains the operational schema for the current local setup, but core-owned tables must not be reintroduced there as new duplicated declarations.

## Controlled Debt

Some duplicated `create table if not exists` declarations still exist for compatibility while the DGE 2.0 backbone is being consolidated. The check `npm run check:db-foundation-hygiene` reports these as controlled debt and fails only on new uncontrolled duplicate table declarations.

Current controlled duplicates:

- `operational_nodes`
- `tenant_users`
- `tenant_user_roles`
- `tenant_user_node_assignments`
- `tenant_user_responsibilities`
- `approval_workflows`
- `approval_requests`
- `approval_decisions`

## Catalog Boundary

Canonical catalog:

- `erp_products`
- `erp_product_variants`

Compatibility/read model:

- `products`

New operational development must use the ERP catalog. The legacy `products` table remains only for compatibility until a migration pass removes old dependencies.

## Numeric Policy

Financial columns should graduate toward explicit precision:

- currency amounts: `numeric(14,2)`;
- rates, ratios and coefficients: `numeric(18,4)`;
- experimental imported payloads may stay in JSONB until promoted.

## updated_at Policy

Tables with `updated_at` should use a shared trigger policy before production hardening. V1 is report-only so the current local schema remains compatible.
