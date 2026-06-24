from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import Settings
from pgvector_store import uses_pgvector


CONTEXT_TABLE = "rag_studio_context_chunks"


def _require_database_url(settings: Settings) -> str:
    database_url = settings.database_url.strip()
    if not database_url.startswith(("postgres://", "postgresql://")):
        raise RuntimeError("DATABASE_URL precisa apontar para um Postgres valido para indexar contexto do RAG Studio.")
    return database_url


def _connect(settings: Settings):
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(_require_database_url(settings), row_factory=dict_row, autocommit=True)


def _embedding_literal(values: Iterable[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in values) + "]"


def _safe_metadata(metadata: Dict[str, Any]) -> str:
    return json.dumps(metadata, ensure_ascii=False, separators=(",", ":"), default=str)


def ensure_context_schema(settings: Settings) -> None:
    if not uses_pgvector(settings):
        return
    dimension = int(settings.pgvector_dimension)
    with _connect(settings) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CONTEXT_TABLE} (
                id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                context_id TEXT NOT NULL,
                source TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                embedding vector({dimension}) NOT NULL,
                indexed_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{CONTEXT_TABLE}_proposal ON {CONTEXT_TABLE}(proposal_id)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{CONTEXT_TABLE}_context ON {CONTEXT_TABLE}(context_id)")
        try:
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{CONTEXT_TABLE}_embedding_hnsw "
                f"ON {CONTEXT_TABLE} USING hnsw (embedding vector_cosine_ops)"
            )
        except Exception:
            # HNSW may be unavailable in local/test Postgres; exact search still works.
            pass


def _chunk_id(context_id: str, content: str, index: int) -> str:
    seed = f"{context_id}\n{index}\n{content}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def index_context_document(settings: Settings, document: Dict[str, Any]) -> Dict[str, Any]:
    if not uses_pgvector(settings):
        return {"indexed": False, "chunks": 0, "error": "VECTORSTORE_BACKEND nao esta em pgvector."}
    ensure_context_schema(settings)
    text = str(document.get("extracted_text") or "").strip()
    if not text:
        return {"indexed": False, "chunks": 0, "error": "Documento contextual sem texto extraido."}

    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
    chunks = splitter.split_text(text)
    embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model, api_key=settings.openai_api_key)
    vectors = embeddings.embed_documents(chunks)
    if vectors and len(vectors[0]) != int(settings.pgvector_dimension):
        raise RuntimeError(
            f"Dimensao do embedding ({len(vectors[0])}) difere de PGVECTOR_DIMENSION={settings.pgvector_dimension}."
        )

    indexed_at = datetime.now(timezone.utc)
    rows = []
    for index, (content, vector) in enumerate(zip(chunks, vectors)):
        metadata = {
            "proposal_id": document.get("proposal_id"),
            "context_id": document.get("id"),
            "source": document.get("git_path") or document.get("filename"),
            "filename": document.get("filename"),
            "sha256": document.get("sha256"),
            "status": document.get("status"),
        }
        rows.append(
            (
                _chunk_id(str(document.get("id")), content, index),
                document.get("proposal_id"),
                document.get("id"),
                document.get("git_path") or document.get("filename"),
                document.get("title") or document.get("filename"),
                content,
                _safe_metadata(metadata),
                _embedding_literal(vector),
                indexed_at,
            )
        )

    with _connect(settings) as conn:
        conn.execute(f"DELETE FROM {CONTEXT_TABLE} WHERE context_id = %s", (document.get("id"),))
        if rows:
            with conn.cursor() as cursor:
                cursor.executemany(
                    f"""
                    INSERT INTO {CONTEXT_TABLE}
                    (id, proposal_id, context_id, source, title, content, metadata_json, embedding, indexed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector, %s)
                    """,
                    rows,
                )
    return {"indexed": True, "chunks": len(rows), "indexed_at": indexed_at.isoformat()}


def remove_context_document_chunks(settings: Settings, context_id: str) -> None:
    if not uses_pgvector(settings):
        return
    ensure_context_schema(settings)
    with _connect(settings) as conn:
        conn.execute(f"DELETE FROM {CONTEXT_TABLE} WHERE context_id = %s", (context_id,))


def search_context_documents(settings: Settings, proposal_id: str, query: str, limit: int = 6) -> List[Dict[str, Any]]:
    if not uses_pgvector(settings):
        return []
    if not query.strip():
        return []
    ensure_context_schema(settings)
    embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model, api_key=settings.openai_api_key)
    query_vector = embeddings.embed_query(query)
    if len(query_vector) != int(settings.pgvector_dimension):
        raise RuntimeError(
            f"Dimensao da query ({len(query_vector)}) difere de PGVECTOR_DIMENSION={settings.pgvector_dimension}."
        )
    vector_literal = _embedding_literal(query_vector)
    with _connect(settings) as conn:
        rows = conn.execute(
            f"""
            SELECT context_id, source, title, content, metadata_json, embedding <=> %s::vector AS distance
            FROM {CONTEXT_TABLE}
            WHERE proposal_id = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (vector_literal, proposal_id, vector_literal, max(1, int(limit))),
        ).fetchall()
    output: List[Dict[str, Any]] = []
    for row in rows:
        try:
            metadata = json.loads(row.get("metadata_json") or "{}")
        except json.JSONDecodeError:
            metadata = {}
        distance = float(row.get("distance") or 0)
        output.append(
            {
                "context_id": row.get("context_id"),
                "source": row.get("source"),
                "title": row.get("title"),
                "excerpt": re.sub(r"\s+", " ", row.get("content") or "").strip()[:900],
                "distance": distance,
                "relevance_score": round(max(0.0, 1.0 - min(distance, 2.0) / 2.0), 4),
                "channel": "private_context",
                "metadata": metadata,
            }
        )
    return output
