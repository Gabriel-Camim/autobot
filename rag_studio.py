from __future__ import annotations

import difflib
import hashlib
import json
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional
from uuid import uuid4

import yaml
from langchain_core.messages import HumanMessage, SystemMessage

from agent import AppError, _build_llm, _response_content_to_text, build_rag_probe, sanitize_answer_text
from config import Settings
from rag_quality import get_rag_feedback, get_rag_trace, list_rag_feedback, triage_rag_feedback


_lock = threading.Lock()
OPEN_STATUSES = {"open", "investigating", "documents_selected", "patch_ready", "applied", "validating"}
DOC_DONE_STATUSES = {"applied", "ignored"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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

    db_path = settings.resolved_events_db_path.parent / "rag_studio.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn, postgres=False)
    return conn


def _add_column_if_missing(conn, table: str, column: str, definition: str, *, postgres: bool) -> None:
    if postgres:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
        return
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _ensure_schema(conn, *, postgres: bool) -> None:
    timestamp = "TIMESTAMPTZ" if postgres else "TEXT"
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS rag_change_proposals (
            id TEXT PRIMARY KEY,
            created_at {timestamp} NOT NULL,
            updated_at {timestamp} NOT NULL,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            origin_type TEXT NOT NULL,
            origin_id TEXT,
            problem_statement TEXT,
            question TEXT,
            answer_excerpt TEXT,
            active_context TEXT,
            investigation_json TEXT NOT NULL,
            validation_json TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS rag_change_documents (
            id TEXT PRIMARY KEY,
            proposal_id TEXT NOT NULL,
            created_at {timestamp} NOT NULL,
            updated_at {timestamp} NOT NULL,
            status TEXT NOT NULL,
            path TEXT NOT NULL,
            title TEXT,
            selection_reason TEXT,
            evidence_json TEXT NOT NULL,
            current_hash TEXT,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS rag_change_patches (
            id TEXT PRIMARY KEY,
            proposal_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            created_at {timestamp} NOT NULL,
            updated_at {timestamp} NOT NULL,
            status TEXT NOT NULL,
            target_path TEXT NOT NULL,
            original_content TEXT NOT NULL,
            proposed_content TEXT NOT NULL,
            diff_text TEXT NOT NULL,
            rationale TEXT,
            model TEXT,
            commit_sha TEXT,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS rag_change_events (
            id TEXT PRIMARY KEY,
            proposal_id TEXT NOT NULL,
            created_at {timestamp} NOT NULL,
            kind TEXT NOT NULL,
            message TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS rag_change_attachments (
            id TEXT PRIMARY KEY,
            proposal_id TEXT NOT NULL,
            document_id TEXT,
            created_at {timestamp} NOT NULL,
            filename TEXT NOT NULL,
            content_type TEXT,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            extracted_text TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        )
        """
    )
    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_rag_change_proposals_status ON rag_change_proposals(status)",
        "CREATE INDEX IF NOT EXISTS idx_rag_change_proposals_origin ON rag_change_proposals(origin_type, origin_id)",
        "CREATE INDEX IF NOT EXISTS idx_rag_change_documents_proposal ON rag_change_documents(proposal_id)",
        "CREATE INDEX IF NOT EXISTS idx_rag_change_patches_document ON rag_change_patches(document_id)",
        "CREATE INDEX IF NOT EXISTS idx_rag_change_events_proposal ON rag_change_events(proposal_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_rag_change_attachments_proposal ON rag_change_attachments(proposal_id)",
    ):
        conn.execute(statement)
    _add_column_if_missing(conn, "rag_change_proposals", "question", "TEXT", postgres=postgres)
    _add_column_if_missing(conn, "rag_change_proposals", "answer_excerpt", "TEXT", postgres=postgres)
    _add_column_if_missing(conn, "rag_change_proposals", "active_context", "TEXT", postgres=postgres)


def init_rag_studio_db(settings: Settings) -> None:
    with _lock:
        with _connect(settings):
            pass


def rag_studio_storage_status(settings: Settings) -> Dict[str, Any]:
    try:
        init_rag_studio_db(settings)
        return {"backend": "postgres" if _uses_postgres(settings) else "sqlite", "ok": True, "error": None}
    except Exception as exc:
        return {"backend": "postgres" if _uses_postgres(settings) else "sqlite", "ok": False, "error": str(exc)[:240]}


def _normalize_repo_path(raw_path: str) -> str:
    cleaned = raw_path.strip().replace("\\", "/").strip("/")
    if not cleaned:
        raise AppError("invalid_path", "Informe um caminho valido.", 400)
    path = PurePosixPath(cleaned)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise AppError("invalid_path", "Caminho invalido.", 400)
    if path.suffix.lower() != ".md":
        raise AppError("invalid_path", "O RAG Studio altera apenas Markdown canonico.", 400)
    if path.parts[0] != "knowledge":
        path = PurePosixPath("knowledge") / path
    parts = path.parts
    if len(parts) > 1 and parts[1] == "_drafts":
        raise AppError("invalid_path", "Drafts privados nao sao documentos canonicos.", 400)
    return path.as_posix()


def _canonical_file_path(settings: Settings, repo_path: str) -> Path:
    normalized = _normalize_repo_path(repo_path)
    relative = PurePosixPath(normalized).relative_to("knowledge")
    target = (settings.resolved_knowledge_dir / Path(relative.as_posix())).resolve()
    base = settings.resolved_knowledge_dir.resolve()
    if target != base and base not in target.parents:
        raise AppError("invalid_path", "Caminho fora de knowledge/.", 400)
    return target


def _read_canonical_markdown(settings: Settings, repo_path: str) -> str:
    target = _canonical_file_path(settings, repo_path)
    if not target.exists() or not target.is_file():
        raise AppError("canonical_doc_not_found", "Markdown canonico nao encontrado.", 404)
    return target.read_text(encoding="utf-8")


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _frontmatter(content: str) -> Dict[str, Any]:
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        value = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}
    return value if isinstance(value, dict) else {}


def _diff_text(path: str, original: str, proposed: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            original.splitlines(),
            proposed.splitlines(),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
        )
    )


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    clean = (text or "").strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?", "", clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r"```$", "", clean).strip()
    try:
        parsed = json.loads(clean)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", clean, flags=re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _proposal_from_row(row: Any) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    if not isinstance(row, dict):
        row = dict(row)
    return {
        "id": row.get("id"),
        "created_at": str(row.get("created_at")),
        "updated_at": str(row.get("updated_at")),
        "status": row.get("status"),
        "title": row.get("title"),
        "origin_type": row.get("origin_type"),
        "origin_id": row.get("origin_id"),
        "problem_statement": row.get("problem_statement"),
        "question": row.get("question"),
        "answer_excerpt": row.get("answer_excerpt"),
        "active_context": row.get("active_context"),
        "investigation": _load_json(row.get("investigation_json"), {}),
        "validation": _load_json(row.get("validation_json"), {}),
        "payload": _load_json(row.get("payload_json"), {}),
    }


def _document_from_row(row: Any) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    if not isinstance(row, dict):
        row = dict(row)
    return {
        "id": row.get("id"),
        "proposal_id": row.get("proposal_id"),
        "created_at": str(row.get("created_at")),
        "updated_at": str(row.get("updated_at")),
        "status": row.get("status"),
        "path": row.get("path"),
        "title": row.get("title"),
        "selection_reason": row.get("selection_reason"),
        "evidence": _load_json(row.get("evidence_json"), []),
        "current_hash": row.get("current_hash"),
        "payload": _load_json(row.get("payload_json"), {}),
    }


def _patch_from_row(row: Any) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    if not isinstance(row, dict):
        row = dict(row)
    return {
        "id": row.get("id"),
        "proposal_id": row.get("proposal_id"),
        "document_id": row.get("document_id"),
        "created_at": str(row.get("created_at")),
        "updated_at": str(row.get("updated_at")),
        "status": row.get("status"),
        "target_path": row.get("target_path"),
        "original_content": row.get("original_content"),
        "proposed_content": row.get("proposed_content"),
        "diff_text": row.get("diff_text"),
        "rationale": row.get("rationale"),
        "model": row.get("model"),
        "commit_sha": row.get("commit_sha"),
        "payload": _load_json(row.get("payload_json"), {}),
    }


def _event_from_row(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        row = dict(row)
    return {
        "id": row.get("id"),
        "proposal_id": row.get("proposal_id"),
        "created_at": str(row.get("created_at")),
        "kind": row.get("kind"),
        "message": row.get("message"),
        "payload": _load_json(row.get("payload_json"), {}),
    }


def _attachment_from_row(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        row = dict(row)
    return {
        "id": row.get("id"),
        "proposal_id": row.get("proposal_id"),
        "document_id": row.get("document_id"),
        "created_at": str(row.get("created_at")),
        "filename": row.get("filename"),
        "content_type": row.get("content_type"),
        "size_bytes": row.get("size_bytes"),
        "sha256": row.get("sha256"),
        "extracted_text": row.get("extracted_text"),
        "metadata": _load_json(row.get("metadata_json"), {}),
    }


def _record_event(conn, settings: Settings, proposal_id: str, kind: str, message: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    marker = _placeholder(settings)
    event = {
        "id": str(uuid4()),
        "proposal_id": proposal_id,
        "created_at": _now(),
        "kind": kind,
        "message": message,
        "payload": payload or {},
    }
    conn.execute(
        f"""
        INSERT INTO rag_change_events (id, proposal_id, created_at, kind, message, payload_json)
        VALUES ({",".join([marker] * 6)})
        """,
        (event["id"], proposal_id, event["created_at"], kind, message, _safe_json(event["payload"])),
    )
    return event


def _update_proposal_status(conn, settings: Settings, proposal_id: str, status: str, **fields: Any) -> None:
    marker = _placeholder(settings)
    updates = ["status = " + marker, "updated_at = " + marker]
    params: List[Any] = [status, _now()]
    for key, value in fields.items():
        column = f"{key}_json" if key in {"investigation", "validation", "payload"} else key
        updates.append(f"{column} = {marker}")
        params.append(_safe_json(value) if key in {"investigation", "validation", "payload"} else value)
    params.append(proposal_id)
    conn.execute(f"UPDATE rag_change_proposals SET {', '.join(updates)} WHERE id = {marker}", params)


def _proposal_query(conn, settings: Settings, proposal_id: str) -> Optional[Dict[str, Any]]:
    marker = _placeholder(settings)
    row = conn.execute(f"SELECT * FROM rag_change_proposals WHERE id = {marker}", (proposal_id,)).fetchone()
    return _proposal_from_row(row)


def _document_query(conn, settings: Settings, document_id: str) -> Optional[Dict[str, Any]]:
    marker = _placeholder(settings)
    row = conn.execute(f"SELECT * FROM rag_change_documents WHERE id = {marker}", (document_id,)).fetchone()
    return _document_from_row(row)


def _patch_query(conn, settings: Settings, patch_id: str) -> Optional[Dict[str, Any]]:
    marker = _placeholder(settings)
    row = conn.execute(f"SELECT * FROM rag_change_patches WHERE id = {marker}", (patch_id,)).fetchone()
    return _patch_from_row(row)


def _hydrate_proposal(conn, settings: Settings, proposal_id: str) -> Optional[Dict[str, Any]]:
    proposal = _proposal_query(conn, settings, proposal_id)
    if not proposal:
        return None
    marker = _placeholder(settings)
    docs = [
        _document_from_row(row)
        for row in conn.execute(
            f"SELECT * FROM rag_change_documents WHERE proposal_id = {marker} ORDER BY created_at ASC",
            (proposal_id,),
        ).fetchall()
    ]
    patches = [
        _patch_from_row(row)
        for row in conn.execute(
            f"SELECT * FROM rag_change_patches WHERE proposal_id = {marker} ORDER BY created_at ASC",
            (proposal_id,),
        ).fetchall()
    ]
    events = [
        _event_from_row(row)
        for row in conn.execute(
            f"SELECT * FROM rag_change_events WHERE proposal_id = {marker} ORDER BY created_at ASC",
            (proposal_id,),
        ).fetchall()
    ]
    attachments = [
        _attachment_from_row(row)
        for row in conn.execute(
            f"SELECT * FROM rag_change_attachments WHERE proposal_id = {marker} ORDER BY created_at ASC",
            (proposal_id,),
        ).fetchall()
    ]
    patch_map: Dict[str, List[Dict[str, Any]]] = {}
    for patch in patches:
        if patch:
            patch_map.setdefault(str(patch.get("document_id")), []).append(patch)
    for doc in docs:
        if doc:
            doc["patches"] = patch_map.get(str(doc.get("id")), [])
    proposal["documents"] = [doc for doc in docs if doc]
    proposal["patches"] = [patch for patch in patches if patch]
    proposal["events"] = events
    proposal["attachments"] = attachments
    proposal["timeline"] = _timeline(proposal)
    proposal["next_action"] = _next_action(proposal)
    return proposal


def _timeline(proposal: Dict[str, Any]) -> List[Dict[str, Any]]:
    events = proposal.get("events") or []
    kinds = {event.get("kind") for event in events}
    docs = proposal.get("documents") or []
    patches = proposal.get("patches") or []
    validation = proposal.get("validation") or {}
    steps = [
        ("created", "Problema registrado", "created" in kinds),
        ("investigated", "RAG investigado", "investigated" in kinds),
        ("documents_selected", "Documentos aprovados", bool(docs)),
        ("patch_generated", "Diff gerado", bool(patches)),
        ("patch_applied", "Markdown alterado", any(patch.get("status") == "applied" for patch in patches) or all(doc.get("status") in DOC_DONE_STATUSES for doc in docs if docs)),
        ("validated", "Reindex + probe validado", (validation.get("state") == "success")),
        ("resolved", "Proposta fechada", proposal.get("status") == "resolved"),
    ]
    return [{"id": key, "label": label, "done": bool(done)} for key, label, done in steps]


def _next_action(proposal: Dict[str, Any]) -> str:
    status = proposal.get("status")
    docs = proposal.get("documents") or []
    patches = proposal.get("patches") or []
    validation = proposal.get("validation") or {}
    if status == "resolved":
        return "Proposta resolvida e validada."
    if status == "archived":
        return "Proposta arquivada."
    if not proposal.get("investigation"):
        return "Investigue o RAG para entender quais documentos participaram da resposta."
    if not docs:
        return "Aprove os Markdown canonicos que devem ser alterados."
    open_docs = [doc for doc in docs if doc.get("status") not in DOC_DONE_STATUSES]
    if any(not (doc.get("patches") or []) for doc in open_docs):
        return "Gere um diff por Markdown selecionado ou ignore o documento."
    if any(patch.get("status") == "proposed" for patch in patches):
        return "Revise o diff e aplique o patch aprovado no GitHub."
    if open_docs:
        return "Conclua todos os documentos: aplicar patch ou ignorar."
    if validation.get("state") != "success":
        return "Rode a validacao: reindex + probe direcionado."
    return "Validado. A proposta ja pode ser resolvida."


def list_proposals(settings: Settings, *, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 500))
    marker = _placeholder(settings)
    params: List[Any] = []
    query = "SELECT * FROM rag_change_proposals"
    if status:
        query += f" WHERE status = {marker}"
        params.append(status)
    else:
        query += " WHERE status != " + marker
        params.append("archived")
    query += f" ORDER BY updated_at DESC LIMIT {marker}"
    params.append(limit)
    with _lock:
        with _connect(settings) as conn:
            rows = conn.execute(query, params).fetchall()
    return [_proposal_from_row(row) for row in rows if row]


def list_inbox(settings: Settings, *, limit: int = 100) -> Dict[str, Any]:
    active_feedback = [
        feedback
        for feedback in list_rag_feedback(settings, limit=limit)
        if feedback.get("status") not in {"deleted", "resolved"}
    ]
    return {
        "feedback": active_feedback[:limit],
        "proposals": list_proposals(settings, limit=limit),
    }


def create_proposal(settings: Settings, payload: Dict[str, Any]) -> Dict[str, Any]:
    title = str(payload.get("title") or payload.get("question") or "Proposta RAG").strip()[:180]
    problem = str(payload.get("problem_statement") or payload.get("instruction") or "").strip()
    proposal = {
        "id": str(uuid4()),
        "created_at": _now(),
        "updated_at": _now(),
        "status": "open",
        "title": title or "Proposta RAG",
        "origin_type": str(payload.get("origin_type") or "manual"),
        "origin_id": payload.get("origin_id"),
        "problem_statement": problem,
        "question": payload.get("question") or problem,
        "answer_excerpt": payload.get("answer_excerpt"),
        "active_context": payload.get("active_context"),
        "investigation": {},
        "validation": {},
        "payload": payload,
    }
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            conn.execute(
                f"""
                INSERT INTO rag_change_proposals
                (id, created_at, updated_at, status, title, origin_type, origin_id, problem_statement,
                 question, answer_excerpt, active_context, investigation_json, validation_json, payload_json)
                VALUES ({",".join([marker] * 14)})
                """,
                (
                    proposal["id"],
                    proposal["created_at"],
                    proposal["updated_at"],
                    proposal["status"],
                    proposal["title"],
                    proposal["origin_type"],
                    proposal["origin_id"],
                    proposal["problem_statement"],
                    proposal["question"],
                    proposal["answer_excerpt"],
                    proposal["active_context"],
                    _safe_json(proposal["investigation"]),
                    _safe_json(proposal["validation"]),
                    _safe_json(proposal["payload"]),
                ),
            )
            _record_event(conn, settings, proposal["id"], "created", "Proposta criada.", {"origin_type": proposal["origin_type"]})
            return _hydrate_proposal(conn, settings, proposal["id"]) or proposal


def create_proposal_from_feedback(settings: Settings, feedback_id: str) -> Dict[str, Any]:
    feedback = get_rag_feedback(settings, feedback_id)
    if not feedback:
        raise AppError("rag_feedback_not_found", "Feedback RAG nao encontrado.", 404)
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            duplicate = conn.execute(
                f"""
                SELECT * FROM rag_change_proposals
                WHERE origin_type = {marker} AND origin_id = {marker} AND status != {marker}
                ORDER BY created_at DESC LIMIT 1
                """,
                ("feedback", feedback_id, "archived"),
            ).fetchone()
            if duplicate:
                proposal = _hydrate_proposal(conn, settings, str(dict(duplicate).get("id")))
                return {"created": False, "proposal": proposal}

    trace = get_rag_trace(settings, str(feedback.get("trace_id") or "")) if feedback.get("trace_id") else None
    title = f"Corrigir resposta: {feedback.get('reason') or feedback.get('rating') or 'feedback'}"
    if trace and trace.get("question"):
        title = f"Corrigir RAG: {str(trace.get('question'))[:90]}"
    proposal = create_proposal(
        settings,
        {
            "title": title,
            "origin_type": "feedback",
            "origin_id": feedback_id,
            "problem_statement": feedback.get("comment") or feedback.get("expected_answer") or "Feedback negativo recebido.",
            "question": (trace or {}).get("question") or feedback.get("comment") or feedback.get("expected_answer"),
            "answer_excerpt": (trace or {}).get("answer_excerpt"),
            "active_context": (trace or {}).get("active_context"),
            "feedback": feedback,
            "trace": trace,
        },
    )
    triage_rag_feedback(settings, feedback_id, "curation_open", {"proposal_id": proposal.get("id"), "opened_at": _now()})
    return {"created": True, "proposal": proposal}


def get_proposal(settings: Settings, proposal_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        with _connect(settings) as conn:
            return _hydrate_proposal(conn, settings, proposal_id)


def _source_to_repo_path(source: str) -> Optional[str]:
    clean = (source or "").replace("\\", "/").strip("/")
    if not clean:
        return None
    if clean.startswith("knowledge/"):
        repo_path = clean
    else:
        repo_path = f"knowledge/{clean}"
    if "/_drafts/" in repo_path or repo_path.endswith("/_drafts"):
        return None
    if not repo_path.lower().endswith(".md"):
        return None
    try:
        return _normalize_repo_path(repo_path)
    except AppError:
        return None


def investigate_proposal(
    settings: Settings,
    proposal_id: str,
    *,
    question: Optional[str] = None,
    active_context: Optional[str] = None,
    limit: int = 12,
) -> Dict[str, Any]:
    start = time.perf_counter()
    with _lock:
        with _connect(settings) as conn:
            proposal = _proposal_query(conn, settings, proposal_id)
            if not proposal:
                raise AppError("proposal_not_found", "Proposta nao encontrada.", 404)
    clean_question = (question or proposal.get("question") or proposal.get("problem_statement") or "").strip()
    if not clean_question:
        raise AppError("empty_investigation", "Informe uma pergunta ou problema para investigar.", 400)
    context = active_context if active_context is not None else proposal.get("active_context")
    probe = build_rag_probe(settings, clean_question, context, limit=limit)
    evidence = probe.get("evidence") or []
    suggested_docs: Dict[str, Dict[str, Any]] = {}
    for item in evidence:
        if not isinstance(item, dict):
            continue
        repo_path = _source_to_repo_path(str(item.get("source") or ""))
        if not repo_path or repo_path in suggested_docs:
            continue
        suggested_docs[repo_path] = {
            "path": repo_path,
            "title": item.get("title") or Path(repo_path).stem,
            "selection_reason": item.get("match_reason") or item.get("summary") or "Documento recuperado pelo RAG.",
            "evidence": [item],
        }
    investigation = {
        "question": clean_question,
        "active_context": context,
        "probe": probe,
        "suggested_documents": list(suggested_docs.values()),
        "duration_ms": round((time.perf_counter() - start) * 1000, 2),
    }
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            _update_proposal_status(
                conn,
                settings,
                proposal_id,
                "investigating",
                question=clean_question,
                active_context=context,
                investigation=investigation,
            )
            for doc in suggested_docs.values():
                current = conn.execute(
                    f"SELECT id FROM rag_change_documents WHERE proposal_id = {marker} AND path = {marker}",
                    (proposal_id, doc["path"]),
                ).fetchone()
                if current:
                    continue
                content = ""
                current_hash = None
                try:
                    content = _read_canonical_markdown(settings, doc["path"])
                    current_hash = _content_hash(content)
                except AppError:
                    pass
                conn.execute(
                    f"""
                    INSERT INTO rag_change_documents
                    (id, proposal_id, created_at, updated_at, status, path, title, selection_reason, evidence_json, current_hash, payload_json)
                    VALUES ({",".join([marker] * 11)})
                    """,
                    (
                        str(uuid4()),
                        proposal_id,
                        _now(),
                        _now(),
                        "candidate",
                        doc["path"],
                        doc["title"],
                        doc["selection_reason"],
                        _safe_json(doc["evidence"]),
                        current_hash,
                        _safe_json({"suggested_by": "investigation", "content_found": bool(content)}),
                    ),
                )
            _record_event(
                conn,
                settings,
                proposal_id,
                "investigated",
                "RAG investigado e documentos candidatos registrados.",
                {"documents": list(suggested_docs), "duration_ms": investigation["duration_ms"]},
            )
            return _hydrate_proposal(conn, settings, proposal_id) or investigation


def add_documents(settings: Settings, proposal_id: str, paths: List[str]) -> Dict[str, Any]:
    normalized_paths = []
    for path in paths:
        normalized = _normalize_repo_path(path)
        if normalized not in normalized_paths:
            normalized_paths.append(normalized)
    if not normalized_paths:
        raise AppError("empty_documents", "Selecione ao menos um Markdown canonico.", 400)
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            proposal = _proposal_query(conn, settings, proposal_id)
            if not proposal:
                raise AppError("proposal_not_found", "Proposta nao encontrada.", 404)
            for repo_path in normalized_paths:
                content = _read_canonical_markdown(settings, repo_path)
                metadata = _frontmatter(content)
                existing = conn.execute(
                    f"SELECT id FROM rag_change_documents WHERE proposal_id = {marker} AND path = {marker}",
                    (proposal_id, repo_path),
                ).fetchone()
                if existing:
                    conn.execute(
                        f"UPDATE rag_change_documents SET status = {marker}, updated_at = {marker}, current_hash = {marker} WHERE proposal_id = {marker} AND path = {marker}",
                        ("selected", _now(), _content_hash(content), proposal_id, repo_path),
                    )
                    continue
                conn.execute(
                    f"""
                    INSERT INTO rag_change_documents
                    (id, proposal_id, created_at, updated_at, status, path, title, selection_reason, evidence_json, current_hash, payload_json)
                    VALUES ({",".join([marker] * 11)})
                    """,
                    (
                        str(uuid4()),
                        proposal_id,
                        _now(),
                        _now(),
                        "selected",
                        repo_path,
                        metadata.get("title") or Path(repo_path).stem,
                        "Selecionado manualmente por Gabriel.",
                        _safe_json([]),
                        _content_hash(content),
                        _safe_json({"selected_by": "admin"}),
                    ),
                )
            _update_proposal_status(conn, settings, proposal_id, "documents_selected")
            _record_event(conn, settings, proposal_id, "documents_selected", "Documentos canonicos aprovados para correcao.", {"paths": normalized_paths})
            return _hydrate_proposal(conn, settings, proposal_id) or {}


def _patch_prompt(proposal: Dict[str, Any], document: Dict[str, Any], original: str, instruction: str) -> str:
    investigation = proposal.get("investigation") or {}
    evidence = document.get("evidence") or []
    return f"""
Voce e um agente RAGOps que prepara alteracoes de Markdown para revisao humana.

Regras:
- Responda somente JSON valido.
- Nao invente fatos. Se a instrucao pedir algo sem base, inclua conflito em vez de inventar.
- Preserve frontmatter YAML valido.
- Retorne o Markdown completo em proposed_content.
- Nao use marcadores de negrito com **.

Problema/proposta:
{proposal.get("problem_statement") or ""}

Pergunta investigada:
{investigation.get("question") or proposal.get("question") or ""}

Instrucao do Gabriel:
{instruction}

Documento alvo: {document.get("path")}

Evidencias recuperadas:
{json.dumps(evidence, ensure_ascii=False, indent=2)[:7000]}

Markdown atual:
```markdown
{original}
```

Formato:
{{
  "proposed_content": "markdown completo revisado",
  "rationale": "por que a mudanca resolve o problema",
  "conflicts": ["pontos que exigem decisao humana"]
}}
""".strip()


def _fallback_proposed_content(original: str, instruction: str) -> str:
    note = instruction.strip() or "Atualizacao solicitada no RAG Studio."
    addition = f"\n\n## Atualizacao proposta pelo RAG Studio\n\n{note}\n"
    return original.rstrip() + addition


def generate_patch(settings: Settings, document_id: str, instruction: str) -> Dict[str, Any]:
    start = time.perf_counter()
    clean_instruction = (instruction or "").strip()
    if not clean_instruction:
        raise AppError("empty_patch_instruction", "Informe a instrucao para gerar o diff.", 400)
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            document = _document_query(conn, settings, document_id)
            if not document:
                raise AppError("change_document_not_found", "Documento da proposta nao encontrado.", 404)
            if document.get("status") not in {"selected", "patch_ready"}:
                raise AppError("change_document_not_selected", "Aprove o Markdown como alvo antes de gerar o diff.", 409)
            proposal = _proposal_query(conn, settings, str(document.get("proposal_id")))
            if not proposal:
                raise AppError("proposal_not_found", "Proposta nao encontrada.", 404)
    original = _read_canonical_markdown(settings, str(document["path"]))
    model = settings.openai_chat_model
    rationale = "Patch gerado por fallback deterministico."
    payload: Dict[str, Any] = {"instruction": clean_instruction, "fallback": True, "conflicts": []}
    proposed = _fallback_proposed_content(original, clean_instruction)
    try:
        llm = _build_llm(settings)
        response = llm.invoke(
            [
                SystemMessage(content="Voce e um agente RAGOps. Responda apenas JSON valido."),
                HumanMessage(content=_patch_prompt(proposal, document, original, clean_instruction)),
            ]
        )
        parsed = _extract_json_object(_response_content_to_text(response.content))
        if parsed and isinstance(parsed.get("proposed_content"), str) and parsed["proposed_content"].strip():
            proposed = sanitize_answer_text(parsed["proposed_content"]).strip()
            rationale = str(parsed.get("rationale") or "Patch sugerido pela IA.")
            payload = {
                "instruction": clean_instruction,
                "fallback": False,
                "conflicts": parsed.get("conflicts") if isinstance(parsed.get("conflicts"), list) else [],
            }
    except Exception as exc:
        payload["agent_error"] = str(exc)[:500]
    diff = _diff_text(str(document["path"]), original, proposed)
    if not diff.strip():
        raise AppError("empty_patch", "A IA nao produziu alteracao no Markdown.", 422)
    patch = {
        "id": str(uuid4()),
        "proposal_id": document["proposal_id"],
        "document_id": document_id,
        "created_at": _now(),
        "updated_at": _now(),
        "status": "proposed",
        "target_path": document["path"],
        "original_content": original,
        "proposed_content": proposed,
        "diff_text": diff,
        "rationale": rationale,
        "model": model,
        "commit_sha": None,
        "payload": {**payload, "duration_ms": round((time.perf_counter() - start) * 1000, 2)},
    }
    with _lock:
        with _connect(settings) as conn:
            conn.execute(
                f"""
                INSERT INTO rag_change_patches
                (id, proposal_id, document_id, created_at, updated_at, status, target_path, original_content,
                 proposed_content, diff_text, rationale, model, commit_sha, payload_json)
                VALUES ({",".join([marker] * 14)})
                """,
                (
                    patch["id"],
                    patch["proposal_id"],
                    patch["document_id"],
                    patch["created_at"],
                    patch["updated_at"],
                    patch["status"],
                    patch["target_path"],
                    patch["original_content"],
                    patch["proposed_content"],
                    patch["diff_text"],
                    patch["rationale"],
                    patch["model"],
                    patch["commit_sha"],
                    _safe_json(patch["payload"]),
                ),
            )
            conn.execute(
                f"UPDATE rag_change_documents SET status = {marker}, updated_at = {marker} WHERE id = {marker}",
                ("patch_ready", _now(), document_id),
            )
            _update_proposal_status(conn, settings, str(patch["proposal_id"]), "patch_ready")
            _record_event(conn, settings, str(patch["proposal_id"]), "patch_generated", "Diff gerado para revisao humana.", {"document_id": document_id, "patch_id": patch["id"]})
            return _hydrate_proposal(conn, settings, str(patch["proposal_id"])) or patch


def get_patch(settings: Settings, patch_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        with _connect(settings) as conn:
            return _patch_query(conn, settings, patch_id)


def mark_patch_applied(settings: Settings, patch_id: str, commit_sha: Optional[str]) -> Dict[str, Any]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            patch = _patch_query(conn, settings, patch_id)
            if not patch:
                raise AppError("change_patch_not_found", "Patch nao encontrado.", 404)
            conn.execute(
                f"UPDATE rag_change_patches SET status = {marker}, updated_at = {marker}, commit_sha = {marker} WHERE id = {marker}",
                ("applied", _now(), commit_sha, patch_id),
            )
            conn.execute(
                f"UPDATE rag_change_documents SET status = {marker}, updated_at = {marker} WHERE id = {marker}",
                ("applied", _now(), patch["document_id"]),
            )
            _record_event(conn, settings, str(patch["proposal_id"]), "patch_applied", "Patch aplicado no GitHub.", {"patch_id": patch_id, "commit_sha": commit_sha})
            _maybe_mark_applied(conn, settings, str(patch["proposal_id"]))
            return _hydrate_proposal(conn, settings, str(patch["proposal_id"])) or patch


def _maybe_mark_applied(conn, settings: Settings, proposal_id: str) -> None:
    marker = _placeholder(settings)
    docs = [
        _document_from_row(row)
        for row in conn.execute(
            f"SELECT * FROM rag_change_documents WHERE proposal_id = {marker}",
            (proposal_id,),
        ).fetchall()
    ]
    if docs and all(doc and doc.get("status") in DOC_DONE_STATUSES for doc in docs):
        _update_proposal_status(conn, settings, proposal_id, "applied")


def ignore_document(settings: Settings, document_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            doc = _document_query(conn, settings, document_id)
            if not doc:
                raise AppError("change_document_not_found", "Documento da proposta nao encontrado.", 404)
            payload = {**(doc.get("payload") or {}), "ignore_reason": reason}
            conn.execute(
                f"UPDATE rag_change_documents SET status = {marker}, updated_at = {marker}, payload_json = {marker} WHERE id = {marker}",
                ("ignored", _now(), _safe_json(payload), document_id),
            )
            _record_event(conn, settings, str(doc["proposal_id"]), "document_ignored", "Documento ignorado para esta proposta.", {"document_id": document_id, "reason": reason})
            _maybe_mark_applied(conn, settings, str(doc["proposal_id"]))
            return _hydrate_proposal(conn, settings, str(doc["proposal_id"])) or doc


def record_validation(settings: Settings, proposal_id: str, validation: Dict[str, Any]) -> Dict[str, Any]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            proposal = _proposal_query(conn, settings, proposal_id)
            if not proposal:
                raise AppError("proposal_not_found", "Proposta nao encontrada.", 404)
            status = "validated" if validation.get("state") == "success" else "applied"
            conn.execute(
                f"UPDATE rag_change_proposals SET status = {marker}, updated_at = {marker}, validation_json = {marker} WHERE id = {marker}",
                (status, _now(), _safe_json(validation), proposal_id),
            )
            _record_event(conn, settings, proposal_id, "validated", "Reindex e probe registrados.", validation)
            if proposal.get("origin_type") == "feedback" and proposal.get("origin_id") and validation.get("state") == "success":
                triage_rag_feedback(settings, str(proposal["origin_id"]), "validated", {"proposal_id": proposal_id, "validated_at": _now()})
            return _hydrate_proposal(conn, settings, proposal_id) or validation


def resolve_proposal(settings: Settings, proposal_id: str) -> Dict[str, Any]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            proposal = _hydrate_proposal(conn, settings, proposal_id)
            if not proposal:
                raise AppError("proposal_not_found", "Proposta nao encontrada.", 404)
            validation = proposal.get("validation") or {}
            if validation.get("state") != "success":
                raise AppError("proposal_not_validated", "Valide com reindex + probe antes de resolver.", 409)
            conn.execute(
                f"UPDATE rag_change_proposals SET status = {marker}, updated_at = {marker} WHERE id = {marker}",
                ("resolved", _now(), proposal_id),
            )
            _record_event(conn, settings, proposal_id, "resolved", "Proposta resolvida.", {})
            if proposal.get("origin_type") == "feedback" and proposal.get("origin_id"):
                triage_rag_feedback(settings, str(proposal["origin_id"]), "resolved", {"proposal_id": proposal_id, "resolved_at": _now()})
            return _hydrate_proposal(conn, settings, proposal_id) or proposal


def archive_proposal(settings: Settings, proposal_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            proposal = _proposal_query(conn, settings, proposal_id)
            if not proposal:
                raise AppError("proposal_not_found", "Proposta nao encontrada.", 404)
            conn.execute(
                f"UPDATE rag_change_proposals SET status = {marker}, updated_at = {marker} WHERE id = {marker}",
                ("archived", _now(), proposal_id),
            )
            _record_event(conn, settings, proposal_id, "archived", "Proposta arquivada.", {"reason": reason})
            return _hydrate_proposal(conn, settings, proposal_id) or proposal
