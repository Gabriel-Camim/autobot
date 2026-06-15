from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import httpx
from fastapi import Request

from agent import AppError, load_system_prompt, realtime_dossier_context, realtime_search_knowledge
from config import Settings
from events import log_event


logger = logging.getLogger("gabriel_realtime")


REALTIME_CONNECT_TIMEOUT = 20
REALTIME_READ_TIMEOUT = 60


@dataclass
class RealtimeCallContext:
    call_id: str
    session_id: Optional[str]
    visitor_id: Optional[str]
    active_context: Optional[str]
    started_at: float


_active_sidebands: Dict[str, RealtimeCallContext] = {}
_active_lock = threading.Lock()


def _tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": "search_gabriel_knowledge",
            "description": (
                "Busca contexto factual na base Markdown/pgvector do Gabriel. Use antes de responder "
                "perguntas sobre trajetória, projetos, stack, experiências, formação, mercado ou fit."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Pergunta ou trecho que precisa de evidência factual.",
                    },
                    "active_context": {
                        "type": "string",
                        "description": "Contexto opcional da UI, como stack, projetos, trajetória ou entrevista.",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "get_gabriel_dossier",
            "description": "Retorna um dossiê estático curto sobre uma seção do portfólio do Gabriel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": [
                            "gabriel",
                            "trajetoria",
                            "projetos",
                            "stack",
                            "experiencia",
                            "mercado",
                            "entrevista",
                            "materiais",
                        ],
                    }
                },
                "additionalProperties": False,
            },
        },
    ]


def _realtime_instructions(settings: Settings, active_context: Optional[str]) -> str:
    base = load_system_prompt(settings)
    return f"""
{base}

Realtime voice mode:
- This is a live recruiter conversation. Be concise, natural, warm, and interview-ready.
- Speak in first person as Gabriel.
- Keep spoken answers short by default: 20 to 50 seconds, then invite deeper questions.
- Do not use Markdown formatting, bold markers, headings, tables, or code blocks in spoken answers.
- Before factual claims about my skills, projects, history, education, markets, limitations or fit, call search_gabriel_knowledge.
- If the tool returns weak or missing context, say honestly that this detail is not documented yet.
- Never invent technologies, dates, companies, credentials, metrics or project status.
- Current UI context: {active_context or "none"}.
""".strip()


def _session_config(settings: Settings, active_context: Optional[str]) -> Dict[str, Any]:
    return {
        "type": "realtime",
        "model": settings.openai_realtime_model,
        "instructions": _realtime_instructions(settings, active_context),
        "audio": {
            "output": {
                "voice": settings.openai_realtime_voice,
            }
        },
        "tools": _tool_schemas(),
        "tool_choice": "auto",
    }


def _sanitize_openai_error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        body = response.text[:400]
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error.get("code") or body)[:400]
        return str(body.get("message") or body)[:400]
    return str(body)[:400]


def _call_id_from_location(location: Optional[str]) -> Optional[str]:
    if not location:
        return None
    cleaned = location.rstrip("/")
    return cleaned.rsplit("/", 1)[-1] if "/" in cleaned else cleaned


def create_realtime_call(
    *,
    settings: Settings,
    sdp_offer: str,
    session_id: Optional[str],
    visitor_id: Optional[str],
    active_context: Optional[str],
    request: Optional[Request] = None,
) -> Tuple[str, Optional[str]]:
    if not settings.realtime_enabled:
        raise AppError("realtime_disabled", "O modo de voz ao vivo ainda não está habilitado neste backend.", 503)
    if not settings.openai_api_key:
        raise AppError("missing_openai_key", "A chave da OpenAI não está configurada no backend.", 503)
    if not sdp_offer.strip() or "v=0" not in sdp_offer:
        raise AppError("invalid_sdp", "Oferta WebRTC inválida. Recarregue a página e tente novamente.", 400)

    session = _session_config(settings, active_context)
    files = {
        "sdp": (None, sdp_offer, "application/sdp"),
        "session": (None, json.dumps(session, ensure_ascii=False), "application/json"),
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    try:
        with httpx.Client(timeout=httpx.Timeout(REALTIME_READ_TIMEOUT, connect=REALTIME_CONNECT_TIMEOUT)) as client:
            response = client.post("https://api.openai.com/v1/realtime/calls", headers=headers, files=files)
    except httpx.RequestError as exc:
        logger.exception("realtime_openai_request_failed")
        raise AppError(
            "realtime_openai_unavailable",
            "Não consegui conectar ao serviço de voz em tempo real agora.",
            503,
        ) from exc

    if response.status_code >= 400:
        message = _sanitize_openai_error(response)
        logger.warning("realtime_openai_rejected status=%s message=%s", response.status_code, message)
        raise AppError(
            "realtime_openai_rejected",
            f"A OpenAI recusou a sessão em tempo real: {message}",
            502,
        )

    answer_sdp = response.text
    call_id = _call_id_from_location(response.headers.get("location"))
    log_event(
        settings,
        "realtime_session_started",
        request=request,
        visitor_id=visitor_id,
        session_id=session_id,
        actor_type="visitor",
        payload={
            "call_id": call_id,
            "model": settings.openai_realtime_model,
            "voice": settings.openai_realtime_voice,
            "active_context": active_context,
        },
    )
    if call_id:
        start_sideband(settings, call_id, session_id=session_id, visitor_id=visitor_id, active_context=active_context)
    return answer_sdp, call_id


def start_sideband(
    settings: Settings,
    call_id: str,
    *,
    session_id: Optional[str],
    visitor_id: Optional[str],
    active_context: Optional[str],
) -> None:
    context = RealtimeCallContext(
        call_id=call_id,
        session_id=session_id,
        visitor_id=visitor_id,
        active_context=active_context,
        started_at=time.time(),
    )
    with _active_lock:
        _active_sidebands[call_id] = context
    thread = threading.Thread(target=_run_sideband, args=(settings, context), daemon=True)
    thread.start()


def _run_sideband(settings: Settings, context: RealtimeCallContext) -> None:
    try:
        import websocket
    except ImportError:
        logger.warning("realtime_sideband_websocket_client_missing")
        return

    url = f"wss://api.openai.com/v1/realtime?call_id={context.call_id}"
    headers = [
        f"Authorization: Bearer {settings.openai_api_key}",
        "OpenAI-Beta: realtime=v1",
    ]
    ws = websocket.WebSocket()
    try:
        ws.connect(url, header=headers, timeout=REALTIME_CONNECT_TIMEOUT)
        ws.send(
            json.dumps(
                {
                    "type": "session.update",
                    "session": {
                        "instructions": _realtime_instructions(settings, context.active_context),
                        "tools": _tool_schemas(),
                        "tool_choice": "auto",
                    },
                },
                ensure_ascii=False,
            )
        )
        deadline = time.time() + max(settings.realtime_max_session_seconds, 30)
        while time.time() < deadline:
            try:
                raw_event = ws.recv()
            except Exception:
                break
            if not raw_event:
                continue
            try:
                event = json.loads(raw_event)
            except json.JSONDecodeError:
                continue
            _handle_sideband_event(ws, settings, context, event)
    except Exception as exc:
        logger.exception("realtime_sideband_failed")
        log_event(
            settings,
            "realtime_error",
            visitor_id=context.visitor_id,
            session_id=context.session_id,
            actor_type="visitor",
            payload={"call_id": context.call_id, "error": str(exc)[:300]},
        )
    finally:
        try:
            ws.close()
        except Exception:
            pass
        with _active_lock:
            _active_sidebands.pop(context.call_id, None)
        log_event(
            settings,
            "realtime_session_ended",
            visitor_id=context.visitor_id,
            session_id=context.session_id,
            actor_type="visitor",
            payload={"call_id": context.call_id, "duration_ms": int((time.time() - context.started_at) * 1000)},
        )


def _handle_sideband_event(ws: Any, settings: Settings, context: RealtimeCallContext, event: Dict[str, Any]) -> None:
    event_type = str(event.get("type") or "")
    item = event.get("item") if isinstance(event.get("item"), dict) else event
    if event_type not in {"conversation.item.done", "response.output_item.done"}:
        return
    if str(item.get("type") or "") != "function_call":
        return

    name = str(item.get("name") or "")
    call_id = str(item.get("call_id") or item.get("id") or "")
    try:
        arguments = json.loads(item.get("arguments") or "{}")
    except json.JSONDecodeError:
        arguments = {}

    start = time.perf_counter()
    try:
        result = _execute_tool(settings, name, arguments, context.active_context)
    except Exception as exc:
        logger.exception("realtime_tool_failed")
        result = {"status": "error", "message": str(exc)[:300]}
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    log_event(
        settings,
        "realtime_rag_tool",
        visitor_id=context.visitor_id,
        session_id=context.session_id,
        actor_type="visitor",
        payload={
            "call_id": context.call_id,
            "tool": name,
            "elapsed_ms": elapsed_ms,
            "status": result.get("status"),
            "retrieved_docs": result.get("retrieved_docs"),
            "sources": result.get("sources"),
        },
    )
    ws.send(
        json.dumps(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                },
            },
            ensure_ascii=False,
        )
    )
    ws.send(json.dumps({"type": "response.create"}, ensure_ascii=False))


def _execute_tool(
    settings: Settings,
    name: str,
    arguments: Dict[str, Any],
    active_context: Optional[str],
) -> Dict[str, Any]:
    if name == "search_gabriel_knowledge":
        return realtime_search_knowledge(
            settings,
            query=str(arguments.get("query") or ""),
            active_context=str(arguments.get("active_context") or active_context or ""),
        )
    if name == "get_gabriel_dossier":
        return realtime_dossier_context(settings, section=str(arguments.get("section") or active_context or "gabriel"))
    return {"status": "unknown_tool", "message": f"Ferramenta desconhecida: {name}"}
