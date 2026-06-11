from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from agent import AppError
from config import Settings, get_settings
from events import event_summary, list_events, log_event
from ingest import ingest, load_public_documents


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
    error: Optional[str] = None


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
    return _read_session_token(request.cookies.get(settings.admin_cookie_name, ""), settings)


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


@router.get("/session", response_model=AdminSessionResponse)
def admin_session(request: Request):
    settings = _settings()
    return AdminSessionResponse(
        authenticated=bool(_current_admin(request, settings)),
        user=_current_admin(request, settings),
        configured=_admin_configured(settings),
    )


@router.get("/auth/github/login")
def github_login():
    settings = _settings()
    if not _admin_configured(settings):
        raise AppError("admin_not_configured", "Configure GitHub OAuth e ADMIN_SESSION_SECRET no Render.", 503)

    state = secrets.token_urlsafe(32)
    redirect_uri = settings.admin_public_base_url.rstrip("/") + "/admin/auth/github/callback"
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
    _set_cookie(response, settings.admin_state_cookie_name, state, settings, max_age=600)
    return response


@router.get("/auth/github/callback")
def github_callback(request: Request, code: str = Query(default=""), state: str = Query(default="")):
    settings = _settings()
    if not _admin_configured(settings):
        raise AppError("admin_not_configured", "Configure GitHub OAuth e ADMIN_SESSION_SECRET no Render.", 503)
    expected_state = request.cookies.get(settings.admin_state_cookie_name, "")
    if not state or not expected_state or not secrets.compare_digest(state, expected_state):
        raise AppError("admin_oauth_state_invalid", "Sessão OAuth inválida. Tente login novamente.", 401)
    if not code:
        raise AppError("admin_oauth_missing_code", "GitHub não retornou código de autorização.", 400)

    redirect_uri = settings.admin_public_base_url.rstrip("/") + "/admin/auth/github/callback"
    try:
        with httpx.Client(timeout=20) as client:
            token_response = client.post(
                GITHUB_TOKEN,
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_oauth_client_id,
                    "client_secret": settings.github_oauth_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "state": state,
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise AppError("admin_oauth_token_missing", "GitHub não retornou token de acesso.", 401)
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

    response = RedirectResponse(settings.admin_redirect_url)
    _set_cookie(response, settings.admin_cookie_name, _session_token(user, settings), settings, max_age=settings.admin_session_hours * 3600)
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


def _run_reindex(settings: Settings, actor: Optional[str] = None) -> None:
    try:
        docs = load_public_documents(settings)
        chunks = ingest(settings)
        _set_reindex_status(
            state="success",
            finished_at=time.time(),
            duration_ms=int((time.time() - (_reindex_status.get("started_at") or time.time())) * 1000),
            document_count=len(docs),
            chunk_count=chunks,
            error=None,
        )
        log_event(
            settings,
            "admin_reindex_success",
            session_id=actor,
            actor_type="admin",
            payload={"document_count": len(docs), "chunk_count": chunks},
        )
    except Exception as exc:
        sanitized = _sanitize_error(exc)
        _set_reindex_status(
            state="error",
            finished_at=time.time(),
            duration_ms=int((time.time() - (_reindex_status.get("started_at") or time.time())) * 1000),
            error=sanitized,
        )
        log_event(settings, "admin_reindex_error", session_id=actor, actor_type="admin", payload={"error": sanitized})
    finally:
        _reindex_lock.release()


@router.post("/reindex", response_model=ReindexStatusResponse)
def reindex_admin(request: Request):
    settings = _settings()
    user = _require_admin(request, settings)
    if not _reindex_lock.acquire(blocking=False):
        raise AppError("reindex_running", "Reindexação já está em andamento.", 409)
    _set_reindex_status(
        state="running",
        started_at=time.time(),
        finished_at=None,
        duration_ms=None,
        document_count=0,
        chunk_count=0,
        error=None,
    )
    log_event(settings, "admin_reindex_start", request=request, session_id=user.login, actor_type="admin")
    thread = threading.Thread(target=_run_reindex, args=(settings, user.login), daemon=True)
    thread.start()
    return ReindexStatusResponse(**_reindex_status)


@router.get("/reindex/status", response_model=ReindexStatusResponse)
def reindex_status(request: Request):
    settings = _settings()
    _require_admin(request, settings)
    return ReindexStatusResponse(**_reindex_status)


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
