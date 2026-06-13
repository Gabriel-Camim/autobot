from pathlib import Path

import pytest
from starlette.requests import Request

from admin import _admin_redirect_with_token, _current_admin, _github_oauth_token_error, _read_session_token, _resolve_content_path, _session_token
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


def test_admin_accepts_bearer_session_token(tmp_path: Path):
    settings = make_settings(tmp_path)
    token = _session_token({"login": "Gabriel-Camim", "name": "Gabriel", "avatar_url": None}, settings)
    request = Request({"type": "http", "headers": [(b"authorization", f"Bearer {token}".encode("utf-8"))]})

    user = _current_admin(request, settings)

    assert user is not None
    assert user.login == "Gabriel-Camim"


def test_admin_redirect_puts_session_token_in_fragment(tmp_path: Path):
    settings = make_settings(tmp_path)
    settings.public_frontend_url = "https://frontend.example.com"

    redirect_url = _admin_redirect_with_token(settings, "signed-token")

    assert redirect_url == "https://frontend.example.com/admin#admin_token=signed-token"


def test_system_prompt_loads_from_file_and_falls_back(tmp_path: Path):
    prompt_path = tmp_path / "system.md"
    prompt_path.write_text("Prompt customizado com acentuação.", encoding="utf-8")
    settings = Settings(_env_file=None, SYSTEM_PROMPT_PATH=prompt_path)

    assert load_system_prompt(settings) == "Prompt customizado com acentuação."

    missing_settings = Settings(_env_file=None, SYSTEM_PROMPT_PATH=tmp_path / "missing.md")
    assert load_system_prompt(missing_settings) == FALLBACK_SYSTEM_PROMPT


def test_github_oauth_token_error_includes_provider_reason():
    payload = {
        "error": "incorrect_client_credentials",
        "error_description": "The client_id and/or client_secret passed are incorrect.",
    }

    message = _github_oauth_token_error(payload, 200)

    assert "incorrect_client_credentials" in message
    assert "client_secret" in message
