from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Tuple
from uuid import uuid4

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from config import Settings, get_settings
from pgvector_store import pgvector_similarity_search, pgvector_status, uses_pgvector
from rag_quality import rerank_candidate_payloads, save_rag_trace


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
class RagEvidence:
    source: str
    title: str
    category: str
    summary: str
    tags: List[str]
    priority: int
    excerpt: str
    channel: str
    distance: Optional[float]
    relevance_score: float
    match_reason: str


@dataclass
class AgentResult:
    session_id: str
    answer: str
    detected_language: str
    sources: List[SourceSummary]
    evidence: List[RagEvidence]
    usage: Dict[str, Any]
    trace_id: Optional[str] = None


@dataclass
class FitAnalysisResult:
    session_id: str
    answer: str
    summary: str
    fit_score: Optional[int]
    analysis: Dict[str, Any]
    sources: List[SourceSummary]
    evidence: List[RagEvidence]
    usage: Dict[str, Any]
    trace_id: Optional[str] = None


@dataclass
class PreparedAgentRun:
    session_id: str
    clean_message: str
    retrieval_query: str
    docs_with_scores: List[Tuple[Document, float]]
    evidence: List[RagEvidence]
    messages: List[BaseMessage]
    retrieval_ms: float
    total_start: float
    active_node: Optional[str] = None
    rag_trace: Optional[Dict[str, Any]] = None


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
_embeddings_cache: Dict[Tuple[str, str], OpenAIEmbeddings] = {}
_vectorstore_cache: Dict[Tuple[str, str, str, str], Chroma] = {}
_llm_cache: Dict[Tuple[str, str, float, str, str, bool], ChatOpenAI] = {}
_public_docs_cache: Dict[Tuple[str, int], List[Document]] = {}
_system_prompt_cache: Dict[str, Tuple[int, str]] = {}
_auto_reindex_lock = threading.Lock()


def sanitize_answer_text(text: str) -> str:
    return (text or "").replace("**", "").strip()


def _sanitize_stream_delta(text: str, state: Dict[str, bool]) -> str:
    output: List[str] = []
    for char in text or "":
        if state.get("pending_star"):
            if char == "*":
                state["pending_star"] = False
                continue
            output.append("*")
            output.append(char)
            state["pending_star"] = False
            continue
        if char == "*":
            state["pending_star"] = True
            continue
        output.append(char)
    return "".join(output)


def _flush_stream_sanitizer(state: Dict[str, bool]) -> str:
    if state.get("pending_star"):
        state["pending_star"] = False
        return "*"
    return ""


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
- Do not invent skills, frameworks, libraries, employers, credentials, dates, metrics, or project status.
- If asked for a list of skills, only list skills explicitly present in the retrieved context.
- When useful, connect skills to concrete projects and decisions.
- Keep answers concise by default, then offer to go deeper.
- Do not use Markdown bold or italic markers such as **.
""".strip()


def load_system_prompt(settings: Settings) -> str:
    try:
        prompt_path = settings.resolved_system_prompt_path
        cache_key = str(prompt_path)
        mtime = int(prompt_path.stat().st_mtime)
        cached = _system_prompt_cache.get(cache_key)
        if cached and cached[0] == mtime:
            return cached[1]
        prompt = prompt_path.read_text(encoding="utf-8").strip()
    except OSError:
        logger.warning("system_prompt_file_missing")
        return FALLBACK_SYSTEM_PROMPT
    resolved_prompt = prompt or FALLBACK_SYSTEM_PROMPT
    _system_prompt_cache[cache_key] = (mtime, resolved_prompt)
    return resolved_prompt


def clear_rag_caches() -> None:
    _vectorstore_cache.clear()
    _public_docs_cache.clear()
    _system_prompt_cache.clear()


def _response_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type") or "")
            if item_type == "reasoning":
                continue
            if isinstance(item.get("text"), str):
                parts.append(item["text"])
                continue
            nested = item.get("content")
            if isinstance(nested, (list, str)):
                nested_text = _response_content_to_text(nested)
                if nested_text:
                    parts.append(nested_text)
        return "\n".join(part.strip() for part in parts if part and part.strip()).strip()
    return str(content).strip()


def _response_content_to_delta(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type") or "")
            if item_type == "reasoning":
                continue
            if isinstance(item.get("text"), str):
                parts.append(item["text"])
                continue
            nested = item.get("content")
            if isinstance(nested, (list, str)):
                nested_text = _response_content_to_delta(nested)
                if nested_text:
                    parts.append(nested_text)
        return "".join(parts)
    return str(content)


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
    key = (settings.openai_embedding_model, settings.openai_api_key[-12:])
    if key not in _embeddings_cache:
        _embeddings_cache[key] = OpenAIEmbeddings(model=settings.openai_embedding_model, api_key=settings.openai_api_key)
    return _embeddings_cache[key]


def _ensure_vector_index(settings: Settings) -> None:
    chroma_dir = settings.resolved_chroma_dir
    if not chroma_dir.exists() or not any(chroma_dir.rglob("*")):
        raise AppError(
            code="rag_not_indexed",
            message="Minha base de conhecimento ainda não foi indexada neste deploy. Entre no admin e rode a reindexação RAG antes de usar o chat.",
            status_code=503,
        )


def _vector_index_exists(settings: Settings) -> bool:
    if uses_pgvector(settings):
        return bool(pgvector_status(settings).get("ready"))
    chroma_dir = settings.resolved_chroma_dir
    return chroma_dir.exists() and any(chroma_dir.rglob("*"))


def _ensure_vector_index_ready(settings: Settings) -> None:
    if _vector_index_exists(settings):
        return
    if uses_pgvector(settings):
        status = pgvector_status(settings)
        raise AppError(
            code="rag_not_indexed",
            message=(
                "Minha base vetorial persistente ainda não está pronta. "
                "Entre no admin e rode a reindexação RAG antes de usar o chat."
            ),
            status_code=503 if not status.get("error") else 500,
        )
    if not settings.rag_auto_reindex_on_missing:
        _ensure_vector_index(settings)

    if not _auto_reindex_lock.acquire(blocking=False):
        deadline = time.perf_counter() + max(settings.rag_auto_reindex_wait_seconds, 1)
        while time.perf_counter() < deadline:
            if _vector_index_exists(settings):
                clear_rag_caches()
                return
            time.sleep(0.5)
        raise AppError(
            code="rag_reindex_in_progress",
            message="Estou reconstruindo minha base de conhecimento agora. Tente novamente em alguns segundos.",
            status_code=503,
        )

    try:
        logger.info("rag_auto_reindex_start")
        from ingest import ingest

        ingest(settings)
        if not _vector_index_exists(settings):
            _ensure_vector_index(settings)
        logger.info("rag_auto_reindex_success")
    except AppError:
        raise
    except Exception as exc:
        logger.exception("rag_auto_reindex_failed")
        raise AppError(
            code="rag_auto_reindex_failed",
            message="Não consegui reconstruir a base de conhecimento automaticamente. Tente reindexar pelo admin.",
            status_code=503,
        ) from exc
    finally:
        _auto_reindex_lock.release()


def _build_vectorstore(settings: Settings) -> Chroma:
    _ensure_vector_index_ready(settings)
    key = (
        settings.chroma_collection,
        str(settings.resolved_chroma_dir),
        settings.openai_embedding_model,
        settings.openai_api_key[-12:],
    )
    if key not in _vectorstore_cache:
        _vectorstore_cache[key] = Chroma(
            collection_name=settings.chroma_collection,
            persist_directory=str(settings.resolved_chroma_dir),
            embedding_function=_build_embeddings(settings),
        )
    return _vectorstore_cache[key]


def _build_llm(settings: Settings, model: Optional[str] = None) -> ChatOpenAI:
    _require_openai_key(settings)
    model = model or settings.openai_chat_model
    key = (
        model,
        settings.openai_api_key[-12:],
        settings.openai_temperature,
        settings.openai_reasoning_effort,
        settings.openai_text_verbosity,
        settings.openai_use_responses_api,
    )
    if key not in _llm_cache:
        model_name = model.lower()
        supports_reasoning_effort = model_name.startswith("gpt-5") or model_name.startswith(("o1", "o3", "o4"))
        supports_verbosity = model_name.startswith("gpt-5")
        reasoning_effort = settings.openai_reasoning_effort if supports_reasoning_effort else None
        verbosity = settings.openai_text_verbosity if supports_verbosity else None
        use_responses_api = bool(settings.openai_use_responses_api and (supports_reasoning_effort or supports_verbosity))
        _llm_cache[key] = ChatOpenAI(
            model=model,
            temperature=settings.openai_temperature,
            api_key=settings.openai_api_key,
            reasoning_effort=reasoning_effort,
            verbosity=verbosity,
            use_responses_api=use_responses_api,
        )
    return _llm_cache[key]


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


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[\wÀ-ÿ+#.-]{3,}", text.lower())}


def _is_skill_question(text: str, active_node: Optional[str]) -> bool:
    normalized = text.lower()
    markers = ("skill", "stack", "stak", "competência", "competencias", "habilidade", "hard skill", "soft skill", "tecnologia")
    return active_node == "stack" or any(marker in normalized for marker in markers)


SKILL_FOCUS_TERMS = {"skill", "skills", "stack", "stak", "hard", "soft", "competenc", "tecnico", "técnico"}


def _mentioned_project_terms(text: str) -> set[str]:
    normalized = text.lower()
    terms: set[str] = set()
    specific_project = False
    if any(marker in normalized for marker in ("dge", "data growth", "galpao", "galpão")):
        terms.update({"projetos/dge", "dge", "data-growth", "galpao", "galpão"})
        specific_project = True
    if any(marker in normalized for marker in ("ebook", "e-book", "generator", "gerador")):
        terms.update({"projetos/ebookgenerator", "ebook", "ebook-generator", "ebookgenerator", "generator"})
        specific_project = True
    if "autobot" in normalized:
        terms.update({"projetos/autobot", "autobot"})
        specific_project = True
    if any(marker in normalized for marker in ("vetdex", "vdc", "diagnosia", "diagnósia", "veterin")):
        terms.update({"projetos/veterinaria", "veterinaria", "veterinária", "vetdex", "vdc", "diagnosia", "diagnósia"})
        specific_project = True
    if not specific_project and any(marker in normalized for marker in ("projeto", "projetos", "outros projetos")):
        terms.update({"projetos", "autobot", "dge", "ebook", "veterinaria", "veterinária"})
    return terms


def _explicit_focus_terms(text: str) -> set[str]:
    normalized = text.lower()
    terms = set()
    terms.update(_mentioned_project_terms(text))
    if any(marker in normalized for marker in ("trajet", "formação", "formacao", "idioma", "língua", "lingua")):
        terms.update(_node_terms("trajetoria"))
    if any(marker in normalized for marker in ("experiência", "experiencia", "trabalho", "profissional", "desafio")):
        terms.update(_node_terms("experiencia"))
    if any(marker in normalized for marker in ("mercado", "dados", "automação", "automacao", "ia", "sistema")):
        terms.update(_node_terms("mercado"))
    if any(marker in normalized for marker in ("entrevista", "faq", "pergunta técnica", "pergunta tecnica")):
        terms.update(_node_terms("entrevista"))
    if any(marker in normalized for marker in ("currículo", "curriculo", "material", "recrutador")):
        terms.update(_node_terms("materiais"))
    if any(marker in normalized for marker in ("stack", "stak", "skill", "competência", "competencia", "habilidade", "tecnologia")):
        terms.update(SKILL_FOCUS_TERMS)
    return terms


def _expand_retrieval_query(text: str, active_node: Optional[str]) -> str:
    additions = set()
    if _is_skill_question(text, active_node):
        additions.update({"stack", "skills", "tecnologias", "ferramentas", "competências técnicas"})
    additions.update(_mentioned_project_terms(text))
    additions.update(_explicit_focus_terms(text))
    if not additions:
        return text
    return f"{text}\nTermos de busca derivados: {', '.join(sorted(additions))}"


def _query_subqueries(text: str, active_node: Optional[str]) -> List[str]:
    chunks = [text.strip()]
    for marker in (" e ", " ou ", ",", ";", "\n"):
        next_chunks: List[str] = []
        for chunk in chunks:
            parts = [part.strip() for part in chunk.split(marker) if part.strip()]
            next_chunks.extend(parts if len(parts) > 1 else [chunk])
        chunks = next_chunks
    focus = sorted(_explicit_focus_terms(text) | _node_terms(active_node))
    subqueries: List[str] = []
    for chunk in chunks:
        if len(chunk) >= 4:
            subqueries.append(chunk[:240])
    if focus:
        subqueries.append("foco: " + ", ".join(focus[:12]))
    seen: set[str] = set()
    unique = []
    for item in subqueries:
        normalized = item.lower()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(item)
    return unique[:8]


def _node_terms(active_node: Optional[str]) -> set[str]:
    mapping = {
        "gabriel": {"gabriel", "perfil", "personalidade", "valores"},
        "trajetoria": {"trajetoria", "trajetória", "formacao", "formação", "idiomas"},
        "projetos": {"projetos", "autobot", "dge", "ebook", "veterinaria", "veterinária", "vetdex", "vdc"},
        "stack": {"skills", "stack", "hard", "soft", "tecnico", "técnico", "python", "sql"},
        "experiencia": {"experiencia", "experiência", "profissional", "desafios"},
        "mercado": {"mercado", "dados", "ia", "automacao", "automação", "sistemas"},
        "entrevista": {"entrevista", "faq", "perguntas", "casos"},
        "materiais": {"materiais", "curriculo", "currículo", "recrutador"},
    }
    return mapping.get(active_node or "", set())


def _doc_matches_focus(doc: Document, active_node: Optional[str], skill_question: bool, query: str = "") -> bool:
    metadata = doc.metadata or {}
    source = str(metadata.get("source", "")).lower()
    category = str(metadata.get("category", "")).lower()
    tags = str(metadata.get("tags", "")).lower()
    haystack = f"{source} {category} {tags}"
    project_terms = _mentioned_project_terms(query)
    if skill_question:
        if project_terms:
            return any(term in haystack for term in SKILL_FOCUS_TERMS | project_terms)
        return any(term in haystack for term in SKILL_FOCUS_TERMS)
    explicit_terms = _explicit_focus_terms(query)
    terms = explicit_terms or _node_terms(active_node)
    if not terms:
        return True
    return any(term in haystack for term in terms)


def _metadata_key(doc: Document) -> str:
    metadata = doc.metadata or {}
    source = str(metadata.get("source") or metadata.get("title") or "document")
    return f"{source}:{hash(doc.page_content[:500])}"


def _metadata_text(doc: Document) -> str:
    metadata = doc.metadata or {}
    return " ".join(str(value) for value in metadata.values())


def _coerce_tags(tags: Any) -> List[str]:
    if isinstance(tags, list):
        return [str(tag).strip() for tag in tags if str(tag).strip()]
    if isinstance(tags, str):
        cleaned = tags.strip().strip("[]")
        return [tag.strip().strip("'\"") for tag in cleaned.split(",") if tag.strip().strip("'\"")]
    return []


def _document_relevance(
    doc: Document,
    query: str,
    active_node: Optional[str],
    *,
    vector_score: Optional[float] = None,
    channel: str = "lexical",
) -> float:
    query_terms = _tokens(query) | _explicit_focus_terms(query)
    metadata_terms = _tokens(_metadata_text(doc))
    content_terms = _tokens(doc.page_content)
    source = str((doc.metadata or {}).get("source", "")).lower()
    category = str((doc.metadata or {}).get("category", "")).lower()
    tags = str((doc.metadata or {}).get("tags", "")).lower()
    haystack = f"{source} {category} {tags}"

    explicit_terms = _explicit_focus_terms(query)
    haystack_terms = _tokens(haystack)
    metadata_overlap = len(query_terms & metadata_terms)
    content_overlap = len(query_terms & content_terms)
    explicit_metadata_overlap = len(explicit_terms & haystack_terms)
    explicit_content_overlap = len(explicit_terms & content_terms)
    active_overlap = len(_node_terms(active_node) & metadata_terms)
    priority = int((doc.metadata or {}).get("priority", 3) or 3)

    score = metadata_overlap * 3.0 + content_overlap * 0.45
    score += explicit_metadata_overlap * 8.0 + explicit_content_overlap * 1.5
    score += max(0, 4 - priority) * 0.4
    score += min(active_overlap, 3) * 0.4
    if _mentioned_project_terms(query) and source.startswith("projetos/"):
        score += 4.0
    if channel == "vector" and vector_score is not None:
        score += max(0.0, settings_like_vector_ceiling(vector_score)) * 1.5
    if source.startswith("reports/"):
        score -= 100
    return score


def _excerpt_for_query(text: str, query: str, max_chars: int = 420) -> str:
    clean_text = " ".join((text or "").split())
    if len(clean_text) <= max_chars:
        return clean_text
    query_terms = [term for term in _tokens(query) if len(term) >= 4]
    lower_text = clean_text.lower()
    hit = -1
    for term in query_terms:
        hit = lower_text.find(term.lower())
        if hit >= 0:
            break
    if hit < 0:
        return clean_text[: max_chars - 1].rstrip() + "..."
    start = max(0, hit - max_chars // 3)
    end = min(len(clean_text), start + max_chars)
    if end - start < max_chars:
        start = max(0, end - max_chars)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(clean_text) else ""
    return f"{prefix}{clean_text[start:end].strip()}{suffix}"


def _match_reason(doc: Document, query: str, active_node: Optional[str], channel: str, relevance: float) -> str:
    metadata = doc.metadata or {}
    priority = int(metadata.get("priority", 3) or 3)
    metadata_terms = _tokens(_metadata_text(doc))
    content_terms = _tokens(doc.page_content)
    query_terms = _tokens(query) | _explicit_focus_terms(query)
    overlaps = sorted((query_terms & metadata_terms) | (query_terms & content_terms))
    focus_terms = sorted((_explicit_focus_terms(query) or _node_terms(active_node)) & metadata_terms)
    parts = [f"canal {channel}", f"prioridade {priority}", f"score {round(relevance, 2)}"]
    if overlaps:
        parts.append("termos: " + ", ".join(overlaps[:5]))
    if focus_terms:
        parts.append("foco: " + ", ".join(focus_terms[:4]))
    return "; ".join(parts)


def _evidence_from_doc(doc: Document, score: float, query: str, active_node: Optional[str]) -> RagEvidence:
    metadata = doc.metadata or {}
    channel = str(metadata.get("_retrieval_channel") or "unknown")
    distance = metadata.get("_retrieval_distance")
    relevance = float(metadata.get("_retrieval_relevance_score") or _document_relevance(doc, query, active_node))
    return RagEvidence(
        source=str(metadata.get("source", "")),
        title=str(metadata.get("title", "Documento sem título")),
        category=str(metadata.get("category", "geral")),
        summary=str(metadata.get("summary", "Fonte usada pelo agente.")),
        tags=_coerce_tags(metadata.get("tags", [])),
        priority=int(metadata.get("priority", 3) or 3),
        excerpt=_excerpt_for_query(doc.page_content, query),
        channel=channel,
        distance=float(distance) if distance is not None else (float(score) if channel == "vector" else None),
        relevance_score=round(relevance, 4),
        match_reason=str(metadata.get("_retrieval_match_reason") or _match_reason(doc, query, active_node, channel, relevance)),
    )


def _evidence_from_docs(docs_with_scores: List[Tuple[Document, float]], query: str, active_node: Optional[str]) -> List[RagEvidence]:
    evidence: List[RagEvidence] = []
    seen: set[str] = set()
    for doc, score in docs_with_scores:
        item = _evidence_from_doc(doc, score, query, active_node)
        key = f"{item.source}:{item.excerpt[:80]}"
        if key in seen:
            continue
        seen.add(key)
        evidence.append(item)
    return evidence


def settings_like_vector_ceiling(vector_score: float) -> float:
    return 1.8 - min(vector_score, 1.8)


def _cached_public_documents(settings: Settings) -> List[Document]:
    from ingest import load_public_documents

    knowledge_dir = settings.resolved_knowledge_dir
    latest_mtime = 0
    if knowledge_dir.exists():
        latest_mtime = max((int(path.stat().st_mtime) for path in knowledge_dir.rglob("*.md")), default=0)
    key = (str(knowledge_dir), latest_mtime)
    if key not in _public_docs_cache:
        _public_docs_cache.clear()
        _public_docs_cache[key] = load_public_documents(settings)
    return _public_docs_cache[key]


def _lexical_matches(settings: Settings, query: str, active_node: Optional[str], limit: int) -> List[Tuple[Document, float]]:
    query_terms = _tokens(query) | _explicit_focus_terms(query)
    if not query_terms or limit <= 0:
        return []
    scored: List[Tuple[Document, float]] = []
    for doc in _cached_public_documents(settings):
        doc_terms = _tokens(f"{_metadata_text(doc)}\n{doc.page_content}")
        if not query_terms & doc_terms:
            continue
        relevance = _document_relevance(doc, query, active_node, channel="lexical")
        if relevance > 0:
            scored.append((doc, -relevance))
    scored.sort(key=lambda item: item[1])
    return scored[:limit]


def _candidate_payload(
    key: str,
    doc: Document,
    *,
    channel: str,
    distance: Optional[float],
    relevance: float,
    query: str,
    active_node: Optional[str],
) -> Dict[str, Any]:
    metadata = doc.metadata or {}
    reason = _match_reason(doc, query, active_node, channel, relevance)
    return {
        "id": key,
        "source": str(metadata.get("source", "")),
        "title": str(metadata.get("title", "Documento sem tÃ­tulo")),
        "category": str(metadata.get("category", "geral")),
        "summary": str(metadata.get("summary", "")),
        "tags": _coerce_tags(metadata.get("tags", [])),
        "priority": int(metadata.get("priority", 3) or 3),
        "channel": channel,
        "distance": float(distance) if distance is not None else None,
        "base_relevance": round(float(relevance), 4),
        "match_reason": reason,
        "excerpt": _excerpt_for_query(doc.page_content, query, max_chars=260),
    }


def _retrieve_documents_with_trace(
    settings: Settings,
    retrieval_query: str,
    active_node: Optional[str],
) -> Tuple[List[Tuple[Document, float]], Dict[str, Any]]:
    compat_retriever = globals().get("_retrieve_documents")
    if compat_retriever is not None and not getattr(compat_retriever, "_traced_wrapper", False):
        selected = compat_retriever(settings, retrieval_query, active_node)
        evidence_candidates = [
            _candidate_payload(
                _metadata_key(doc),
                doc,
                channel=str((doc.metadata or {}).get("_retrieval_channel") or "test"),
                distance=(doc.metadata or {}).get("_retrieval_distance", score),
                relevance=float((doc.metadata or {}).get("_retrieval_relevance_score") or _document_relevance(doc, retrieval_query, active_node)),
                query=retrieval_query,
                active_node=active_node,
            )
            for doc, score in selected
        ]
        reranked = rerank_candidate_payloads(settings, evidence_candidates)
        selected_ids = {_metadata_key(doc) for doc, _score in selected}
        return selected, {
            "subqueries": _query_subqueries(retrieval_query, active_node),
            "vector_limit": 0,
            "lexical_limit": 0,
            "candidate_count": len(evidence_candidates),
            "selected_count": len(selected),
            "candidates_before_rerank": evidence_candidates,
            "candidates_after_rerank": [
                {**candidate, "selected": str(candidate.get("id")) in selected_ids}
                for candidate in reranked
            ],
            "rerank": {"enabled": settings.rag_rerank_enabled, "provider": settings.rag_rerank_provider},
        }

    vector_limit = max(settings.rag_k * 4, 24)
    lexical_limit = max(settings.rag_lexical_k, settings.rag_k * 3, 12)
    if uses_pgvector(settings):
        _ensure_vector_index_ready(settings)
        docs_with_scores = pgvector_similarity_search(settings, retrieval_query, vector_limit, assume_ready=True)
    else:
        vectorstore = _build_vectorstore(settings)
        docs_with_scores = vectorstore.similarity_search_with_score(retrieval_query, k=vector_limit)
    candidates: List[Tuple[Document, float, str, float]] = []
    channels_by_key: Dict[str, set[str]] = {}
    best_distance_by_key: Dict[str, float] = {}
    best_relevance_by_key: Dict[str, float] = {}

    def remember_candidate(doc: Document, score: float, channel: str, relevance: float) -> None:
        key = _metadata_key(doc)
        channels_by_key.setdefault(key, set()).add(channel)
        if channel == "vector":
            best_distance_by_key[key] = min(score, best_distance_by_key.get(key, score))
        best_relevance_by_key[key] = max(relevance, best_relevance_by_key.get(key, relevance))
        candidates.append((doc, score, channel, relevance))

    for doc, score in docs_with_scores:
        relevance = _document_relevance(doc, retrieval_query, active_node, vector_score=score, channel="vector")
        if score <= settings.rag_max_distance or relevance > 0:
            remember_candidate(doc, score, "vector", relevance)

    for doc, score in _lexical_matches(settings, retrieval_query, active_node, lexical_limit):
        remember_candidate(doc, score, "lexical", -score)

    doc_by_key: Dict[str, Tuple[Document, float, float]] = {}
    for doc, score, _channel, relevance in candidates:
        key = _metadata_key(doc)
        previous = doc_by_key.get(key)
        if previous is None or relevance > previous[2]:
            doc_by_key[key] = (doc, score, relevance)

    merged_candidates: List[Dict[str, Any]] = []
    for key, (doc, score, relevance) in doc_by_key.items():
        channel_set = channels_by_key.get(key, set())
        channel = "hybrid" if len(channel_set) > 1 else next(iter(channel_set or {"unknown"}))
        merged_candidates.append(
            _candidate_payload(
                key,
                doc,
                channel=channel,
                distance=best_distance_by_key.get(key),
                relevance=best_relevance_by_key.get(key, relevance),
                query=retrieval_query,
                active_node=active_node,
            )
        )

    candidates_before = sorted(merged_candidates, key=lambda item: (-float(item.get("base_relevance") or 0), str(item.get("source") or "")))
    candidates_after = rerank_candidate_payloads(settings, candidates_before)

    selected: List[Tuple[Document, float]] = []
    seen: set[str] = set()
    source_counts: Dict[str, int] = {}
    for candidate in candidates_after:
        relevance = float(candidate.get("rerank_score") or candidate.get("base_relevance") or 0)
        if relevance <= 0:
            continue
        key = str(candidate.get("id") or "")
        if key in seen:
            continue
        doc_tuple = doc_by_key.get(key)
        if not doc_tuple:
            continue
        doc, score, base_relevance = doc_tuple
        source = str((doc.metadata or {}).get("source", key))
        if source_counts.get(source, 0) >= 2:
            continue
        seen.add(key)
        source_counts[source] = source_counts.get(source, 0) + 1
        channel = str(candidate.get("channel") or "unknown")
        evidence_doc = Document(
            page_content=doc.page_content,
            metadata={
                **(doc.metadata or {}),
                "_retrieval_channel": channel,
                "_retrieval_distance": candidate.get("distance"),
                "_retrieval_relevance_score": relevance,
                "_retrieval_base_relevance_score": base_relevance,
                "_retrieval_rerank_score": relevance,
                "_retrieval_match_reason": candidate.get("match_reason")
                or _match_reason(doc, retrieval_query, active_node, channel, relevance),
            },
        )
        selected.append((evidence_doc, score))
        if len(selected) >= max(settings.rag_k, 1):
            break
    selected_ids = {_metadata_key(doc) for doc, _score in selected}
    trace = {
        "subqueries": _query_subqueries(retrieval_query, active_node),
        "vector_limit": vector_limit,
        "lexical_limit": lexical_limit,
        "candidate_count": len(candidates_before),
        "selected_count": len(selected),
        "candidates_before_rerank": candidates_before[:32],
        "candidates_after_rerank": [
            {**candidate, "selected": str(candidate.get("id")) in selected_ids}
            for candidate in candidates_after[:32]
        ],
        "rerank": {
            "enabled": settings.rag_rerank_enabled,
            "provider": settings.rag_rerank_provider,
        },
    }
    return selected, trace


def _retrieve_documents(settings: Settings, retrieval_query: str, active_node: Optional[str]) -> List[Tuple[Document, float]]:
    selected, _trace = _retrieve_documents_with_trace(settings, retrieval_query, active_node)
    return selected


_retrieve_documents._traced_wrapper = True  # type: ignore[attr-defined]


def build_rag_probe(settings: Settings, question: str, active_context: Optional[str] = None, *, limit: Optional[int] = None) -> Dict[str, Any]:
    clean_question = question.strip()
    if not clean_question:
        raise AppError("empty_rag_probe", "Informe uma pergunta para testar o RAG.", 400)
    start = time.perf_counter()
    retrieval_query = _expand_retrieval_query(clean_question, active_context)
    docs_with_scores, trace = _retrieve_documents_with_trace(settings, retrieval_query, active_context)
    took_ms = round((time.perf_counter() - start) * 1000, 2)
    evidence = _evidence_from_docs(docs_with_scores, retrieval_query, active_context)
    if limit is not None and limit > 0:
        evidence = evidence[: min(max(int(limit), 1), 20)]
    return {
        "question": clean_question,
        "active_context": active_context,
        "retrieval_query": retrieval_query,
        "subqueries": trace.get("subqueries", []),
        "documents": len(docs_with_scores),
        "took_ms": took_ms,
        "candidate_count": trace.get("candidate_count", 0),
        "rerank": trace.get("rerank", {}),
        "candidates_before_rerank": trace.get("candidates_before_rerank", []),
        "candidates_after_rerank": trace.get("candidates_after_rerank", []),
        "evidence": [item.__dict__ for item in evidence],
    }


def warm_rag(settings: Optional[Settings] = None) -> Dict[str, Any]:
    settings = settings or get_settings()
    load_system_prompt(settings)
    _build_embeddings(settings)
    docs = _cached_public_documents(settings)
    if uses_pgvector(settings):
        status = pgvector_status(settings)
        return {"documents": len(docs), "vector": status}
    ready = _vector_index_exists(settings)
    if ready:
        _build_vectorstore(settings)
    return {"documents": len(docs), "vector": {"backend": "chroma", "ready": ready, "chunks": None, "error": None}}


def _format_context(docs_with_scores, max_chars: int) -> str:
    blocks = []
    total_chars = 0
    for doc, score in docs_with_scores:
        metadata = doc.metadata or {}
        title = metadata.get("title", "Documento sem título")
        category = metadata.get("category", "geral")
        summary = metadata.get("summary", "")
        source = metadata.get("source", "")
        block = "\n".join(
            [
                f"[title: {title}]",
                f"[category: {category}]",
                f"[summary: {summary}]",
                f"[source: {source}]",
                f"[score: {score}]",
                doc.page_content,
            ]
        )
        if total_chars and total_chars + len(block) > max_chars:
            break
        blocks.append(block)
        total_chars += len(block)
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
        tags = _coerce_tags(metadata.get("tags", []))
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


def realtime_search_knowledge(
    settings: Settings,
    query: str,
    active_context: Optional[str] = None,
) -> Dict[str, Any]:
    clean_query = (query or "").strip()
    if not clean_query:
        raise AppError("empty_realtime_query", "A busca em tempo real recebeu uma consulta vazia.", 400)
    retrieval_query = _expand_retrieval_query(clean_query, active_context)
    docs_with_scores = _retrieve_documents(settings, retrieval_query, active_context)
    if len(docs_with_scores) < settings.rag_min_docs:
        return {
            "status": "weak_context",
            "message": "Nao encontrei contexto documentado suficiente para responder com seguranca.",
            "context": "",
            "sources": [],
        }
    return {
        "status": "ok",
        "context": _format_context(docs_with_scores, settings.realtime_max_context_chars),
        "sources": [source.__dict__ for source in _source_summaries(docs_with_scores)],
        "evidence": [item.__dict__ for item in _evidence_from_docs(docs_with_scores, retrieval_query, active_context)],
        "retrieved_docs": len(docs_with_scores),
    }


def realtime_dossier_context(settings: Settings, section: Optional[str] = None) -> Dict[str, Any]:
    allowed = {"gabriel", "trajetoria", "projetos", "stack", "experiencia", "mercado", "entrevista", "materiais"}
    selected = (section or "gabriel").strip().lower()
    if selected not in allowed:
        selected = "gabriel"
    report_path = settings.resolved_knowledge_dir / "reports" / f"{selected}.md"
    if not report_path.exists():
        return {
            "status": "missing",
            "section": selected,
            "content": "Relatorio estatico nao encontrado para esta secao.",
        }
    return {
        "status": "ok",
        "section": selected,
        "content": report_path.read_text(encoding="utf-8")[: settings.realtime_max_context_chars],
    }


def _usage_from_response(response: AIMessage) -> Dict[str, Any]:
    usage = getattr(response, "usage_metadata", None) or {}
    return {
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
    }


def _stage(stage_id: str, label: str, status: str = "active", **extra: Any) -> Dict[str, Any]:
    payload = {"id": stage_id, "label": label, "status": status}
    payload.update({key: value for key, value in extra.items() if value is not None})
    return {"event": "stage", "data": payload}


def _build_user_prompt(context: str, active_node: Optional[str], clean_message: str) -> str:
    return f"""
Retrieved Markdown context:
{context}

Active mind-map node: {active_node or "none"}

Grounding guardrails:
- Use only the retrieved Markdown context above as factual basis.
- If the context does not explicitly mention a tool, skill, date, employer, metric, or credential, do not mention it as mine.
- For skill lists, list only technologies explicitly present in the context.
- If context is insufficient, say that this is not documented yet.

User question:
{clean_message}
""".strip()


FIT_SYSTEM_PROMPT = """
You are Gabriel's Interview OS for recruiters.

Goal:
- Analyze the pasted job description against Gabriel's documented knowledge base.
- Help the recruiter understand fit quickly, honestly, and with evidence.

Rules:
- Answer in Portuguese unless the job description is clearly in English.
- Speak about Gabriel in first person when describing fit, as if Gabriel is explaining himself.
- Use only the retrieved Markdown context as factual basis about Gabriel.
- Do not invent skills, years of experience, employers, certifications, tools, metrics, or project facts.
- If a requirement is not documented, mark it as a gap or "não documentado".
- Do not use Markdown bold or italic markers.
- Keep the analysis structured and practical.

Output format:
Fit estimado: NN/100

Resumo executivo:
One short paragraph.

Aderências fortes:
- Bullet list.

Lacunas honestas:
- Bullet list.

Projetos que provam fit:
- Bullet list connecting requirements to documented projects.

Perguntas sugeridas:
- Bullet list of useful interview questions.

Resumo copiável:
One compact paragraph a recruiter could share internally.
""".strip()


def _job_fit_query(job_title: str, company: str, job_description: str) -> str:
    return "\n".join(
        part
        for part in [
            f"Vaga: {job_title.strip()}" if job_title.strip() else "",
            f"Empresa: {company.strip()}" if company.strip() else "",
            job_description.strip(),
            "Termos de busca derivados: stack, hard skills, projetos, experiência, IA, dados, automação, backend, produto, limitações técnicas, lacunas, fit de vaga",
        ]
        if part
    )


def _build_fit_prompt(context: str, job_title: str, company: str, job_description: str) -> str:
    trimmed_description = job_description.strip()[:18000]
    return f"""
Retrieved Markdown context about Gabriel:
{context}

Job title:
{job_title or "não informado"}

Company:
{company or "não informada"}

Job description:
{trimmed_description}

Analysis instructions:
- Cross the job requirements against the retrieved context.
- Separate what is strongly documented from what is weak, missing, or not documented.
- Mention concrete projects only when present in the context.
- For the fit score, estimate from 0 to 100 based only on documented evidence.
""".strip()


def _save_trace_for_answer(
    settings: Settings,
    *,
    session_id: str,
    question: str,
    answer: str,
    active_node: Optional[str],
    retrieval_query: str,
    docs_with_scores: List[Tuple[Document, float]],
    rag_trace: Optional[Dict[str, Any]],
    usage: Dict[str, Any],
    model: str,
) -> Optional[str]:
    trace = rag_trace or {}
    selected_sources = [
        str((doc.metadata or {}).get("source", ""))
        for doc, _score in docs_with_scores
        if (doc.metadata or {}).get("source")
    ]
    payload = {
        "session_id": session_id,
        "active_context": active_node,
        "question": question,
        "answer": answer,
        "retrieval_query": retrieval_query,
        "subqueries": trace.get("subqueries") or _query_subqueries(retrieval_query, active_node),
        "candidates": trace.get("candidates_after_rerank") or [],
        "selected_sources": selected_sources,
        "rerank": trace.get("rerank") or {},
        "metrics": {
            **(usage or {}),
            "candidate_count": trace.get("candidate_count"),
            "selected_count": len(selected_sources),
        },
        "model": model,
    }
    try:
        return save_rag_trace(settings, payload)
    except Exception:
        logger.exception("rag_trace_save_failed")
        return None


def _extract_fit_score(answer: str) -> Optional[int]:
    match = re.search(r"fit\s+estimado\s*:\s*(\d{1,3})\s*/\s*100", answer, flags=re.IGNORECASE)
    if not match:
        return None
    return max(0, min(100, int(match.group(1))))


def _extract_section(answer: str, title: str) -> str:
    pattern = re.compile(
        rf"{re.escape(title)}\s*:\s*(.*?)(?=\n[A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n:]+:\s*|\Z)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(answer)
    return match.group(1).strip() if match else ""


def _first_paragraph(text: str) -> str:
    for block in re.split(r"\n\s*\n", text.strip()):
        clean = block.strip()
        if clean:
            return clean[:1200]
    return ""


def _fit_analysis_map(answer: str) -> Dict[str, Any]:
    return {
        "fit_score": _extract_fit_score(answer),
        "executive_summary": _first_paragraph(_extract_section(answer, "Resumo executivo")),
        "strong_matches": _extract_section(answer, "Aderências fortes"),
        "honest_gaps": _extract_section(answer, "Lacunas honestas"),
        "proof_projects": _extract_section(answer, "Projetos que provam fit"),
        "suggested_questions": _extract_section(answer, "Perguntas sugeridas"),
        "shareable_summary": _first_paragraph(_extract_section(answer, "Resumo copiável")),
    }


def stream_fit_analysis(
    *,
    job_title: str,
    company: str,
    job_description: str,
    session_id: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> Iterator[Dict[str, Any]]:
    settings = settings or get_settings()
    total_start = time.perf_counter()
    session_id = session_id or str(uuid4())
    clean_description = job_description.strip()
    if len(clean_description) < 80:
        raise AppError("job_description_too_short", "Cole uma descrição de vaga mais completa para eu analisar o fit.", 400)

    yield _stage("received", "Vaga recebida", "complete", elapsed_ms=0)

    yield _stage("retrieving_context", "Cruzando vaga com a base", "active")
    retrieval_start = time.perf_counter()
    retrieval_query = _job_fit_query(job_title, company, clean_description)
    try:
        docs_with_scores, rag_trace = _retrieve_documents_with_trace(settings, retrieval_query, None)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("fit_rag_retrieval_failed")
        raise AppError(
            code="rag_unavailable",
            message="Não consegui consultar a base de conhecimento agora. Tente novamente em instantes.",
            status_code=503,
        ) from exc
    retrieval_ms = round((time.perf_counter() - retrieval_start) * 1000, 2)
    yield _stage("retrieving_context", "Cruzando vaga com a base", "complete", elapsed_ms=retrieval_ms, docs=len(docs_with_scores))

    if len(docs_with_scores) < settings.rag_min_docs:
        raise AppError(
            code="rag_weak_context",
            message="Não encontrei contexto suficiente nos Markdown para analisar essa vaga com segurança.",
            status_code=422,
        )

    yield _stage("selecting_evidence", "Selecionando evidências", "active")
    evidence_start = time.perf_counter()
    context = _format_context(docs_with_scores, settings.rag_max_context_chars)
    prompt = _build_fit_prompt(context, job_title.strip(), company.strip(), clean_description)
    messages: List[BaseMessage] = [
        SystemMessage(content=f"{load_system_prompt(settings)}\n\n{FIT_SYSTEM_PROMPT}"),
        HumanMessage(content=prompt),
    ]
    yield _stage("selecting_evidence", "Selecionando evidências", "complete", elapsed_ms=round((time.perf_counter() - evidence_start) * 1000, 2))

    yield _stage("generating_answer", "Gerando análise de fit", "active", model=settings.openai_chat_model)
    llm_start = time.perf_counter()
    first_token_ms: Optional[float] = None
    answer = ""
    raw_stream_text = ""
    sanitizer_state: Dict[str, bool] = {"pending_star": False}
    usage: Dict[str, Any] = {}
    model_used = settings.openai_chat_model
    fallback_used = False

    try:
        for chunk in _build_llm(settings, model_used).stream(messages):
            chunk_usage = getattr(chunk, "usage_metadata", None) or {}
            if chunk_usage:
                usage = {
                    "input_tokens": int(chunk_usage.get("input_tokens", 0) or 0),
                    "output_tokens": int(chunk_usage.get("output_tokens", 0) or 0),
                    "total_tokens": int(chunk_usage.get("total_tokens", 0) or 0),
                }
            chunk_text = _response_content_to_delta(getattr(chunk, "content", ""))
            if not chunk_text:
                continue
            if raw_stream_text and len(raw_stream_text) >= 12 and chunk_text.startswith(raw_stream_text):
                delta = chunk_text[len(raw_stream_text) :]
                raw_stream_text = chunk_text
            else:
                delta = chunk_text
                raw_stream_text += chunk_text
            delta = _sanitize_stream_delta(delta, sanitizer_state)
            if not delta:
                continue
            if first_token_ms is None:
                first_token_ms = round((time.perf_counter() - llm_start) * 1000, 2)
            answer += delta
            yield {"event": "delta", "data": {"text": delta}}
    except Exception as exc:
        logger.exception("fit_llm_stream_failed")
        if answer or not settings.openai_fast_chat_model or settings.openai_fast_chat_model == settings.openai_chat_model:
            raise AppError(
                code="llm_unavailable",
                message="Não consegui gerar a análise com a OpenAI agora. Verifique créditos, chave e limite de uso.",
                status_code=503,
            ) from exc
        fallback_used = True
        model_used = settings.openai_fast_chat_model
        yield _stage("generating_answer", "Gerando análise de fit", "active", detail="Usando modelo rápido de fallback", model=model_used)
        try:
            response = _build_llm(settings, model_used).invoke(messages)
        except Exception as fallback_exc:
            logger.exception("fit_llm_fallback_failed")
            raise AppError(
                code="llm_unavailable",
                message="Não consegui gerar a análise com a OpenAI agora. Verifique créditos, chave e limite de uso.",
                status_code=503,
            ) from fallback_exc
        answer = sanitize_answer_text(_response_content_to_text(response.content))
        usage = _usage_from_response(response)
        if answer:
            first_token_ms = first_token_ms or round((time.perf_counter() - llm_start) * 1000, 2)
            yield {"event": "delta", "data": {"text": answer}}

    tail = _flush_stream_sanitizer(sanitizer_state)
    if tail:
        answer += tail
        yield {"event": "delta", "data": {"text": tail}}

    llm_ms = round((time.perf_counter() - llm_start) * 1000, 2)
    yield _stage("generating_answer", "Gerando análise de fit", "complete", elapsed_ms=llm_ms, model=model_used)

    answer = sanitize_answer_text(answer)
    if not answer:
        raise AppError("empty_llm_response", "A OpenAI retornou uma análise vazia. Tente novamente em instantes.", 503)

    analysis = _fit_analysis_map(answer)
    fit_score = analysis.get("fit_score")
    summary = analysis.get("shareable_summary") or analysis.get("executive_summary") or answer[:1000]
    evidence = _evidence_from_docs(docs_with_scores, retrieval_query, None)
    usage.update(
        {
            "model": model_used,
            "fallback_used": fallback_used,
            "retrieval_ms": retrieval_ms,
            "llm_ms": llm_ms,
            "time_to_first_token_ms": first_token_ms,
            "total_ms": round((time.perf_counter() - total_start) * 1000, 2),
            "retrieved_docs": len(docs_with_scores),
            "retrieved_sources": [
                str((doc.metadata or {}).get("source", ""))
                for doc, _score in docs_with_scores
                if (doc.metadata or {}).get("source")
            ],
            "evidence_count": len(evidence),
        }
    )
    _get_store(settings).append(session_id, f"Análise de vaga: {job_title or 'vaga sem título'}", answer)
    trace_id = _save_trace_for_answer(
        settings,
        session_id=session_id,
        question=f"Fit Scanner: {job_title or 'vaga sem titulo'}\n{clean_description[:3000]}",
        answer=answer,
        active_node="fit",
        retrieval_query=retrieval_query,
        docs_with_scores=docs_with_scores,
        rag_trace=rag_trace,
        usage=usage,
        model=model_used,
    )
    usage["trace_id"] = trace_id
    yield {
        "event": "done",
        "result": FitAnalysisResult(
            session_id=session_id,
            answer=answer,
            summary=summary,
            fit_score=fit_score,
            analysis=analysis,
            sources=_source_summaries(docs_with_scores),
            evidence=evidence,
            usage=usage,
            trace_id=trace_id,
        ),
    }


def _prepare_agent_run(
    message: str,
    session_id: Optional[str] = None,
    active_node: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> PreparedAgentRun:
    settings = settings or get_settings()
    total_start = time.perf_counter()
    session_id = session_id or str(uuid4())
    clean_message = message.strip()
    if not clean_message:
        raise AppError(code="empty_message", message="Envie uma pergunta ou mensagem para conversar.", status_code=400)

    retrieval_query = _expand_retrieval_query(clean_message, active_node)
    retrieval_start = time.perf_counter()
    try:
        docs_with_scores, rag_trace = _retrieve_documents_with_trace(settings, retrieval_query, active_node)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("rag_retrieval_failed")
        raise AppError(
            code="rag_unavailable",
            message="Não consegui consultar a base de conhecimento agora. Tente novamente em instantes.",
            status_code=503,
        ) from exc
    retrieval_ms = round((time.perf_counter() - retrieval_start) * 1000, 2)

    if len(docs_with_scores) < settings.rag_min_docs:
        raise AppError(
            code="rag_weak_context",
            message="Não encontrei contexto suficiente nos Markdown para responder com segurança. Posso responder melhor depois que essa parte for documentada ou reindexada.",
            status_code=422,
        )

    context = _format_context(docs_with_scores, settings.rag_max_context_chars)
    history = _get_store(settings).get(session_id)
    user_prompt = _build_user_prompt(context, active_node, clean_message)
    messages: List[BaseMessage] = [SystemMessage(content=load_system_prompt(settings)), *history, HumanMessage(content=user_prompt)]
    return PreparedAgentRun(
        session_id=session_id,
        clean_message=clean_message,
        retrieval_query=retrieval_query,
        docs_with_scores=docs_with_scores,
        evidence=_evidence_from_docs(docs_with_scores, retrieval_query, active_node),
        messages=messages,
        retrieval_ms=retrieval_ms,
        total_start=total_start,
        active_node=active_node,
        rag_trace=rag_trace,
    )


def _finalize_agent_result(
    prepared: PreparedAgentRun,
    answer: str,
    settings: Settings,
    usage: Optional[Dict[str, Any]] = None,
    *,
    llm_ms: float,
    time_to_first_token_ms: Optional[float] = None,
    model: Optional[str] = None,
    fallback_used: bool = False,
) -> AgentResult:
    answer = sanitize_answer_text(answer)
    if not answer:
        raise AppError(
            code="empty_llm_response",
            message="A OpenAI retornou uma resposta vazia. Tente novamente em instantes.",
            status_code=503,
        )
    _get_store(settings).append(prepared.session_id, prepared.clean_message, answer)
    usage = usage or {}
    usage.update(
        {
            "model": model or settings.openai_chat_model,
            "fallback_used": fallback_used,
            "retrieval_ms": prepared.retrieval_ms,
            "llm_ms": llm_ms,
            "time_to_first_token_ms": time_to_first_token_ms,
            "total_ms": round((time.perf_counter() - prepared.total_start) * 1000, 2),
            "retrieved_docs": len(prepared.docs_with_scores),
            "retrieved_sources": [
                str((doc.metadata or {}).get("source", ""))
                for doc, _score in prepared.docs_with_scores
                if (doc.metadata or {}).get("source")
            ],
            "evidence_count": len(prepared.evidence),
        }
    )
    trace_id = _save_trace_for_answer(
        settings,
        session_id=prepared.session_id,
        question=prepared.clean_message,
        answer=answer,
        active_node=prepared.active_node,
        retrieval_query=prepared.retrieval_query,
        docs_with_scores=prepared.docs_with_scores,
        rag_trace=prepared.rag_trace,
        usage=usage,
        model=model or settings.openai_chat_model,
    )
    usage["trace_id"] = trace_id
    return AgentResult(
        session_id=prepared.session_id,
        answer=answer,
        detected_language=_detect_language(prepared.clean_message),
        sources=_source_summaries(prepared.docs_with_scores),
        evidence=prepared.evidence,
        usage=usage,
        trace_id=trace_id,
    )


def answer_question(
    message: str,
    session_id: Optional[str] = None,
    active_node: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> AgentResult:
    settings = settings or get_settings()
    prepared = _prepare_agent_run(message, session_id, active_node, settings)

    try:
        llm_start = time.perf_counter()
        response = _build_llm(settings).invoke(prepared.messages)
        llm_ms = round((time.perf_counter() - llm_start) * 1000, 2)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("llm_call_failed")
        raise AppError(
            code="llm_unavailable",
            message="Não consegui gerar a resposta com a OpenAI agora. Verifique créditos, chave e limite de uso.",
            status_code=503,
        ) from exc

    answer = sanitize_answer_text(_response_content_to_text(response.content))
    return _finalize_agent_result(
        prepared,
        answer,
        settings,
        _usage_from_response(response),
        llm_ms=llm_ms,
        model=settings.openai_chat_model,
    )


def stream_answer_question(
    message: str,
    session_id: Optional[str] = None,
    active_node: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> Iterator[Dict[str, Any]]:
    settings = settings or get_settings()
    total_start = time.perf_counter()
    yield _stage("received", "Pergunta recebida", "complete", elapsed_ms=0)

    clean_message = message.strip()
    if not clean_message:
        raise AppError(code="empty_message", message="Envie uma pergunta ou mensagem para conversar.", status_code=400)

    yield _stage("expanding_query", "Expandindo consulta", "active")
    query_start = time.perf_counter()
    retrieval_query = _expand_retrieval_query(clean_message, active_node)
    yield _stage("expanding_query", "Expandindo consulta", "complete", elapsed_ms=round((time.perf_counter() - query_start) * 1000, 2))

    yield _stage("retrieving_context", "Buscando Markdown", "active")
    retrieval_start = time.perf_counter()
    try:
        docs_with_scores, rag_trace = _retrieve_documents_with_trace(settings, retrieval_query, active_node)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("rag_retrieval_failed")
        raise AppError(
            code="rag_unavailable",
            message="Não consegui consultar a base de conhecimento agora. Tente novamente em instantes.",
            status_code=503,
        ) from exc
    retrieval_ms = round((time.perf_counter() - retrieval_start) * 1000, 2)
    yield _stage("retrieving_context", "Buscando Markdown", "complete", elapsed_ms=retrieval_ms, docs=len(docs_with_scores))

    if len(docs_with_scores) < settings.rag_min_docs:
        raise AppError(
            code="rag_weak_context",
            message="Não encontrei contexto suficiente nos Markdown para responder com segurança. Posso responder melhor depois que essa parte for documentada ou reindexada.",
            status_code=422,
        )

    yield _stage("selecting_evidence", "Selecionando evidências", "active")
    evidence_start = time.perf_counter()
    context = _format_context(docs_with_scores, settings.rag_max_context_chars)
    history = _get_store(settings).get(session_id or "")
    user_prompt = _build_user_prompt(context, active_node, clean_message)
    messages: List[BaseMessage] = [SystemMessage(content=load_system_prompt(settings)), *history, HumanMessage(content=user_prompt)]
    prepared = PreparedAgentRun(
        session_id=session_id or str(uuid4()),
        clean_message=clean_message,
        retrieval_query=retrieval_query,
        docs_with_scores=docs_with_scores,
        evidence=_evidence_from_docs(docs_with_scores, retrieval_query, active_node),
        messages=messages,
        retrieval_ms=retrieval_ms,
        total_start=total_start,
        active_node=active_node,
        rag_trace=rag_trace,
    )
    yield _stage("selecting_evidence", "Selecionando evidências", "complete", elapsed_ms=round((time.perf_counter() - evidence_start) * 1000, 2))

    yield _stage("generating_answer", "Gerando resposta", "active", model=settings.openai_chat_model)
    llm_start = time.perf_counter()
    first_token_ms: Optional[float] = None
    answer = ""
    raw_stream_text = ""
    sanitizer_state: Dict[str, bool] = {"pending_star": False}
    usage: Dict[str, Any] = {}
    model_used = settings.openai_chat_model
    fallback_used = False

    try:
        for chunk in _build_llm(settings, model_used).stream(messages):
            chunk_usage = getattr(chunk, "usage_metadata", None) or {}
            if chunk_usage:
                usage = {
                    "input_tokens": int(chunk_usage.get("input_tokens", 0) or 0),
                    "output_tokens": int(chunk_usage.get("output_tokens", 0) or 0),
                    "total_tokens": int(chunk_usage.get("total_tokens", 0) or 0),
                }
            chunk_text = _response_content_to_delta(getattr(chunk, "content", ""))
            if not chunk_text:
                continue
            if raw_stream_text and len(raw_stream_text) >= 12 and chunk_text.startswith(raw_stream_text):
                delta = chunk_text[len(raw_stream_text) :]
                raw_stream_text = chunk_text
            else:
                delta = chunk_text
                raw_stream_text += chunk_text
            delta = _sanitize_stream_delta(delta, sanitizer_state)
            if not delta:
                continue
            if first_token_ms is None:
                first_token_ms = round((time.perf_counter() - llm_start) * 1000, 2)
            answer += delta
            yield {"event": "delta", "data": {"text": delta}}
    except Exception as exc:
        logger.exception("llm_stream_failed")
        if answer or not settings.openai_fast_chat_model or settings.openai_fast_chat_model == settings.openai_chat_model:
            raise AppError(
                code="llm_unavailable",
                message="Não consegui gerar a resposta com a OpenAI agora. Verifique créditos, chave e limite de uso.",
                status_code=503,
            ) from exc
        fallback_used = True
        model_used = settings.openai_fast_chat_model
        yield _stage("generating_answer", "Gerando resposta", "active", detail="Usando modelo rápido de fallback", model=model_used)
        try:
            response = _build_llm(settings, model_used).invoke(messages)
        except Exception as fallback_exc:
            logger.exception("llm_fallback_failed")
            raise AppError(
                code="llm_unavailable",
                message="Não consegui gerar a resposta com a OpenAI agora. Verifique créditos, chave e limite de uso.",
                status_code=503,
            ) from fallback_exc
        answer = sanitize_answer_text(_response_content_to_text(response.content))
        usage = _usage_from_response(response)
        if answer:
            first_token_ms = first_token_ms or round((time.perf_counter() - llm_start) * 1000, 2)
            yield {"event": "delta", "data": {"text": answer}}

    tail = _flush_stream_sanitizer(sanitizer_state)
    if tail:
        answer += tail
        yield {"event": "delta", "data": {"text": tail}}

    llm_ms = round((time.perf_counter() - llm_start) * 1000, 2)
    yield _stage("generating_answer", "Gerando resposta", "complete", elapsed_ms=llm_ms, model=model_used)

    result = _finalize_agent_result(
        prepared,
        answer,
        settings,
        usage,
        llm_ms=llm_ms,
        time_to_first_token_ms=first_token_ms,
        model=model_used,
        fallback_used=fallback_used,
    )
    yield {"event": "done", "result": result}
