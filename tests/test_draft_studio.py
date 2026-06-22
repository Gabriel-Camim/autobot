from pathlib import Path

import pytest

from agent import AppError
from config import Settings
from draft_studio import (
    add_attachment,
    add_targets_to_case,
    create_curation_case,
    create_draft,
    get_curation_case,
    get_draft,
    ignore_case_draft,
    list_canonical_documents,
    list_drafts,
    record_case_reindex,
    resolve_curation_case,
)


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        EVENTS_DB_PATH=tmp_path / "events.sqlite3",
        KNOWLEDGE_DIR=tmp_path / "knowledge",
        MATERIALS_DIR=tmp_path / "materials" / "recruiter-pack",
    )


def test_create_draft_uses_private_draft_path(tmp_path: Path):
    settings = make_settings(tmp_path)

    draft = create_draft(
        settings,
        {
            "title": "Refinar Ebook Generator",
            "instruction": "Adicionar contexto sobre pipeline editorial.",
            "suggested_path": "knowledge/projetos/ebookgenerator/refino.md",
        },
    )

    assert draft["suggested_path"].startswith("knowledge/_drafts/")
    assert "visibility: draft" in draft["draft_markdown"]
    assert list_drafts(settings)[0]["id"] == draft["id"]


def test_attachment_extracts_txt_and_json(tmp_path: Path):
    settings = make_settings(tmp_path)
    draft = create_draft(settings, {"title": "Draft com anexos", "instruction": "Usar anexos."})

    txt = add_attachment(
        settings,
        draft["id"],
        filename="contexto.txt",
        content_type="text/plain",
        data="Stack real: Python, FastAPI e pgvector.".encode("utf-8"),
    )
    json_attachment = add_attachment(
        settings,
        draft["id"],
        filename="base.json",
        content_type="application/json",
        data=b'{"projeto":"Ebook Generator","stack":["n8n","OpenAI"]}',
    )
    hydrated = get_draft(settings, draft["id"], include_related=True)

    assert "Python" in txt["extracted_text"]
    assert "Ebook Generator" in json_attachment["extracted_text"]
    assert len(hydrated["attachments"]) == 2


def test_attachment_rejects_unsupported_file(tmp_path: Path):
    settings = make_settings(tmp_path)
    draft = create_draft(settings, {"title": "Draft seguro", "instruction": "Validar anexo."})

    with pytest.raises(AppError) as exc:
        add_attachment(
            settings,
            draft["id"],
            filename="planilha.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            data=b"xlsx",
        )

    assert exc.value.code == "unsupported_attachment"


def write_public_md(settings: Settings, relative: str, title: str = "Doc") -> Path:
    path = settings.resolved_knowledge_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
title: {title}
category: teste
tags:
  - teste
visibility: public
priority: 2
updated_at: '2026-06-22'
summary: Documento de teste.
---

# {title}

Conteúdo público.
""",
        encoding="utf-8",
    )
    return path


def test_curation_case_creates_child_drafts_for_targets(tmp_path: Path):
    settings = make_settings(tmp_path)
    write_public_md(settings, "skills/hard-skills.md", "Hard Skills")
    write_public_md(settings, "projetos/autobot/overview.md", "Autobot")

    case = create_curation_case(
        settings,
        {
            "title": "Atualizar stack",
            "instruction": "Refinar stack real.",
            "target_paths": ["knowledge/skills/hard-skills.md", "knowledge/projetos/autobot/overview.md"],
        },
    )

    hydrated = get_curation_case(settings, case["id"])
    assert hydrated["status"] == "targets_selected"
    assert len(hydrated["drafts"]) == 2
    assert {draft["target_path"] for draft in hydrated["drafts"]} == {
        "knowledge/skills/hard-skills.md",
        "knowledge/projetos/autobot/overview.md",
    }


def test_canonical_documents_excludes_drafts(tmp_path: Path):
    settings = make_settings(tmp_path)
    write_public_md(settings, "skills/hard-skills.md", "Hard Skills")
    write_public_md(settings, "_drafts/rascunho.md", "Draft")

    docs = list_canonical_documents(settings)

    assert [doc["path"] for doc in docs] == ["knowledge/skills/hard-skills.md"]


def test_case_resolution_requires_reindex_after_docs_done(tmp_path: Path):
    settings = make_settings(tmp_path)
    write_public_md(settings, "skills/hard-skills.md", "Hard Skills")
    case = create_curation_case(
        settings,
        {"title": "Caso", "instruction": "Teste.", "target_paths": ["knowledge/skills/hard-skills.md"]},
    )
    draft_id = case["drafts"][0]["id"]
    ignore_case_draft(settings, case["id"], draft_id)

    with pytest.raises(AppError) as exc:
        resolve_curation_case(settings, case["id"])
    assert exc.value.code == "curation_case_not_reindexed"

    record_case_reindex(settings, case["id"], {"state": "success", "document_count": 1, "chunk_count": 1})
    resolved = resolve_curation_case(settings, case["id"])

    assert resolved["status"] == "resolved"
