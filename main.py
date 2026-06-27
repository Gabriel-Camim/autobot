from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from admin import _current_admin, router as admin_router
from agent import AppError, AgentResult, answer_question, stream_answer_question, stream_fit_analysis
from config import get_settings
from draft_studio import draft_studio_storage_status
from events import event_storage_status, log_event
from job_scans import create_job_scan, fail_job_scan, finish_job_scan, job_scan_storage_status
from pgvector_store import pgvector_status, uses_pgvector
from rag_quality import (
    create_rag_feedback,
    rag_quality_storage_status,
    update_rag_trace_actor,
)
from rag_studio import rag_studio_storage_status
from realtime import create_realtime_call
from voice import synthesize_speech_base64, transcribe_upload
from warmup import start_warmup, warmup_status


settings = get_settings()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("gabriel_api")

app = FastAPI(title="Gabriel Portfolio Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origin_list,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Realtime-Call-Id"],
)

app.include_router(admin_router)


@app.on_event("startup")
def startup_warmup() -> None:
    start_warmup(settings, actor="startup")

class SourceSummaryResponse(BaseModel):
    title: str
    category: str
    summary: str
    source: str
    tags: List[str] = Field(default_factory=list)


class EvidenceResponse(BaseModel):
    source: str
    title: str
    category: str
    summary: str
    tags: List[str] = Field(default_factory=list)
    priority: int
    excerpt: str
    channel: str
    distance: Optional[float] = None
    relevance_score: float
    match_reason: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    active_node: Optional[str] = None
    visitor_id: Optional[str] = None
    visitor_identity: Optional[Dict[str, Any]] = None


class FitScanRequest(BaseModel):
    job_title: str = ""
    company: str = ""
    job_description: str
    session_id: Optional[str] = None
    visitor_id: Optional[str] = None
    visitor_identity: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    detected_language: str
    sources_summary: List[SourceSummaryResponse]
    evidence: List[EvidenceResponse] = Field(default_factory=list)
    usage: dict
    trace_id: Optional[str] = None


class TranscriptionResponse(BaseModel):
    transcript: str


class ReportResponse(BaseModel):
    node_id: str
    title: str
    content: str


class VoiceChatResponse(ChatResponse):
    transcript: str
    audio_base64: Optional[str] = None
    audio_mime_type: str = "audio/mpeg"
    tts_error: Optional[str] = None


class TTSRequest(BaseModel):
    text: str
    visitor_id: Optional[str] = None
    session_id: Optional[str] = None
    visitor_identity: Optional[Dict[str, Any]] = None


class TTSResponse(BaseModel):
    audio_base64: str
    audio_mime_type: str = "audio/mpeg"


class VisitRequest(BaseModel):
    path: str = "/"
    referrer: Optional[str] = None
    title: Optional[str] = None
    visitor_id: Optional[str] = None
    visitor_identity: Optional[Dict[str, Any]] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    viewport: Optional[dict] = None


class TrackEventRequest(BaseModel):
    kind: str
    visitor_id: Optional[str] = None
    session_id: Optional[str] = None
    visitor_identity: Optional[Dict[str, Any]] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class PublicWarmupRequest(BaseModel):
    visitor_id: Optional[str] = None
    session_id: Optional[str] = None
    reason: str = "page"


class RagFeedbackRequest(BaseModel):
    trace_id: Optional[str] = None
    session_id: Optional[str] = None
    visitor_id: Optional[str] = None
    visitor_identity: Optional[Dict[str, Any]] = None
    rating: str
    reason: Optional[str] = None
    comment: Optional[str] = None
    expected_answer: Optional[str] = None


PUBLIC_EVENT_KINDS = {
    "material_download",
    "report_open",
    "gallery_open",
    "gallery_navigate",
    "visitor_identity",
    "frontend_error",
    "dossier_open",
    "evidence_open",
    "summary_copied",
}

_public_warmup_last: Dict[str, float] = {}


def _writable_directory_status(directory: Path) -> Dict[str, Any]:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".health-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return {"ok": True, "error": None}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:240]}


def _actor_type(request: Request, visitor_identity: Optional[Dict[str, Any]] = None) -> str:
    admin = _current_admin(request, settings)
    if admin:
        return "admin"
    if visitor_identity and any(visitor_identity.get(field) for field in ("name", "company", "email")):
        return "identified_visitor"
    return "visitor"


def _with_identity(payload: Dict[str, Any], visitor_identity: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not visitor_identity:
        return payload
    clean_identity = {
        key: str(value).strip()[:160]
        for key, value in visitor_identity.items()
        if key in {"name", "company", "role", "email"} and str(value).strip()
    }
    if not clean_identity:
        return payload
    return {**payload, "identity": clean_identity}


def _public_warmup_key(payload: PublicWarmupRequest, request: Request) -> str:
    if payload.visitor_id:
        return payload.visitor_id
    if request.client and request.client.host:
        return request.client.host
    return "anonymous"


def _vector_index_ready() -> bool:
    if uses_pgvector(settings):
        return bool(pgvector_status(settings).get("ready"))
    chroma_dir = settings.resolved_chroma_dir
    return chroma_dir.exists() and any(chroma_dir.rglob("*"))


def _chat_response_from_result(result: AgentResult) -> ChatResponse:
    sources = [SourceSummaryResponse(**source.__dict__) for source in result.sources]
    evidence = [EvidenceResponse(**item.__dict__) for item in result.evidence]
    return ChatResponse(
        session_id=result.session_id,
        answer=result.answer,
        detected_language=result.detected_language,
        sources_summary=sources,
        evidence=evidence,
        usage=result.usage,
        trace_id=result.trace_id or result.usage.get("trace_id"),
    )


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    start = time.perf_counter()
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as exc:
        status_code = 500
        log_event(
            settings,
            "backend_error",
            request=request,
            payload={"error": str(exc)[:500], "request_id": request_id},
        )
        raise
    finally:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "latency_ms": elapsed_ms,
                },
                ensure_ascii=True,
            )
        )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    log_event(
        settings,
        "app_error",
        request=request,
        payload={"code": exc.code, "message": exc.message, "status_code": exc.status_code},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


@app.get("/health")
def health():
    materials_dir = settings.resolved_materials_dir
    material_files = [path for path in materials_dir.rglob("*") if path.is_file()] if materials_dir.exists() else []
    chroma_dir = settings.resolved_chroma_dir
    chroma_exists = chroma_dir.exists() and any(chroma_dir.rglob("*"))
    vector_status = (
        pgvector_status(settings)
        if uses_pgvector(settings)
        else {"backend": "chroma", "ready": chroma_exists, "chunks": None, "last_reindex_at": None, "error": None, "index_type": "none"}
    )
    return {
        "status": "ok",
        "openai_configured": bool(settings.openai_api_key),
        "chroma_dir": str(chroma_dir),
        "chroma_exists": chroma_exists,
        "chroma_writable": _writable_directory_status(chroma_dir),
        "rag_auto_reindex_on_missing": settings.rag_auto_reindex_on_missing,
        "vector_backend": vector_status["backend"],
        "vector_index_ready": vector_status["ready"],
        "vector_index_type": vector_status.get("index_type"),
        "vector_chunks": vector_status["chunks"],
        "last_reindex_at": vector_status["last_reindex_at"],
        "vector_error": vector_status["error"],
        "warmup_status": warmup_status(),
        "realtime_enabled": settings.realtime_enabled,
        "realtime_model": settings.openai_realtime_model,
        "realtime_voice": settings.openai_realtime_voice,
        "app_env": settings.app_env,
        "public_backend_url": settings.public_backend_url,
        "public_frontend_url": settings.public_frontend_url,
        "github_branch": settings.github_branch,
        "rag_lab_available": True,
        "admin_features": [
            "markdown",
            "prompt",
            "events",
            "jobs",
            "rag_lab",
            "rag_evals",
            "rag_probe",
            "rag_quality",
            "rag_feedback",
            "knowledge_suggestions",
            "draft_studio",
            "draft_agent",
            "rag_studio",
            "rag_change_proposals",
        ],
        "cors_local_enabled": settings.allow_local_cors,
        "frontend_origins": settings.frontend_origin_list,
        "local_origin_regex": settings.local_frontend_origin_regex if settings.allow_local_cors else "",
        "knowledge_dir": str(settings.resolved_knowledge_dir),
        "knowledge_exists": settings.resolved_knowledge_dir.exists(),
        "materials_dir": str(materials_dir),
        "materials_exists": materials_dir.exists(),
        "materials_count": len(material_files),
        "materials_dir_safe": materials_dir.exists() and settings.backend_dir.resolve() in materials_dir.resolve().parents,
        "events": event_storage_status(settings),
        "job_scans": job_scan_storage_status(settings),
        "rag_quality": rag_quality_storage_status(settings),
        "draft_studio": draft_studio_storage_status(settings),
        "rag_studio": rag_studio_storage_status(settings),
        "rag_rerank_enabled": settings.rag_rerank_enabled,
        "rag_rerank_provider": settings.rag_rerank_provider,
        "rag_feedback_enabled": settings.rag_feedback_enabled,
        "rag_suggestions_enabled": settings.rag_suggestions_enabled,
        "version": getattr(settings, "app_version", "1.0.0"),
        "commit": getattr(settings, "app_commit", ""),
        "chat_model": settings.openai_chat_model,
        "fast_chat_model": settings.openai_fast_chat_model,
        "embedding_model": settings.openai_embedding_model,
    }


@app.post("/warmup/public")
def public_warmup(payload: PublicWarmupRequest, request: Request):
    key = _public_warmup_key(payload, request)
    now = time.time()
    min_interval = max(settings.public_warmup_min_interval_seconds, 30)
    last = _public_warmup_last.get(key)
    current_status = warmup_status()
    if last and now - last < min_interval and current_status.get("state") in {"running", "success"}:
        return {
            "status": "skipped",
            "warmed": current_status.get("state") == "success",
            "took_ms": 0,
            "vector_index_ready": _vector_index_ready(),
            "warmup_status": current_status,
        }

    _public_warmup_last[key] = now
    start = time.perf_counter()
    status = start_warmup(settings, actor=f"public:{payload.reason[:40]}")
    log_event(
        settings,
        "warmup_started",
        request=request,
        visitor_id=payload.visitor_id,
        session_id=payload.session_id,
        actor_type=_actor_type(request),
        payload={"reason": payload.reason, "state": status.get("state")},
    )
    return {
        "status": status.get("state", "running"),
        "warmed": status.get("state") == "success",
        "took_ms": round((time.perf_counter() - start) * 1000, 2),
        "vector_index_ready": _vector_index_ready(),
        "warmup_status": status,
    }


@app.post("/realtime/call")
async def realtime_call(request: Request):
    sdp_offer = (await request.body()).decode("utf-8", errors="ignore")
    session_id = request.query_params.get("session_id")
    visitor_id = request.query_params.get("visitor_id")
    active_context = request.query_params.get("active_context")
    start_warmup(settings, actor="realtime")
    answer_sdp, call_id = create_realtime_call(
        settings=settings,
        sdp_offer=sdp_offer,
        session_id=session_id,
        visitor_id=visitor_id,
        active_context=active_context,
        request=request,
    )
    headers = {"Cache-Control": "no-store"}
    if call_id:
        headers["X-Realtime-Call-Id"] = call_id
    return Response(content=answer_sdp, media_type="application/sdp", headers=headers)


@app.post("/events/visit")
def track_visit(payload: VisitRequest, request: Request):
    log_event(
        settings,
        "site_visit",
        request=request,
        visitor_id=payload.visitor_id,
        session_id=payload.visitor_id,
        actor_type=_actor_type(request, payload.visitor_identity),
        payload=_with_identity(payload.model_dump(exclude={"visitor_identity"}), payload.visitor_identity),
    )
    return {"ok": True}


@app.post("/events/track")
def track_public_event(payload: TrackEventRequest, request: Request):
    if payload.kind not in PUBLIC_EVENT_KINDS:
        raise AppError("invalid_event_kind", "Evento público não permitido.", 400)
    log_event(
        settings,
        payload.kind,
        request=request,
        visitor_id=payload.visitor_id,
        session_id=payload.session_id,
        actor_type=_actor_type(request, payload.visitor_identity),
        payload=_with_identity(payload.payload, payload.visitor_identity),
    )
    return {"ok": True}


@app.post("/rag/feedback")
def rag_feedback(payload: RagFeedbackRequest, request: Request):
    if not settings.rag_feedback_enabled:
        raise AppError("rag_feedback_disabled", "Feedback RAG desabilitado neste ambiente.", 503)
    update_rag_trace_actor(
        settings,
        payload.trace_id,
        visitor_id=payload.visitor_id,
        session_id=payload.session_id,
    )
    result = create_rag_feedback(
        settings,
        {
            "trace_id": payload.trace_id,
            "session_id": payload.session_id,
            "visitor_id": payload.visitor_id,
            "visitor_identity": payload.visitor_identity,
            "rating": payload.rating,
            "reason": payload.reason,
            "comment": payload.comment,
            "expected_answer": payload.expected_answer,
        },
    )
    log_event(
        settings,
        "rag_feedback",
        request=request,
        visitor_id=payload.visitor_id,
        session_id=payload.session_id,
        actor_type=_actor_type(request, payload.visitor_identity),
        payload={
            "trace_id": payload.trace_id,
            "rating": payload.rating,
            "reason": payload.reason,
            "suggestion_id": (result.get("suggestion") or {}).get("id"),
            **({"identity": _with_identity({}, payload.visitor_identity).get("identity")} if payload.visitor_identity else {}),
        },
    )
    return result


def _parse_report(raw: str) -> tuple[str, str]:
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            raw = parts[2].strip()
    title = "Relatório"
    for line in raw.splitlines():
        if line.startswith("# "):
            title = line.removeprefix("# ").strip()
            break
    return title, raw


@app.get("/reports/{node_id}", response_model=ReportResponse)
def node_report(node_id: str):
    allowed = {"gabriel", "trajetoria", "projetos", "stack", "experiencia", "mercado", "entrevista", "materiais"}
    if node_id not in allowed:
        raise AppError(code="report_not_found", message="Relatório não encontrado.", status_code=404)

    reports_dir = settings.resolved_knowledge_dir / "reports"
    report_path = (reports_dir / f"{node_id}.md").resolve()
    if reports_dir.resolve() not in report_path.parents or not report_path.exists():
        raise AppError(code="report_not_found", message="Relatório não encontrado.", status_code=404)

    title, content = _parse_report(report_path.read_text(encoding="utf-8"))
    return ReportResponse(node_id=node_id, title=title, content=content)


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request):
    result = answer_question(
        message=payload.message,
        session_id=payload.session_id,
        active_node=payload.active_node,
        settings=settings,
    )
    response_body = _chat_response_from_result(result)
    update_rag_trace_actor(settings, response_body.trace_id, visitor_id=payload.visitor_id, session_id=result.session_id)
    log_event(
        settings,
        "chat_exchange",
        request=request,
        visitor_id=payload.visitor_id,
        session_id=result.session_id,
        actor_type=_actor_type(request, payload.visitor_identity),
        payload={
            "question": payload.message,
            "answer": result.answer,
            "active_node": payload.active_node,
            "detected_language": result.detected_language,
            "usage": result.usage,
            "sources": [source.model_dump() for source in response_body.sources_summary],
            **({"identity": _with_identity({}, payload.visitor_identity).get("identity")} if payload.visitor_identity else {}),
        },
    )
    return response_body


@app.post("/chat/stream")
def chat_stream(payload: ChatRequest, request: Request):
    def events():
        try:
            for item in stream_answer_question(
                message=payload.message,
                session_id=payload.session_id,
                active_node=payload.active_node,
                settings=settings,
            ):
                if item.get("event") != "done":
                    yield _sse(item["event"], item.get("data", {}))
                    continue

                result = item["result"]
                response_body = _chat_response_from_result(result)
                update_rag_trace_actor(settings, response_body.trace_id, visitor_id=payload.visitor_id, session_id=result.session_id)
                yield _sse("stage", {"id": "saving_event", "label": "Salvando evento", "status": "active"})
                event_start = time.perf_counter()
                log_event(
                    settings,
                    "chat_exchange",
                    request=request,
                    visitor_id=payload.visitor_id,
                    session_id=result.session_id,
                    actor_type=_actor_type(request, payload.visitor_identity),
                    payload={
                        "question": payload.message,
                        "answer": result.answer,
                        "active_node": payload.active_node,
                        "detected_language": result.detected_language,
                        "usage": result.usage,
                        "stream": True,
                        "sources": [source.model_dump() for source in response_body.sources_summary],
                        **({"identity": _with_identity({}, payload.visitor_identity).get("identity")} if payload.visitor_identity else {}),
                    },
                )
                event_log_ms = round((time.perf_counter() - event_start) * 1000, 2)
                response_body.usage["event_log_ms"] = event_log_ms
                yield _sse("stage", {"id": "saving_event", "label": "Salvando evento", "status": "complete", "elapsed_ms": event_log_ms})
                yield _sse("metrics", response_body.usage)
                yield _sse("done", response_body.model_dump())
        except AppError as exc:
            body = {"code": exc.code, "message": exc.message}
            log_event(
                settings,
                "app_error",
                request=request,
                visitor_id=payload.visitor_id,
                session_id=payload.session_id,
                actor_type=_actor_type(request, payload.visitor_identity),
                payload={"code": exc.code, "message": exc.message, "status_code": exc.status_code, "stream": True},
            )
            yield _sse("stage", {"id": "error", "label": "Erro no processamento", "status": "error"})
            yield _sse("error", body)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/fit/stream")
def fit_stream(payload: FitScanRequest, request: Request):
    clean_description = payload.job_description.strip()
    if not clean_description:
        raise AppError("empty_job_description", "Cole a descrição da vaga para analisar o fit.", 400)

    scan_id = create_job_scan(
        settings,
        job_title=payload.job_title.strip(),
        company=payload.company.strip(),
        job_description=clean_description,
        visitor_id=payload.visitor_id,
        session_id=payload.session_id,
        visitor_identity=payload.visitor_identity,
    )
    log_event(
        settings,
        "fit_started",
        request=request,
        visitor_id=payload.visitor_id,
        session_id=payload.session_id,
        actor_type=_actor_type(request, payload.visitor_identity),
        payload={
            "scan_id": scan_id,
            "job_title": payload.job_title,
            "company": payload.company,
            "job_description_chars": len(clean_description),
            **({"identity": _with_identity({}, payload.visitor_identity).get("identity")} if payload.visitor_identity else {}),
        },
    )

    def events():
        try:
            yield _sse("stage", {"id": "job_saved", "label": "Vaga salva", "status": "complete", "scan_id": scan_id})
            for item in stream_fit_analysis(
                job_title=payload.job_title,
                company=payload.company,
                job_description=clean_description,
                session_id=payload.session_id,
                settings=settings,
            ):
                if item.get("event") != "done":
                    yield _sse(item["event"], item.get("data", {}))
                    continue

                result = item["result"]
                update_rag_trace_actor(settings, result.trace_id, visitor_id=payload.visitor_id, session_id=result.session_id)
                sources = [SourceSummaryResponse(**source.__dict__) for source in result.sources]
                evidence = [EvidenceResponse(**item.__dict__) for item in result.evidence]
                docs = list(result.usage.get("retrieved_sources") or [])
                yield _sse("stage", {"id": "saving_scan", "label": "Salvando análise", "status": "active"})
                event_start = time.perf_counter()
                finish_job_scan(
                    settings,
                    scan_id,
                    summary=result.summary,
                    analysis_text=result.answer,
                    analysis=result.analysis,
                    metrics=result.usage,
                    sources=[source.model_dump() for source in sources],
                    docs=docs,
                    fit_score=result.fit_score,
                    model=result.usage.get("model"),
                )
                log_event(
                    settings,
                    "fit_completed",
                    request=request,
                    visitor_id=payload.visitor_id,
                    session_id=result.session_id,
                    actor_type=_actor_type(request, payload.visitor_identity),
                    payload={
                        "scan_id": scan_id,
                        "job_title": payload.job_title,
                        "company": payload.company,
                        "job_description_chars": len(clean_description),
                        "fit_score": result.fit_score,
                        "summary": result.summary,
                        "usage": result.usage,
                        "trace_id": result.trace_id,
                        "sources": [source.model_dump() for source in sources],
                        "evidence_count": len(evidence),
                        **({"identity": _with_identity({}, payload.visitor_identity).get("identity")} if payload.visitor_identity else {}),
                    },
                )
                event_log_ms = round((time.perf_counter() - event_start) * 1000, 2)
                result.usage["event_log_ms"] = event_log_ms
                yield _sse("stage", {"id": "saving_scan", "label": "Salvando análise", "status": "complete", "elapsed_ms": event_log_ms})
                yield _sse("metrics", result.usage)
                yield _sse(
                    "done",
                    {
                        "scan_id": scan_id,
                        "session_id": result.session_id,
                        "answer": result.answer,
                        "summary": result.summary,
                        "fit_score": result.fit_score,
                        "analysis": result.analysis,
                        "trace_id": result.trace_id,
                        "sources_summary": [source.model_dump() for source in sources],
                        "evidence": [item.model_dump() for item in evidence],
                        "usage": result.usage,
                    },
                )
        except AppError as exc:
            body = {"code": exc.code, "message": exc.message}
            fail_job_scan(settings, scan_id, exc.message)
            log_event(
                settings,
                "fit_error",
                request=request,
                visitor_id=payload.visitor_id,
                session_id=payload.session_id,
                actor_type=_actor_type(request, payload.visitor_identity),
                payload={
                    "scan_id": scan_id,
                    "job_title": payload.job_title,
                    "company": payload.company,
                    "job_description_chars": len(clean_description),
                    "code": exc.code,
                    "message": exc.message,
                    "status_code": exc.status_code,
                    **({"identity": _with_identity({}, payload.visitor_identity).get("identity")} if payload.visitor_identity else {}),
                },
            )
            yield _sse("stage", {"id": "error", "label": "Erro na análise", "status": "error"})
            yield _sse("error", body)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/voice/transcribe", response_model=TranscriptionResponse)
async def voice_transcribe(file: UploadFile = File(...)):
    transcript = await transcribe_upload(file, settings=settings)
    if not transcript:
        raise AppError(
            code="empty_transcript",
            message="Não consegui identificar fala no áudio enviado.",
            status_code=422,
        )
    return TranscriptionResponse(transcript=transcript)


@app.post("/voice/tts", response_model=TTSResponse)
def voice_tts(payload: TTSRequest, request: Request):
    audio_base64 = synthesize_speech_base64(payload.text, settings=settings)
    log_event(
        settings,
        "tts_synthesis",
        request=request,
        visitor_id=payload.visitor_id,
        session_id=payload.session_id,
        actor_type=_actor_type(request, payload.visitor_identity),
        payload={
            "text_chars": len(payload.text or ""),
            **({"identity": _with_identity({}, payload.visitor_identity).get("identity")} if payload.visitor_identity else {}),
        },
    )
    return TTSResponse(audio_base64=audio_base64)


@app.post("/voice/chat", response_model=VoiceChatResponse)
async def voice_chat(
    request: Request,
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(default=None),
    active_node: Optional[str] = Form(default=None),
    visitor_id: Optional[str] = Form(default=None),
    visitor_identity: Optional[str] = Form(default=None),
):
    identity_data: Optional[Dict[str, Any]] = None
    if visitor_identity:
        try:
            parsed = json.loads(visitor_identity)
            if isinstance(parsed, dict):
                identity_data = parsed
        except json.JSONDecodeError:
            identity_data = None

    transcript = await transcribe_upload(file, settings=settings)
    if not transcript:
        raise AppError(
            code="empty_transcript",
            message="Não consegui identificar fala no áudio enviado.",
            status_code=422,
        )

    result = answer_question(
        message=transcript,
        session_id=session_id,
        active_node=active_node,
        settings=settings,
    )
    update_rag_trace_actor(settings, result.trace_id, visitor_id=visitor_id, session_id=result.session_id)

    audio_base64 = None
    tts_error = None
    try:
        audio_base64 = synthesize_speech_base64(result.answer, settings=settings)
    except AppError as exc:
        tts_error = exc.message

    sources = [SourceSummaryResponse(**source.__dict__) for source in result.sources]
    evidence = [EvidenceResponse(**item.__dict__) for item in result.evidence]
    log_event(
        settings,
        "voice_chat_exchange",
        request=request,
        visitor_id=visitor_id,
        session_id=result.session_id,
        actor_type=_actor_type(request, identity_data),
        payload={
            "transcript": transcript,
            "answer": result.answer,
            "active_node": active_node,
            "detected_language": result.detected_language,
            "usage": result.usage,
            "tts_error": tts_error,
            "sources": [source.model_dump() for source in sources],
            "evidence_count": len(evidence),
            **({"identity": _with_identity({}, identity_data).get("identity")} if identity_data else {}),
        },
    )

    return VoiceChatResponse(
        session_id=result.session_id,
        transcript=transcript,
        answer=result.answer,
        detected_language=result.detected_language,
        sources_summary=sources,
        evidence=evidence,
        usage=result.usage,
        trace_id=result.trace_id,
        audio_base64=audio_base64,
        tts_error=tts_error,
    )


@app.get("/materials/extract-gabriel")
def extract_gabriel():
    materials_dir = settings.resolved_materials_dir
    if not materials_dir.exists():
        raise AppError(
            code="materials_missing",
            message="O currículo ainda não foi configurado.",
            status_code=404,
        )

    candidates = [
        path
        for path in materials_dir.rglob("*.docx")
        if any(token in path.stem.lower() for token in ("curriculo", "currículo", "resume", "cv"))
    ]
    if not candidates:
        raise AppError(
            code="curriculum_missing",
            message="O currículo em DOCX ainda não foi configurado.",
            status_code=404,
        )

    curriculum_path = sorted(candidates, key=lambda path: (len(path.name), path.name.lower()))[0]
    return FileResponse(
        curriculum_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="Curriculo_Gabriel_Camim.docx",
    )
