from pathlib import Path

import pytest

from agent import AppError
from config import Settings
from draft_studio import add_attachment, create_draft, get_draft, list_drafts


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
