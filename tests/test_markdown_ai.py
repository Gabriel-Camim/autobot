from pathlib import Path

import pytest

import markdown_ai
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


def test_markdown_ai_session_and_fallback_generation(monkeypatch, tmp_path: Path):
    settings = _settings(tmp_path)
    monkeypatch.setattr(markdown_ai, "_build_llm", lambda _settings: (_ for _ in ()).throw(RuntimeError("offline")))

    session = markdown_ai.create_session(
        settings,
        mode="create",
        path="knowledge/projetos/teste.md",
        base_content="",
    )
    generated = markdown_ai.generate_version(
        settings,
        session["id"],
        instruction="Adicionar um resumo sobre automações com dados.",
    )

    assert generated["selected_version_id"]
    assert generated["versions"][0]["payload"]["fallback"] is True
    assert "automações com dados" in generated["versions"][0]["content"]

    used = markdown_ai.use_version(settings, generated["selected_version_id"])

    assert used["version"]["id"] == generated["selected_version_id"]
    assert used["session"]["selected_version_id"] == generated["selected_version_id"]


def test_markdown_ai_private_attachment_is_context_markdown(tmp_path: Path):
    settings = _settings(tmp_path)
    session = markdown_ai.create_session(
        settings,
        mode="edit",
        path="knowledge/gabriel/perfil.md",
        base_content="# Perfil",
    )

    attachment = markdown_ai.prepare_attachment(
        settings,
        session["id"],
        filename="contexto.txt",
        content_type="text/plain",
        data="Contexto externo para curadoria.".encode("utf-8"),
    )
    markdown = markdown_ai.attachment_markdown(attachment)
    updated = markdown_ai.save_attachment(settings, attachment, commit_sha="abc1234")

    assert "visibility: context" in markdown
    assert "knowledge/_context/markdown-ai/" in attachment["git_path"]
    assert updated["attachments"][0]["git_commit_sha"] == "abc1234"


def test_markdown_ai_attachment_limit_is_enforced(tmp_path: Path):
    settings = _settings(tmp_path)
    session = markdown_ai.create_session(
        settings,
        mode="create",
        path="knowledge/teste.md",
        base_content="",
    )

    for index in range(markdown_ai.MAX_ATTACHMENTS):
        attachment = markdown_ai.prepare_attachment(
            settings,
            session["id"],
            filename=f"contexto-{index}.txt",
            content_type="text/plain",
            data=f"Contexto {index}".encode("utf-8"),
        )
        markdown_ai.save_attachment(settings, attachment, commit_sha=f"sha{index}")

    extra = markdown_ai.prepare_attachment(
        settings,
        session["id"],
        filename="extra.txt",
        content_type="text/plain",
        data=b"extra",
    )

    with pytest.raises(Exception, match="Limite de 5 anexos"):
        markdown_ai.save_attachment(settings, extra, commit_sha="sha-extra")
