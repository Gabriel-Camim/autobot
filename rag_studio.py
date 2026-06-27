from __future__ import annotations

import difflib
import hashlib
import io
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
from rag_studio_context_store import index_context_document, remove_context_document_chunks, search_context_documents


_lock = threading.Lock()
OPEN_STATUSES = {"open", "investigating", "documents_selected", "patch_ready", "applied", "validating"}
DOC_DONE_STATUSES = {"applied", "ignored"}
CONTEXT_PENDING_STATUSES = {"extracted", "approved"}
CONTEXT_READY_STATUS = "indexed"
ALLOWED_ATTACHMENT_SUFFIXES = {".md", ".txt", ".json", ".pdf", ".docx"}
MAX_ATTACHMENTS_PER_PROPOSAL = 5
MAX_ATTACHMENT_MB = 10


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
    _add_column_if_missing(conn, "rag_change_attachments", "status", "TEXT", postgres=postgres)
    _add_column_if_missing(conn, "rag_change_attachments", "title", "TEXT", postgres=postgres)
    _add_column_if_missing(conn, "rag_change_attachments", "summary", "TEXT", postgres=postgres)
    _add_column_if_missing(conn, "rag_change_attachments", "git_path", "TEXT", postgres=postgres)
    _add_column_if_missing(conn, "rag_change_attachments", "git_commit_sha", "TEXT", postgres=postgres)
    _add_column_if_missing(conn, "rag_change_attachments", "indexed_at", "TEXT", postgres=postgres)
    _add_column_if_missing(conn, "rag_change_attachments", "ignored_at", "TEXT", postgres=postgres)


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
    if len(parts) > 1 and parts[1] in {"_drafts", "_context", "_system"}:
        raise AppError("invalid_path", "Arquivos privados do RAG Studio nao sao documentos canonicos.", 400)
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
        "status": row.get("status") or "extracted",
        "title": row.get("title") or row.get("filename"),
        "summary": row.get("summary") or "",
        "git_path": row.get("git_path"),
        "git_commit_sha": row.get("git_commit_sha"),
        "indexed_at": str(row.get("indexed_at")) if row.get("indexed_at") else None,
        "ignored_at": str(row.get("ignored_at")) if row.get("ignored_at") else None,
        "filename": row.get("filename"),
        "content_type": row.get("content_type"),
        "size_bytes": row.get("size_bytes"),
        "sha256": row.get("sha256"),
        "extracted_text": row.get("extracted_text"),
        "metadata": _load_json(row.get("metadata_json"), {}),
    }


def _attachment_public(item: Dict[str, Any]) -> Dict[str, Any]:
    output = dict(item)
    text = str(output.get("extracted_text") or "")
    output["text_preview"] = text[:700]
    output.pop("extracted_text", None)
    return output


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
            f"SELECT * FROM rag_change_patches WHERE proposal_id = {marker} ORDER BY created_at DESC",
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
            f"SELECT * FROM rag_change_attachments WHERE proposal_id = {marker} ORDER BY created_at DESC",
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
    context_documents = [_attachment_public(item) for item in attachments]
    proposal["attachments"] = context_documents
    proposal["context_documents"] = context_documents
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


def get_case_file(settings: Settings, proposal_id: str) -> Dict[str, Any]:
    proposal = get_proposal(settings, proposal_id)
    if not proposal:
        raise AppError("proposal_not_found", "Proposta nao encontrada.", 404)
    documents = []
    for doc in proposal.get("documents") or []:
        item = dict(doc)
        try:
            item["current_content"] = _read_canonical_markdown(settings, str(doc.get("path") or ""))
        except AppError as exc:
            item["current_content_error"] = exc.message
        documents.append(item)
    proposal["documents"] = documents
    return proposal


def get_document_content(settings: Settings, document_id: str) -> Dict[str, Any]:
    with _lock:
        with _connect(settings) as conn:
            document = _document_query(conn, settings, document_id)
            if not document:
                raise AppError("change_document_not_found", "Documento da proposta nao encontrado.", 404)
            proposal = _proposal_query(conn, settings, str(document["proposal_id"]))
            patches = [
                _patch_from_row(row)
                for row in conn.execute(
                    f"SELECT * FROM rag_change_patches WHERE document_id = {_placeholder(settings)} ORDER BY created_at DESC",
                    (document_id,),
                ).fetchall()
            ]
    content = _read_canonical_markdown(settings, str(document.get("path") or ""))
    return {
        "document": {**document, "patches": [patch for patch in patches if patch]},
        "proposal": proposal,
        "current_content": content,
        "current_hash": _content_hash(content),
    }


def _source_to_repo_path(source: str) -> Optional[str]:
    clean = (source or "").replace("\\", "/").strip("/")
    if not clean:
        return None
    if clean.startswith("knowledge/"):
        repo_path = clean
    else:
        repo_path = f"knowledge/{clean}"
    if any(token in repo_path for token in ["/_drafts/", "/_context/", "/_system/"]) or repo_path.endswith(("/_drafts", "/_context", "/_system")):
        return None
    if not repo_path.lower().endswith(".md"):
        return None
    try:
        return _normalize_repo_path(repo_path)
    except AppError:
        return None


def _curation_history_for_path(settings: Settings, repo_path: str, limit: int = 8) -> List[Dict[str, Any]]:
    try:
        normalized = _normalize_repo_path(repo_path)
    except AppError:
        return []
    marker = _placeholder(settings)
    try:
        with _connect(settings) as conn:
            rows = conn.execute(
                f"""
                SELECT p.id AS patch_id, p.proposal_id, p.created_at, p.updated_at, p.status,
                       p.target_path, p.rationale, p.model, p.commit_sha,
                       c.title AS proposal_title, c.origin_type, c.origin_id
                FROM rag_change_patches p
                LEFT JOIN rag_change_proposals c ON c.id = p.proposal_id
                WHERE p.target_path = {marker} AND p.status = {marker}
                ORDER BY p.updated_at DESC
                LIMIT {marker}
                """,
                (normalized, "applied", max(1, int(limit))),
            ).fetchall()
    except Exception:
        return []
    history: List[Dict[str, Any]] = []
    for row in rows:
        data = dict(row)
        history.append(
            {
                "patch_id": data.get("patch_id"),
                "proposal_id": data.get("proposal_id"),
                "proposal_title": data.get("proposal_title"),
                "origin_type": data.get("origin_type"),
                "origin_id": data.get("origin_id"),
                "target_path": data.get("target_path"),
                "rationale": data.get("rationale"),
                "model": data.get("model"),
                "commit_sha": data.get("commit_sha"),
                "created_at": str(data.get("created_at")),
                "updated_at": str(data.get("updated_at")),
            }
        )
    return history


def _enrich_probe_evidence(settings: Settings, evidence: List[Any]) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        payload = dict(item)
        repo_path = _source_to_repo_path(str(payload.get("source") or ""))
        if repo_path:
            payload["repo_path"] = repo_path
            payload.setdefault("directory", str(PurePosixPath(repo_path).parent))
            payload["curation_history"] = _curation_history_for_path(settings, repo_path)
        payload.setdefault("semantic_bridges", payload.get("bridge_ids") or [])
        enriched.append(payload)
    return enriched


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
    evidence = _enrich_probe_evidence(settings, probe.get("evidence") or [])
    probe["evidence"] = evidence
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


def _count_attachments(conn, settings: Settings, proposal_id: str) -> int:
    marker = _placeholder(settings)
    row = conn.execute(f"SELECT COUNT(*) AS total FROM rag_change_attachments WHERE proposal_id = {marker}", (proposal_id,)).fetchone()
    if isinstance(row, dict):
        return int(row.get("total") or 0)
    return int(row[0] if row else 0)


def _extract_json_text(data: bytes) -> str:
    parsed = json.loads(data.decode("utf-8"))
    return json.dumps(parsed, ensure_ascii=False, indent=2)


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise AppError("pdf_parser_missing", "Parser PDF indisponivel. Instale pypdf no backend.", 503) from exc
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages if (page.extract_text() or "").strip())


def _extract_docx_text(data: bytes) -> str:
    try:
        import docx
    except ImportError as exc:
        raise AppError("docx_parser_missing", "Parser DOCX indisponivel. Instale python-docx no backend.", 503) from exc
    document = docx.Document(io.BytesIO(data))
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())


def extract_attachment_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_ATTACHMENT_SUFFIXES:
        raise AppError("unsupported_attachment", "Anexo precisa ser .md, .txt, .json, .pdf ou .docx.", 422)
    if suffix in {".md", ".txt"}:
        return data.decode("utf-8", errors="replace")
    if suffix == ".json":
        return _extract_json_text(data)
    if suffix == ".pdf":
        return _extract_pdf_text(data)
    if suffix == ".docx":
        return _extract_docx_text(data)
    return ""


def _slugify(value: str, fallback: str = "contexto") -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return clean[:64] or fallback


def _context_git_path(proposal_id: str, context_id: str, filename: str) -> str:
    stem = _slugify(Path(filename).stem, "documento")
    date = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"knowledge/_context/rag-studio/{proposal_id}/{date}-{stem}-{context_id[:8]}.md"


def context_document_markdown(document: Dict[str, Any]) -> str:
    title = str(document.get("title") or f"Contexto externo: {document.get('filename')}")
    metadata = {
        "title": title,
        "category": "rag-studio-context",
        "tags": ["rag-studio", "context", "external-document"],
        "visibility": "context",
        "priority": 5,
        "updated_at": datetime.now(timezone.utc).date().isoformat(),
        "summary": document.get("summary") or "Documento contextual privado usado somente no RAG Studio.",
        "proposal_id": document.get("proposal_id"),
        "context_id": document.get("id"),
        "source_filename": document.get("filename"),
        "source_hash": document.get("sha256"),
        "status": document.get("status") or "extracted",
    }
    frontmatter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    extracted = str(document.get("extracted_text") or "").strip()
    return (
        f"---\n{frontmatter}\n---\n\n"
        f"# {title}\n\n"
        "> Documento contextual privado. Ele nao entra no RAG publico; primeiro precisa orientar um patch aprovado em Markdown canonico.\n\n"
        f"{extracted}\n"
    )


def prepare_context_document(settings: Settings, proposal_id: str, *, filename: str, content_type: str, data: bytes) -> Dict[str, Any]:
    safe_name = Path(filename or "attachment.txt").name
    max_bytes = MAX_ATTACHMENT_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise AppError("attachment_too_large", "Anexo maior que 10 MB.", 422)
    extracted = extract_attachment_text(safe_name, data).strip()
    if not extracted:
        raise AppError("empty_attachment", "Nao consegui extrair texto deste anexo.", 422)
    context_id = str(uuid4())
    attachment = {
        "id": context_id,
        "proposal_id": proposal_id,
        "document_id": None,
        "created_at": _now(),
        "status": "extracted",
        "title": f"Contexto externo: {safe_name}",
        "summary": f"Texto extraido de {safe_name} para curadoria no RAG Studio.",
        "git_path": _context_git_path(proposal_id, context_id, safe_name),
        "git_commit_sha": None,
        "indexed_at": None,
        "ignored_at": None,
        "filename": safe_name,
        "content_type": content_type or "application/octet-stream",
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "extracted_text": extracted[:120000],
        "metadata": {"suffix": Path(safe_name).suffix.lower(), "truncated": len(extracted) > 120000},
    }
    return attachment


def save_context_document(settings: Settings, document: Dict[str, Any], *, git_commit_sha: Optional[str] = None) -> Dict[str, Any]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            proposal_id = str(document.get("proposal_id"))
            proposal = _proposal_query(conn, settings, proposal_id)
            if not proposal:
                raise AppError("proposal_not_found", "Proposta nao encontrada.", 404)
            if _count_attachments(conn, settings, proposal_id) >= MAX_ATTACHMENTS_PER_PROPOSAL:
                raise AppError("too_many_attachments", "Limite de 5 anexos por proposta atingido.", 422)
            conn.execute(
                f"""
                INSERT INTO rag_change_attachments
                (id, proposal_id, document_id, created_at, filename, content_type, size_bytes, sha256, extracted_text, metadata_json,
                 status, title, summary, git_path, git_commit_sha, indexed_at, ignored_at)
                VALUES ({",".join([marker] * 17)})
                """,
                (
                    document["id"],
                    document["proposal_id"],
                    document.get("document_id"),
                    document["created_at"],
                    document["filename"],
                    document["content_type"],
                    document["size_bytes"],
                    document["sha256"],
                    document["extracted_text"],
                    _safe_json(document.get("metadata") or {}),
                    document.get("status") or "extracted",
                    document.get("title") or document.get("filename"),
                    document.get("summary") or "",
                    document.get("git_path"),
                    git_commit_sha,
                    document.get("indexed_at"),
                    document.get("ignored_at"),
                ),
            )
            _record_event(
                conn,
                settings,
                proposal_id,
                "context_document_extracted",
                "Documento contextual extraido e persistido para revisao.",
                {"context_id": document["id"], "filename": document["filename"], "git_path": document.get("git_path")},
            )
            saved = _attachment_from_row(
                conn.execute(f"SELECT * FROM rag_change_attachments WHERE id = {marker}", (document["id"],)).fetchone()
            )
    return _attachment_public(saved)


def add_attachment(settings: Settings, proposal_id: str, *, filename: str, content_type: str, data: bytes) -> Dict[str, Any]:
    document = prepare_context_document(settings, proposal_id, filename=filename, content_type=content_type, data=data)
    return save_context_document(settings, document)


def delete_attachment(settings: Settings, attachment_id: str) -> bool:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            if _uses_postgres(settings):
                row = conn.execute(f"DELETE FROM rag_change_attachments WHERE id = {marker} RETURNING proposal_id", (attachment_id,)).fetchone()
                if row:
                    proposal_id = dict(row).get("proposal_id")
                    if proposal_id:
                        _record_event(conn, settings, str(proposal_id), "attachment_deleted", "Anexo privado removido.", {"attachment_id": attachment_id})
                return bool(row)
            row = conn.execute(f"SELECT proposal_id FROM rag_change_attachments WHERE id = {marker}", (attachment_id,)).fetchone()
            cursor = conn.execute(f"DELETE FROM rag_change_attachments WHERE id = {marker}", (attachment_id,))
            if cursor.rowcount > 0 and row:
                proposal_id = dict(row).get("proposal_id")
                _record_event(conn, settings, str(proposal_id), "attachment_deleted", "Anexo privado removido.", {"attachment_id": attachment_id})
            return cursor.rowcount > 0


def get_context_document(settings: Settings, context_id: str, *, include_text: bool = True) -> Optional[Dict[str, Any]]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            row = conn.execute(f"SELECT * FROM rag_change_attachments WHERE id = {marker}", (context_id,)).fetchone()
    item = _attachment_from_row(row) if row else None
    if not item:
        return None
    return item if include_text else _attachment_public(item)


def list_context_documents(settings: Settings, proposal_id: str) -> List[Dict[str, Any]]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            rows = conn.execute(
                f"SELECT * FROM rag_change_attachments WHERE proposal_id = {marker} ORDER BY created_at DESC",
                (proposal_id,),
            ).fetchall()
    return [_attachment_public(_attachment_from_row(row)) for row in rows]


def approve_context_document(settings: Settings, context_id: str) -> Dict[str, Any]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            row = conn.execute(f"SELECT * FROM rag_change_attachments WHERE id = {marker}", (context_id,)).fetchone()
            if not row:
                raise AppError("context_document_not_found", "Documento contextual nao encontrado.", 404)
            item = _attachment_from_row(row)
            if item.get("status") == "ignored":
                raise AppError("context_document_ignored", "Documento contextual ignorado nao pode ser aprovado.", 409)
            metadata = {**(item.get("metadata") or {}), "previous_status": item.get("status") or "extracted"}
            conn.execute(
                f"UPDATE rag_change_attachments SET status = {marker}, indexed_at = NULL, ignored_at = NULL, metadata_json = {marker} WHERE id = {marker}",
                ("approved", _safe_json(metadata), context_id),
            )
            _record_event(
                conn,
                settings,
                str(item["proposal_id"]),
                "context_document_approved",
                "Documento contextual aprovado para indexacao privada.",
                {"context_id": context_id},
            )
            updated = _attachment_from_row(conn.execute(f"SELECT * FROM rag_change_attachments WHERE id = {marker}", (context_id,)).fetchone())
    return _attachment_public(updated)


def index_approved_context_document(settings: Settings, context_id: str) -> Dict[str, Any]:
    document = get_context_document(settings, context_id, include_text=True)
    if not document:
        raise AppError("context_document_not_found", "Documento contextual nao encontrado.", 404)
    if document.get("status") not in {"approved", "indexed"}:
        raise AppError("context_document_not_approved", "Aprove o documento contextual antes de indexar.", 409)
    result = index_context_document(settings, document)
    if not result.get("indexed"):
        raise AppError("context_index_failed", str(result.get("error") or "Nao foi possivel indexar o documento contextual."), 503)
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            conn.execute(
                f"UPDATE rag_change_attachments SET status = {marker}, indexed_at = {marker} WHERE id = {marker}",
                ("indexed", result.get("indexed_at") or _now(), context_id),
            )
            _record_event(
                conn,
                settings,
                str(document["proposal_id"]),
                "context_document_indexed",
                "Documento contextual aprovado e indexado no RAG Studio.",
                {"context_id": context_id, "chunks": result.get("chunks")},
            )
            updated = _attachment_from_row(conn.execute(f"SELECT * FROM rag_change_attachments WHERE id = {marker}", (context_id,)).fetchone())
    return {"context_document": _attachment_public(updated), "index": result}


def ignore_context_document(settings: Settings, context_id: str) -> Dict[str, Any]:
    document = get_context_document(settings, context_id, include_text=True)
    if not document:
        raise AppError("context_document_not_found", "Documento contextual nao encontrado.", 404)
    remove_context_document_chunks(settings, context_id)
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            metadata = {**(document.get("metadata") or {}), "previous_status": document.get("status") or "extracted"}
            conn.execute(
                f"UPDATE rag_change_attachments SET status = {marker}, ignored_at = {marker}, indexed_at = NULL, metadata_json = {marker} WHERE id = {marker}",
                ("ignored", _now(), _safe_json(metadata), context_id),
            )
            _record_event(
                conn,
                settings,
                str(document["proposal_id"]),
                "context_document_ignored",
                "Documento contextual ignorado para esta proposta.",
                {"context_id": context_id},
            )
            updated = _attachment_from_row(conn.execute(f"SELECT * FROM rag_change_attachments WHERE id = {marker}", (context_id,)).fetchone())
    return _attachment_public(updated)


def restore_context_document(settings: Settings, context_id: str) -> Dict[str, Any]:
    document = get_context_document(settings, context_id, include_text=True)
    if not document:
        raise AppError("context_document_not_found", "Documento contextual nao encontrado.", 404)
    current_status = str(document.get("status") or "extracted")
    metadata = dict(document.get("metadata") or {})
    if current_status == "indexed":
        remove_context_document_chunks(settings, context_id)
        next_status = "approved"
    elif current_status == "approved":
        next_status = "extracted"
    elif current_status == "ignored":
        next_status = str(metadata.get("previous_status") or "extracted")
        if next_status == "indexed":
            next_status = "approved"
    else:
        raise AppError("context_restore_not_available", "Este documento contextual ainda nao tem uma etapa reversivel.", 409)
    metadata["restored_from"] = current_status
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            conn.execute(
                f"UPDATE rag_change_attachments SET status = {marker}, ignored_at = NULL, indexed_at = NULL, metadata_json = {marker} WHERE id = {marker}",
                (next_status, _safe_json(metadata), context_id),
            )
            _record_event(
                conn,
                settings,
                str(document["proposal_id"]),
                "context_restored",
                "Etapa do documento contextual desfeita.",
                {"context_id": context_id, "from": current_status, "to": next_status},
            )
            updated = _attachment_from_row(conn.execute(f"SELECT * FROM rag_change_attachments WHERE id = {marker}", (context_id,)).fetchone())
    return _attachment_public(updated)


def delete_context_document(settings: Settings, context_id: str) -> bool:
    remove_context_document_chunks(settings, context_id)
    return delete_attachment(settings, context_id)


def _attachments_for_prompt(conn, settings: Settings, proposal_id: str, document_id: str) -> List[Dict[str, Any]]:
    marker = _placeholder(settings)
    rows = conn.execute(
        f"""
        SELECT * FROM rag_change_attachments
        WHERE proposal_id = {marker} AND (document_id IS NULL OR document_id = {marker})
        ORDER BY created_at DESC
        """,
        (proposal_id, document_id),
    ).fetchall()
    return [_attachment_from_row(row) for row in rows]


def _context_documents_for_proposal(conn, settings: Settings, proposal_id: str) -> List[Dict[str, Any]]:
    marker = _placeholder(settings)
    rows = conn.execute(
        f"SELECT * FROM rag_change_attachments WHERE proposal_id = {marker} ORDER BY created_at DESC",
        (proposal_id,),
    ).fetchall()
    return [_attachment_from_row(row) for row in rows]


def _private_context_prompt_block(context_hits: List[Dict[str, Any]]) -> str:
    if not context_hits:
        return "Nenhum trecho de contexto privado foi recuperado."
    blocks: List[str] = []
    for item in context_hits[:8]:
        text = str(item.get("excerpt") or "").strip()
        if not text:
            continue
        blocks.append(
            "\n".join(
                [
                    f"[contexto privado: {item.get('title') or item.get('source')}]",
                    f"source: {item.get('source')}",
                    f"context_id: {item.get('context_id')}",
                    f"score: {item.get('relevance_score')}",
                    text[:1200],
                ]
            )
        )
    return "\n\n---\n\n".join(blocks) if blocks else "Nenhum trecho util foi recuperado do contexto privado."


def _patch_prompt(
    proposal: Dict[str, Any],
    document: Dict[str, Any],
    original: str,
    instruction: str,
    private_context: Optional[List[Dict[str, Any]]] = None,
    current_content_snapshot: Optional[str] = None,
) -> str:
    investigation = proposal.get("investigation") or {}
    evidence = document.get("evidence") or []
    private_context_block = _private_context_prompt_block(private_context or [])
    current_snapshot_block = (
        f"""
Snapshot editado pelo Gabriel para partir desta versao:
```markdown
{current_content_snapshot}
```
"""
        if current_content_snapshot and current_content_snapshot.strip()
        else "Nenhum snapshot editado foi enviado; parta do Markdown atual."
    )
    return f"""
Voce e um agente RAGOps que prepara alteracoes de Markdown para revisao humana.

Regras:
- Responda somente JSON valido.
- Nao invente fatos. Se a instrucao pedir algo sem base, inclua conflito em vez de inventar.
- Preserve frontmatter YAML valido.
- Retorne o Markdown completo em proposed_content.
- Nao use marcadores de negrito com **.
- Contexto privado indexado e contexto publico sao auxiliares. Se conflitarem com o Markdown atual, registre em conflicts.
- Nao trate contexto privado como fonte publica ate Gabriel aprovar o diff no Markdown canonico.

Problema/proposta:
{proposal.get("problem_statement") or ""}

Pergunta investigada:
{investigation.get("question") or proposal.get("question") or ""}

Instrucao do Gabriel:
{instruction}

Documento alvo: {document.get("path")}

Evidencias recuperadas:
{json.dumps(evidence, ensure_ascii=False, indent=2)[:7000]}

Contexto privado indexado do RAG Studio:
{private_context_block}

Snapshot atual do diff/editor:
{current_snapshot_block}

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


def generate_patch(
    settings: Settings,
    document_id: str,
    instruction: str,
    *,
    current_content_snapshot: Optional[str] = None,
) -> Dict[str, Any]:
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
            context_documents = _context_documents_for_proposal(conn, settings, str(proposal["id"]))
            pending_context = [item for item in context_documents if item.get("status") in CONTEXT_PENDING_STATUSES]
            if pending_context:
                raise AppError(
                    "context_documents_pending",
                    "Revise, indexe ou ignore os documentos de contexto pendentes antes de gerar o diff.",
                    409,
                )
    original = _read_canonical_markdown(settings, str(document["path"]))
    private_context_error: Optional[str] = None
    try:
        private_context = search_context_documents(
            settings,
            str(proposal["id"]),
            "\n".join(
                item
                for item in [
                    clean_instruction,
                    current_content_snapshot or "",
                    str(proposal.get("question") or ""),
                    str(proposal.get("problem_statement") or ""),
                    str(document.get("path") or ""),
                ]
                if item
            ),
            limit=6,
        )
    except Exception as exc:
        private_context = []
        private_context_error = str(exc)[:300]
    model = settings.openai_chat_model
    rationale = "Patch gerado por fallback deterministico."
    context_document_ids = sorted({str(item.get("context_id")) for item in private_context if item.get("context_id")})
    payload: Dict[str, Any] = {
        "instruction": clean_instruction,
        "fallback": True,
        "conflicts": [],
        "context_document_ids": context_document_ids,
        "private_context": private_context,
        "current_content_snapshot": bool(current_content_snapshot and current_content_snapshot.strip()),
        "private_context_error": private_context_error,
    }
    proposed = (current_content_snapshot or "").strip() or _fallback_proposed_content(original, clean_instruction)
    try:
        llm = _build_llm(settings)
        response = llm.invoke(
            [
                SystemMessage(content="Voce e um agente RAGOps. Responda apenas JSON valido."),
                HumanMessage(
                    content=_patch_prompt(
                        proposal,
                        document,
                        original,
                        clean_instruction,
                        private_context,
                        current_content_snapshot=current_content_snapshot,
                    )
                ),
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
                "context_document_ids": context_document_ids,
                "private_context": private_context,
                "current_content_snapshot": bool(current_content_snapshot and current_content_snapshot.strip()),
                "private_context_error": private_context_error,
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
                f"UPDATE rag_change_patches SET status = {marker}, updated_at = {marker} WHERE document_id = {marker} AND status = {marker}",
                ("superseded", _now(), document_id, "proposed"),
            )
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
            _record_event(
                conn,
                settings,
                str(patch["proposal_id"]),
                "patch_generated",
                "Diff gerado para revisao humana.",
                {"document_id": document_id, "patch_id": patch["id"], "context_document_ids": context_document_ids},
            )
            hydrated = _hydrate_proposal(conn, settings, str(patch["proposal_id"])) or patch
            hydrated["new_patch_id"] = patch["id"]
            return hydrated


def edit_patch_content(settings: Settings, patch_id: str, proposed_content: str) -> Dict[str, Any]:
    clean_content = (proposed_content or "").strip()
    if not clean_content:
        raise AppError("empty_patch_content", "O diff precisa ter conteudo para salvar.", 400)
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            patch = _patch_query(conn, settings, patch_id)
            if not patch:
                raise AppError("change_patch_not_found", "Patch nao encontrado.", 404)
            if patch.get("status") != "proposed":
                raise AppError("patch_edit_not_available", "Apenas diffs propostos podem ser editados.", 409)
            diff = _diff_text(str(patch["target_path"]), str(patch["original_content"] or ""), clean_content)
            if not diff.strip():
                raise AppError("empty_patch", "O conteudo salvo nao gera diferenca no Markdown.", 422)
            payload = {**(patch.get("payload") or {}), "edited_by_admin": True}
            conn.execute(
                f"""
                UPDATE rag_change_patches
                SET proposed_content = {marker}, diff_text = {marker}, payload_json = {marker}, updated_at = {marker}
                WHERE id = {marker}
                """,
                (clean_content, diff, _safe_json(payload), _now(), patch_id),
            )
            _record_event(
                conn,
                settings,
                str(patch["proposal_id"]),
                "patch_saved",
                "Diff editado e salvo para revisao.",
                {"patch_id": patch_id, "document_id": patch.get("document_id")},
            )
            proposal = _hydrate_proposal(conn, settings, str(patch["proposal_id"]))
            if proposal:
                proposal["saved_patch_id"] = patch_id
            return proposal or {"id": str(patch["proposal_id"]), "saved_patch_id": patch_id}


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


def discard_patch(settings: Settings, patch_id: str) -> Dict[str, Any]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            patch = _patch_query(conn, settings, patch_id)
            if not patch:
                raise AppError("change_patch_not_found", "Patch nao encontrado.", 404)
            if patch.get("status") != "proposed":
                raise AppError("patch_discard_not_available", "Apenas diffs propostos podem ser descartados.", 409)
            conn.execute(
                f"UPDATE rag_change_patches SET status = {marker}, updated_at = {marker} WHERE id = {marker}",
                ("discarded", _now(), patch_id),
            )
            active_patch = conn.execute(
                f"SELECT id FROM rag_change_patches WHERE document_id = {marker} AND status = {marker} LIMIT 1",
                (patch["document_id"], "proposed"),
            ).fetchone()
            if not active_patch:
                conn.execute(
                    f"UPDATE rag_change_documents SET status = {marker}, updated_at = {marker} WHERE id = {marker} AND status = {marker}",
                    ("selected", _now(), patch["document_id"], "patch_ready"),
                )
            _update_proposal_status(conn, settings, str(patch["proposal_id"]), "documents_selected")
            _record_event(
                conn,
                settings,
                str(patch["proposal_id"]),
                "patch_discarded",
                "Diff descartado antes de aplicar no Git.",
                {"patch_id": patch_id, "document_id": patch["document_id"]},
            )
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
            payload = {**(doc.get("payload") or {}), "ignore_reason": reason, "previous_status": doc.get("status")}
            conn.execute(
                f"UPDATE rag_change_documents SET status = {marker}, updated_at = {marker}, payload_json = {marker} WHERE id = {marker}",
                ("ignored", _now(), _safe_json(payload), document_id),
            )
            _record_event(conn, settings, str(doc["proposal_id"]), "document_ignored", "Documento ignorado para esta proposta.", {"document_id": document_id, "reason": reason})
            _maybe_mark_applied(conn, settings, str(doc["proposal_id"]))
            return _hydrate_proposal(conn, settings, str(doc["proposal_id"])) or doc


def restore_document(settings: Settings, document_id: str) -> Dict[str, Any]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            doc = _document_query(conn, settings, document_id)
            if not doc:
                raise AppError("change_document_not_found", "Documento da proposta nao encontrado.", 404)
            current_status = str(doc.get("status") or "")
            if current_status == "ignored":
                next_status = str((doc.get("payload") or {}).get("previous_status") or "candidate")
                if next_status in {"applied", "ignored", "patch_ready"}:
                    next_status = "selected"
            elif current_status == "selected":
                next_status = "candidate"
            else:
                raise AppError("document_restore_not_available", "Este documento nao tem uma etapa reversivel agora.", 409)
            payload = {**(doc.get("payload") or {}), "restored_from": current_status}
            conn.execute(
                f"UPDATE rag_change_documents SET status = {marker}, updated_at = {marker}, payload_json = {marker} WHERE id = {marker}",
                (next_status, _now(), _safe_json(payload), document_id),
            )
            _update_proposal_status(conn, settings, str(doc["proposal_id"]), "documents_selected" if next_status == "selected" else "investigating")
            _record_event(
                conn,
                settings,
                str(doc["proposal_id"]),
                "document_restored",
                "Decisao sobre documento desfeita.",
                {"document_id": document_id, "from": current_status, "to": next_status},
            )
            return _hydrate_proposal(conn, settings, str(doc["proposal_id"])) or doc


def create_reverse_proposal_from_patch(settings: Settings, patch_id: str) -> Dict[str, Any]:
    marker = _placeholder(settings)
    with _lock:
        with _connect(settings) as conn:
            patch = _patch_query(conn, settings, patch_id)
            if not patch:
                raise AppError("change_patch_not_found", "Patch nao encontrado.", 404)
            if patch.get("status") != "applied":
                raise AppError("reverse_requires_applied_patch", "Somente patches ja aplicados geram proposta reversa.", 409)
            original_proposal = _proposal_query(conn, settings, str(patch["proposal_id"])) or {}
    current_content = _read_canonical_markdown(settings, str(patch["target_path"]))
    reverse = create_proposal(
        settings,
        {
            "title": f"Reverter alteracao: {patch.get('target_path')}",
            "origin_type": "reverse_patch",
            "origin_id": patch_id,
            "problem_statement": "Revisar reversao de patch canonico aplicado anteriormente.",
            "question": original_proposal.get("question") or original_proposal.get("problem_statement"),
            "active_context": original_proposal.get("active_context"),
            "source_patch_id": patch_id,
        },
    )
    reverse_with_doc = add_documents(settings, str(reverse["id"]), [str(patch["target_path"])])
    reverse_documents = reverse_with_doc.get("documents") or []
    reverse_document_id = str(reverse_documents[0].get("id") or "") if reverse_documents else ""
    diff = _diff_text(str(patch["target_path"]), current_content, str(patch.get("original_content") or ""))
    reverse_patch = {
        "id": str(uuid4()),
        "proposal_id": reverse["id"],
        "document_id": reverse_document_id,
        "created_at": _now(),
        "updated_at": _now(),
        "status": "proposed",
        "target_path": patch["target_path"],
        "original_content": current_content,
        "proposed_content": patch.get("original_content") or "",
        "diff_text": diff,
        "rationale": f"Proposta reversa do patch {patch_id}.",
        "model": "reverse-proposal",
        "commit_sha": None,
        "payload": {"source_patch_id": patch_id},
    }
    if not reverse_patch["document_id"]:
        raise AppError("reverse_document_missing", "Nao consegui criar documento alvo da proposta reversa.", 500)
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
                    reverse_patch["id"],
                    reverse_patch["proposal_id"],
                    reverse_patch["document_id"],
                    reverse_patch["created_at"],
                    reverse_patch["updated_at"],
                    reverse_patch["status"],
                    reverse_patch["target_path"],
                    reverse_patch["original_content"],
                    reverse_patch["proposed_content"],
                    reverse_patch["diff_text"],
                    reverse_patch["rationale"],
                    reverse_patch["model"],
                    reverse_patch["commit_sha"],
                    _safe_json(reverse_patch["payload"]),
                ),
            )
            conn.execute(
                f"UPDATE rag_change_documents SET status = {marker}, updated_at = {marker} WHERE id = {marker}",
                ("patch_ready", _now(), reverse_patch["document_id"]),
            )
            _update_proposal_status(conn, settings, str(reverse["id"]), "patch_ready")
            _record_event(
                conn,
                settings,
                str(reverse["id"]),
                "reverse_proposal_created",
                "Proposta reversa criada para revisao humana.",
                {"source_patch_id": patch_id, "patch_id": reverse_patch["id"]},
            )
            return _hydrate_proposal(conn, settings, str(reverse["id"])) or reverse


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
