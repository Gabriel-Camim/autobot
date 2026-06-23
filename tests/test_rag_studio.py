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
