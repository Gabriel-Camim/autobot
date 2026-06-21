from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from config import Settings
from ingest import _parse_frontmatter, load_public_documents
from pgvector_store import pgvector_status, uses_pgvector


_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uses_postgres(settings: Settings) -> bool:
    return settings.database_url.strip().startswith(("postgres://", "postgresql://"))


def _connect(settings: Settings):
    if _uses_postgres(settings):
        import psycopg
        from psycopg.rows import dict_row

        conn = psycopg.connect(settings.database_url.strip(), row_factory=dict_row, autocommit=True)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rag_eval_runs (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL,
                app_version TEXT,
                app_commit TEXT,
                total INTEGER NOT NULL,
                passed INTEGER NOT NULL,
                failed INTEGER NOT NULL,
                duration_ms DOUBLE PRECISION NOT NULL,
                result_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_eval_runs_created_at ON rag_eval_runs(created_at)")
        return conn

    db_path = settings.resolved_events_db_path.parent / "rag_eval_runs.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_eval_runs (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            app_version TEXT,
            app_commit TEXT,
            total INTEGER NOT NULL,
            passed INTEGER NOT NULL,
            failed INTEGER NOT NULL,
            duration_ms REAL NOT NULL,
            result_json TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_eval_runs_created_at ON rag_eval_runs(created_at)")
    return conn


def _safe_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)


def _row_to_run(row: Any) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    if not isinstance(row, dict):
        row = dict(row)
    try:
        result = json.loads(row.get("result_json") or "{}")
    except json.JSONDecodeError:
        result = {}
    return {
        "id": row.get("id"),
        "created_at": str(row.get("created_at")),
        "app_version": row.get("app_version"),
        "app_commit": row.get("app_commit"),
        "total": row.get("total"),
        "passed": row.get("passed"),
        "failed": row.get("failed"),
        "duration_ms": row.get("duration_ms"),
        "result": result,
    }


def load_rag_eval_cases(settings: Settings) -> List[Dict[str, Any]]:
    path = settings.backend_dir / "evals" / "rag_cases.json"
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [case for case in raw if isinstance(case, dict)]


def _source_matches(actual: str, expected: str) -> bool:
    actual = actual.strip().strip("/")
    expected = expected.strip().strip("/")
    if not expected:
        return False
    return actual == expected or actual.startswith(expected.rstrip("/") + "/")


def _case_passes(case: Dict[str, Any], probe: Dict[str, Any]) -> Dict[str, Any]:
    evidence = probe.get("evidence") or []
    sources = [str(item.get("source", "")) for item in evidence if item.get("source")]
    expected_sources = [str(source) for source in case.get("expected_sources") or []]
    forbidden_terms = [str(term) for term in case.get("forbidden_terms") or []]
    min_docs = int(case.get("min_docs") or 1)

    missing_sources = [
        expected for expected in expected_sources if not any(_source_matches(source, expected) for source in sources)
    ]
    evidence_text = "\n".join(
        " ".join(
            str(item.get(field, ""))
            for field in ("source", "title", "category", "summary", "excerpt", "match_reason")
        )
        for item in evidence
    ).lower()
    forbidden_detected = [term for term in forbidden_terms if term.lower() in evidence_text]
    passed = len(evidence) >= min_docs and not missing_sources and not forbidden_detected
    return {
        "id": case.get("id"),
        "question": case.get("question"),
        "active_context": case.get("active_context"),
        "passed": passed,
        "documents": len(evidence),
        "min_docs": min_docs,
        "sources": sources,
        "missing_sources": missing_sources,
        "forbidden_terms_detected": forbidden_detected,
        "took_ms": probe.get("took_ms"),
        "retrieval_query": probe.get("retrieval_query"),
        "evidence": evidence,
    }


def save_eval_run(settings: Settings, run: Dict[str, Any]) -> Dict[str, Any]:
    row = (
        run["id"],
        run["created_at"],
        settings.app_version,
        settings.app_commit,
        int(run["total"]),
        int(run["passed"]),
        int(run["failed"]),
        float(run["duration_ms"]),
        _safe_json(run),
    )
    with _lock:
        with _connect(settings) as conn:
            if _uses_postgres(settings):
                conn.execute(
                    """
                    INSERT INTO rag_eval_runs
                    (id, created_at, app_version, app_commit, total, passed, failed, duration_ms, result_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    row,
                )
            else:
                conn.execute(
                    """
                    INSERT INTO rag_eval_runs
                    (id, created_at, app_version, app_commit, total, passed, failed, duration_ms, result_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
    return run


def last_eval_run(settings: Settings) -> Optional[Dict[str, Any]]:
    try:
        with _lock:
            with _connect(settings) as conn:
                row = conn.execute("SELECT * FROM rag_eval_runs ORDER BY created_at DESC LIMIT 1").fetchone()
    except Exception:
        return None
    return _row_to_run(row)


def run_rag_eval(settings: Settings) -> Dict[str, Any]:
    from agent import build_rag_probe

    cases = load_rag_eval_cases(settings)
    started = time.perf_counter()
    results: List[Dict[str, Any]] = []
    for case in cases:
        probe = build_rag_probe(
            settings,
            str(case.get("question", "")),
            str(case.get("active_context") or "") or None,
            limit=max(int(case.get("min_docs") or 1), 8),
        )
        results.append(_case_passes(case, probe))

    passed = sum(1 for result in results if result.get("passed"))
    run = {
        "id": str(uuid4()),
        "created_at": _now(),
        "app_version": settings.app_version,
        "app_commit": settings.app_commit,
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "cases": results,
    }
    return save_eval_run(settings, run)


def _markdown_visibility(path: Path) -> str:
    try:
        metadata, _body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    except Exception:
        return "invalid_frontmatter"
    return str(metadata.get("visibility", "")).strip().lower()


def coverage_summary(settings: Settings) -> Dict[str, Any]:
    public_docs = load_public_documents(settings)
    all_markdown = list(settings.resolved_knowledge_dir.rglob("*.md")) if settings.resolved_knowledge_dir.exists() else []
    public_sources = [str(doc.metadata.get("source", "")) for doc in public_docs if doc.metadata.get("source")]

    missing_summary = [str(doc.metadata.get("source", "")) for doc in public_docs if not str(doc.metadata.get("summary", "")).strip()]
    missing_tags = [str(doc.metadata.get("source", "")) for doc in public_docs if not str(doc.metadata.get("tags", "")).strip()]
    missing_priority = [
        str(doc.metadata.get("source", ""))
        for doc in public_docs
        if doc.metadata.get("priority") in (None, "", 0)
    ]
    invalid_visibility = []
    valid_visibility = {"public", "private", "draft", "internal", ""}
    for path in all_markdown:
        visibility = _markdown_visibility(path)
        if visibility not in valid_visibility:
            invalid_visibility.append(path.relative_to(settings.resolved_knowledge_dir).as_posix())

    last_run = last_eval_run(settings)
    retrieved_counter: Counter[str] = Counter()
    if last_run and last_run.get("result"):
        for case in (last_run.get("result") or {}).get("cases", []):
            retrieved_counter.update(case.get("sources") or [])
    never_retrieved = sorted(set(public_sources) - set(retrieved_counter))
    vector = pgvector_status(settings) if uses_pgvector(settings) else {"backend": "chroma", "chunks": None, "ready": None}

    return {
        "public_markdown": len(public_docs),
        "all_markdown": len(all_markdown),
        "hidden_or_non_public_markdown": max(0, len(all_markdown) - len(public_docs)),
        "chunks": vector.get("chunks"),
        "vector_backend": vector.get("backend"),
        "vector_ready": vector.get("ready"),
        "missing_summary": missing_summary,
        "missing_tags": missing_tags,
        "missing_priority": missing_priority,
        "invalid_visibility": invalid_visibility,
        "top_retrieved_sources": [{"source": source, "count": count} for source, count in retrieved_counter.most_common(10)],
        "never_retrieved_in_last_eval": never_retrieved[:50],
    }
