from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx
import yaml
from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from agent import AppError, build_rag_probe, realtime_search_knowledge
from config import Settings, get_settings
from draft_studio import (
    add_attachment,
    add_targets_to_case,
    create_case_from_feedback,
    create_curation_case,
    create_draft,
    delete_attachment,
    delete_draft,
    generate_draft_with_agent,
    get_curation_case,
    get_draft,
    get_patch,
    ignore_case_draft,
    list_canonical_documents,
    list_curation_cases,
    list_drafts,
    propose_patch_from_draft,
    record_case_eval,
    record_case_reindex,
    refresh_curation_case_status,
    revert_draft_step,
    resolve_curation_case,
    update_draft,
    update_patch_status,
)
from events import event_summary, list_events, log_event
from ingest import ingest, load_public_documents
from job_scans import delete_job_scan, get_job_scan, list_job_scans
from pgvector_store import pgvector_status, uses_pgvector
from rag_lab import coverage_summary, last_eval_run, run_rag_eval
from rag_quality import (
    archive_rag_feedback,
    eval_case_from_suggestion,
    get_knowledge_suggestion,
    get_rag_trace,
    list_knowledge_suggestions,
    list_rag_feedback,
    list_rag_traces,
    triage_rag_feedback,
    update_knowledge_suggestion_details,
    update_knowledge_suggestion_status,
)
import rag_studio
import markdown_ai
from warmup import start_warmup, warmup_status


router = APIRouter(prefix="/admin", tags=["admin"])

GITHUB_API = "https://api.github.com"
GITHUB_AUTHORIZE = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN = "https://github.com/login/oauth/access_token"

_reindex_lock = threading.Lock()
_reindex_status: Dict[str, Any] = {
    "state": "idle",
    "started_at": None,
    "finished_at": None,
    "duration_ms": None,
    "document_count": 0,
    "chunk_count": 0,
    "vector_backend": None,
    "vector_ready": None,
    "vector_chunks": None,
    "last_reindex_at": None,
    "sample_query": None,
    "sample_sources": [],
    "sample_ok": None,
    "sample_error": None,
    "github_branch": None,
    "case_id": None,
    "error": None,
}


class AdminUser(BaseModel):
    login: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class AdminSessionResponse(BaseModel):
    authenticated: bool
    user: Optional[AdminUser] = None
    configured: bool


class TreeNode(BaseModel):
    name: str
    path: str
    type: Literal["directory", "file"]
    children: List["TreeNode"] = Field(default_factory=list)


class KnowledgeTreeResponse(BaseModel):
    roots: List[TreeNode]


class KnowledgeFileResponse(BaseModel):
    path: str
    content: str
    exists: bool


class FileWriteRequest(BaseModel):
    path: str
    content: str
    message: Optional[str] = None


class FolderRequest(BaseModel):
    path: str
    message: Optional[str] = None


class PromptResponse(BaseModel):
    path: str
    content: str


class PromptWriteRequest(BaseModel):
    content: str
    message: Optional[str] = None


class CommitResponse(BaseModel):
    ok: bool
    path: str
    commit_sha: Optional[str] = None
    html_url: Optional[str] = None


class ImportResponse(BaseModel):
    ok: bool
    files: List[CommitResponse]


class ReindexStatusResponse(BaseModel):
    state: str
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    duration_ms: Optional[int] = None
    document_count: int = 0
    chunk_count: int = 0
    vector_backend: Optional[str] = None
    vector_ready: Optional[bool] = None
    vector_chunks: Optional[int] = None
    last_reindex_at: Optional[str] = None
    sample_query: Optional[str] = None
    sample_sources: List[str] = Field(default_factory=list)
    sample_ok: Optional[bool] = None
    sample_error: Optional[str] = None
    github_branch: Optional[str] = None
    knowledge_dir: Optional[str] = None
    storage_target: Optional[str] = None
    case_id: Optional[str] = None
    error: Optional[str] = None


class RagProbeRequest(BaseModel):
    question: str
    active_context: Optional[str] = None
    limit: int = Field(default=8, ge=1, le=20)


class RagFeedbackTriageRequest(BaseModel):
    status: str = Field(default="triaged")
    notes: Optional[str] = None
    action: Optional[str] = None


class SuggestionActionRequest(BaseModel):
    message: Optional[str] = None
    status: Optional[str] = None


class SuggestionUpdateRequest(BaseModel):
    title: Optional[str] = None
    suggested_path: Optional[str] = None
    frontmatter: Optional[Dict[str, Any]] = None
    draft_markdown: Optional[str] = None
    status: Optional[str] = None
    rationale: Optional[str] = None


class DraftCreateRequest(BaseModel):
    title: Optional[str] = None
    instruction: Optional[str] = None
    suggestion_id: Optional[str] = None
    trace_id: Optional[str] = None
    suggested_path: Optional[str] = None
    canonical_targets: List[str] = Field(default_factory=list)
    draft_markdown: Optional[str] = None


class DraftUpdateRequest(BaseModel):
    title: Optional[str] = None
    instruction: Optional[str] = None
    status: Optional[str] = None
    suggested_path: Optional[str] = None
    draft_markdown: Optional[str] = None
    canonical_targets: Optional[List[str]] = None


class DraftAgentRequest(BaseModel):
    instruction: str
    target_paths: List[str] = Field(default_factory=list)


class DraftActionRequest(BaseModel):
    message: Optional[str] = None
    target_path: Optional[str] = None
    patch_id: Optional[str] = None
    step: Optional[str] = None


class CurationCaseCreateRequest(BaseModel):
    title: Optional[str] = None
    instruction: Optional[str] = None
    trace_id: Optional[str] = None
    target_paths: List[str] = Field(default_factory=list)


class CurationCaseTargetsRequest(BaseModel):
    target_paths: List[str] = Field(default_factory=list)


class CurationCaseResolveRequest(BaseModel):
    message: Optional[str] = None


class RagStudioProposalCreateRequest(BaseModel):
    title: Optional[str] = None
    problem_statement: Optional[str] = None
    question: Optional[str] = None
    active_context: Optional[str] = None
    origin_type: Optional[str] = None
    origin_id: Optional[str] = None


class RagStudioInvestigateRequest(BaseModel):
    question: Optional[str] = None
    active_context: Optional[str] = None
    limit: int = Field(default=12, ge=1, le=20)


class RagStudioDocumentsRequest(BaseModel):
    paths: List[str] = Field(default_factory=list)


class RagStudioPatchRequest(BaseModel):
    instruction: str


class RagStudioArchiveRequest(BaseModel):
    reason: Optional[str] = None


class MarkdownAiSessionRequest(BaseModel):
    mode: Literal["edit", "create"]
    path: Optional[str] = None
    base_content: str = ""


class MarkdownAiGenerateRequest(BaseModel):
    instruction: str
    base_version_id: Optional[str] = None


class MarkdownAiCommitRequest(BaseModel):
    path: str
    message: Optional[str] = None


class MarkdownAiBridgeApplyRequest(BaseModel):
    message: Optional[str] = None


TreeNode.model_rebuild()


def _settings() -> Settings:
    return get_settings()


def _admin_configured(settings: Settings) -> bool:
    return bool(settings.github_oauth_client_id and settings.github_oauth_client_secret and settings.admin_session_secret)


def _github_configured(settings: Settings) -> bool:
    return bool(settings.github_repo and settings.github_content_token)


def _safe_samesite(settings: Settings) -> Literal["lax", "strict", "none"]:
    value = settings.admin_cookie_samesite.lower()
    if value in {"lax", "strict", "none"}:
        return value  # type: ignore[return-value]
    return "none"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(value: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).digest()
    return _b64(digest)


def _session_token(user: Dict[str, Any], settings: Settings) -> str:
    payload = {
        "login": user.get("login"),
        "name": user.get("name"),
        "avatar_url": user.get("avatar_url"),
        "exp": int(time.time() + settings.admin_session_hours * 3600),
    }
    encoded = _b64(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    return f"{encoded}.{_sign(encoded, settings.admin_session_secret)}"


def _read_session_token(token: str, settings: Settings) -> Optional[AdminUser]:
    if not token or "." not in token or not settings.admin_session_secret:
        return None
    encoded, signature = token.rsplit(".", 1)
    expected = _sign(encoded, settings.admin_session_secret)
    if not secrets.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_unb64(encoded).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(payload.get("exp", 0) or 0) < int(time.time()):
        return None
    login = str(payload.get("login") or "")
    if login.lower() not in settings.admin_github_user_list:
        return None
    return AdminUser(login=login, name=payload.get("name"), avatar_url=payload.get("avatar_url"))


def _is_allowed_frontend_return(settings: Settings, return_to: str) -> bool:
    parts = urlsplit(return_to)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return False
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin.rstrip("/") in settings.frontend_origin_list:
        return True
    try:
        return bool(re.fullmatch(settings.cors_allow_origin_regex, origin))
    except re.error:
        return False


def _sanitize_admin_return_to(settings: Settings, return_to: Optional[str]) -> Optional[str]:
    if not return_to:
        return None
    parts = urlsplit(return_to.strip())
    if not parts.path.startswith("/admin"):
        return None
    clean = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
    return clean if _is_allowed_frontend_return(settings, clean) else None


def _oauth_state_cookie_value(state: str, return_to: Optional[str]) -> str:
    payload = {"state": state, "return_to": return_to or ""}
    return _b64(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _read_oauth_state_cookie(value: str) -> tuple[str, Optional[str]]:
    if not value:
        return "", None
    try:
        payload = json.loads(_unb64(value).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return value, None
    return str(payload.get("state") or ""), str(payload.get("return_to") or "") or None


def _admin_redirect_with_token(settings: Settings, token: str, return_to: Optional[str] = None) -> str:
    parts = urlsplit(return_to or settings.admin_redirect_url)
    fragment = urlencode({"admin_token": token})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, fragment))


def _set_cookie(response, name: str, value: str, settings: Settings, max_age: int) -> None:
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        httponly=True,
        secure=settings.admin_cookie_secure,
        samesite=_safe_samesite(settings),
    )


def _clear_cookie(response, name: str, settings: Settings) -> None:
    response.delete_cookie(name, httponly=True, secure=settings.admin_cookie_secure, samesite=_safe_samesite(settings))


def _current_admin(request: Request, settings: Settings) -> Optional[AdminUser]:
    cookie_user = _read_session_token(request.cookies.get(settings.admin_cookie_name, ""), settings)
    if cookie_user:
        return cookie_user
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return _read_session_token(token.strip(), settings)
    return None


def _require_admin(request: Request, settings: Settings) -> AdminUser:
    if not _admin_configured(settings):
        raise AppError("admin_not_configured", "Painel admin ainda não configurado no backend.", 503)
    user = _current_admin(request, settings)
    if not user:
        raise AppError("admin_unauthorized", "Faça login com GitHub para acessar o painel admin.", 401)
    return user


def _require_github(settings: Settings) -> None:
    if not _github_configured(settings):
        raise AppError("github_not_configured", "GITHUB_CONTENT_TOKEN ou GITHUB_REPO não configurado.", 503)


def _sanitize_error(exc: Exception) -> str:
    message = str(exc)
    for sensitive in (_settings().github_content_token, _settings().github_oauth_client_secret, _settings().admin_session_secret):
        if sensitive:
            message = message.replace(sensitive, "[redacted]")
    return message[:500]


def _github_oauth_token_error(payload: Any, status_code: int) -> str:
    if isinstance(payload, dict):
        parts = [
            str(payload.get("error") or "").strip(),
            str(payload.get("error_description") or "").strip(),
        ]
        details = " - ".join(part for part in parts if part)
        if details:
            return _sanitize_error(RuntimeError(details))
    return f"status {status_code}"


def _normalize_posix_path(raw_path: str) -> str:
    cleaned = raw_path.strip().replace("\\", "/").strip("/")
    if not cleaned:
        raise AppError("invalid_path", "Informe um caminho válido.", 400)
    path = PurePosixPath(cleaned)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise AppError("invalid_path", "Caminho inválido.", 400)
    return path.as_posix()


def _resolve_content_path(raw_path: str, settings: Settings, *, require_markdown: bool = True) -> tuple[str, Path]:
    normalized = _normalize_posix_path(raw_path)
    parts = PurePosixPath(normalized).parts
    if parts[0] == "knowledge":
        base = settings.resolved_knowledge_dir
        relative = PurePosixPath(*parts[1:]) if len(parts) > 1 else PurePosixPath()
    elif len(parts) >= 2 and parts[0] == "materials" and parts[1] == "recruiter-pack":
        base = settings.resolved_materials_dir
        relative = PurePosixPath(*parts[2:]) if len(parts) > 2 else PurePosixPath()
    else:
        raise AppError("invalid_path", "Admin v1 só edita knowledge/ e materials/recruiter-pack/.", 400)

    if require_markdown and PurePosixPath(normalized).suffix.lower() != ".md":
        raise AppError("invalid_path", "Admin v1 só edita arquivos Markdown.", 400)

    target = (base / Path(relative.as_posix())).resolve()
    base_resolved = base.resolve()
    if target != base_resolved and base_resolved not in target.parents:
        raise AppError("invalid_path", "Caminho fora do diretório permitido.", 400)
    return normalized, target


def _validate_markdown_frontmatter(content: str) -> Dict[str, Any]:
    if not content.startswith("---"):
        raise AppError("invalid_markdown_frontmatter", "O Markdown precisa começar com frontmatter YAML entre ---.", 422)
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise AppError("invalid_markdown_frontmatter", "Frontmatter YAML incompleto. Feche o bloco com ---.", 422)
    try:
        metadata = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise AppError(
            "invalid_markdown_frontmatter",
            f"Frontmatter YAML inválido: {_sanitize_error(exc)}",
            422,
        ) from exc
    if not isinstance(metadata, dict):
        raise AppError("invalid_markdown_frontmatter", "Frontmatter precisa ser um objeto YAML.", 422)
    required = ("title", "category", "visibility", "priority", "summary")
    missing = [field for field in required if metadata.get(field) in (None, "")]
    if missing:
        raise AppError("invalid_markdown_frontmatter", f"Frontmatter sem campos obrigatórios: {', '.join(missing)}.", 422)
    return metadata


def _prompt_paths(settings: Settings) -> tuple[str, Path]:
    target = settings.resolved_system_prompt_path.resolve()
    backend_dir = settings.backend_dir.resolve()
    if backend_dir != target and backend_dir not in target.parents:
        raise AppError("invalid_prompt_path", "SYSTEM_PROMPT_PATH fora do backend.", 400)
    return _normalize_posix_path(settings.github_prompt_path), target


def _tree_for_root(root: Path, label: str) -> TreeNode:
    root = root.resolve()

    def build(directory: Path, posix_prefix: str) -> Optional[TreeNode]:
        children: List[TreeNode] = []
        if directory.exists():
            for item in sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                child_path = f"{posix_prefix}/{item.name}"
                if item.is_dir():
                    child = build(item, child_path)
                    if child and child.children:
                        children.append(child)
                elif item.suffix.lower() == ".md":
                    children.append(TreeNode(name=item.name, path=child_path, type="file"))
        return TreeNode(name=directory.name if posix_prefix != label else label, path=posix_prefix, type="directory", children=children)

    return build(root, label) or TreeNode(name=label, path=label, type="directory")


def _github_content_url(settings: Settings, repo_path: str) -> str:
    owner_repo = settings.github_repo.strip().strip("/")
    return f"{GITHUB_API}/repos/{owner_repo}/contents/{repo_path}"


def _github_headers(settings: Settings) -> Dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {settings.github_content_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _github_existing_sha(settings: Settings, repo_path: str) -> Optional[str]:
    with httpx.Client(timeout=20) as client:
        response = client.get(
            _github_content_url(settings, repo_path),
            headers=_github_headers(settings),
            params={"ref": settings.github_branch},
        )
    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise AppError("github_read_failed", f"GitHub recusou leitura de {repo_path}: {response.status_code}", 502)
    data = response.json()
    return data.get("sha")


def _github_read_text(settings: Settings, repo_path: str) -> Optional[str]:
    _require_github(settings)
    with httpx.Client(timeout=20) as client:
        response = client.get(
            _github_content_url(settings, repo_path),
            headers=_github_headers(settings),
            params={"ref": settings.github_branch},
        )
    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise AppError("github_read_failed", f"GitHub recusou leitura de {repo_path}: {response.status_code}", 502)
    data = response.json()
    content = data.get("content") or ""
    if data.get("encoding") == "base64":
        return base64.b64decode(content).decode("utf-8")
    return str(content)


def _github_put(settings: Settings, repo_path: str, content: str, message: str) -> CommitResponse:
    _require_github(settings)
    sha = _github_existing_sha(settings, repo_path)
    payload: Dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": settings.github_branch,
    }
    if sha:
        payload["sha"] = sha

    with httpx.Client(timeout=30) as client:
        response = client.put(_github_content_url(settings, repo_path), headers=_github_headers(settings), json=payload)
    if response.status_code >= 400:
        raise AppError("github_write_failed", f"GitHub recusou escrita de {repo_path}: {response.status_code}", 502)

    data = response.json()
    commit = data.get("commit") or {}
    return CommitResponse(ok=True, path=repo_path, commit_sha=commit.get("sha"), html_url=commit.get("html_url"))


def _github_delete(settings: Settings, repo_path: str, message: str) -> CommitResponse:
    _require_github(settings)
    sha = _github_existing_sha(settings, repo_path)
    if not sha:
        raise AppError("file_not_found", "Arquivo não encontrado no GitHub.", 404)
    payload = {"message": message, "sha": sha, "branch": settings.github_branch}

    with httpx.Client(timeout=30) as client:
        response = client.request("DELETE", _github_content_url(settings, repo_path), headers=_github_headers(settings), json=payload)
    if response.status_code >= 400:
        raise AppError("github_delete_failed", f"GitHub recusou exclusão de {repo_path}: {response.status_code}", 502)

    data = response.json()
    commit = data.get("commit") or {}
    return CommitResponse(ok=True, path=repo_path, commit_sha=commit.get("sha"), html_url=commit.get("html_url"))


def _admin_sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/session", response_model=AdminSessionResponse)
def admin_session(request: Request):
    settings = _settings()
    return AdminSessionResponse(
        authenticated=bool(_current_admin(request, settings)),
        user=_current_admin(request, settings),
        configured=_admin_configured(settings),
    )


@router.get("/bootstrap")
def admin_bootstrap(request: Request):
    settings = _settings()
    user = _current_admin(request, settings)
    vector_status = (
        pgvector_status(settings)
        if uses_pgvector(settings)
        else {"backend": "chroma", "ready": False, "chunks": None, "last_reindex_at": None, "error": None, "index_type": "none"}
    )
    return {
        "session": {
            "authenticated": bool(user),
            "user": user.model_dump() if user else None,
            "configured": _admin_configured(settings),
        },
        "environment": {
            "version": settings.app_version,
            "commit": settings.app_commit,
            "app_env": settings.app_env,
            "github_branch": settings.github_branch,
            "public_frontend_url": settings.public_frontend_url,
            "admin_frontend_url": settings.admin_frontend_url,
            "public_backend_url": settings.public_backend_url or settings.admin_public_base_url,
        },
        "rag": {
            "vector_backend": vector_status.get("backend"),
            "vector_index_ready": vector_status.get("ready"),
            "vector_index_type": vector_status.get("index_type"),
            "vector_chunks": vector_status.get("chunks"),
            "last_reindex_at": vector_status.get("last_reindex_at"),
            "vector_error": vector_status.get("error"),
            "rerank_enabled": settings.rag_rerank_enabled,
            "rerank_provider": settings.rag_rerank_provider,
        },
        "warmup": warmup_status(),
        "features": {
            "rag_lab": True,
            "rag_studio": True,
            "semantic_bridges": True,
            "rollback": True,
            "context_documents": True,
        },
    }


@router.get("/auth/github/login")
def github_login(return_to: Optional[str] = Query(default=None)):
    settings = _settings()
    if not _admin_configured(settings):
        raise AppError("admin_not_configured", "Configure GitHub OAuth e ADMIN_SESSION_SECRET no Render.", 503)

    state = secrets.token_urlsafe(32)
    safe_return_to = _sanitize_admin_return_to(settings, return_to)
    redirect_uri = settings.admin_callback_base_url + "/admin/auth/github/callback"
    params = urlencode(
        {
            "client_id": settings.github_oauth_client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user",
            "state": state,
            "allow_signup": "false",
        }
    )
    response = RedirectResponse(f"{GITHUB_AUTHORIZE}?{params}")
    _set_cookie(response, settings.admin_state_cookie_name, _oauth_state_cookie_value(state, safe_return_to), settings, max_age=600)
    return response


@router.get("/auth/github/callback")
def github_callback(request: Request, code: str = Query(default=""), state: str = Query(default="")):
    settings = _settings()
    if not _admin_configured(settings):
        raise AppError("admin_not_configured", "Configure GitHub OAuth e ADMIN_SESSION_SECRET no Render.", 503)
    expected_state, return_to = _read_oauth_state_cookie(request.cookies.get(settings.admin_state_cookie_name, ""))
    if not state or not expected_state or not secrets.compare_digest(state, expected_state):
        raise AppError("admin_oauth_state_invalid", "Sessão OAuth inválida. Tente login novamente.", 401)
    if not code:
        raise AppError("admin_oauth_missing_code", "GitHub não retornou código de autorização.", 400)

    redirect_uri = settings.admin_callback_base_url + "/admin/auth/github/callback"
    try:
        with httpx.Client(timeout=20) as client:
            token_response = client.post(
                GITHUB_TOKEN,
                headers={"Accept": "application/json", "User-Agent": "gabriel-portfolio-admin"},
                data={
                    "client_id": settings.github_oauth_client_id,
                    "client_secret": settings.github_oauth_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "state": state,
                },
            )
            token_response.raise_for_status()
            token_payload = token_response.json()
            access_token = token_payload.get("access_token") if isinstance(token_payload, dict) else None
            if not access_token:
                details = _github_oauth_token_error(token_payload, token_response.status_code)
                raise AppError("admin_oauth_token_missing", f"GitHub não retornou token de acesso: {details}.", 401)
            user_response = client.get(
                f"{GITHUB_API}/user",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {access_token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            user_response.raise_for_status()
            user = user_response.json()
    except httpx.HTTPError as exc:
        raise AppError("admin_oauth_failed", f"Falha ao concluir OAuth do GitHub: {_sanitize_error(exc)}", 502) from exc

    login = str(user.get("login") or "")
    if login.lower() not in settings.admin_github_user_list:
        raise AppError("admin_forbidden", "Este usuário GitHub não está autorizado para o painel.", 403)

    session_token = _session_token(user, settings)
    response = RedirectResponse(_admin_redirect_with_token(settings, session_token, return_to))
    _set_cookie(response, settings.admin_cookie_name, session_token, settings, max_age=settings.admin_session_hours * 3600)
    _clear_cookie(response, settings.admin_state_cookie_name, settings)
    return response


@router.post("/auth/logout")
def admin_logout():
    response = JSONResponse({"ok": True})
    _clear_cookie(response, _settings().admin_cookie_name, _settings())
    return response


@router.get("/knowledge/tree", response_model=KnowledgeTreeResponse)
def knowledge_tree(request: Request):
    settings = _settings()
    _require_admin(request, settings)
    return KnowledgeTreeResponse(
        roots=[
            _tree_for_root(settings.resolved_knowledge_dir, "knowledge"),
            _tree_for_root(settings.resolved_materials_dir, "materials/recruiter-pack"),
        ]
    )


@router.get("/knowledge/file", response_model=KnowledgeFileResponse)
def read_knowledge_file(path: str, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    normalized, target = _resolve_content_path(path, settings)
    if not target.exists():
        return KnowledgeFileResponse(path=normalized, content="", exists=False)
    return KnowledgeFileResponse(path=normalized, content=target.read_text(encoding="utf-8"), exists=True)


@router.put("/knowledge/file", response_model=CommitResponse)
def write_knowledge_file(payload: FileWriteRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    normalized, target = _resolve_content_path(payload.path, settings)
    _validate_markdown_frontmatter(payload.content)
    message = payload.message or f"admin: update {normalized}"
    commit = _github_put(settings, normalized, payload.content, message)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8", newline="\n")
    log_event(settings, "admin_file_write", request=request, session_id=user.login, actor_type="admin", payload=commit.model_dump())
    return commit


@router.delete("/knowledge/file", response_model=CommitResponse)
def delete_knowledge_file(path: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    normalized, target = _resolve_content_path(path, settings)
    commit = _github_delete(settings, normalized, f"admin: delete {normalized}")
    if target.exists():
        target.unlink()
    log_event(settings, "admin_file_delete", request=request, session_id=user.login, actor_type="admin", payload=commit.model_dump())
    return commit


@router.post("/markdown-ai/sessions")
def admin_markdown_ai_create_session(payload: MarkdownAiSessionRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    session = markdown_ai.create_session(
        settings,
        mode=payload.mode,
        path=payload.path or "",
        base_content=payload.base_content,
    )
    log_event(
        settings,
        "admin_markdown_ai_session",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"session_id": session["id"], "mode": payload.mode, "path": payload.path},
    )
    return session


@router.get("/markdown-ai/sessions/{session_id}")
def admin_markdown_ai_get_session(session_id: str, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    return markdown_ai.get_session(settings, session_id)


@router.post("/markdown-ai/sessions/{session_id}/attachments")
async def admin_markdown_ai_attachments(session_id: str, request: Request, files: List[UploadFile] = File(...)):
    settings = _settings()
    user = _require_admin(request, settings)
    current_session = markdown_ai.get_session(settings, session_id)
    if len(current_session.get("attachments") or []) + len(files) > markdown_ai.MAX_ATTACHMENTS:
        raise AppError("markdown_ai_too_many_attachments", "Limite de 5 anexos por sessão atingido.", 422)
    saved_session = None
    commits: List[Dict[str, Any]] = []
    for upload in files:
        data = await upload.read()
        attachment = markdown_ai.prepare_attachment(
            settings,
            session_id,
            filename=upload.filename or "attachment.txt",
            content_type=upload.content_type or "application/octet-stream",
            data=data,
        )
        markdown = markdown_ai.attachment_markdown(attachment)
        commit = _github_put(settings, attachment["git_path"], markdown, f"markdown-ai: add context {attachment['filename']}")
        normalized, target = _resolve_content_path(str(attachment["git_path"]), settings)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8", newline="\n")
        saved_session = markdown_ai.save_attachment(settings, attachment, commit_sha=commit.commit_sha)
        commits.append(commit.model_dump())
        log_event(
            settings,
            "admin_markdown_ai_attachment",
            request=request,
            session_id=user.login,
            actor_type="admin",
            payload={"session_id": session_id, "path": normalized, "commit_sha": commit.commit_sha},
        )
    return {"session": saved_session or markdown_ai.get_session(settings, session_id), "commits": commits}


@router.post("/markdown-ai/sessions/{session_id}/generate")
def admin_markdown_ai_generate(session_id: str, payload: MarkdownAiGenerateRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    session = markdown_ai.generate_version(
        settings,
        session_id,
        instruction=payload.instruction,
        base_version_id=payload.base_version_id,
    )
    log_event(
        settings,
        "admin_markdown_ai_generate",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"session_id": session_id, "version_id": session.get("selected_version_id")},
    )
    return session


@router.post("/markdown-ai/versions/{version_id}/use")
def admin_markdown_ai_use_version(version_id: str, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    return markdown_ai.use_version(settings, version_id)


@router.post("/markdown-ai/versions/{version_id}/commit")
def admin_markdown_ai_commit_version(version_id: str, payload: MarkdownAiCommitRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    version = markdown_ai.get_version(settings, version_id)
    normalized, target = _resolve_content_path(payload.path, settings)
    _validate_markdown_frontmatter(version["content"])
    commit = _github_put(settings, normalized, version["content"], payload.message or f"markdown-ai: update {normalized}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(version["content"], encoding="utf-8", newline="\n")
    log_event(
        settings,
        "admin_markdown_ai_commit",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"version_id": version_id, "path": normalized, "commit_sha": commit.commit_sha},
    )
    return {"commit": commit.model_dump(), "version": version}


@router.post("/markdown-ai/versions/{version_id}/bridges/apply")
def admin_markdown_ai_apply_bridges(version_id: str, payload: MarkdownAiBridgeApplyRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    version = markdown_ai.get_version(settings, version_id)
    bridges = version.get("bridges") or []
    if not bridges:
        raise AppError("markdown_ai_no_bridges", "Esta versão não tem semantic bridges sugeridas.", 422)
    repo_path = "knowledge/_system/semantic-bridges.yaml"
    current = _github_read_text(settings, repo_path)
    if current is None:
        _normalized, target = _resolve_content_path(repo_path, settings, require_markdown=False)
        current = target.read_text(encoding="utf-8") if target.exists() else "version: 1\nconcepts: []\n"
    parsed = yaml.safe_load(current) or {}
    if not isinstance(parsed, dict):
        parsed = {"version": 1, "concepts": []}
    concepts = parsed.setdefault("concepts", [])
    existing_ids = {str(item.get("id")) for item in concepts if isinstance(item, dict)}
    for bridge in bridges:
        if not isinstance(bridge, dict):
            continue
        bridge_id = str(bridge.get("id") or "").strip()
        if bridge_id and bridge_id not in existing_ids:
            concepts.append(bridge)
            existing_ids.add(bridge_id)
    content = yaml.safe_dump(parsed, allow_unicode=True, sort_keys=False)
    commit = _github_put(settings, repo_path, content, payload.message or "markdown-ai: update semantic bridges")
    _normalized, target = _resolve_content_path(repo_path, settings, require_markdown=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")
    log_event(
        settings,
        "admin_markdown_ai_bridges_apply",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"version_id": version_id, "commit_sha": commit.commit_sha, "bridges": len(bridges)},
    )
    return {"commit": commit.model_dump(), "bridges": bridges}


@router.post("/knowledge/folder", response_model=CommitResponse)
def create_knowledge_folder(payload: FolderRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    normalized, target = _resolve_content_path(payload.path, settings, require_markdown=False)
    repo_path = f"{normalized}/.gitkeep"
    message = payload.message or f"admin: create folder {normalized}"
    commit = _github_put(settings, repo_path, "", message)
    target.mkdir(parents=True, exist_ok=True)
    (target / ".gitkeep").write_text("", encoding="utf-8")
    log_event(settings, "admin_folder_create", request=request, session_id=user.login, actor_type="admin", payload=commit.model_dump())
    return commit


@router.post("/knowledge/import", response_model=ImportResponse)
async def import_markdown(request: Request, directory: str = Form(...), files: List[UploadFile] = File(...)):
    settings = _settings()
    user = _require_admin(request, settings)
    directory_path, local_directory = _resolve_content_path(directory, settings, require_markdown=False)
    local_directory.mkdir(parents=True, exist_ok=True)
    results: List[CommitResponse] = []
    for upload in files:
        filename = Path(upload.filename or "").name
        if not filename.lower().endswith(".md"):
            raise AppError("invalid_upload", "Importação aceita apenas arquivos .md.", 400)
        content = (await upload.read()).decode("utf-8")
        _validate_markdown_frontmatter(content)
        repo_path = _normalize_posix_path(f"{directory_path}/{filename}")
        _, target = _resolve_content_path(repo_path, settings)
        commit = _github_put(settings, repo_path, content, f"admin: import {repo_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        results.append(commit)
    response = ImportResponse(ok=True, files=results)
    log_event(
        settings,
        "admin_markdown_import",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"directory": directory_path, "files": [result.model_dump() for result in results]},
    )
    return response


@router.get("/prompt", response_model=PromptResponse)
def read_prompt(request: Request):
    settings = _settings()
    _require_admin(request, settings)
    repo_path, target = _prompt_paths(settings)
    content = target.read_text(encoding="utf-8") if target.exists() else ""
    return PromptResponse(path=repo_path, content=content)


@router.put("/prompt", response_model=CommitResponse)
def write_prompt(payload: PromptWriteRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    repo_path, target = _prompt_paths(settings)
    message = payload.message or "admin: update system prompt"
    commit = _github_put(settings, repo_path, payload.content, message)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8", newline="\n")
    log_event(settings, "admin_prompt_write", request=request, session_id=user.login, actor_type="admin", payload=commit.model_dump())
    return commit


def _set_reindex_status(**values: Any) -> None:
    _reindex_status.update(values)


def _document_sample_query(docs: List[Any]) -> tuple[Optional[str], Optional[str]]:
    for doc in docs:
        metadata = doc.metadata or {}
        source = str(metadata.get("source") or "")
        title = str(metadata.get("title") or "")
        summary = str(metadata.get("summary") or "")
        body = " ".join((doc.page_content or "").split())[:360]
        query = " ".join(part for part in (title, summary, body) if part).strip()
        if source and query:
            return query[:700], source
    return None, None


def _reindex_diagnostics(settings: Settings, docs: List[Any]) -> Dict[str, Any]:
    vector_status = (
        pgvector_status(settings)
        if uses_pgvector(settings)
        else {"backend": "chroma", "ready": True, "chunks": None, "last_reindex_at": None, "error": None, "index_type": "none"}
    )
    sample_query, expected_source = _document_sample_query(docs)
    diagnostics: Dict[str, Any] = {
        "vector_backend": vector_status.get("backend"),
        "vector_ready": vector_status.get("ready"),
        "vector_index_type": vector_status.get("index_type"),
        "vector_chunks": vector_status.get("chunks"),
        "last_reindex_at": vector_status.get("last_reindex_at"),
        "sample_query": sample_query,
        "sample_sources": [],
        "sample_ok": None,
        "sample_error": vector_status.get("error"),
        "github_branch": settings.github_branch,
        "knowledge_dir": str(settings.resolved_knowledge_dir),
        "storage_target": settings.pgvector_table if uses_pgvector(settings) else str(settings.resolved_chroma_dir),
    }
    if not sample_query:
        diagnostics["sample_error"] = "Nenhum documento público disponível para consulta sintética."
        return diagnostics
    try:
        result = realtime_search_knowledge(settings, sample_query)
        sources = [
            str(source.get("source") or "")
            for source in result.get("sources", [])
            if isinstance(source, dict) and source.get("source")
        ]
        diagnostics["sample_sources"] = sources
        diagnostics["sample_ok"] = bool(expected_source and expected_source in sources)
        if not diagnostics["sample_ok"]:
            diagnostics["sample_error"] = f"Consulta sintética não recuperou a fonte esperada: {expected_source}"
    except Exception as exc:
        diagnostics["sample_error"] = _sanitize_error(exc)
        diagnostics["sample_ok"] = False
    return diagnostics


def _run_reindex(settings: Settings, actor: Optional[str] = None, case_id: Optional[str] = None) -> None:
    try:
        docs = load_public_documents(settings)
        chunks = ingest(settings)
        diagnostics = _reindex_diagnostics(settings, docs)
        _set_reindex_status(
            state="success",
            finished_at=time.time(),
            duration_ms=int((time.time() - (_reindex_status.get("started_at") or time.time())) * 1000),
            document_count=len(docs),
            chunk_count=chunks,
            **diagnostics,
            case_id=case_id,
            error=None,
        )
        if case_id:
            record_case_reindex(settings, case_id, dict(_reindex_status))
        log_event(
            settings,
            "admin_reindex_success",
            session_id=actor,
            actor_type="admin",
            payload={"document_count": len(docs), "chunk_count": chunks, "case_id": case_id, **diagnostics},
        )
    except Exception as exc:
        sanitized = _sanitize_error(exc)
        _set_reindex_status(
            state="error",
            finished_at=time.time(),
            duration_ms=int((time.time() - (_reindex_status.get("started_at") or time.time())) * 1000),
            case_id=case_id,
            error=sanitized,
        )
        if case_id:
            record_case_reindex(settings, case_id, dict(_reindex_status))
        log_event(settings, "admin_reindex_error", session_id=actor, actor_type="admin", payload={"error": sanitized})
    finally:
        _reindex_lock.release()


@router.post("/reindex", response_model=ReindexStatusResponse)
def reindex_admin(request: Request, case_id: Optional[str] = Query(default=None)):
    settings = _settings()
    user = _require_admin(request, settings)
    if case_id and not get_curation_case(settings, case_id):
        raise AppError("curation_case_not_found", "Caso de curadoria não encontrado.", 404)
    if not _reindex_lock.acquire(blocking=False):
        raise AppError("reindex_running", "Reindexação já está em andamento.", 409)
    _set_reindex_status(
        state="running",
        started_at=time.time(),
        finished_at=None,
        duration_ms=None,
        document_count=0,
        chunk_count=0,
        vector_backend=settings.vector_backend,
        vector_ready=None,
        vector_chunks=None,
        last_reindex_at=None,
        sample_query=None,
        sample_sources=[],
        sample_ok=None,
        sample_error=None,
        github_branch=settings.github_branch,
        knowledge_dir=str(settings.resolved_knowledge_dir),
        storage_target=settings.pgvector_table if uses_pgvector(settings) else str(settings.resolved_chroma_dir),
        case_id=case_id,
        error=None,
    )
    log_event(settings, "admin_reindex_start", request=request, session_id=user.login, actor_type="admin", payload={"case_id": case_id})
    thread = threading.Thread(target=_run_reindex, args=(settings, user.login, case_id), daemon=True)
    thread.start()
    return ReindexStatusResponse(**_reindex_status)


@router.get("/reindex/status", response_model=ReindexStatusResponse)
def reindex_status(request: Request):
    settings = _settings()
    _require_admin(request, settings)
    return ReindexStatusResponse(**_reindex_status)


@router.post("/warmup")
def warmup_admin(request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    status = start_warmup(settings, actor=user.login)
    log_event(settings, "admin_warmup_start", request=request, session_id=user.login, actor_type="admin", payload=status)
    return status


@router.get("/warmup/status")
def warmup_admin_status(request: Request):
    settings = _settings()
    _require_admin(request, settings)
    return warmup_status()


@router.post("/rag/probe")
def admin_rag_probe(payload: RagProbeRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    result = build_rag_probe(settings, payload.question, payload.active_context, limit=payload.limit)
    log_event(
        settings,
        "admin_rag_probe",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={
            "question": payload.question,
            "active_context": payload.active_context,
            "documents": result.get("documents"),
            "took_ms": result.get("took_ms"),
            "sources": [item.get("source") for item in result.get("evidence", [])],
        },
    )
    return result


@router.post("/rag/evals/run")
def admin_rag_eval_run(request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    result = run_rag_eval(settings)
    log_event(
        settings,
        "admin_rag_eval_run",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={
            "total": result.get("total"),
            "passed": result.get("passed"),
            "failed": result.get("failed"),
            "duration_ms": result.get("duration_ms"),
        },
    )
    return {"run": result, "coverage": coverage_summary(settings)}


@router.get("/rag/evals/last")
def admin_rag_eval_last(request: Request):
    settings = _settings()
    _require_admin(request, settings)
    return {"run": last_eval_run(settings), "coverage": coverage_summary(settings)}


@router.get("/rag/traces")
def admin_rag_traces(
    request: Request,
    visitor_id: Optional[str] = Query(default=None),
    session_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    settings = _settings()
    _require_admin(request, settings)
    return {"traces": list_rag_traces(settings, visitor_id=visitor_id, session_id=session_id, limit=limit)}


@router.get("/rag/traces/{trace_id}")
def admin_rag_trace_detail(trace_id: str, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    trace = get_rag_trace(settings, trace_id)
    if not trace:
        raise AppError("rag_trace_not_found", "Trace RAG não encontrado.", 404)
    return trace


@router.get("/rag/feedback")
def admin_rag_feedback(
    request: Request,
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    settings = _settings()
    _require_admin(request, settings)
    return {"feedback": list_rag_feedback(settings, status=status, limit=limit)}


@router.post("/rag/feedback/{feedback_id}/draft-case")
def admin_rag_feedback_draft_case(feedback_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    result = create_case_from_feedback(settings, feedback_id)
    log_event(
        settings,
        "admin_rag_feedback_draft_case",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"feedback_id": feedback_id, "case_id": result.get("case", {}).get("id"), "created": result.get("created")},
    )
    return result


@router.delete("/rag/feedback/{feedback_id}")
def admin_rag_feedback_delete(feedback_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    feedback = archive_rag_feedback(settings, feedback_id, admin=user.login)
    if not feedback:
        raise AppError("rag_feedback_not_found", "Feedback RAG não encontrado.", 404)
    log_event(settings, "admin_rag_feedback_archive", request=request, session_id=user.login, actor_type="admin", payload={"feedback_id": feedback_id})
    return {"ok": True, "feedback": feedback}


@router.get("/rag-studio/inbox")
def admin_rag_studio_inbox(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    settings = _settings()
    _require_admin(request, settings)
    return rag_studio.list_inbox(settings, limit=limit)


@router.post("/rag-studio/proposals")
def admin_rag_studio_create_proposal(payload: RagStudioProposalCreateRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    proposal = rag_studio.create_proposal(settings, payload.model_dump(exclude_none=True))
    log_event(
        settings,
        "admin_rag_studio_proposal_create",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"proposal_id": proposal.get("id"), "origin_type": proposal.get("origin_type")},
    )
    return proposal


@router.post("/rag-studio/proposals/from-feedback/{feedback_id}")
def admin_rag_studio_create_from_feedback(feedback_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    result = rag_studio.create_proposal_from_feedback(settings, feedback_id)
    proposal = result.get("proposal") or {}
    log_event(
        settings,
        "admin_rag_studio_from_feedback",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"feedback_id": feedback_id, "proposal_id": proposal.get("id"), "created": result.get("created")},
    )
    return result


@router.get("/rag-studio/proposals/{proposal_id}")
def admin_rag_studio_proposal_detail(proposal_id: str, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    proposal = rag_studio.get_proposal(settings, proposal_id)
    if not proposal:
        raise AppError("proposal_not_found", "Proposta RAG Studio nao encontrada.", 404)
    return proposal


@router.get("/rag-studio/proposals/{proposal_id}/case-file")
def admin_rag_studio_case_file(proposal_id: str, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    return rag_studio.get_case_file(settings, proposal_id)


@router.get("/rag-studio/documents/{document_id}/content")
def admin_rag_studio_document_content(document_id: str, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    return rag_studio.get_document_content(settings, document_id)


@router.post("/rag-studio/proposals/{proposal_id}/investigate")
def admin_rag_studio_investigate(proposal_id: str, payload: RagStudioInvestigateRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    proposal = rag_studio.investigate_proposal(
        settings,
        proposal_id,
        question=payload.question,
        active_context=payload.active_context,
        limit=payload.limit,
    )
    log_event(
        settings,
        "admin_rag_studio_investigate",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"proposal_id": proposal_id, "documents": len(proposal.get("documents") or [])},
    )
    return proposal


@router.post("/rag-studio/proposals/{proposal_id}/documents")
def admin_rag_studio_add_documents(proposal_id: str, payload: RagStudioDocumentsRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    proposal = rag_studio.add_documents(settings, proposal_id, payload.paths)
    log_event(
        settings,
        "admin_rag_studio_documents",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"proposal_id": proposal_id, "paths": payload.paths},
    )
    return proposal


@router.post("/rag-studio/proposals/{proposal_id}/attachments")
async def admin_rag_studio_add_attachments(proposal_id: str, request: Request, files: List[UploadFile] = File(...)):
    settings = _settings()
    user = _require_admin(request, settings)
    saved = []
    for upload in files[:5]:
        data = await upload.read()
        saved.append(
            rag_studio.add_attachment(
                settings,
                proposal_id,
                filename=upload.filename or "attachment.txt",
                content_type=upload.content_type or "application/octet-stream",
                data=data,
            )
        )
    proposal = rag_studio.get_proposal(settings, proposal_id)
    log_event(
        settings,
        "admin_rag_studio_attachment",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"proposal_id": proposal_id, "count": len(saved)},
    )
    return {"attachments": saved, "proposal": proposal}


@router.delete("/rag-studio/attachments/{attachment_id}")
def admin_rag_studio_delete_attachment(attachment_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    if not rag_studio.delete_attachment(settings, attachment_id):
        raise AppError("attachment_not_found", "Anexo nao encontrado.", 404)
    log_event(
        settings,
        "admin_rag_studio_attachment_delete",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"attachment_id": attachment_id},
    )
    return {"ok": True}


@router.post("/rag-studio/proposals/{proposal_id}/context-documents")
async def admin_rag_studio_add_context_documents(proposal_id: str, request: Request, files: List[UploadFile] = File(...)):
    settings = _settings()
    user = _require_admin(request, settings)
    saved = []
    for upload in files[:5]:
        data = await upload.read()
        context_doc = rag_studio.prepare_context_document(
            settings,
            proposal_id,
            filename=upload.filename or "context.txt",
            content_type=upload.content_type or "application/octet-stream",
            data=data,
        )
        markdown = rag_studio.context_document_markdown(context_doc)
        commit = _github_put(settings, str(context_doc["git_path"]), markdown, f"rag-studio: add context {context_doc['filename']}")
        normalized, target = _resolve_content_path(str(context_doc["git_path"]), settings, require_markdown=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8", newline="\n")
        context_doc["git_path"] = normalized
        saved.append(rag_studio.save_context_document(settings, context_doc, git_commit_sha=commit.commit_sha))
    proposal = rag_studio.get_proposal(settings, proposal_id)
    log_event(
        settings,
        "admin_rag_studio_context_document",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"proposal_id": proposal_id, "count": len(saved)},
    )
    return {"context_documents": saved, "proposal": proposal}


@router.get("/rag-studio/proposals/{proposal_id}/context-documents")
def admin_rag_studio_context_documents(proposal_id: str, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    return {"context_documents": rag_studio.list_context_documents(settings, proposal_id)}


@router.post("/rag-studio/context-documents/{context_id}/approve")
def admin_rag_studio_approve_context_document(context_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    context_doc = rag_studio.approve_context_document(settings, context_id)
    proposal = rag_studio.get_proposal(settings, str(context_doc["proposal_id"]))
    log_event(settings, "admin_rag_studio_context_approve", request=request, session_id=user.login, actor_type="admin", payload={"context_id": context_id})
    return {"context_document": context_doc, "proposal": proposal}


@router.post("/rag-studio/context-documents/{context_id}/index")
def admin_rag_studio_index_context_document(context_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    result = rag_studio.index_approved_context_document(settings, context_id)
    context_doc = result.get("context_document") or {}
    proposal = rag_studio.get_proposal(settings, str(context_doc.get("proposal_id") or ""))
    log_event(
        settings,
        "admin_rag_studio_context_index",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"context_id": context_id, "chunks": (result.get("index") or {}).get("chunks")},
    )
    return {"context_document": context_doc, "index": result.get("index"), "proposal": proposal}


@router.post("/rag-studio/context-documents/{context_id}/ignore")
def admin_rag_studio_ignore_context_document(context_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    context_doc = rag_studio.ignore_context_document(settings, context_id)
    proposal = rag_studio.get_proposal(settings, str(context_doc["proposal_id"]))
    log_event(settings, "admin_rag_studio_context_ignore", request=request, session_id=user.login, actor_type="admin", payload={"context_id": context_id})
    return {"context_document": context_doc, "proposal": proposal}


@router.get("/rag-studio/context-documents/{context_id}")
def admin_rag_studio_get_context_document(context_id: str, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    context_doc = rag_studio.get_context_document(settings, context_id, include_text=True)
    if not context_doc:
        raise AppError("context_document_not_found", "Documento contextual nao encontrado.", 404)
    return {"context_document": context_doc}


@router.post("/rag-studio/context-documents/{context_id}/restore")
def admin_rag_studio_restore_context_document(context_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    context_doc = rag_studio.restore_context_document(settings, context_id)
    proposal = rag_studio.get_proposal(settings, str(context_doc["proposal_id"]))
    log_event(settings, "admin_rag_studio_context_restore", request=request, session_id=user.login, actor_type="admin", payload={"context_id": context_id})
    return {"context_document": context_doc, "proposal": proposal}


@router.delete("/rag-studio/context-documents/{context_id}")
def admin_rag_studio_delete_context_document(context_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    context_doc = rag_studio.get_context_document(settings, context_id, include_text=False)
    if not context_doc:
        raise AppError("context_document_not_found", "Documento contextual nao encontrado.", 404)
    git_path = context_doc.get("git_path")
    commit = None
    if git_path:
        try:
            commit = _github_delete(settings, str(git_path), f"rag-studio: remove context {context_doc.get('filename') or context_id}")
        except AppError as exc:
            if exc.code != "file_not_found":
                raise
        try:
            _normalized, target = _resolve_content_path(str(git_path), settings, require_markdown=True)
            target.unlink(missing_ok=True)
        except AppError:
            pass
    if not rag_studio.delete_context_document(settings, context_id):
        raise AppError("context_document_not_found", "Documento contextual nao encontrado.", 404)
    log_event(
        settings,
        "admin_rag_studio_context_delete",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"context_id": context_id, "commit_sha": commit.commit_sha if commit else None},
    )
    return {"ok": True, "commit": commit.model_dump() if commit else None}


@router.post("/rag-studio/documents/{document_id}/generate-patch")
def admin_rag_studio_generate_patch(document_id: str, payload: RagStudioPatchRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    proposal = rag_studio.generate_patch(settings, document_id, payload.instruction)
    log_event(
        settings,
        "admin_rag_studio_patch_generate",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"document_id": document_id, "proposal_id": proposal.get("id")},
    )
    return proposal


@router.post("/rag-studio/patches/{patch_id}/apply")
def admin_rag_studio_apply_patch(patch_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    patch = rag_studio.get_patch(settings, patch_id)
    if not patch:
        raise AppError("change_patch_not_found", "Patch nao encontrado.", 404)
    if patch.get("status") != "proposed":
        raise AppError("change_patch_not_proposed", "Este patch ja foi aplicado ou descartado.", 409)
    normalized, target = _resolve_content_path(str(patch.get("target_path") or ""), settings)
    proposed = str(patch.get("proposed_content") or "")
    _validate_markdown_frontmatter(proposed)
    commit = _github_put(settings, normalized, proposed, f"rag-studio: update {normalized}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(proposed, encoding="utf-8", newline="\n")
    proposal = rag_studio.mark_patch_applied(settings, patch_id, commit.commit_sha)
    log_event(
        settings,
        "admin_rag_studio_patch_apply",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"patch_id": patch_id, "proposal_id": proposal.get("id"), "commit_sha": commit.commit_sha},
    )
    return {"proposal": proposal, "commit": commit.model_dump()}


@router.post("/rag-studio/patches/{patch_id}/discard")
def admin_rag_studio_discard_patch(patch_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    proposal = rag_studio.discard_patch(settings, patch_id)
    log_event(
        settings,
        "admin_rag_studio_patch_discard",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"patch_id": patch_id, "proposal_id": proposal.get("id")},
    )
    return proposal


@router.post("/rag-studio/patches/{patch_id}/reverse-proposal")
def admin_rag_studio_reverse_patch(patch_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    proposal = rag_studio.create_reverse_proposal_from_patch(settings, patch_id)
    log_event(
        settings,
        "admin_rag_studio_reverse_proposal",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"patch_id": patch_id, "proposal_id": proposal.get("id")},
    )
    return proposal


@router.post("/rag-studio/documents/{document_id}/ignore")
def admin_rag_studio_ignore_document(document_id: str, payload: RagStudioArchiveRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    proposal = rag_studio.ignore_document(settings, document_id, payload.reason)
    log_event(
        settings,
        "admin_rag_studio_document_ignore",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"document_id": document_id, "proposal_id": proposal.get("id")},
    )
    return proposal


@router.post("/rag-studio/documents/{document_id}/restore")
def admin_rag_studio_restore_document(document_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    proposal = rag_studio.restore_document(settings, document_id)
    log_event(
        settings,
        "admin_rag_studio_document_restore",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"document_id": document_id, "proposal_id": proposal.get("id")},
    )
    return proposal


def _evidence_sources(result: Dict[str, Any]) -> List[str]:
    sources: List[str] = []
    for item in result.get("evidence") or []:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "").replace("\\", "/").strip("/")
        if source and source not in sources:
            sources.append(source)
            prefixed = f"knowledge/{source}" if not source.startswith("knowledge/") else source
            if prefixed not in sources:
                sources.append(prefixed)
    return sources


@router.post("/rag-studio/proposals/{proposal_id}/validate")
def admin_rag_studio_validate(proposal_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    proposal = rag_studio.get_proposal(settings, proposal_id)
    if not proposal:
        raise AppError("proposal_not_found", "Proposta RAG Studio nao encontrada.", 404)
    documents = proposal.get("documents") or []
    if not documents:
        raise AppError("proposal_without_documents", "Selecione ao menos um Markdown antes de validar.", 409)
    unfinished = [doc for doc in documents if doc.get("status") not in {"applied", "ignored"}]
    if unfinished:
        raise AppError("proposal_documents_pending", "Aplique ou ignore todos os documentos antes de validar.", 409)
    if not _reindex_lock.acquire(blocking=False):
        raise AppError("reindex_running", "Reindexacao ja esta em andamento.", 409)
    _set_reindex_status(
        state="running",
        started_at=time.time(),
        finished_at=None,
        duration_ms=None,
        document_count=0,
        chunk_count=0,
        vector_backend=settings.vector_backend,
        vector_ready=None,
        vector_chunks=None,
        last_reindex_at=None,
        sample_query=None,
        sample_sources=[],
        sample_ok=None,
        sample_error=None,
        github_branch=settings.github_branch,
        knowledge_dir=str(settings.resolved_knowledge_dir),
        storage_target=settings.pgvector_table if uses_pgvector(settings) else str(settings.resolved_chroma_dir),
        case_id=None,
        error=None,
    )
    _run_reindex(settings, user.login, None)
    reindex_result = dict(_reindex_status)
    probe_result: Dict[str, Any] = {}
    expected_paths = [str(doc.get("path") or "") for doc in documents if doc.get("status") == "applied"]
    validation_state = "error"
    validation_error = reindex_result.get("error")
    if reindex_result.get("state") == "success":
        probe_question = str(proposal.get("question") or proposal.get("problem_statement") or "").strip()
        if not probe_question:
            validation_error = "A proposta nao tem pergunta ou problema para o probe."
        else:
            probe_result = build_rag_probe(settings, probe_question, proposal.get("active_context"), limit=12)
            sources = _evidence_sources(probe_result)
            recovered_expected = not expected_paths or any(path in sources for path in expected_paths)
            validation_state = "success" if probe_result.get("documents", 0) and recovered_expected else "failed"
            if validation_state == "failed":
                validation_error = "Probe executado, mas nao recuperou documento esperado."
    validation = {
        "state": validation_state,
        "validated_at": time.time(),
        "reindex": reindex_result,
        "probe": probe_result,
        "expected_paths": expected_paths,
        "error": validation_error,
    }
    updated = rag_studio.record_validation(settings, proposal_id, validation)
    log_event(
        settings,
        "admin_rag_studio_validate",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"proposal_id": proposal_id, "state": validation_state, "expected_paths": expected_paths},
    )
    return updated


@router.post("/rag-studio/proposals/{proposal_id}/resolve")
def admin_rag_studio_resolve(proposal_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    proposal = rag_studio.resolve_proposal(settings, proposal_id)
    log_event(
        settings,
        "admin_rag_studio_resolve",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"proposal_id": proposal_id},
    )
    return proposal


@router.post("/rag-studio/proposals/{proposal_id}/archive")
def admin_rag_studio_archive(proposal_id: str, payload: RagStudioArchiveRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    proposal = rag_studio.archive_proposal(settings, proposal_id, payload.reason)
    log_event(
        settings,
        "admin_rag_studio_archive",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"proposal_id": proposal_id, "reason": payload.reason},
    )
    return proposal


@router.post("/rag/feedback/{feedback_id}/triage")
def admin_rag_feedback_triage(feedback_id: str, payload: RagFeedbackTriageRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    feedback = triage_rag_feedback(
        settings,
        feedback_id,
        payload.status.strip() or "triaged",
        {"notes": payload.notes, "action": payload.action, "admin": user.login},
    )
    if not feedback:
        raise AppError("rag_feedback_not_found", "Feedback RAG não encontrado.", 404)
    log_event(settings, "admin_rag_feedback_triage", request=request, session_id=user.login, actor_type="admin", payload={"feedback_id": feedback_id, "status": payload.status})
    return feedback


@router.get("/curation/cases")
def admin_curation_cases(
    request: Request,
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    settings = _settings()
    _require_admin(request, settings)
    return {"cases": list_curation_cases(settings, status=status, limit=limit)}


@router.post("/curation/cases")
def admin_curation_case_create(payload: CurationCaseCreateRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    case = create_curation_case(settings, payload.model_dump(exclude_none=True))
    log_event(settings, "admin_curation_case_create", request=request, session_id=user.login, actor_type="admin", payload={"case_id": case.get("id")})
    return case


@router.get("/curation/cases/{case_id}")
def admin_curation_case_detail(case_id: str, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    case = get_curation_case(settings, case_id)
    if not case:
        raise AppError("curation_case_not_found", "Caso de curadoria não encontrado.", 404)
    return case


@router.post("/curation/cases/{case_id}/targets")
def admin_curation_case_targets(case_id: str, payload: CurationCaseTargetsRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    result = add_targets_to_case(settings, case_id, payload.target_paths)
    log_event(settings, "admin_curation_case_targets", request=request, session_id=user.login, actor_type="admin", payload={"case_id": case_id, "targets": payload.target_paths})
    return result


@router.post("/curation/cases/{case_id}/drafts/{draft_id}/ignore")
def admin_curation_case_draft_ignore(case_id: str, draft_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    result = ignore_case_draft(settings, case_id, draft_id)
    log_event(settings, "admin_curation_draft_ignore", request=request, session_id=user.login, actor_type="admin", payload={"case_id": case_id, "draft_id": draft_id})
    return result


@router.post("/curation/cases/{case_id}/drafts/{draft_id}/agent/stream")
def admin_curation_case_draft_agent_stream(case_id: str, draft_id: str, payload: DraftAgentRequest, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    draft = get_draft(settings, draft_id)
    if not draft or draft.get("case_id") != case_id:
        raise AppError("draft_not_found", "Draft do caso não encontrado.", 404)
    return admin_knowledge_draft_agent_stream(draft_id, payload, request)


@router.post("/curation/cases/{case_id}/validate/reindex")
def admin_curation_case_reindex(case_id: str, request: Request):
    return reindex_admin(request, case_id=case_id)


@router.post("/curation/cases/{case_id}/validate/eval")
def admin_curation_case_eval(case_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    if not get_curation_case(settings, case_id):
        raise AppError("curation_case_not_found", "Caso de curadoria não encontrado.", 404)
    result = run_rag_eval(settings)
    case = record_case_eval(settings, case_id, result)
    log_event(settings, "admin_curation_case_eval", request=request, session_id=user.login, actor_type="admin", payload={"case_id": case_id, "failed": result.get("failed")})
    return {"run": result, "case": case, "coverage": coverage_summary(settings)}


@router.post("/curation/cases/{case_id}/resolve")
def admin_curation_case_resolve(case_id: str, payload: CurationCaseResolveRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    case = resolve_curation_case(settings, case_id)
    log_event(settings, "admin_curation_case_resolve", request=request, session_id=user.login, actor_type="admin", payload={"case_id": case_id, "message": payload.message})
    return case


@router.get("/knowledge/suggestions")
def admin_knowledge_suggestions(
    request: Request,
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    settings = _settings()
    _require_admin(request, settings)
    return {"suggestions": list_knowledge_suggestions(settings, status=status, limit=limit)}


@router.get("/knowledge/suggestions/{suggestion_id}")
def admin_knowledge_suggestion_detail(suggestion_id: str, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    suggestion = get_knowledge_suggestion(settings, suggestion_id)
    if not suggestion:
        raise AppError("knowledge_suggestion_not_found", "Sugestão não encontrada.", 404)
    return suggestion


@router.put("/knowledge/suggestions/{suggestion_id}")
def admin_knowledge_suggestion_update(suggestion_id: str, payload: SuggestionUpdateRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("suggested_path"):
        _resolve_content_path(updates["suggested_path"], settings, require_markdown=True)
    if updates.get("draft_markdown"):
        _validate_markdown_frontmatter(updates["draft_markdown"])
    suggestion = update_knowledge_suggestion_details(settings, suggestion_id, updates)
    if not suggestion:
        raise AppError("knowledge_suggestion_not_found", "Sugestão não encontrada.", 404)
    log_event(
        settings,
        "admin_knowledge_suggestion_update",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"suggestion_id": suggestion_id, "path": suggestion.get("suggested_path")},
    )
    return suggestion


@router.post("/knowledge/suggestions/{suggestion_id}/accept")
def admin_knowledge_suggestion_accept(suggestion_id: str, payload: SuggestionActionRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    suggestion = update_knowledge_suggestion_status(settings, suggestion_id, payload.status or "accepted", {"accepted_by": user.login, "message": payload.message})
    if not suggestion:
        raise AppError("knowledge_suggestion_not_found", "Sugestão não encontrada.", 404)
    log_event(settings, "admin_knowledge_suggestion_accept", request=request, session_id=user.login, actor_type="admin", payload={"suggestion_id": suggestion_id})
    return suggestion


@router.post("/knowledge/suggestions/{suggestion_id}/ignore")
def admin_knowledge_suggestion_ignore(suggestion_id: str, payload: SuggestionActionRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    suggestion = update_knowledge_suggestion_status(settings, suggestion_id, payload.status or "ignored", {"ignored_by": user.login, "message": payload.message})
    if not suggestion:
        raise AppError("knowledge_suggestion_not_found", "Sugestão não encontrada.", 404)
    log_event(settings, "admin_knowledge_suggestion_ignore", request=request, session_id=user.login, actor_type="admin", payload={"suggestion_id": suggestion_id})
    return suggestion


@router.post("/knowledge/suggestions/{suggestion_id}/create-markdown")
def admin_knowledge_suggestion_create_markdown(suggestion_id: str, payload: SuggestionActionRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    suggestion = get_knowledge_suggestion(settings, suggestion_id)
    if not suggestion:
        raise AppError("knowledge_suggestion_not_found", "Sugestão não encontrada.", 404)
    repo_path, _target = _resolve_content_path(suggestion["suggested_path"], settings, require_markdown=True)
    _validate_markdown_frontmatter(suggestion["draft_markdown"])
    commit = _github_put(settings, repo_path, suggestion["draft_markdown"], payload.message or f"admin: create suggested knowledge {repo_path}")
    updated = update_knowledge_suggestion_status(settings, suggestion_id, "converted_to_markdown", {"commit_sha": commit.commit_sha, "path": repo_path, "converted_by": user.login})
    log_event(settings, "admin_knowledge_suggestion_markdown", request=request, session_id=user.login, actor_type="admin", payload={"suggestion_id": suggestion_id, "path": repo_path, "commit_sha": commit.commit_sha})
    return {"ok": True, "path": repo_path, "commit": commit, "suggestion": updated}


@router.post("/knowledge/suggestions/{suggestion_id}/create-eval-case")
def admin_knowledge_suggestion_create_eval_case(suggestion_id: str, payload: SuggestionActionRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    suggestion = get_knowledge_suggestion(settings, suggestion_id)
    if not suggestion:
        raise AppError("knowledge_suggestion_not_found", "Sugestão não encontrada.", 404)
    repo_path = "evals/rag_cases.json"
    current_raw = _github_read_text(settings, repo_path)
    cases = json.loads(current_raw) if current_raw else []
    if not isinstance(cases, list):
        raise AppError("invalid_eval_cases", "evals/rag_cases.json precisa conter uma lista JSON.", 422)
    case = eval_case_from_suggestion(suggestion)
    existing_ids = {str(item.get("id")) for item in cases if isinstance(item, dict)}
    if case["id"] in existing_ids:
        case["id"] = f"{case['id']}-{len(existing_ids) + 1}"
    cases.append(case)
    content = json.dumps(cases, ensure_ascii=False, indent=2) + "\n"
    commit = _github_put(settings, repo_path, content, payload.message or f"admin: add RAG eval case {case['id']}")
    update_knowledge_suggestion_status(settings, suggestion_id, "converted_to_eval", {"commit_sha": commit.commit_sha, "eval_case": case, "converted_by": user.login})
    log_event(settings, "admin_knowledge_suggestion_eval_case", request=request, session_id=user.login, actor_type="admin", payload={"suggestion_id": suggestion_id, "case_id": case["id"], "commit_sha": commit.commit_sha})
    return {"ok": True, "case": case, "commit": commit}


@router.get("/knowledge/canonical-docs")
def admin_knowledge_canonical_docs(request: Request):
    settings = _settings()
    _require_admin(request, settings)
    return {"documents": list_canonical_documents(settings)}


@router.get("/knowledge/drafts")
def admin_knowledge_drafts(
    request: Request,
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    settings = _settings()
    _require_admin(request, settings)
    return {"drafts": list_drafts(settings, status=status, limit=limit)}


@router.post("/knowledge/drafts")
def admin_knowledge_draft_create(payload: DraftCreateRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    draft = create_draft(settings, payload.model_dump(exclude_none=True))
    if draft.get("source_suggestion_id"):
        update_knowledge_suggestion_details(
            settings,
            str(draft["source_suggestion_id"]),
            {"status": "draft_opened", "payload_update": {"draft_id": draft["id"]}},
        )
    log_event(
        settings,
        "admin_draft_create",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"draft_id": draft["id"], "suggestion_id": draft.get("source_suggestion_id")},
    )
    return draft


@router.get("/knowledge/drafts/{draft_id}")
def admin_knowledge_draft_detail(draft_id: str, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    draft = get_draft(settings, draft_id, include_related=True)
    if not draft:
        raise AppError("draft_not_found", "Draft não encontrado.", 404)
    return draft


@router.put("/knowledge/drafts/{draft_id}")
def admin_knowledge_draft_update(draft_id: str, payload: DraftUpdateRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("draft_markdown"):
        _validate_markdown_frontmatter(updates["draft_markdown"])
    draft = update_draft(settings, draft_id, updates)
    if not draft:
        raise AppError("draft_not_found", "Draft não encontrado.", 404)
    log_event(settings, "admin_draft_update", request=request, session_id=user.login, actor_type="admin", payload={"draft_id": draft_id})
    return draft


@router.post("/knowledge/drafts/{draft_id}/attachments")
async def admin_knowledge_draft_attachments(draft_id: str, request: Request, files: List[UploadFile] = File(...)):
    settings = _settings()
    user = _require_admin(request, settings)
    saved = []
    for upload in files[:5]:
        data = await upload.read()
        saved.append(
            add_attachment(
                settings,
                draft_id,
                filename=upload.filename or "attachment.txt",
                content_type=upload.content_type or "application/octet-stream",
                data=data,
            )
        )
    log_event(
        settings,
        "admin_draft_attachment",
        request=request,
        session_id=user.login,
        actor_type="admin",
        payload={"draft_id": draft_id, "count": len(saved)},
    )
    return {"attachments": saved, "draft": get_draft(settings, draft_id, include_related=True)}


@router.delete("/knowledge/drafts/{draft_id}/attachments/{attachment_id}")
def admin_knowledge_draft_attachment_delete(draft_id: str, attachment_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    if not delete_attachment(settings, draft_id, attachment_id):
        raise AppError("attachment_not_found", "Anexo não encontrado.", 404)
    log_event(settings, "admin_draft_attachment_delete", request=request, session_id=user.login, actor_type="admin", payload={"draft_id": draft_id, "attachment_id": attachment_id})
    return {"ok": True, "draft": get_draft(settings, draft_id, include_related=True)}


@router.post("/knowledge/drafts/{draft_id}/agent/stream")
def admin_knowledge_draft_agent_stream(draft_id: str, payload: DraftAgentRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)

    def generate():
        try:
            yield _admin_sse("stage", {"id": "received", "label": "Instrução recebida", "status": "done"})
            yield _admin_sse("stage", {"id": "retrieval", "label": "Recuperando contexto no RAG", "status": "active"})
            result = generate_draft_with_agent(
                settings,
                draft_id,
                instruction=payload.instruction,
                target_paths=payload.target_paths,
            )
            case = refresh_curation_case_status(settings, str(result["draft"].get("case_id"))) if result.get("draft", {}).get("case_id") else None
            yield _admin_sse("stage", {"id": "draft", "label": "Draft e patches preparados", "status": "done"})
            yield _admin_sse(
                "done",
                {
                    "draft": result["draft"],
                    "case": case,
                    "run": result["run"],
                    "patches": result["patches"],
                    "fallback": result["fallback"],
                },
            )
            log_event(
                settings,
                "admin_draft_agent",
                request=request,
                session_id=user.login,
                actor_type="admin",
                payload={"draft_id": draft_id, "fallback": result["fallback"]},
            )
        except AppError as exc:
            yield _admin_sse("error", {"code": exc.code, "message": exc.message})
        except Exception as exc:
            yield _admin_sse("error", {"code": "draft_agent_failed", "message": _sanitize_error(exc)})

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/knowledge/drafts/{draft_id}/commit-draft")
def admin_knowledge_draft_commit(draft_id: str, payload: DraftActionRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    draft = get_draft(settings, draft_id, include_related=True)
    if not draft:
        raise AppError("draft_not_found", "Draft não encontrado.", 404)
    repo_path = draft.get("suggested_path") or f"knowledge/_drafts/{draft_id}.md"
    if not str(repo_path).startswith("knowledge/_drafts/"):
        raise AppError("invalid_draft_path", "Draft precisa ser salvo dentro de knowledge/_drafts/.", 422)
    _resolve_content_path(repo_path, settings, require_markdown=True)
    _validate_markdown_frontmatter(draft["draft_markdown"])
    commit = _github_put(settings, repo_path, draft["draft_markdown"], payload.message or f"admin: commit draft {repo_path}")
    updated = update_draft(settings, draft_id, {"status": "draft_committed", "git_path": repo_path, "git_commit_sha": commit.commit_sha})
    if updated and updated.get("case_id"):
        refresh_curation_case_status(settings, str(updated["case_id"]))
    log_event(settings, "admin_draft_commit", request=request, session_id=user.login, actor_type="admin", payload={"draft_id": draft_id, "path": repo_path, "commit_sha": commit.commit_sha})
    return {"ok": True, "draft": updated, "commit": commit}


@router.post("/knowledge/drafts/{draft_id}/propose-patch")
def admin_knowledge_draft_propose_patch(draft_id: str, payload: DraftActionRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    result = propose_patch_from_draft(settings, draft_id, target_path=payload.target_path)
    if result.get("draft", {}).get("case_id"):
        result["case"] = refresh_curation_case_status(settings, str(result["draft"]["case_id"]))
    log_event(settings, "admin_draft_patch_propose", request=request, session_id=user.login, actor_type="admin", payload={"draft_id": draft_id, "patch_id": result.get("patch", {}).get("id")})
    return result


@router.post("/knowledge/drafts/{draft_id}/apply-patch")
def admin_knowledge_draft_apply_patch(draft_id: str, payload: DraftActionRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    draft = get_draft(settings, draft_id, include_related=True)
    if not draft:
        raise AppError("draft_not_found", "Draft não encontrado.", 404)
    patch_id = payload.patch_id or next((patch.get("id") for patch in draft.get("patches") or [] if patch.get("status") == "proposed"), None)
    if not patch_id:
        raise AppError("patch_not_found", "Nenhum patch proposto para aplicar.", 404)
    patch = get_patch(settings, draft_id, patch_id)
    if not patch:
        raise AppError("patch_not_found", "Patch não encontrado.", 404)
    repo_path, _target = _resolve_content_path(patch["target_path"], settings, require_markdown=True)
    _validate_markdown_frontmatter(patch["proposed_content"])
    commit = _github_put(settings, repo_path, patch["proposed_content"], payload.message or f"admin: apply draft patch {repo_path}")
    update_patch_status(settings, draft_id, patch_id, "applied", commit.commit_sha)
    updated = update_draft(settings, draft_id, {"status": "merged", "decision": "edited", "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    case = refresh_curation_case_status(settings, str(updated["case_id"])) if updated and updated.get("case_id") else None
    log_event(settings, "admin_draft_patch_apply", request=request, session_id=user.login, actor_type="admin", payload={"draft_id": draft_id, "patch_id": patch_id, "path": repo_path, "commit_sha": commit.commit_sha})
    return {"ok": True, "draft": updated, "case": case, "patch": get_patch(settings, draft_id, patch_id), "commit": commit}


@router.post("/knowledge/drafts/{draft_id}/revert-step")
def admin_knowledge_draft_revert_step(draft_id: str, payload: DraftActionRequest, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    draft = get_draft(settings, draft_id, include_related=True)
    if not draft:
        raise AppError("draft_not_found", "Draft não encontrado.", 404)
    commit = None
    step = payload.step or "review"
    if step in {"review", "delete_committed_draft"} and draft.get("git_path"):
        try:
            commit = _github_delete(settings, draft["git_path"], payload.message or f"admin: remove draft {draft['git_path']}")
        except AppError as exc:
            if exc.code != "file_not_found":
                raise
    updated = revert_draft_step(settings, draft_id, "review" if step == "delete_committed_draft" else step)
    log_event(settings, "admin_draft_revert", request=request, session_id=user.login, actor_type="admin", payload={"draft_id": draft_id, "step": step})
    return {"ok": True, "draft": updated, "commit": commit}


@router.delete("/knowledge/drafts/{draft_id}")
def admin_knowledge_draft_delete(draft_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    draft = get_draft(settings, draft_id, include_related=True)
    if not draft:
        raise AppError("draft_not_found", "Draft não encontrado.", 404)
    if draft.get("git_path"):
        try:
            _github_delete(settings, draft["git_path"], f"admin: delete draft {draft['git_path']}")
        except AppError as exc:
            if exc.code != "file_not_found":
                raise
    deleted = delete_draft(settings, draft_id)
    log_event(settings, "admin_draft_delete", request=request, session_id=user.login, actor_type="admin", payload={"draft_id": draft_id})
    return {"ok": deleted}


@router.get("/events/summary")
def admin_events_summary(request: Request, hours: int = Query(default=168, ge=1, le=2160)):
    settings = _settings()
    _require_admin(request, settings)
    return event_summary(settings, hours=hours)


@router.get("/events")
def admin_events(
    request: Request,
    kind: Optional[str] = Query(default=None),
    visitor_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    settings = _settings()
    _require_admin(request, settings)
    return {"events": list_events(settings, kind=kind, visitor_id=visitor_id, limit=limit)}


@router.get("/jobs/scans")
def admin_job_scans(
    request: Request,
    status: Optional[str] = Query(default=None),
    visitor_id: Optional[str] = Query(default=None),
    company: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    settings = _settings()
    _require_admin(request, settings)
    return {"scans": list_job_scans(settings, status=status, visitor_id=visitor_id, company=company, limit=limit)}


@router.get("/jobs/scans/{scan_id}")
def admin_job_scan_detail(scan_id: str, request: Request):
    settings = _settings()
    _require_admin(request, settings)
    scan = get_job_scan(settings, scan_id)
    if not scan:
        raise AppError("job_scan_not_found", "Vaga scaneada não encontrada.", 404)
    return scan


@router.delete("/jobs/scans/{scan_id}")
def admin_job_scan_delete(scan_id: str, request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    deleted = delete_job_scan(settings, scan_id)
    if not deleted:
        raise AppError("job_scan_not_found", "Vaga scaneada não encontrada.", 404)
    log_event(settings, "admin_job_scan_delete", request=request, session_id=user.login, actor_type="admin", payload={"scan_id": scan_id})
    return {"ok": True, "scan_id": scan_id}
