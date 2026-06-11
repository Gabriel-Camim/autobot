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


def _connect(settings: Settings) -> sqlite3.Connection:
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
            session_id TEXT,
            path TEXT,
            ip_hash TEXT,
            user_agent TEXT,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind)")
    return conn


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


def log_event(
    settings: Settings,
    kind: str,
    *,
    request: Optional[Request] = None,
    session_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    payload = payload or {}
    path = str(request.url.path) if request else None
    user_agent = request.headers.get("user-agent", "")[:320] if request else None
    ip_hash = _hash_ip(_client_ip(request), settings)
    row = (
        str(uuid4()),
        _now(),
        kind,
        session_id,
        path,
        ip_hash,
        user_agent,
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )

    try:
        with _lock:
            with _connect(settings) as conn:
                conn.execute(
                    """
                    INSERT INTO events (id, created_at, kind, session_id, path, ip_hash, user_agent, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
    except Exception:
        logger.exception("event_log_failed")


def list_events(settings: Settings, *, limit: int = 100, kind: Optional[str] = None) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 500))
    query = "SELECT * FROM events"
    params: List[Any] = []
    if kind:
        query += " WHERE kind = ?"
        params.append(kind)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with _lock:
        with _connect(settings) as conn:
            rows = conn.execute(query, params).fetchall()

    events: List[Dict[str, Any]] = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        events.append(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "kind": row["kind"],
                "session_id": row["session_id"],
                "path": row["path"],
                "ip_hash": row["ip_hash"],
                "user_agent": row["user_agent"],
                "payload": payload,
            }
        )
    return events


def event_summary(settings: Settings, *, hours: int = 168) -> Dict[str, Any]:
    hours = max(1, min(hours, 24 * 90))
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    with _lock:
        with _connect(settings) as conn:
            rows = conn.execute(
                "SELECT kind, COUNT(*) AS total FROM events WHERE created_at >= ? GROUP BY kind",
                (since,),
            ).fetchall()
            visitor_rows = conn.execute(
                """
                SELECT DISTINCT ip_hash
                FROM events
                WHERE created_at >= ? AND kind = 'site_visit' AND ip_hash IS NOT NULL
                """,
                (since,),
            ).fetchall()

    by_kind = {row["kind"]: int(row["total"]) for row in rows}
    return {
        "hours": hours,
        "total_events": sum(by_kind.values()),
        "by_kind": by_kind,
        "visits": by_kind.get("site_visit", 0),
        "unique_visitors": len(visitor_rows),
        "chat_exchanges": by_kind.get("chat_exchange", 0) + by_kind.get("voice_chat_exchange", 0),
        "admin_actions": sum(count for kind, count in by_kind.items() if kind.startswith("admin_")),
        "errors": sum(count for kind, count in by_kind.items() if "error" in kind),
    }
