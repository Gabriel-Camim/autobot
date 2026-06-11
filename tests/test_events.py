from pathlib import Path

import events as events_module
from config import Settings
from events import event_summary, list_events, log_event


def test_log_event_and_summary(tmp_path: Path):
    settings = Settings(
        _env_file=None,
        DATA_DIR=tmp_path,
        EVENTS_DB_PATH=tmp_path / "events.sqlite3",
        ADMIN_SESSION_SECRET="secret",
    )

    log_event(
        settings,
        "site_visit",
        visitor_id="visitor-1",
        session_id="visitor-1",
        actor_type="identified_visitor",
        payload={"path": "/", "identity": {"name": "Recrutador"}},
    )
    log_event(
        settings,
        "chat_exchange",
        visitor_id="visitor-1",
        session_id="session-1",
        payload={"question": "Oi", "answer": "Olá"},
    )

    events = list_events(settings, limit=10)
    summary = event_summary(settings, hours=24)

    assert len(events) == 2
    assert events[0]["kind"] == "chat_exchange"
    assert events[0]["visitor_id"] == "visitor-1"
    assert summary["visits"] == 1
    assert summary["identified_visitors"] == 1
    assert summary["chat_exchanges"] == 1


def test_invalid_database_url_returns_storage_diagnostic(tmp_path: Path):
    settings = Settings(
        _env_file=None,
        DATA_DIR=tmp_path,
        EVENTS_DB_PATH=tmp_path / "events.sqlite3",
        DATABASE_URL="https://dashboard.render.com/new/database",
        ADMIN_SESSION_SECRET="secret",
    )

    events = list_events(settings, limit=10)
    summary = event_summary(settings, hours=24)

    assert events[0]["kind"] == "event_storage_error"
    assert events[0]["payload"]["storage"]["ok"] is False
    assert summary["storage"]["ok"] is False
    assert summary["errors"] == 1


def test_postgres_summary_uses_parameterized_like(monkeypatch, tmp_path: Path):
    settings = Settings(
        _env_file=None,
        DATA_DIR=tmp_path,
        DATABASE_URL="postgresql://host/db",
        ADMIN_SESSION_SECRET="secret",
    )
    calls = []

    class Rows:
        def __init__(self, rows):
            self.rows = rows

        def fetchall(self):
            return self.rows

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, query, params=()):
            calls.append((query, params))
            if "GROUP BY kind" in query:
                return Rows([{"kind": "site_visit", "total": 1}])
            return Rows([])

    monkeypatch.setattr(events_module, "_connect", lambda _settings: Conn())
    monkeypatch.setattr(
        events_module,
        "event_storage_status",
        lambda _settings: {"backend": "postgres", "ok": True, "error": None},
    )

    summary = events_module.event_summary(settings, hours=24)

    identity_query, identity_params = calls[2]
    assert "payload_json LIKE %s" in identity_query
    assert len(identity_params) == 2
    assert identity_params[1] == '%"identity"%'
    assert summary["storage"]["ok"] is True
