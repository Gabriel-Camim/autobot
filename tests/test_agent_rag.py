from pathlib import Path

import pytest
from langchain_core.documents import Document

from agent import AppError, _doc_matches_focus, _ensure_vector_index, _expand_retrieval_query, _lexical_matches, _response_content_to_text
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
    assert _doc_matches_focus(project_doc, "gabriel", skill_question=True, query="stack da DGE")


def test_response_content_list_extracts_only_text():
    content = [
        {"id": "rs_1", "type": "reasoning", "summary": [], "content": []},
        {"type": "text", "text": "Minha stack combina Python, FastAPI e LangChain."},
    ]

    assert _response_content_to_text(content) == "Minha stack combina Python, FastAPI e LangChain."


def test_lexical_retrieval_crosses_active_node_and_project_context(tmp_path: Path):
    knowledge = tmp_path / "knowledge"
    (knowledge / "skills").mkdir(parents=True)
    (knowledge / "projetos" / "ebookgenerator").mkdir(parents=True)
    (knowledge / "projetos" / "dge").mkdir(parents=True)

    (knowledge / "skills" / "hard-skills.md").write_text(
        """---
title: Hard skills
category: skills
tags: [hard-skills, stack]
visibility: public
priority: 1
summary: Stack e competências técnicas.
---
OpenAI, LangChain, Python, SQL, FastAPI, React, n8n e APIs REST.
""",
        encoding="utf-8",
    )
    (knowledge / "projetos" / "ebookgenerator" / "overview.md").write_text(
        """---
title: Ebook Generator
category: projetos
tags: [ebook-generator, n8n, openai, gamma]
visibility: public
priority: 1
summary: Automação editorial com LLMs.
---
Workflow em n8n com OpenAI API, Gamma API, JSON estruturado, Supabase e memória.
""",
        encoding="utf-8",
    )
    (knowledge / "projetos" / "dge" / "overview.md").write_text(
        """---
title: DGE
category: projetos
tags: [dge, postgres, superset]
visibility: public
priority: 1
summary: Inteligência operacional auditável.
---
Sistema com PostgreSQL, BI, Superset, contratos de dados, KPIs e reforecast.
""",
        encoding="utf-8",
    )

    settings = Settings(_env_file=None, KNOWLEDGE_DIR=knowledge)
    query = _expand_retrieval_query("e a stak de outros projetos, tipo ebook generator e dge?", "gabriel")
    sources = [doc.metadata["source"] for doc, _score in _lexical_matches(settings, query, "gabriel", 10)]

    assert "skills/hard-skills.md" in sources
    assert "projetos/ebookgenerator/overview.md" in sources
    assert "projetos/dge/overview.md" in sources
