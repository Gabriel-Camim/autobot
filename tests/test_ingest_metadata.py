from pathlib import Path

from ingest import _reset_chroma_dir
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
    reports = knowledge / "reports"
    reports.mkdir()
    (reports / "stack.md").write_text(
        """---
title: Relatorio Stack
category: reports
visibility: public
---
Conteudo estatico para o botao play, fora do RAG.
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


def test_reset_chroma_allows_temp_directory(tmp_path: Path):
    chroma_dir = tmp_path / "gabriel-agent" / "chroma"
    chroma_dir.mkdir(parents=True)
    (chroma_dir / "old.sqlite3").write_text("old", encoding="utf-8")
    settings = Settings(_env_file=None, CHROMA_DIR=chroma_dir)

    _reset_chroma_dir(settings)

    assert chroma_dir.exists()
    assert not (chroma_dir / "old.sqlite3").exists()
    (chroma_dir / "new.sqlite3").write_text("new", encoding="utf-8")
    assert (chroma_dir / "new.sqlite3").exists()
