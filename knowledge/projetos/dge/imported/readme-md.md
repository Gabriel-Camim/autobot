---
title: DGE fonte - DGE 2.0
category: projetos
tags:
- dge
- fonte-original
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: README.md.'
source_path: README.md
---

# DGE 2.0

Fonte original DGE 2.0: `README.md`.

---

# DGE 2.0

Diretorio raiz dos artefatos exclusivos da DGE 2.0.

Tudo que for novo backbone, arquitetura, contratos, banco, modulos, scripts de validacao, entregaveis tecnicos e planos de produto da DGE 2.0 deve nascer aqui.

Durante a transicao, alguns arquivos executaveis ainda podem permanecer na raiz historica do projeto para nao quebrar imports, scripts npm e smoke tests. Esses arquivos devem ser migrados em etapas controladas, com manifestos de origem/destino e validacao apos cada lote.

Estrutura-alvo:

- `docs/architecture`: blueprints e decisoes de arquitetura da DGE 2.0.
- `docs/contracts`: contratos operacionais, contratos de leitura/escrita e diretrizes de integracao.
- `docs/operations`: operacao, implantacao, auditoria e rotinas.
- `docs/database`: modelagem, MER, Postgres e RAI persistence.
- `db`: schemas e scripts de setup/import especificos da DGE 2.0.
- `server`: modulos backend, contratos e servicos especificos da DGE 2.0.
- `scripts`: smoke tests e validadores especificos da DGE 2.0.
- `deliverables`: documentos, PDFs, assets e materiais finais da DGE 2.0.
