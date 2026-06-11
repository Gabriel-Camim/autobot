from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Request

from config import Settings


logger = logging.getLogger("gabriel_events")
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uses_postgres(settings: Settings) -> bool:
    return bool(settings.database_url.strip())


def _storage_backend(settings: Settings) -> str:
    return "postgres" if _uses_postgres(settings) else "sqlite"


def _storage_error(settings: Settings, exc: Exception) -> Dict[str, Any]:
    return {"backend": _storage_backend(settings), "ok": False, "error": str(exc)[:240]}


def _sqlite_connect(settings: Settings) -> sqlite3.Connection:
    db_path = settings.resolved_events_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            kind TEXT NOT NULL,
            visitor_id TEXT,
            session_id TEXT,
            actor_type TEXT,
            path TEXT,
            ip_hash TEXT,
            user_agent TEXT,
            payload_json TEXT NOT NULL
        )
        """
    )
    _sqlite_ensure_column(conn, "visitor_id")
    _sqlite_ensure_column(conn, "actor_type")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_visitor_id ON events(visitor_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id)")
    return conn


def _sqlite_ensure_column(conn: sqlite3.Connection, column: str) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(events)").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE events ADD COLUMN {column} TEXT")


def _postgres_connect(settings: Settings):
    database_url = settings.database_url.strip()
    if not database_url.startswith(("postgres://", "postgresql://")):
        raise RuntimeError(
            "DATABASE_URL deve ser a Internal Database URL do Postgres no Render, começando com postgresql:// ou postgres://."
        )

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("psycopg is required when DATABASE_URL is configured") from exc

    conn = psycopg.connect(database_url, row_factory=dict_row, autocommit=True)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL,
            kind TEXT NOT NULL,
            visitor_id TEXT,
            session_id TEXT,
            actor_type TEXT,
            path TEXT,
            ip_hash TEXT,
            user_agent TEXT,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_visitor_id ON events(visitor_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id)")
    return conn


def _connect(settings: Settings):
    if _uses_postgres(settings):
        return _postgres_connect(settings)
    return _sqlite_connect(settings)


def _client_ip(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _hash_ip(ip: Optional[str], settings: Settings) -> Optional[str]:
    if not ip:
        return None
    secret = settings.admin_session_secret or settings.openai_api_key or "gabriel-agent"
    return hashlib.sha256(f"{secret}:{ip}".encode("utf-8")).hexdigest()[:32]


def _safe_json(payload: Optional[Dict[str, Any]]) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":"), default=str)


def init_events_db(settings: Settings) -> None:
    with _lock:
        with _connect(settings):
            pass


def event_storage_status(settings: Settings) -> Dict[str, Any]:
    try:
        init_events_db(settings)
        return {"backend": _storage_backend(settings), "ok": True, "error": None}
    except Exception as exc:
        logger.exception("event_storage_unavailable")
        return _storage_error(settings, exc)


def log_event(
    settings: Settings,
    kind: str,
    *,
    request: Optional[Request] = None,
    visitor_id: Optional[str] = None,
    session_id: Optional[str] = None,
    actor_type: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    payload = payload or {}
    path = str(request.url.path) if request else None
    user_agent = request.headers.get("user-agent", "")[:420] if request else None
    ip_hash = _hash_ip(_client_ip(request), settings)
    row = (
        str(uuid4()),
        _now(),
        kind,
        visitor_id,
        session_id,
        actor_type or "visitor",
        path,
        ip_hash,
        user_agent,
        _safe_json(payload),
    )

    try:
        with _lock:
            with _connect(settings) as conn:
                if _uses_postgres(settings):
                    conn.execute(
                        """
                        INSERT INTO events
                        (id, created_at, kind, visitor_id, session_id, actor_type, path, ip_hash, user_agent, payload_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        row,
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO events
                        (id, created_at, kind, visitor_id, session_id, actor_type, path, ip_hash, user_agent, payload_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        row,
                    )
    except Exception:
        logger.exception("event_log_failed")


def list_events(
    settings: Settings,
    *,
    limit: int = 100,
    kind: Optional[str] = None,
    visitor_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 500))
    params: List[Any] = []
    where: List[str] = []
    if kind:
        where.append("kind = ?")
        params.append(kind)
    if visitor_id:
        where.append("visitor_id = ?")
        params.append(visitor_id)

    placeholder = "?" if not _uses_postgres(settings) else "%s"
    query = "SELECT * FROM events"
    if where:
        query += " WHERE " + " AND ".join(clause.replace("?", placeholder) for clause in where)
    query += f" ORDER BY created_at DESC LIMIT {placeholder}"
    params.append(limit)

    try:
        with _lock:
            with _connect(settings) as conn:
                rows = conn.execute(query, params).fetchall()
    except Exception as exc:
        logger.exception("event_list_failed")
        return [
            {
                "id": "event-storage-error",
                "created_at": _now(),
                "kind": "event_storage_error",
                "visitor_id": None,
                "session_id": None,
                "actor_type": "system",
                "path": None,
                "ip_hash": None,
                "user_agent": None,
                "payload": {
                    "error": "Não consegui ler o banco de eventos. Verifique DATABASE_URL no Render.",
                    "storage": _storage_error(settings, exc),
                },
            }
        ]

    events: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            row = dict(row)
        try:
            payload = json.loads(row.get("payload_json") or "{}")
        except json.JSONDecodeError:
            payload = {}
        events.append(
            {
                "id": row.get("id"),
                "created_at": str(row.get("created_at")),
                "kind": row.get("kind"),
                "visitor_id": row.get("visitor_id"),
                "session_id": row.get("session_id"),
                "actor_type": row.get("actor_type") or "visitor",
                "path": row.get("path"),
                "ip_hash": row.get("ip_hash"),
                "user_agent": row.get("user_agent"),
                "payload": payload,
            }
        )
    return events


def event_summary(settings: Settings, *, hours: int = 168) -> Dict[str, Any]:
    hours = max(1, min(hours, 24 * 90))
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    placeholder = "%s" if _uses_postgres(settings) else "?"

    try:
        with _lock:
            with _connect(settings) as conn:
                rows = conn.execute(
                    f"SELECT kind, COUNT(*) AS total FROM events WHERE created_at >= {placeholder} GROUP BY kind",
                    (since,),
                ).fetchall()
                visitor_rows = conn.execute(
                    f"""
                    SELECT DISTINCT COALESCE(visitor_id, ip_hash) AS visitor_key
                    FROM events
                    WHERE created_at >= {placeholder}
                      AND kind = 'site_visit'
                      AND COALESCE(visitor_id, ip_hash) IS NOT NULL
                    """,
                    (since,),
                ).fetchall()
                identified_rows = conn.execute(
                    f"""
                    SELECT DISTINCT visitor_id
                    FROM events
                    WHERE created_at >= {placeholder}
                      AND visitor_id IS NOT NULL
                      AND payload_json LIKE '%"identity"%'
                    """,
                    (since,),
                ).fetchall()
    except Exception as exc:
        logger.exception("event_summary_failed")
        return {
            "hours": hours,
            "storage": _storage_error(settings, exc),
            "total_events": 0,
            "by_kind": {},
            "visits": 0,
            "unique_visitors": 0,
            "identified_visitors": 0,
            "chat_exchanges": 0,
            "downloads": 0,
            "admin_actions": 0,
            "errors": 1,
        }

    normalized_rows = [row if isinstance(row, dict) else dict(row) for row in rows]
    by_kind = {row["kind"]: int(row["total"]) for row in normalized_rows}
    return {
        "hours": hours,
        "storage": event_storage_status(settings),
        "total_events": sum(by_kind.values()),
        "by_kind": by_kind,
        "visits": by_kind.get("site_visit", 0),
        "unique_visitors": len(visitor_rows),
        "identified_visitors": len(identified_rows),
        "chat_exchanges": by_kind.get("chat_exchange", 0) + by_kind.get("voice_chat_exchange", 0),
        "downloads": by_kind.get("material_download", 0),
        "admin_actions": sum(count for kind, count in by_kind.items() if kind.startswith("admin_")),
        "errors": sum(count for kind, count in by_kind.items() if "error" in kind),
    }
