from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional
from uuid import uuid4

import yaml
from langchain_core.messages import HumanMessage, SystemMessage

from agent import AppError, _build_llm, _response_content_to_text, sanitize_answer_text
from config import Settings
from rag_studio import extract_attachment_text


MAX_ATTACHMENTS = 5
MAX_ATTACHMENT_MB = 10


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uses_postgres(settings: Settings) -> bool:
    return settings.database_url.strip().startswith(("postgres://", "postgresql://"))


def _placeholder(settings: Settings) -> str:
    return "%s" if _uses_postgres(settings) else "?"


def _connect(settings: Settings):
    if _uses_postgres(settings):
        import psycopg
        from psycopg.rows import dict_row

        conn = psycopg.connect(settings.database_url.strip(), row_factory=dict_row, autocommit=True)
        _ensure_schema(conn, postgres=True)
        return conn

    db_path = settings.resolved_events_db_path.parent / "markdown_ai.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn, postgres=False)
    return conn


def _ensure_schema(conn, *, postgres: bool) -> None:
    text = "TEXT"
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS markdown_ai_sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            mode TEXT NOT NULL,
            path TEXT,
            base_content {text} NOT NULL,
            selected_version_id TEXT,
            payload_json {text} NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS markdown_ai_versions (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            parent_version_id TEXT,
            instruction {text} NOT NULL,
            content {text} NOT NULL,
            model TEXT,
            bridges_json {text} NOT NULL,
            payload_json {text} NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS markdown_ai_attachments (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            filename TEXT NOT NULL,
            content_type TEXT,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            extracted_text {text} NOT NULL,
            git_path TEXT,
            git_commit_sha TEXT,
            metadata_json {text} NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_markdown_ai_versions_session ON markdown_ai_versions(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_markdown_ai_attachments_session ON markdown_ai_attachments(session_id)")


def _safe_json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, separators=(",", ":"), default=str)


def _load_json(value: Any, fallback: Any = None) -> Any:
    if value in (None, ""):
        return {} if fallback is None else fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {} if fallback is None else fallback


def _row_to_session(row: Any) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    if not isinstance(row, dict):
        row = dict(row)
    return {
        "id": row.get("id"),
        "created_at": str(row.get("created_at")),
        "updated_at": str(row.get("updated_at")),
        "mode": row.get("mode"),
        "path": row.get("path"),
        "base_content": row.get("base_content") or "",
        "selected_version_id": row.get("selected_version_id"),
        "payload": _load_json(row.get("payload_json"), {}),
    }


def _row_to_version(row: Any) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    if not isinstance(row, dict):
        row = dict(row)
    return {
        "id": row.get("id"),
        "session_id": row.get("session_id"),
        "created_at": str(row.get("created_at")),
        "status": row.get("status"),
        "parent_version_id": row.get("parent_version_id"),
        "instruction": row.get("instruction") or "",
        "content": row.get("content") or "",
        "model": row.get("model"),
        "bridges": _load_json(row.get("bridges_json"), []),
        "payload": _load_json(row.get("payload_json"), {}),
    }


def _row_to_attachment(row: Any, *, include_text: bool = False) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    if not isinstance(row, dict):
        row = dict(row)
    extracted = row.get("extracted_text") or ""
    output = {
        "id": row.get("id"),
        "session_id": row.get("session_id"),
        "created_at": str(row.get("created_at")),
        "filename": row.get("filename"),
        "content_type": row.get("content_type"),
        "size_bytes": row.get("size_bytes"),
        "sha256": row.get("sha256"),
        "git_path": row.get("git_path"),
        "git_commit_sha": row.get("git_commit_sha"),
        "metadata": _load_json(row.get("metadata_json"), {}),
        "text_preview": " ".join(extracted.split())[:900],
    }
    if include_text:
        output["extracted_text"] = extracted
    return output


def _hydrate_session(conn, settings: Settings, session_id: str) -> Dict[str, Any]:
    marker = _placeholder(settings)
    session = _row_to_session(conn.execute(f"SELECT * FROM markdown_ai_sessions WHERE id = {marker}", (session_id,)).fetchone())
    if not session:
        raise AppError("markdown_ai_session_not_found", "Sessão Markdown AI não encontrada.", 404)
    versions = [
        _row_to_version(row)
        for row in conn.execute(
            f"SELECT * FROM markdown_ai_versions WHERE session_id = {marker} ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
    ]
    attachments = [
        _row_to_attachment(row)
        for row in conn.execute(
            f"SELECT * FROM markdown_ai_attachments WHERE session_id = {marker} ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
    ]
    session["versions"] = [item for item in versions if item]
    session["attachments"] = [item for item in attachments if item]
    return session


def create_session(settings: Settings, *, mode: str, path: str, base_content: str) -> Dict[str, Any]:
    if mode not in {"edit", "create"}:
        raise AppError("invalid_markdown_ai_mode", "Modo precisa ser edit ou create.", 422)
    session_id = str(uuid4())
    marker = _placeholder(settings)
    with _connect(settings) as conn:
        conn.execute(
            f"""
            INSERT INTO markdown_ai_sessions
            (id, created_at, updated_at, mode, path, base_content, selected_version_id, payload_json)
            VALUES ({",".join([marker] * 8)})
            """,
            (session_id, _now(), _now(), mode, path, base_content or "", None, _safe_json({})),
        )
        return _hydrate_session(conn, settings, session_id)


def get_session(settings: Settings, session_id: str) -> Dict[str, Any]:
    with _connect(settings) as conn:
        return _hydrate_session(conn, settings, session_id)


def _context_git_path(session_id: str, attachment_id: str, filename: str) -> str:
    stem = Path(filename or "documento").stem.lower()
    stem = "".join(ch if ch.isalnum() else "-" for ch in stem).strip("-")[:64] or "documento"
    date = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"knowledge/_context/markdown-ai/{session_id}/{date}-{stem}-{attachment_id[:8]}.md"


def attachment_markdown(attachment: Dict[str, Any]) -> str:
    metadata = {
        "title": f"Contexto Markdown AI: {attachment.get('filename')}",
        "category": "markdown-ai-context",
        "tags": ["markdown-ai", "context", "external-document"],
        "visibility": "context",
        "priority": 5,
        "updated_at": datetime.now(timezone.utc).date().isoformat(),
        "summary": f"Documento privado usado para gerar Markdown no admin: {attachment.get('filename')}.",
        "markdown_ai_session_id": attachment.get("session_id"),
        "context_id": attachment.get("id"),
        "source_filename": attachment.get("filename"),
        "source_hash": attachment.get("sha256"),
    }
    frontmatter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    return (
        f"---\n{frontmatter}\n---\n\n"
        f"# Contexto Markdown AI: {attachment.get('filename')}\n\n"
        "> Documento privado. Ele não entra no RAG público automaticamente.\n\n"
        f"{str(attachment.get('extracted_text') or '').strip()}\n"
    )


def prepare_attachment(settings: Settings, session_id: str, *, filename: str, content_type: str, data: bytes) -> Dict[str, Any]:
    safe_name = Path(filename or "attachment.txt").name
    if len(data) > MAX_ATTACHMENT_MB * 1024 * 1024:
        raise AppError("markdown_ai_attachment_too_large", "Anexo maior que 10 MB.", 422)
    extracted = extract_attachment_text(safe_name, data).strip()
    if not extracted:
        raise AppError("markdown_ai_attachment_empty", "Não consegui extrair texto deste anexo.", 422)
    attachment_id = str(uuid4())
    sha256 = hashlib.sha256(data).hexdigest()
    return {
        "id": attachment_id,
        "session_id": session_id,
        "created_at": _now(),
        "filename": safe_name,
        "content_type": content_type,
        "size_bytes": len(data),
        "sha256": sha256,
        "extracted_text": extracted[:120000],
        "git_path": _context_git_path(session_id, attachment_id, safe_name),
        "metadata": {"truncated": len(extracted) > 120000, "suffix": Path(safe_name).suffix.lower()},
    }


def save_attachment(settings: Settings, attachment: Dict[str, Any], *, commit_sha: Optional[str] = None) -> Dict[str, Any]:
    marker = _placeholder(settings)
    with _connect(settings) as conn:
        row = conn.execute(
            f"SELECT COUNT(*) AS total FROM markdown_ai_attachments WHERE session_id = {marker}",
            (attachment["session_id"],),
        ).fetchone()
        total = int((dict(row) if not isinstance(row, dict) else row).get("total") or 0)
        if total >= MAX_ATTACHMENTS:
            raise AppError("markdown_ai_too_many_attachments", "Limite de 5 anexos por sessão atingido.", 422)
        conn.execute(
            f"""
            INSERT INTO markdown_ai_attachments
            (id, session_id, created_at, filename, content_type, size_bytes, sha256, extracted_text, git_path, git_commit_sha, metadata_json)
            VALUES ({",".join([marker] * 11)})
            """,
            (
                attachment["id"],
                attachment["session_id"],
                attachment["created_at"],
                attachment["filename"],
                attachment.get("content_type"),
                attachment["size_bytes"],
                attachment["sha256"],
                attachment["extracted_text"],
                attachment["git_path"],
                commit_sha,
                _safe_json(attachment.get("metadata") or {}),
            ),
        )
        return _hydrate_session(conn, settings, attachment["session_id"])


def _default_markdown(path: str, instruction: str) -> str:
    title = Path(PurePosixPath(path or "novo-documento.md").stem).stem.replace("-", " ").title() or "Novo Documento"
    metadata = {
        "title": title,
        "category": "geral",
        "tags": [],
        "visibility": "public",
        "priority": 3,
        "updated_at": datetime.now(timezone.utc).date().isoformat(),
        "summary": instruction[:160] or "Documento criado com apoio da IA.",
    }
    frontmatter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{frontmatter}\n---\n\n# {title}\n\n{instruction.strip() or 'Conteúdo a curar.'}\n"


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    clean = (text or "").strip()
    if clean.startswith("```"):
        clean = clean.strip("`")
        clean = clean.removeprefix("json").strip()
    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(clean[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _generation_prompt(session: Dict[str, Any], base_content: str, instruction: str, attachments: List[Dict[str, Any]]) -> str:
    attachment_block = "\n\n".join(
        f"### {item.get('filename')}\n{str(item.get('extracted_text') or '')[:12000]}" for item in attachments
    )
    return f"""
Você é o editor técnico da base Markdown pública do Gabriel.
Gere ou refine um único arquivo Markdown com frontmatter YAML completo.

Modo: {session.get("mode")}
Caminho alvo: {session.get("path")}
Instrução do Gabriel:
{instruction}

Conteúdo base:
```markdown
{base_content}
```

Anexos privados extraídos:
{attachment_block or "Nenhum anexo enviado."}

Regras:
- preservar fatos; não inventar tecnologias, datas ou resultados;
- usar português com acentuação correta;
- criar title, category, tags, visibility, priority, updated_at e summary;
- sugerir semantic bridges quando houver aliases úteis;
- responder somente JSON válido.

Formato:
{{
  "content": "markdown completo",
  "semantic_bridges": [
    {{
      "id": "alias-curto",
      "aliases": ["termo"],
      "expansion_terms": ["termo relacionado"],
      "target_sources": ["knowledge/...md"],
      "active_contexts": ["gabriel"],
      "priority_boost": 0.2
    }}
  ],
  "notes": "observações de curadoria"
}}
""".strip()


def generate_version(
    settings: Settings,
    session_id: str,
    *,
    instruction: str,
    base_version_id: Optional[str] = None,
) -> Dict[str, Any]:
    clean_instruction = (instruction or "").strip()
    if not clean_instruction:
        raise AppError("markdown_ai_empty_instruction", "Informe uma instrução para gerar a versão.", 422)
    marker = _placeholder(settings)
    start = time.perf_counter()
    with _connect(settings) as conn:
        session = _hydrate_session(conn, settings, session_id)
        base_version = None
        if base_version_id:
            base_version = _row_to_version(
                conn.execute(
                    f"SELECT * FROM markdown_ai_versions WHERE id = {marker} AND session_id = {marker}",
                    (base_version_id, session_id),
                ).fetchone()
            )
        elif session.get("selected_version_id"):
            base_version = _row_to_version(
                conn.execute(
                    f"SELECT * FROM markdown_ai_versions WHERE id = {marker}",
                    (session.get("selected_version_id"),),
                ).fetchone()
            )
        attachments = [
            _row_to_attachment(row, include_text=True)
            for row in conn.execute(
                f"SELECT * FROM markdown_ai_attachments WHERE session_id = {marker} ORDER BY created_at DESC",
                (session_id,),
            ).fetchall()
        ]
    base_content = str(base_version.get("content") if base_version else session.get("base_content") or "")
    if not base_content.strip():
        base_content = _default_markdown(str(session.get("path") or ""), clean_instruction)
    content = _default_markdown(str(session.get("path") or ""), clean_instruction)
    bridges: List[Dict[str, Any]] = []
    payload: Dict[str, Any] = {"fallback": True, "notes": "", "attachment_count": len(attachments)}
    model = settings.openai_chat_model
    try:
        llm = _build_llm(settings)
        response = llm.invoke(
            [
                SystemMessage(content="Você responde somente JSON válido para curadoria Markdown."),
                HumanMessage(content=_generation_prompt(session, base_content, clean_instruction, attachments)),
            ]
        )
        parsed = _extract_json_object(_response_content_to_text(response.content))
        if parsed and isinstance(parsed.get("content"), str) and parsed["content"].strip():
            content = sanitize_answer_text(parsed["content"]).strip()
            if isinstance(parsed.get("semantic_bridges"), list):
                bridges = parsed["semantic_bridges"]
            payload = {
                "fallback": False,
                "notes": parsed.get("notes") or "",
                "attachment_count": len(attachments),
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            }
    except Exception as exc:
        content = base_content.rstrip() + f"\n\n## Atualização sugerida\n\n{clean_instruction}\n"
        payload["agent_error"] = str(exc)[:500]
    version_id = str(uuid4())
    with _connect(settings) as conn:
        conn.execute(
            f"""
            INSERT INTO markdown_ai_versions
            (id, session_id, created_at, status, parent_version_id, instruction, content, model, bridges_json, payload_json)
            VALUES ({",".join([marker] * 10)})
            """,
            (
                version_id,
                session_id,
                _now(),
                "generated",
                base_version.get("id") if base_version else None,
                clean_instruction,
                content,
                model,
                _safe_json(bridges),
                _safe_json(payload),
            ),
        )
        conn.execute(
            f"UPDATE markdown_ai_sessions SET selected_version_id = {marker}, updated_at = {marker} WHERE id = {marker}",
            (version_id, _now(), session_id),
        )
        return _hydrate_session(conn, settings, session_id)


def use_version(settings: Settings, version_id: str) -> Dict[str, Any]:
    marker = _placeholder(settings)
    with _connect(settings) as conn:
        version = _row_to_version(conn.execute(f"SELECT * FROM markdown_ai_versions WHERE id = {marker}", (version_id,)).fetchone())
        if not version:
            raise AppError("markdown_ai_version_not_found", "Versão Markdown AI não encontrada.", 404)
        conn.execute(
            f"UPDATE markdown_ai_sessions SET selected_version_id = {marker}, updated_at = {marker} WHERE id = {marker}",
            (version_id, _now(), version["session_id"]),
        )
        session = _hydrate_session(conn, settings, version["session_id"])
    return {"version": version, "session": session}


def get_version(settings: Settings, version_id: str) -> Dict[str, Any]:
    marker = _placeholder(settings)
    with _connect(settings) as conn:
        version = _row_to_version(conn.execute(f"SELECT * FROM markdown_ai_versions WHERE id = {marker}", (version_id,)).fetchone())
    if not version:
        raise AppError("markdown_ai_version_not_found", "Versão Markdown AI não encontrada.", 404)
    return version
