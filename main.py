from __future__ import annotations

import json
import logging
import time
import zipfile
from io import BytesIO
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from admin import _current_admin, router as admin_router
from agent import AppError, answer_question
from config import get_settings
from events import event_storage_status, log_event
from voice import synthesize_speech_base64, transcribe_upload


settings = get_settings()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("gabriel_api")

app = FastAPI(title="Gabriel Portfolio Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *settings.frontend_origin_list,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)

class SourceSummaryResponse(BaseModel):
    title: str
    category: str
    summary: str
    source: str
    tags: List[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    active_node: Optional[str] = None
    visitor_id: Optional[str] = None
    visitor_identity: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    detected_language: str
    sources_summary: List[SourceSummaryResponse]
    usage: dict


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


PUBLIC_EVENT_KINDS = {
    "material_download",
    "report_open",
    "gallery_open",
    "gallery_navigate",
    "visitor_identity",
    "frontend_error",
}


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
    return {
        "status": "ok",
        "openai_configured": bool(settings.openai_api_key),
        "chroma_dir": str(chroma_dir),
        "chroma_exists": chroma_dir.exists() and any(chroma_dir.rglob("*")),
        "knowledge_dir": str(settings.resolved_knowledge_dir),
        "knowledge_exists": settings.resolved_knowledge_dir.exists(),
        "materials_dir": str(materials_dir),
        "materials_exists": materials_dir.exists(),
        "materials_count": len(material_files),
        "materials_dir_safe": materials_dir.exists() and settings.backend_dir.resolve() in materials_dir.resolve().parents,
        "events": event_storage_status(settings),
    }


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
    sources = [SourceSummaryResponse(**source.__dict__) for source in result.sources]
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
            "sources": [source.model_dump() for source in sources],
            **({"identity": _with_identity({}, payload.visitor_identity).get("identity")} if payload.visitor_identity else {}),
        },
    )
    return ChatResponse(
        session_id=result.session_id,
        answer=result.answer,
        detected_language=result.detected_language,
        sources_summary=sources,
        usage=result.usage,
    )


@app.post("/chat/stream")
def chat_stream(payload: ChatRequest, request: Request):
    def events():
        try:
            result = answer_question(
                message=payload.message,
                session_id=payload.session_id,
                active_node=payload.active_node,
                settings=settings,
            )
            sources = [SourceSummaryResponse(**source.__dict__) for source in result.sources]
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
                    "sources": [source.model_dump() for source in sources],
                    **({"identity": _with_identity({}, payload.visitor_identity).get("identity")} if payload.visitor_identity else {}),
                },
            )
            body = ChatResponse(
                session_id=result.session_id,
                answer=result.answer,
                detected_language=result.detected_language,
                sources_summary=sources,
                usage=result.usage,
            ).model_dump()
            yield f"event: done\ndata: {json.dumps(body, ensure_ascii=False)}\n\n"
        except AppError as exc:
            body = {"code": exc.code, "message": exc.message}
            yield f"event: error\ndata: {json.dumps(body, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


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

    audio_base64 = None
    tts_error = None
    try:
        audio_base64 = synthesize_speech_base64(result.answer, settings=settings)
    except AppError as exc:
        tts_error = exc.message

    sources = [SourceSummaryResponse(**source.__dict__) for source in result.sources]
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
            **({"identity": _with_identity({}, identity_data).get("identity")} if identity_data else {}),
        },
    )

    return VoiceChatResponse(
        session_id=result.session_id,
        transcript=transcript,
        answer=result.answer,
        detected_language=result.detected_language,
        sources_summary=sources,
        usage=result.usage,
        audio_base64=audio_base64,
        tts_error=tts_error,
    )


@app.get("/materials/extract-gabriel")
def extract_gabriel():
    materials_dir = settings.resolved_materials_dir
    if not materials_dir.exists():
        raise AppError(
            code="materials_missing",
            message="O pacote recrutador ainda não foi configurado.",
            status_code=404,
        )

    files = [path for path in materials_dir.rglob("*") if path.is_file()]
    if not files:
        raise AppError(
            code="materials_empty",
            message="O pacote recrutador está vazio.",
            status_code=404,
        )

    archive = BytesIO()
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for path in files:
            zip_file.write(path, arcname=path.relative_to(materials_dir).as_posix())
    archive.seek(0)

    return StreamingResponse(
        archive,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="extrair-gabriel.zip"'},
    )
