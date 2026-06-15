import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
import realtime
from agent import AppError
from config import Settings
from realtime import create_realtime_call


def make_settings(tmp_path: Path, **overrides):
    defaults = {
        "_env_file": None,
        "OPENAI_API_KEY": "sk-test-secret",
        "REALTIME_ENABLED": True,
        "DATA_DIR": tmp_path,
        "EVENTS_DB_PATH": tmp_path / "events.sqlite3",
        "KNOWLEDGE_DIR": tmp_path / "knowledge",
        "CHROMA_DIR": tmp_path / "chroma",
        "ADMIN_SESSION_SECRET": "secret",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_realtime_call_relays_sdp_without_returning_openai_key(monkeypatch, tmp_path):
    captured = {}

    class FakeResponse:
        status_code = 200
        text = "v=0\r\nanswer"
        headers = {"location": "https://api.openai.com/v1/realtime/calls/call_test123"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, url, headers=None, files=None):
            captured["url"] = url
            captured["headers"] = headers or {}
            captured["files"] = files or {}
            return FakeResponse()

    monkeypatch.setattr(realtime.httpx, "Client", FakeClient)
    monkeypatch.setattr(realtime, "start_sideband", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(realtime, "log_event", lambda *_args, **_kwargs: None)
    settings = make_settings(tmp_path)

    answer, call_id = create_realtime_call(
        settings=settings,
        sdp_offer="v=0\r\no=- 0 0 IN IP4 127.0.0.1",
        session_id="session-1",
        visitor_id="visitor-1",
        active_context="gabriel",
    )

    assert answer == "v=0\r\nanswer"
    assert call_id == "call_test123"
    assert captured["url"] == "https://api.openai.com/v1/realtime/calls"
    assert captured["headers"]["Authorization"] == "Bearer sk-test-secret"
    assert captured["files"]["sdp"][0] is None
    assert captured["files"]["sdp"][1].startswith("v=0")
    assert captured["files"]["sdp"][2] == "application/sdp"
    session_payload = json.loads(captured["files"]["session"][1])
    assert session_payload["model"] == "gpt-realtime-2"
    assert session_payload["audio"]["output"]["voice"] == "marin"
    assert {tool["name"] for tool in session_payload["tools"]} == {"search_gabriel_knowledge", "get_gabriel_dossier"}
    assert "sk-test-secret" not in answer


def test_realtime_call_respects_feature_flag(tmp_path):
    settings = make_settings(tmp_path, REALTIME_ENABLED=False)

    with pytest.raises(AppError) as error:
        create_realtime_call(
            settings=settings,
            sdp_offer="v=0\r\no=- 0 0 IN IP4 127.0.0.1",
            session_id="session-1",
            visitor_id="visitor-1",
            active_context="gabriel",
        )

    assert error.value.code == "realtime_disabled"


def test_public_warmup_endpoint_starts_background_warmup(monkeypatch, tmp_path):
    settings = make_settings(tmp_path, OPENAI_API_KEY="")
    monkeypatch.setattr(main, "settings", settings)
    monkeypatch.setattr(main, "log_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        main,
        "start_warmup",
        lambda _settings, actor=None: {"state": "running", "actor": actor, "error": None},
    )

    client = TestClient(main.app)
    response = client.post("/warmup/public", json={"visitor_id": "visitor-1", "session_id": "session-1", "reason": "page"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["warmup_status"]["actor"] == "public:page"
