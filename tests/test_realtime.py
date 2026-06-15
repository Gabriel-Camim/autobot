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
    assert session_payload["audio"]["output"]["voice"] == "cedar"
    assert {tool["name"] for tool in session_payload["tools"]} == {"search_gabriel_knowledge", "get_gabriel_dossier"}
    assert "sk-test-secret" not in answer


def test_sideband_session_update_includes_required_session_type(tmp_path):
    settings = make_settings(tmp_path)

    event = realtime._sideband_session_update(settings, "stack")

    assert event["type"] == "session.update"
    assert event["session"]["type"] == "realtime"
    assert event["session"]["tool_choice"] == "auto"
    assert {tool["name"] for tool in event["session"]["tools"]} == {
        "search_gabriel_knowledge",
        "get_gabriel_dossier",
    }


def test_sideband_tool_output_does_not_force_duplicate_response(monkeypatch, tmp_path):
    sent_events = []

    class FakeWs:
        def send(self, payload):
            sent_events.append(json.loads(payload))

    settings = make_settings(tmp_path)
    context = realtime.RealtimeCallContext(
        call_id="call-1",
        session_id="session-1",
        visitor_id="visitor-1",
        active_context="stack",
        started_at=0,
    )
    monkeypatch.setattr(
        realtime,
        "_execute_tool",
        lambda *_args, **_kwargs: {"status": "ok", "retrieved_docs": 1, "sources": ["knowledge/skills/stack.md"]},
    )
    monkeypatch.setattr(realtime, "log_event", lambda *_args, **_kwargs: None)

    realtime._handle_sideband_event(
        FakeWs(),
        settings,
        context,
        {
            "type": "response.output_item.done",
            "item": {
                "type": "function_call",
                "name": "search_gabriel_knowledge",
                "call_id": "tool-call-1",
                "arguments": json.dumps({"query": "stack"}),
            },
        },
    )

    assert [event["type"] for event in sent_events] == ["conversation.item.create"]
    assert sent_events[0]["item"]["type"] == "function_call_output"
    assert sent_events[0]["item"]["call_id"] == "tool-call-1"


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
