from pathlib import Path

import pytest

import rag_quality
import rag_studio
from agent import AppError
from config import Settings


def _settings(tmp_path: Path) -> Settings:
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    return Settings(
        _env_file=None,
        EVENTS_DB_PATH=tmp_path / "events.sqlite3",
        KNOWLEDGE_DIR=knowledge,
        DATABASE_URL="",
        OPENAI_API_KEY="",
    )


def _write_md(base: Path, relative: str, title: str = "Hard skills") -> Path:
    path = base / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
title: {title}
category: skills
tags:
  - stack
visibility: public
priority: 1
summary: Documento de teste.
---

# {title}

Python, SQL, FastAPI e LangChain.
""",
        encoding="utf-8",
    )
    return path


def test_create_manual_proposal_and_add_document(tmp_path: Path):
    settings = _settings(tmp_path)
    _write_md(settings.resolved_knowledge_dir, "skills/hard-skills.md")

    proposal = rag_studio.create_proposal(
        settings,
        {
            "title": "Corrigir stack",
            "problem_statement": "A resposta precisa recuperar hard skills.",
            "question": "Quais hard skills?",
        },
    )
    proposal = rag_studio.add_documents(settings, proposal["id"], ["knowledge/skills/hard-skills.md"])

    assert proposal["status"] == "documents_selected"
    assert proposal["documents"][0]["path"] == "knowledge/skills/hard-skills.md"
    assert proposal["timeline"][2]["done"] is True


def test_feedback_creates_single_active_proposal(monkeypatch, tmp_path: Path):
    settings = _settings(tmp_path)
    trace_id = rag_quality.save_rag_trace(
        settings,
        {
            "question": "Quais hard skills?",
            "answer": "Python.",
            "active_context": "stack",
            "selected_sources": ["skills/hard-skills.md"],
        },
    )
    feedback = rag_quality.create_rag_feedback(
        settings,
        {
            "trace_id": trace_id,
            "rating": "negative",
            "reason": "missing_context",
            "comment": "Faltou citar automação.",
        },
    )["feedback"]

    first = rag_studio.create_proposal_from_feedback(settings, feedback["id"])
    second = rag_studio.create_proposal_from_feedback(settings, feedback["id"])

    assert first["created"] is True
    assert second["created"] is False
    assert first["proposal"]["id"] == second["proposal"]["id"]


def test_investigate_registers_candidates_from_probe(monkeypatch, tmp_path: Path):
    settings = _settings(tmp_path)
    _write_md(settings.resolved_knowledge_dir, "skills/hard-skills.md")
    proposal = rag_studio.create_proposal(settings, {"title": "Probe", "question": "LangChain"})

    monkeypatch.setattr(
        rag_studio,
        "build_rag_probe",
        lambda *_args, **_kwargs: {
            "question": "LangChain",
            "documents": 1,
            "evidence": [
                {
                    "source": "skills/hard-skills.md",
                    "title": "Hard skills",
                    "match_reason": "match lexical",
                    "excerpt": "LangChain aparece.",
                }
            ],
        },
    )

    updated = rag_studio.investigate_proposal(settings, proposal["id"], question="LangChain")

    assert updated["status"] == "investigating"
    assert updated["documents"][0]["path"] == "knowledge/skills/hard-skills.md"
    assert updated["events"][-1]["kind"] == "investigated"


def test_generate_patch_fallback_and_resolve_requires_validation(tmp_path: Path):
    settings = _settings(tmp_path)
    _write_md(settings.resolved_knowledge_dir, "skills/hard-skills.md")
    proposal = rag_studio.create_proposal(settings, {"title": "Patch", "question": "Stack"})
    proposal = rag_studio.add_documents(settings, proposal["id"], ["knowledge/skills/hard-skills.md"])
    document_id = proposal["documents"][0]["id"]

    updated = rag_studio.generate_patch(settings, document_id, "Adicionar metodologias ágeis quando documentado.")
    patch = updated["patches"][0]

    assert patch["status"] == "proposed"
    assert "+## Atualizacao proposta pelo RAG Studio" in patch["diff_text"]
    with pytest.raises(AppError):
        rag_studio.resolve_proposal(settings, proposal["id"])

    validated = rag_studio.record_validation(settings, proposal["id"], {"state": "success", "probe": {"documents": 1}})
    resolved = rag_studio.resolve_proposal(settings, proposal["id"])

    assert validated["status"] == "validated"
    assert resolved["status"] == "resolved"


def test_regenerated_patch_supersedes_previous_version(tmp_path: Path):
    settings = _settings(tmp_path)
    _write_md(settings.resolved_knowledge_dir, "skills/hard-skills.md")
    proposal = rag_studio.create_proposal(settings, {"title": "Patch", "question": "Stack"})
    proposal = rag_studio.add_documents(settings, proposal["id"], ["knowledge/skills/hard-skills.md"])
    document_id = proposal["documents"][0]["id"]

    first = rag_studio.generate_patch(settings, document_id, "Adicionar SQL.")
    first_patch_id = first["patches"][0]["id"]
    second = rag_studio.generate_patch(settings, document_id, "Adicionar SQL e metodologias ageis.")
    patches = second["documents"][0]["patches"]

    assert patches[0]["id"] != first_patch_id
    assert patches[0]["status"] == "proposed"
    assert patches[0]["payload"]["instruction"] == "Adicionar SQL e metodologias ageis."
    assert any(patch["id"] == first_patch_id and patch["status"] == "superseded" for patch in patches)


def test_context_document_blocks_until_indexed_and_feeds_patch(monkeypatch, tmp_path: Path):
    settings = _settings(tmp_path)
    _write_md(settings.resolved_knowledge_dir, "skills/hard-skills.md")
    proposal = rag_studio.create_proposal(settings, {"title": "Patch com contexto", "question": "Stack"})
    proposal = rag_studio.add_documents(settings, proposal["id"], ["knowledge/skills/hard-skills.md"])
    context_doc = rag_studio.add_attachment(
        settings,
        proposal["id"],
        filename="contexto.txt",
        content_type="text/plain",
        data="Metodologias ageis aparecem no documento externo.".encode("utf-8"),
    )

    with pytest.raises(AppError) as pending:
        rag_studio.generate_patch(settings, proposal["documents"][0]["id"], "Use o contexto privado para completar o contexto.")
    assert pending.value.code == "context_documents_pending"

    approved = rag_studio.approve_context_document(settings, context_doc["id"])
    assert approved["status"] == "approved"

    monkeypatch.setattr(
        rag_studio,
        "index_context_document",
        lambda _settings, document: {"indexed": True, "chunks": 1, "indexed_at": "2026-06-24T00:00:00+00:00"},
    )
    indexed = rag_studio.index_approved_context_document(settings, context_doc["id"])
    assert indexed["context_document"]["status"] == "indexed"

    monkeypatch.setattr(
        rag_studio,
        "search_context_documents",
        lambda *_args, **_kwargs: [
            {
                "context_id": context_doc["id"],
                "source": context_doc["filename"],
                "title": context_doc["title"],
                "excerpt": "Metodologias ageis aparecem no documento externo.",
                "relevance_score": 0.91,
                "channel": "private_context",
            }
        ],
    )

    updated = rag_studio.generate_patch(settings, proposal["documents"][0]["id"], "Use o contexto privado para completar o contexto.")
    patch = updated["patches"][0]

    assert context_doc["filename"] == "contexto.txt"
    assert context_doc["id"] in patch["payload"]["context_document_ids"]
    assert patch["payload"]["private_context"][0]["channel"] == "private_context"
    assert updated["context_documents"][0]["status"] == "indexed"


def test_context_document_markdown_is_private(tmp_path: Path):
    settings = _settings(tmp_path)
    proposal = rag_studio.create_proposal(settings, {"title": "Contexto", "question": "Stack"})
    context_doc = rag_studio.prepare_context_document(
        settings,
        proposal["id"],
        filename="referencia.md",
        content_type="text/markdown",
        data="# Referencia\n\nConteudo auxiliar.".encode("utf-8"),
    )
    markdown = rag_studio.context_document_markdown(context_doc)

    assert context_doc["git_path"].startswith(f"knowledge/_context/rag-studio/{proposal['id']}/")
    assert "visibility: context" in markdown
    assert "Conteudo auxiliar." in markdown
