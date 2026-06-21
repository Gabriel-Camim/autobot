from __future__ import annotations

import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from config import Settings


_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _uses_postgres(settings: Settings) -> bool:
    return settings.database_url.strip().startswith(("postgres://", "postgresql://"))


def _placeholder(settings: Settings) -> str:
    return "%s" if _uses_postgres(settings) else "?"


def _safe_json(data: Any) -> str:
    return json.dumps(data if data is not None else {}, ensure_ascii=False, separators=(",", ":"), default=str)


def _load_json(value: Any, fallback: Any = None) -> Any:
    if value in (None, ""):
        return {} if fallback is None else fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {} if fallback is None else fallback


def _connect(settings: Settings):
    if _uses_postgres(settings):
        import psycopg
        from psycopg.rows import dict_row

        conn = psycopg.connect(settings.database_url.strip(), row_factory=dict_row, autocommit=True)
        _ensure_schema(conn, postgres=True)
        return conn

    db_path = settings.resolved_events_db_path.parent / "rag_quality.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn, postgres=False)
    return conn


def _ensure_schema(conn, *, postgres: bool) -> None:
    timestamp = "TIMESTAMPTZ" if postgres else "TEXT"
    float_type = "DOUBLE PRECISION" if postgres else "REAL"
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS rag_traces (
            id TEXT PRIMARY KEY,
            created_at {timestamp} NOT NULL,
            session_id TEXT,
            visitor_id TEXT,
            active_context TEXT,
            question TEXT NOT NULL,
            answer_excerpt TEXT,
            retrieval_query TEXT,
            subqueries_json TEXT NOT NULL,
            candidates_json TEXT NOT NULL,
            selected_sources_json TEXT NOT NULL,
            rerank_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            model TEXT,
            app_version TEXT,
            app_commit TEXT
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS rag_feedback (
            id TEXT PRIMARY KEY,
            created_at {timestamp} NOT NULL,
            trace_id TEXT,
            session_id TEXT,
            visitor_id TEXT,
            visitor_identity_json TEXT NOT NULL,
            rating TEXT NOT NULL,
            reason TEXT,
            comment TEXT,
            expected_answer TEXT,
            status TEXT NOT NULL,
            triage_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS knowledge_suggestions (
            id TEXT PRIMARY KEY,
            created_at {timestamp} NOT NULL,
            updated_at {timestamp} NOT NULL,
            status TEXT NOT NULL,
            suggestion_type TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_id TEXT,
            title TEXT NOT NULL,
            suggested_path TEXT NOT NULL,
            frontmatter_json TEXT NOT NULL,
            draft_markdown TEXT NOT NULL,
            confidence {float_type} NOT NULL,
            rationale TEXT,
            payload_json TEXT NOT NULL
        )
        """
    )
    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_rag_traces_created_at ON rag_traces(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_rag_traces_session_id ON rag_traces(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_rag_traces_visitor_id ON rag_traces(visitor_id)",
        "CREATE INDEX IF NOT EXISTS idx_rag_feedback_created_at ON rag_feedback(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_rag_feedback_trace_id ON rag_feedback(trace_id)",
        "CREATE INDEX IF NOT EXISTS idx_knowledge_suggestions_status ON knowledge_suggestions(status)",
        "CREATE INDEX IF NOT EXISTS idx_knowledge_suggestions_created_at ON knowledge_suggestions(created_at)",
    ):
        conn.execute(statement)


def init_rag_quality_db(settings: Settings) -> None:
    with _lock:
        with _connect(settings):
            pass


def rag_quality_storage_status(settings: Settings) -> Dict[str, Any]:
    try:
        init_rag_quality_db(settings)
        return {"backend": "postgres" if _uses_postgres(settings) else "sqlite", "ok": True, "error": None}
    except Exception as exc:
        return {
            "backend": "postgres" if _uses_postgres(settings) else "sqlite",
            "ok": False,
            "error": str(exc)[:240],
        }


def _priority_boost(priority: int) -> float:
    return max(0.0, (6 - max(1, min(priority, 5))) * 0.18)


def rerank_candidate_payloads(settings: Settings, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    provider = settings.rag_rerank_provider.strip().lower()
    if not settings.rag_rerank_enabled or provider == "none":
        return [
            {
                **candidate,
                "rerank_provider": "disabled",
                "rerank_score": round(float(candidate.get("base_relevance") or 0), 4),
            }
            for candidate in candidates
        ]

    reranked: List[Dict[str, Any]] = []
    for candidate in candidates:
        base = float(candidate.get("base_relevance") or 0)
        priority = int(candidate.get("priority") or 3)
        channel = str(candidate.get("channel") or "")
        distance = candidate.get("distance")
        source = str(candidate.get("source") or "")
        match_reason = str(candidate.get("match_reason") or "")
        channel_boost = 0.55 if channel == "hybrid" else 0.22 if channel == "lexical" else 0.12
        distance_boost = max(0.0, 0.45 - float(distance or 0) * 0.08) if distance is not None else 0.0
        focus_boost = 0.35 if "foco:" in match_reason else 0.0
        source_boost = 0.2 if source.startswith(("skills/", "projetos/", "experiencia/", "trajetoria/")) else 0.0
        rerank_score = base + _priority_boost(priority) + channel_boost + distance_boost + focus_boost + source_boost
        reranked.append(
            {
                **candidate,
                "rerank_provider": provider or "heuristic",
                "rerank_score": round(rerank_score, 4),
            }
        )
    reranked.sort(
        key=lambda item: (
            -float(item.get("rerank_score") or 0),
            int(item.get("priority") or 3),
            str(item.get("source") or ""),
        )
    )
    return reranked


def save_rag_trace(settings: Settings, payload: Dict[str, Any]) -> Optional[str]:
    if not settings.rag_trace_enabled:
        return None
    trace_id = payload.get("id") or str(uuid4())
    metrics = payload.get("metrics") or {}
    selected_sources = payload.get("selected_sources") or []
    row = (
        trace_id,
        _now(),
        payload.get("session_id"),
        payload.get("visitor_id"),
        payload.get("active_context"),
        str(payload.get("question") or "")[:8000],
        str(payload.get("answer") or "")[:2200],
        str(payload.get("retrieval_query") or "")[:8000],
        _safe_json(payload.get("subqueries") or []),
        _safe_json(payload.get("candidates") or []),
        _safe_json(selected_sources),
        _safe_json(payload.get("rerank") or {}),
        _safe_json(metrics),
        payload.get("model"),
        settings.app_version,
        settings.app_commit,
    )
    with _lock:
        with _connect(settings) as conn:
            marker = _placeholder(settings)
            conn.execute(
                f"""
                INSERT INTO rag_traces
                (id, created_at, session_id, visitor_id, active_context, question, answer_excerpt,
                 retrieval_query, subqueries_json, candidates_json, selected_sources_json, rerank_json,
                 metrics_json, model, app_version, app_commit)
                VALUES ({",".join([marker] * 16)})
                """,
                row,
            )
    return trace_id


def update_rag_trace_actor(
    settings: Settings,
    trace_id: Optional[str],
    *,
    visitor_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    if not trace_id:
        return
    updates: List[str] = []
    params: List[Any] = []
    marker = _placeholder(settings)
    if visitor_id:
        updates.append(f"visitor_id = {marker}")
        params.append(visitor_id)
    if session_id:
        updates.append(f"session_id = {marker}")
        params.append(session_id)
    if not updates:
        return
    params.append(trace_id)
    with _lock:
        with _connect(settings) as conn:
            conn.execute(f"UPDATE rag_traces SET {', '.join(updates)} WHERE id = {marker}", params)


def _trace_from_row(row: Any) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    if not isinstance(row, dict):
        row = dict(row)
    return {
        "id": row.get("id"),
        "created_at": str(row.get("created_at")),
        "session_id": row.get("session_id"),
        "visitor_id": row.get("visitor_id"),
        "active_context": row.get("active_context"),
        "question": row.get("question"),
        "answer_excerpt": row.get("answer_excerpt"),
        "retrieval_query": row.get("retrieval_query"),
        "subqueries": _load_json(row.get("subqueries_json"), []),
        "candidates": _load_json(row.get("candidates_json"), []),
        "selected_sources": _load_json(row.get("selected_sources_json"), []),
        "rerank": _load_json(row.get("rerank_json"), {}),
        "metrics": _load_json(row.get("metrics_json"), {}),
        "model": row.get("model"),
        "app_version": row.get("app_version"),
        "app_commit": row.get("app_commit"),
    }


def list_rag_traces(
    settings: Settings,
    *,
    visitor_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 500))
    marker = _placeholder(settings)
    where: List[str] = []
    params: List[Any] = []
    if visitor_id:
        where.append(f"visitor_id = {marker}")
        params.append(visitor_id)
    if session_id:
        where.append(f"session_id = {marker}")
        params.append(session_id)
    query = "SELECT * FROM rag_traces"
    if where:
        query += " WHERE " + " AND ".join(where)
    query += f" ORDER BY created_at DESC LIMIT {marker}"
    params.append(limit)
    with _lock:
        with _connect(settings) as conn:
            rows = conn.execute(query, params).fetchall()
    return [trace for trace in (_trace_from_row(row) for row in rows) if trace]


def get_rag_trace(settings: Settings, trace_id: str) -> Optional[Dict[str, Any]]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            row = conn.execute(f"SELECT * FROM rag_traces WHERE id = {marker}", (trace_id,)).fetchone()
    return _trace_from_row(row)


def _slugify(text: str, fallback: str = "sugestao") -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").lower()).strip("-")
    return (normalized or fallback)[:72].strip("-") or fallback


def _suggested_path(trace: Optional[Dict[str, Any]], reason: str) -> str:
    context = str((trace or {}).get("active_context") or "").strip().lower()
    question = str((trace or {}).get("question") or reason or "sugestao")
    slug = _slugify(question)
    if context in {"stack", "skills"}:
        return f"knowledge/skills/inbox-{_today()}-{slug}.md"
    if context in {"projetos", "projects"}:
        return f"knowledge/projetos/inbox-{_today()}-{slug}.md"
    if context in {"trajetoria", "experiencia", "mercado", "entrevista"}:
        return f"knowledge/{context}/inbox-{_today()}-{slug}.md"
    return f"knowledge/inbox/{_today()}-{slug}.md"


def _draft_markdown(frontmatter: Dict[str, Any], trace: Optional[Dict[str, Any]], feedback: Dict[str, Any]) -> str:
    tags = frontmatter.get("tags") or []
    yaml_tags = "\n".join(f"- {tag}" for tag in tags)
    question = str((trace or {}).get("question") or "Pergunta sem trace")
    answer = str((trace or {}).get("answer_excerpt") or "")
    selected = ", ".join(str(source) for source in (trace or {}).get("selected_sources") or [])
    return f"""---
title: {frontmatter["title"]}
category: {frontmatter["category"]}
tags:
{yaml_tags}
visibility: draft
priority: {frontmatter["priority"]}
updated_at: '{frontmatter["updated_at"]}'
summary: {frontmatter["summary"]}
---

# {frontmatter["title"]}

## Origem da sugestão

Feedback: {feedback.get("reason") or feedback.get("rating")}

Comentário:
{feedback.get("comment") or "Sem comentário adicional."}

Pergunta original:
{question}

Fontes recuperadas no momento:
{selected or "Nenhuma fonte registrada."}

## Rascunho para curadoria

TODO: validar a resposta correta, complementar com fatos documentados e remover este bloco antes de publicar.

Resposta gerada na época:
{answer or "Sem resposta registrada."}
""".strip() + "\n"


def _create_suggestion_from_feedback(settings: Settings, feedback: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not settings.rag_suggestions_enabled:
        return None
    trace = get_rag_trace(settings, feedback.get("trace_id") or "") if feedback.get("trace_id") else None
    title = f"Curadoria RAG: {str((trace or {}).get('question') or feedback.get('reason') or 'feedback')[:80]}"
    frontmatter = {
        "title": title,
        "category": "curadoria",
        "tags": ["feedback", "rag", "draft"],
        "visibility": "draft",
        "priority": 3,
        "updated_at": _today(),
        "summary": "Sugestão gerada por feedback ou falha de recuperação RAG.",
    }
    payload = {"feedback": feedback, "trace": trace}
    suggestion = {
        "id": str(uuid4()),
        "status": "open",
        "suggestion_type": "update_knowledge",
        "source_kind": "feedback",
        "source_id": feedback.get("id"),
        "title": title,
        "suggested_path": _suggested_path(trace, str(feedback.get("reason") or "")),
        "frontmatter": frontmatter,
        "draft_markdown": _draft_markdown(frontmatter, trace, feedback),
        "confidence": 0.72 if trace else 0.48,
        "rationale": "Feedback negativo indica possível lacuna, fato incorreto ou recuperação insuficiente.",
        "payload": payload,
    }
    return create_knowledge_suggestion(settings, suggestion)


def create_rag_feedback(settings: Settings, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not settings.rag_feedback_enabled:
        raise RuntimeError("RAG feedback is disabled")
    rating = str(payload.get("rating") or "").strip().lower()
    reason = str(payload.get("reason") or "").strip().lower()
    feedback = {
        "id": str(uuid4()),
        "created_at": _now(),
        "trace_id": payload.get("trace_id"),
        "session_id": payload.get("session_id"),
        "visitor_id": payload.get("visitor_id"),
        "visitor_identity": payload.get("visitor_identity") or {},
        "rating": rating or "other",
        "reason": reason or None,
        "comment": str(payload.get("comment") or "").strip()[:4000] or None,
        "expected_answer": str(payload.get("expected_answer") or "").strip()[:8000] or None,
        "status": "open",
        "triage": {},
    }
    row = (
        feedback["id"],
        feedback["created_at"],
        feedback["trace_id"],
        feedback["session_id"],
        feedback["visitor_id"],
        _safe_json(feedback["visitor_identity"]),
        feedback["rating"],
        feedback["reason"],
        feedback["comment"],
        feedback["expected_answer"],
        feedback["status"],
        _safe_json(feedback["triage"]),
    )
    with _lock:
        with _connect(settings) as conn:
            marker = _placeholder(settings)
            conn.execute(
                f"""
                INSERT INTO rag_feedback
                (id, created_at, trace_id, session_id, visitor_id, visitor_identity_json, rating, reason,
                 comment, expected_answer, status, triage_json)
                VALUES ({",".join([marker] * 12)})
                """,
                row,
            )
    suggestion = None
    if rating not in {"positive", "good", "ok"} or reason in {"missing_context", "wrong_fact", "vague"}:
        suggestion = _create_suggestion_from_feedback(settings, feedback)
    return {"feedback": feedback, "suggestion": suggestion}


def _feedback_from_row(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        row = dict(row)
    return {
        "id": row.get("id"),
        "created_at": str(row.get("created_at")),
        "trace_id": row.get("trace_id"),
        "session_id": row.get("session_id"),
        "visitor_id": row.get("visitor_id"),
        "visitor_identity": _load_json(row.get("visitor_identity_json"), {}),
        "rating": row.get("rating"),
        "reason": row.get("reason"),
        "comment": row.get("comment"),
        "expected_answer": row.get("expected_answer"),
        "status": row.get("status"),
        "triage": _load_json(row.get("triage_json"), {}),
    }


def list_rag_feedback(settings: Settings, *, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 500))
    marker = _placeholder(settings)
    params: List[Any] = []
    query = "SELECT * FROM rag_feedback"
    if status:
        query += f" WHERE status = {marker}"
        params.append(status)
    query += f" ORDER BY created_at DESC LIMIT {marker}"
    params.append(limit)
    with _lock:
        with _connect(settings) as conn:
            rows = conn.execute(query, params).fetchall()
    return [_feedback_from_row(row) for row in rows]


def triage_rag_feedback(settings: Settings, feedback_id: str, status: str, triage: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            conn.execute(
                f"UPDATE rag_feedback SET status = {marker}, triage_json = {marker} WHERE id = {marker}",
                (status, _safe_json(triage), feedback_id),
            )
            row = conn.execute(f"SELECT * FROM rag_feedback WHERE id = {marker}", (feedback_id,)).fetchone()
    return _feedback_from_row(row) if row else None


def create_knowledge_suggestion(settings: Settings, suggestion: Dict[str, Any]) -> Dict[str, Any]:
    now = _now()
    row = (
        suggestion["id"],
        now,
        now,
        suggestion.get("status", "open"),
        suggestion["suggestion_type"],
        suggestion["source_kind"],
        suggestion.get("source_id"),
        suggestion["title"],
        suggestion["suggested_path"],
        _safe_json(suggestion.get("frontmatter") or {}),
        suggestion["draft_markdown"],
        float(suggestion.get("confidence") or 0.5),
        suggestion.get("rationale"),
        _safe_json(suggestion.get("payload") or {}),
    )
    with _lock:
        with _connect(settings) as conn:
            marker = _placeholder(settings)
            conn.execute(
                f"""
                INSERT INTO knowledge_suggestions
                (id, created_at, updated_at, status, suggestion_type, source_kind, source_id, title,
                 suggested_path, frontmatter_json, draft_markdown, confidence, rationale, payload_json)
                VALUES ({",".join([marker] * 14)})
                """,
                row,
            )
    return get_knowledge_suggestion(settings, suggestion["id"]) or suggestion


def _suggestion_from_row(row: Any) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    if not isinstance(row, dict):
        row = dict(row)
    return {
        "id": row.get("id"),
        "created_at": str(row.get("created_at")),
        "updated_at": str(row.get("updated_at")),
        "status": row.get("status"),
        "suggestion_type": row.get("suggestion_type"),
        "source_kind": row.get("source_kind"),
        "source_id": row.get("source_id"),
        "title": row.get("title"),
        "suggested_path": row.get("suggested_path"),
        "frontmatter": _load_json(row.get("frontmatter_json"), {}),
        "draft_markdown": row.get("draft_markdown"),
        "confidence": row.get("confidence"),
        "rationale": row.get("rationale"),
        "payload": _load_json(row.get("payload_json"), {}),
    }


def list_knowledge_suggestions(settings: Settings, *, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 500))
    marker = _placeholder(settings)
    params: List[Any] = []
    query = "SELECT * FROM knowledge_suggestions"
    if status:
        query += f" WHERE status = {marker}"
        params.append(status)
    query += f" ORDER BY created_at DESC LIMIT {marker}"
    params.append(limit)
    with _lock:
        with _connect(settings) as conn:
            rows = conn.execute(query, params).fetchall()
    return [item for item in (_suggestion_from_row(row) for row in rows) if item]


def get_knowledge_suggestion(settings: Settings, suggestion_id: str) -> Optional[Dict[str, Any]]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            row = conn.execute(f"SELECT * FROM knowledge_suggestions WHERE id = {marker}", (suggestion_id,)).fetchone()
    return _suggestion_from_row(row)


def update_knowledge_suggestion_status(
    settings: Settings,
    suggestion_id: str,
    status: str,
    payload_update: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    suggestion = get_knowledge_suggestion(settings, suggestion_id)
    if not suggestion:
        return None
    payload = suggestion.get("payload") or {}
    if payload_update:
        payload.update(payload_update)
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            conn.execute(
                f"UPDATE knowledge_suggestions SET status = {marker}, updated_at = {marker}, payload_json = {marker} WHERE id = {marker}",
                (status, _now(), _safe_json(payload), suggestion_id),
            )
    return get_knowledge_suggestion(settings, suggestion_id)


def eval_case_from_suggestion(suggestion: Dict[str, Any]) -> Dict[str, Any]:
    trace = ((suggestion.get("payload") or {}).get("trace") or {})
    question = str(trace.get("question") or suggestion.get("title") or "Caso sugerido")
    active_context = trace.get("active_context")
    selected = trace.get("selected_sources") or []
    return {
        "id": f"suggestion-{str(suggestion.get('id'))[:8]}",
        "question": question[:500],
        "active_context": active_context,
        "expected_sources": selected[:4],
        "forbidden_terms": [],
        "min_docs": 1,
    }
