from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from config import Settings


logger = logging.getLogger("gabriel_pgvector")


def uses_pgvector(settings: Settings) -> bool:
    return settings.vector_backend == "pgvector"


def _require_database_url(settings: Settings) -> str:
    database_url = settings.database_url.strip()
    if not database_url.startswith(("postgres://", "postgresql://")):
        raise RuntimeError("DATABASE_URL precisa apontar para um Postgres valido para usar pgvector.")
    return database_url


def _table_name(settings: Settings) -> str:
    table = settings.pgvector_table.strip() or "rag_chunks"
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
        raise RuntimeError("PGVECTOR_TABLE invalida. Use apenas letras, numeros e underscore.")
    return table


def _connect(settings: Settings):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("psycopg e necessario para usar pgvector") from exc

    return psycopg.connect(_require_database_url(settings), row_factory=dict_row, autocommit=True)


def _embedding_literal(values: Iterable[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in values) + "]"


def _metadata_json(doc: Document) -> str:
    return json.dumps(doc.metadata or {}, ensure_ascii=False, separators=(",", ":"), default=str)


def _chunk_id(doc: Document) -> str:
    metadata = doc.metadata or {}
    seed = "\n".join(
        [
            str(metadata.get("source", "")),
            str(metadata.get("title", "")),
            doc.page_content,
        ]
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def ensure_pgvector_schema(settings: Settings) -> None:
    table = _table_name(settings)
    dimension = int(settings.pgvector_dimension)
    with _connect(settings) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                source TEXT NOT NULL,
                title TEXT,
                category TEXT,
                tags TEXT,
                priority INTEGER,
                updated_at TEXT,
                summary TEXT,
                content TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                embedding vector({dimension}) NOT NULL,
                reindexed_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_source ON {table}(source)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_category ON {table}(category)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_reindexed_at ON {table}(reindexed_at)")
        try:
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{table}_embedding_hnsw "
                f"ON {table} USING hnsw (embedding vector_cosine_ops)"
            )
        except Exception:
            logger.warning("pgvector_hnsw_index_unavailable", exc_info=True)


def pgvector_status(settings: Settings) -> Dict[str, Any]:
    if not uses_pgvector(settings):
        return {"backend": settings.vector_backend, "ready": False, "chunks": 0, "last_reindex_at": None, "error": None}
    try:
        ensure_pgvector_schema(settings)
        table = _table_name(settings)
        with _connect(settings) as conn:
            row = conn.execute(f"SELECT COUNT(*) AS chunks, MAX(reindexed_at) AS last_reindex_at FROM {table}").fetchone()
        chunks = int(row.get("chunks") or 0)
        return {
            "backend": "pgvector",
            "ready": chunks > 0,
            "chunks": chunks,
            "last_reindex_at": str(row.get("last_reindex_at")) if row.get("last_reindex_at") else None,
            "error": None,
        }
    except Exception as exc:
        logger.exception("pgvector_status_failed")
        return {"backend": "pgvector", "ready": False, "chunks": 0, "last_reindex_at": None, "error": str(exc)[:240]}


def pgvector_index_documents(settings: Settings, chunks: List[Document]) -> int:
    ensure_pgvector_schema(settings)
    table = _table_name(settings)
    embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model, api_key=settings.openai_api_key)
    texts = [chunk.page_content for chunk in chunks]
    vectors = embeddings.embed_documents(texts)
    if vectors and len(vectors[0]) != int(settings.pgvector_dimension):
        raise RuntimeError(
            f"Dimensao do embedding ({len(vectors[0])}) difere de PGVECTOR_DIMENSION={settings.pgvector_dimension}."
        )

    now = datetime.now(timezone.utc)
    rows = []
    for doc, vector in zip(chunks, vectors):
        metadata = doc.metadata or {}
        content_hash = hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest()
        rows.append(
            (
                _chunk_id(doc),
                content_hash,
                str(metadata.get("source", "")),
                str(metadata.get("title", "")),
                str(metadata.get("category", "")),
                str(metadata.get("tags", "")),
                int(metadata.get("priority", 3) or 3),
                str(metadata.get("updated_at", "")),
                str(metadata.get("summary", "")),
                doc.page_content,
                _metadata_json(doc),
                _embedding_literal(vector),
                now,
            )
        )

    with _connect(settings) as conn:
        conn.execute(f"TRUNCATE TABLE {table}")
        if not rows:
            return 0
        conn.executemany(
            f"""
            INSERT INTO {table}
            (id, content_hash, source, title, category, tags, priority, updated_at, summary, content, metadata_json, embedding, reindexed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s)
            """,
            rows,
        )
    return len(rows)


def pgvector_similarity_search(
    settings: Settings,
    query: str,
    limit: int,
    *,
    assume_ready: bool = False,
) -> List[Tuple[Document, float]]:
    if not assume_ready and not pgvector_status(settings).get("ready"):
        return []

    embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model, api_key=settings.openai_api_key)
    query_vector = embeddings.embed_query(query)
    if len(query_vector) != int(settings.pgvector_dimension):
        raise RuntimeError(
            f"Dimensao da query ({len(query_vector)}) difere de PGVECTOR_DIMENSION={settings.pgvector_dimension}."
        )

    table = _table_name(settings)
    vector_literal = _embedding_literal(query_vector)
    with _connect(settings) as conn:
        rows = conn.execute(
            f"""
            SELECT content, metadata_json, embedding <=> %s::vector AS distance
            FROM {table}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (vector_literal, vector_literal, max(1, int(limit))),
        ).fetchall()

    results: List[Tuple[Document, float]] = []
    for row in rows:
        try:
            metadata = json.loads(row.get("metadata_json") or "{}")
        except json.JSONDecodeError:
            metadata = {}
        results.append((Document(page_content=row.get("content") or "", metadata=metadata), float(row.get("distance") or 0.0)))
    return results
