from pathlib import Path

import rag_quality
from config import Settings


def test_heuristic_reranker_promotes_hybrid_priority_sources():
    settings = Settings(_env_file=None, RAG_RERANK_PROVIDER="heuristic")
    candidates = [
        {
            "id": "b",
            "source": "reports/stack.md",
            "title": "Report",
            "priority": 4,
            "channel": "vector",
            "distance": 1.2,
            "base_relevance": 5.0,
            "match_reason": "canal vector",
        },
        {
            "id": "a",
            "source": "skills/hard-skills.md",
            "title": "Hard skills",
            "priority": 1,
            "channel": "hybrid",
            "distance": 0.2,
            "base_relevance": 4.8,
            "match_reason": "canal hybrid; foco: stack",
        },
    ]

    reranked = rag_quality.rerank_candidate_payloads(settings, candidates)

    assert reranked[0]["source"] == "skills/hard-skills.md"
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]


def test_trace_and_negative_feedback_create_draft_suggestion(tmp_path: Path):
    settings = Settings(
        _env_file=None,
        EVENTS_DB_PATH=tmp_path / "events.sqlite3",
        RAG_TRACE_ENABLED=True,
        RAG_FEEDBACK_ENABLED=True,
        RAG_SUGGESTIONS_ENABLED=True,
    )

    trace_id = rag_quality.save_rag_trace(
        settings,
        {
            "session_id": "session-1",
            "visitor_id": "visitor-1",
            "active_context": "stack",
            "question": "Quais hard skills?",
            "answer": "Python e SQL.",
            "retrieval_query": "Quais hard skills? stack",
            "subqueries": ["Quais hard skills?", "foco: stack"],
            "candidates": [{"source": "skills/hard-skills.md", "rerank_score": 8.0}],
            "selected_sources": ["skills/hard-skills.md"],
            "rerank": {"provider": "heuristic"},
            "metrics": {"retrieval_ms": 12},
            "model": "test-model",
        },
    )

    result = rag_quality.create_rag_feedback(
        settings,
        {
            "trace_id": trace_id,
            "session_id": "session-1",
            "visitor_id": "visitor-1",
            "rating": "negative",
            "reason": "missing_context",
            "comment": "Faltou citar n8n.",
        },
    )

    suggestions = rag_quality.list_knowledge_suggestions(settings)

    assert result["feedback"]["trace_id"] == trace_id
    assert result["suggestion"]["status"] == "open"
    assert suggestions[0]["frontmatter"]["visibility"] == "draft"
    assert suggestions[0]["suggested_path"].startswith("knowledge/skills/")
    assert "Faltou citar n8n." in suggestions[0]["draft_markdown"]
