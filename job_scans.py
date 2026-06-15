from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from config import Settings


logger = logging.getLogger("gabriel_job_scans")
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uses_postgres(settings: Settings) -> bool:
    return bool(settings.database_url.strip())


def _safe_json(payload: Optional[Dict[str, Any] | List[Any]]) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":"), default=str)


def _parse_json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback


def _sqlite_connect(settings: Settings) -> sqlite3.Connection:
    db_path = settings.resolved_events_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_scans (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL,
            job_title TEXT,
            company TEXT,
            job_description TEXT NOT NULL,
            visitor_id TEXT,
            session_id TEXT,
            visitor_identity_json TEXT NOT NULL,
            summary TEXT,
            analysis_text TEXT,
            analysis_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            sources_json TEXT NOT NULL,
            docs_json TEXT NOT NULL,
            fit_score INTEGER,
            model TEXT,
            error TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_job_scans_created_at ON job_scans(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_job_scans_status ON job_scans(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_job_scans_visitor_id ON job_scans(visitor_id)")
    return conn


def _postgres_connect(settings: Settings):
    database_url = settings.database_url.strip()
    if not database_url.startswith(("postgres://", "postgresql://")):
        raise RuntimeError("DATABASE_URL precisa apontar para Postgres para salvar vagas scaneadas.")
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("psycopg is required when DATABASE_URL is configured") from exc

    conn = psycopg.connect(database_url, row_factory=dict_row, autocommit=True)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_scans (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            status TEXT NOT NULL,
            job_title TEXT,
            company TEXT,
            job_description TEXT NOT NULL,
            visitor_id TEXT,
            session_id TEXT,
            visitor_identity_json TEXT NOT NULL,
            summary TEXT,
            analysis_text TEXT,
            analysis_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            sources_json TEXT NOT NULL,
            docs_json TEXT NOT NULL,
            fit_score INTEGER,
            model TEXT,
            error TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_job_scans_created_at ON job_scans(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_job_scans_status ON job_scans(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_job_scans_visitor_id ON job_scans(visitor_id)")
    return conn


def _connect(settings: Settings):
    return _postgres_connect(settings) if _uses_postgres(settings) else _sqlite_connect(settings)


def init_job_scans_db(settings: Settings) -> None:
    with _lock:
        with _connect(settings):
            pass


def job_scan_storage_status(settings: Settings) -> Dict[str, Any]:
    try:
        init_job_scans_db(settings)
        return {"backend": "postgres" if _uses_postgres(settings) else "sqlite", "ok": True, "error": None}
    except Exception as exc:
        logger.exception("job_scan_storage_unavailable")
        return {"backend": "postgres" if _uses_postgres(settings) else "sqlite", "ok": False, "error": str(exc)[:240]}


def create_job_scan(
    settings: Settings,
    *,
    job_title: str,
    company: str,
    job_description: str,
    visitor_id: Optional[str],
    session_id: Optional[str],
    visitor_identity: Optional[Dict[str, Any]],
) -> str:
    scan_id = str(uuid4())
    now = _now()
    row = (
        scan_id,
        now,
        now,
        "running",
        job_title[:240],
        company[:240],
        job_description,
        visitor_id,
        session_id,
        _safe_json(visitor_identity),
        "",
        "",
        _safe_json({}),
        _safe_json({}),
        _safe_json([]),
        _safe_json([]),
        None,
        "",
        None,
    )
    with _lock:
        with _connect(settings) as conn:
            placeholder = "%s" if _uses_postgres(settings) else "?"
            conn.execute(
                f"""
                INSERT INTO job_scans
                (id, created_at, updated_at, status, job_title, company, job_description, visitor_id, session_id,
                 visitor_identity_json, summary, analysis_text, analysis_json, metrics_json, sources_json, docs_json,
                 fit_score, model, error)
                VALUES ({", ".join([placeholder] * 19)})
                """,
                row,
            )
    return scan_id


def finish_job_scan(
    settings: Settings,
    scan_id: str,
    *,
    summary: str,
    analysis_text: str,
    analysis: Dict[str, Any],
    metrics: Dict[str, Any],
    sources: List[Dict[str, Any]],
    docs: List[str],
    fit_score: Optional[int],
    model: Optional[str],
) -> None:
    with _lock:
        with _connect(settings) as conn:
            placeholder = "%s" if _uses_postgres(settings) else "?"
            conn.execute(
                f"""
                UPDATE job_scans
                SET updated_at = {placeholder}, status = {placeholder}, summary = {placeholder}, analysis_text = {placeholder},
                    analysis_json = {placeholder}, metrics_json = {placeholder}, sources_json = {placeholder},
                    docs_json = {placeholder}, fit_score = {placeholder}, model = {placeholder}, error = NULL
                WHERE id = {placeholder}
                """,
                (
                    _now(),
                    "completed",
                    summary[:1200],
                    analysis_text,
                    _safe_json(analysis),
                    _safe_json(metrics),
                    _safe_json(sources),
                    _safe_json(docs),
                    fit_score,
                    model or "",
                    scan_id,
                ),
            )


def fail_job_scan(settings: Settings, scan_id: str, error: str) -> None:
    with _lock:
        with _connect(settings) as conn:
            placeholder = "%s" if _uses_postgres(settings) else "?"
            conn.execute(
                f"""
                UPDATE job_scans
                SET updated_at = {placeholder}, status = {placeholder}, error = {placeholder}
                WHERE id = {placeholder}
                """,
                (_now(), "error", error[:1000], scan_id),
            )


def _normalize_row(row: Any, *, include_description: bool) -> Dict[str, Any]:
    if not isinstance(row, dict):
        row = dict(row)
    result = {
        "id": row.get("id"),
        "created_at": str(row.get("created_at")),
        "updated_at": str(row.get("updated_at")),
        "status": row.get("status"),
        "job_title": row.get("job_title") or "",
        "company": row.get("company") or "",
        "visitor_id": row.get("visitor_id"),
        "session_id": row.get("session_id"),
        "visitor_identity": _parse_json(row.get("visitor_identity_json"), {}),
        "summary": row.get("summary") or "",
        "analysis_text": row.get("analysis_text") or "",
        "analysis": _parse_json(row.get("analysis_json"), {}),
        "metrics": _parse_json(row.get("metrics_json"), {}),
        "sources": _parse_json(row.get("sources_json"), []),
        "docs": _parse_json(row.get("docs_json"), []),
        "fit_score": row.get("fit_score"),
        "model": row.get("model") or "",
        "error": row.get("error"),
    }
    if include_description:
        result["job_description"] = row.get("job_description") or ""
    else:
        result["job_description_chars"] = len(row.get("job_description") or "")
    return result


def list_job_scans(
    settings: Settings,
    *,
    limit: int = 100,
    status: Optional[str] = None,
    visitor_id: Optional[str] = None,
    company: Optional[str] = None,
) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 500))
    where: List[str] = []
    params: List[Any] = []
    placeholder = "%s" if _uses_postgres(settings) else "?"
    if status:
        where.append(f"status = {placeholder}")
        params.append(status)
    if visitor_id:
        where.append(f"visitor_id = {placeholder}")
        params.append(visitor_id)
    if company:
        where.append(f"LOWER(company) LIKE {placeholder}")
        params.append(f"%{company.lower()}%")

    query = "SELECT * FROM job_scans"
    if where:
        query += " WHERE " + " AND ".join(where)
    query += f" ORDER BY created_at DESC LIMIT {placeholder}"
    params.append(limit)

    with _lock:
        with _connect(settings) as conn:
            rows = conn.execute(query, params).fetchall()
    return [_normalize_row(row, include_description=False) for row in rows]


def get_job_scan(settings: Settings, scan_id: str) -> Optional[Dict[str, Any]]:
    placeholder = "%s" if _uses_postgres(settings) else "?"
    with _lock:
        with _connect(settings) as conn:
            row = conn.execute(f"SELECT * FROM job_scans WHERE id = {placeholder}", (scan_id,)).fetchone()
    return _normalize_row(row, include_description=True) if row else None


def delete_job_scan(settings: Settings, scan_id: str) -> bool:
    placeholder = "%s" if _uses_postgres(settings) else "?"
    with _lock:
        with _connect(settings) as conn:
            if _uses_postgres(settings):
                row = conn.execute(f"DELETE FROM job_scans WHERE id = {placeholder} RETURNING id", (scan_id,)).fetchone()
                return bool(row)
            cursor = conn.execute(f"DELETE FROM job_scans WHERE id = {placeholder}", (scan_id,))
            return cursor.rowcount > 0

