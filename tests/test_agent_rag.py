from pathlib import Path

import pytest
from langchain_core.documents import Document

from agent import AppError, _doc_matches_focus, _ensure_vector_index, _response_content_to_text
from config import Settings


def test_missing_chroma_index_is_explicit(tmp_path: Path):
    settings = Settings(_env_file=None, CHROMA_DIR=tmp_path / "missing-chroma")

    with pytest.raises(AppError) as error:
        _ensure_vector_index(settings)

    assert error.value.code == "rag_not_indexed"


def test_skill_questions_only_accept_skill_or_stack_documents():
    skill_doc = Document(
        page_content="Python, SQL, LangChain e OpenAI.",
        metadata={"source": "skills/hard-skills.md", "category": "skills", "tags": "hard-skills"},
    )
    project_doc = Document(
        page_content="Documento arquitetural amplo de projeto.",
        metadata={"source": "projetos/dge/arquitetura.md", "category": "projetos", "tags": "dge"},
    )

    assert _doc_matches_focus(skill_doc, "stack", skill_question=True)
    assert not _doc_matches_focus(project_doc, "stack", skill_question=True)


def test_response_content_list_extracts_only_text():
    content = [
        {"id": "rs_1", "type": "reasoning", "summary": [], "content": []},
        {"type": "text", "text": "Minha stack combina Python, FastAPI e LangChain."},
    ]

    assert _response_content_to_text(content) == "Minha stack combina Python, FastAPI e LangChain."
