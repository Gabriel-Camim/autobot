from pathlib import Path

import pytest

from admin import _read_session_token, _resolve_content_path, _session_token
from agent import AppError, FALLBACK_SYSTEM_PROMPT, load_system_prompt
from config import Settings


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        KNOWLEDGE_DIR=tmp_path / "knowledge",
        MATERIALS_DIR=tmp_path / "materials" / "recruiter-pack",
        CHROMA_DIR=tmp_path / "chroma",
        ADMIN_SESSION_SECRET="test-secret",
        ADMIN_GITHUB_USERS="Gabriel-Camim",
    )


def test_admin_rejects_path_traversal(tmp_path: Path):
    settings = make_settings(tmp_path)

    with pytest.raises(AppError) as exc:
        _resolve_content_path("knowledge/../.env", settings)

    assert exc.value.code == "invalid_path"


def test_admin_accepts_markdown_inside_allowed_roots(tmp_path: Path):
    settings = make_settings(tmp_path)

    normalized, target = _resolve_content_path("knowledge/gabriel/perfil.md", settings)

    assert normalized == "knowledge/gabriel/perfil.md"
    assert target == (tmp_path / "knowledge" / "gabriel" / "perfil.md").resolve()


def test_admin_session_is_signed_and_limited_to_allowed_users(tmp_path: Path):
    settings = make_settings(tmp_path)
    token = _session_token({"login": "Gabriel-Camim", "name": "Gabriel", "avatar_url": None}, settings)

    user = _read_session_token(token, settings)

    assert user is not None
    assert user.login == "Gabriel-Camim"
    assert _read_session_token(token + "tamper", settings) is None


def test_system_prompt_loads_from_file_and_falls_back(tmp_path: Path):
    prompt_path = tmp_path / "system.md"
    prompt_path.write_text("Prompt customizado com acentuação.", encoding="utf-8")
    settings = Settings(_env_file=None, SYSTEM_PROMPT_PATH=prompt_path)

    assert load_system_prompt(settings) == "Prompt customizado com acentuação."

    missing_settings = Settings(_env_file=None, SYSTEM_PROMPT_PATH=tmp_path / "missing.md")
    assert load_system_prompt(missing_settings) == FALLBACK_SYSTEM_PROMPT
