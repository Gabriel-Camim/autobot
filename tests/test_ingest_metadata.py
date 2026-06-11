from pathlib import Path

from config import Settings
from ingest import load_public_documents


def test_load_public_documents_ignores_non_public(tmp_path: Path):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "public.md").write_text(
        """---
title: Publico
category: teste
tags: [rag]
visibility: public
priority: 1
updated_at: 2026-06-09
summary: Documento público.
---
Conteúdo público.
""",
        encoding="utf-8",
    )
    (knowledge / "private.md").write_text(
        """---
title: Privado
visibility: private
---
Conteudo privado.
""",
        encoding="utf-8",
    )

    settings = Settings(
        _env_file=None,
        KNOWLEDGE_DIR=knowledge,
        CHROMA_DIR=tmp_path / "chroma",
    )

    docs = load_public_documents(settings)

    assert len(docs) == 1
    assert docs[0].metadata["title"] == "Publico"
    assert docs[0].metadata["source"] == "public.md"
