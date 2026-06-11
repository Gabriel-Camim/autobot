from pathlib import Path

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
