from __future__ import annotations

import argparse
import gc
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from agent import AppError, clear_rag_caches
from config import Settings, get_settings
from pgvector_store import pgvector_index_documents, uses_pgvector


REQUIRED_VISIBILITY = "public"


def _require_openai_key(settings: Settings) -> None:
    if not settings.openai_api_key:
        raise AppError(
            code="missing_openai_key",
            message="OPENAI_API_KEY não configurada. Crie backend/.env a partir de backend/.env.example.",
            status_code=503,
        )


def _parse_frontmatter(raw: str) -> Tuple[Dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    metadata = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    return metadata, body


def _iter_markdown_files(knowledge_dir: Path) -> Iterable[Path]:
    return sorted(
        path
        for path in knowledge_dir.rglob("*.md")
        if path.is_file()
        and not {"_drafts", "_context", "_system"} & set(path.relative_to(knowledge_dir).parts)
    )


def load_public_documents(settings: Settings) -> List[Document]:
    knowledge_dir = settings.resolved_knowledge_dir
    if not knowledge_dir.exists():
        raise AppError(
            code="knowledge_missing",
            message=f"Diretório de conhecimento não encontrado: {knowledge_dir}",
            status_code=404,
        )

    documents: List[Document] = []
    for path in _iter_markdown_files(knowledge_dir):
        raw = path.read_text(encoding="utf-8")
        metadata, body = _parse_frontmatter(raw)
        if str(metadata.get("visibility", "")).lower() != REQUIRED_VISIBILITY:
            continue

        relative_source = path.relative_to(knowledge_dir).as_posix()
        if any(relative_source.startswith(prefix) for prefix in settings.rag_excluded_source_prefix_list):
            continue
        tags = metadata.get("tags", [])
        if isinstance(tags, list):
            tags_value = ", ".join(str(tag) for tag in tags)
        else:
            tags_value = str(tags)

        document_metadata = {
            "title": str(metadata.get("title", path.stem)),
            "category": str(metadata.get("category", path.parent.name)),
            "tags": tags_value,
            "visibility": str(metadata.get("visibility", REQUIRED_VISIBILITY)),
            "priority": int(metadata.get("priority", 3) or 3),
            "updated_at": str(metadata.get("updated_at", "")),
            "summary": str(metadata.get("summary", "")),
            "source": relative_source,
        }
        documents.append(Document(page_content=body, metadata=document_metadata))
    return documents


def _reset_chroma_dir(settings: Settings) -> None:
    target = settings.resolved_chroma_dir
    project_root = settings.project_root.resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    allowed_roots = [project_root, temp_root]
    clear_rag_caches()
    gc.collect()
    if target.exists():
        if not any(root in target.parents for root in allowed_roots):
            raise AppError(
                code="unsafe_chroma_dir",
                message=f"Recusando apagar diretório fora das áreas permitidas: {target}",
                status_code=400,
            )
        if target in allowed_roots:
            raise AppError(
                code="unsafe_chroma_dir",
                message=f"Recusando apagar diretório raiz permitido: {target}",
                status_code=400,
            )
        shutil.rmtree(target, onerror=_make_writable_then_retry)
    target.mkdir(parents=True, exist_ok=True)
    _verify_writable_directory(target)


def _make_writable_then_retry(func, path: str, _exc_info) -> None:
    os.chmod(path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    func(path)


def _verify_writable_directory(directory: Path) -> None:
    probe = directory / ".write-test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise AppError(
            code="chroma_not_writable",
            message=f"Diretório Chroma sem permissão de escrita: {directory}",
            status_code=503,
        ) from exc


def ingest(settings: Settings) -> int:
    _require_openai_key(settings)
    base_documents = load_public_documents(settings)
    if not base_documents:
        raise AppError(
            code="no_public_documents",
            message="Nenhum Markdown público encontrado para indexar.",
            status_code=400,
        )

    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
    chunks = splitter.split_documents(base_documents)

    if uses_pgvector(settings):
        count = pgvector_index_documents(settings, chunks)
        clear_rag_caches()
        return count

    _reset_chroma_dir(settings)
    embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model, api_key=settings.openai_api_key)
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=settings.chroma_collection,
        persist_directory=str(settings.resolved_chroma_dir),
    )
    clear_rag_caches()
    return len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexa a base Markdown pública no ChromaDB local.")
    parser.add_argument("--check", action="store_true", help="Apenas valida quantos documentos públicos seriam indexados.")
    args = parser.parse_args()

    settings = get_settings()
    try:
        if args.check:
            docs = load_public_documents(settings)
            print(f"{len(docs)} documentos públicos encontrados em {settings.resolved_knowledge_dir}")
            return
        count = ingest(settings)
        print(f"Ingestão concluída: {count} chunks salvos em {settings.resolved_chroma_dir}")
    except AppError as exc:
        print(f"Erro [{exc.code}]: {exc.message}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
