from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from uuid import uuid4

from langchain_chroma import Chroma
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from config import Settings, get_settings


logger = logging.getLogger("gabriel_agent")


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass
class SourceSummary:
    title: str
    category: str
    summary: str
    source: str
    tags: List[str]


@dataclass
class AgentResult:
    session_id: str
    answer: str
    detected_language: str
    sources: List[SourceSummary]
    usage: Dict[str, int]


class ConversationStore:
    def __init__(self, max_messages: int):
        self.max_messages = max_messages
        self._sessions: Dict[str, List[BaseMessage]] = {}

    def get(self, session_id: str) -> List[BaseMessage]:
        return self._sessions.get(session_id, [])

    def append(self, session_id: str, user_message: str, assistant_message: str) -> None:
        history = self._sessions.setdefault(session_id, [])
        history.extend([HumanMessage(content=user_message), AIMessage(content=assistant_message)])
        if len(history) > self.max_messages:
            self._sessions[session_id] = history[-self.max_messages :]


_stores: Dict[int, ConversationStore] = {}


FALLBACK_SYSTEM_PROMPT = """
You are Gabriel's personal portfolio agent, speaking as Gabriel in a recruiter interview.

Core rules:
- Answer in first person as Gabriel.
- Respond in the same language as the user's latest message. If the user mixes languages, prefer the dominant language.
- Use correct accents and natural spelling in Portuguese.
- Use the provided retrieved context as the source of truth.
- Be professional, natural, direct, and human. Do not sound robotic or over-marketed.
- If the context does not contain enough information, say honestly that I do not have enough documented context yet.
- Do not invent employers, dates, metrics, credentials, links, or personal details.
- When useful, connect skills to concrete projects and decisions.
- Keep answers concise by default, then offer to go deeper.
""".strip()


def load_system_prompt(settings: Settings) -> str:
    try:
        prompt = settings.resolved_system_prompt_path.read_text(encoding="utf-8").strip()
    except OSError:
        logger.warning("system_prompt_file_missing")
        return FALLBACK_SYSTEM_PROMPT
    return prompt or FALLBACK_SYSTEM_PROMPT


def _require_openai_key(settings: Settings) -> None:
    if not settings.openai_api_key:
        raise AppError(
            code="missing_openai_key",
            message="A chave da OpenAI não está configurada no backend. Defina OPENAI_API_KEY no .env ou no deploy.",
            status_code=503,
        )


def _get_store(settings: Settings) -> ConversationStore:
    key = id(settings)
    if key not in _stores:
        _stores[key] = ConversationStore(max_messages=settings.max_history_messages)
    return _stores[key]


def _build_embeddings(settings: Settings) -> OpenAIEmbeddings:
    _require_openai_key(settings)
    return OpenAIEmbeddings(model=settings.openai_embedding_model, api_key=settings.openai_api_key)


def _build_vectorstore(settings: Settings) -> Chroma:
    return Chroma(
        collection_name=settings.chroma_collection,
        persist_directory=str(settings.resolved_chroma_dir),
        embedding_function=_build_embeddings(settings),
    )


def _build_llm(settings: Settings) -> ChatOpenAI:
    _require_openai_key(settings)
    return ChatOpenAI(
        model=settings.openai_chat_model,
        temperature=0.35,
        api_key=settings.openai_api_key,
    )


def _detect_language(text: str) -> str:
    normalized = f" {text.lower()} "
    portuguese_markers = [
        " você ",
        " você ",
        " sobre ",
        " trajetória ",
        " experiência ",
        " experiência ",
        " projeto ",
        " quais ",
        " como ",
        " por que ",
        " trabalho ",
        " formação ",
    ]
    english_markers = [
        " you ",
        " your ",
        " about ",
        " career ",
        " experience ",
        " project ",
        " why ",
        " how ",
        " work ",
        " skills ",
    ]
    pt_score = sum(marker in normalized for marker in portuguese_markers)
    en_score = sum(marker in normalized for marker in english_markers)
    if pt_score > en_score:
        return "pt-BR"
    if en_score > pt_score:
        return "en"
    return "auto"


def _format_context(docs_with_scores) -> str:
    blocks = []
    for doc, score in docs_with_scores:
        metadata = doc.metadata or {}
        title = metadata.get("title", "Documento sem título")
        category = metadata.get("category", "geral")
        summary = metadata.get("summary", "")
        source = metadata.get("source", "")
        blocks.append(
            "\n".join(
                [
                    f"[title: {title}]",
                    f"[category: {category}]",
                    f"[summary: {summary}]",
                    f"[source: {source}]",
                    f"[score: {score}]",
                    doc.page_content,
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


def _source_summaries(docs_with_scores) -> List[SourceSummary]:
    seen = set()
    summaries: List[SourceSummary] = []
    for doc, _score in docs_with_scores:
        metadata = doc.metadata or {}
        source = metadata.get("source", "")
        if source in seen:
            continue
        seen.add(source)
        tags = metadata.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        summaries.append(
            SourceSummary(
                title=metadata.get("title", "Documento sem título"),
                category=metadata.get("category", "geral"),
                summary=metadata.get("summary", "Fonte usada pelo agente."),
                source=source,
                tags=tags,
            )
        )
    return summaries[:4]


def _usage_from_response(response: AIMessage) -> Dict[str, int]:
    usage = getattr(response, "usage_metadata", None) or {}
    return {
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
    }


def answer_question(
    message: str,
    session_id: Optional[str] = None,
    active_node: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> AgentResult:
    settings = settings or get_settings()
    session_id = session_id or str(uuid4())
    clean_message = message.strip()
    if not clean_message:
        raise AppError(code="empty_message", message="Envie uma pergunta ou mensagem para conversar.", status_code=400)

    retrieval_query = clean_message
    if active_node:
        retrieval_query = f"{clean_message}\nTema ativo no mapa mental: {active_node}"

    try:
        vectorstore = _build_vectorstore(settings)
        docs_with_scores = vectorstore.similarity_search_with_score(retrieval_query, k=5)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("rag_retrieval_failed")
        raise AppError(
            code="rag_unavailable",
            message="Não consegui consultar a base de conhecimento agora. Tente novamente em instantes.",
            status_code=503,
        ) from exc

    context = _format_context(docs_with_scores) if docs_with_scores else ""
    if not context:
        context = "No relevant Markdown context was retrieved for this question."

    history = _get_store(settings).get(session_id)
    user_prompt = f"""
Retrieved Markdown context:
{context}

Active mind-map node: {active_node or "none"}

User question:
{clean_message}
""".strip()

    messages: List[BaseMessage] = [SystemMessage(content=load_system_prompt(settings)), *history, HumanMessage(content=user_prompt)]

    try:
        response = _build_llm(settings).invoke(messages)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("llm_call_failed")
        raise AppError(
            code="llm_unavailable",
            message="Não consegui gerar a resposta com a OpenAI agora. Verifique créditos, chave e limite de uso.",
            status_code=503,
        ) from exc

    answer = str(response.content).strip()
    _get_store(settings).append(session_id, clean_message, answer)

    return AgentResult(
        session_id=session_id,
        answer=answer,
        detected_language=_detect_language(clean_message),
        sources=_source_summaries(docs_with_scores),
        usage=_usage_from_response(response),
    )
