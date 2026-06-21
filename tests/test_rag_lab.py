from pathlib import Path

import agent
import rag_lab
from config import Settings


def test_rag_eval_run_persists_result_without_llm(monkeypatch, tmp_path: Path):
    settings = Settings(
        _env_file=None,
        EVENTS_DB_PATH=tmp_path / "events.sqlite3",
        APP_VERSION="1.5.0",
        APP_COMMIT="abc1234",
    )
    monkeypatch.setattr(
        rag_lab,
        "load_rag_eval_cases",
        lambda _settings: [
            {
                "id": "hard-skills",
                "question": "Quais hard skills?",
                "active_context": "stack",
                "expected_sources": ["skills/hard-skills.md"],
                "forbidden_terms": ["PyTorch"],
                "min_docs": 1,
            }
        ],
    )

    def fake_probe(_settings, question, active_context=None, limit=None):
        return {
            "question": question,
            "active_context": active_context,
            "retrieval_query": question,
            "documents": 1,
            "took_ms": 3.5,
            "evidence": [
                {
                    "source": "skills/hard-skills.md",
                    "title": "Hard skills",
                    "category": "skills",
                    "summary": "Stack real.",
                    "tags": ["python"],
                    "priority": 1,
                    "excerpt": "Python, SQL, FastAPI e LangChain.",
                    "channel": "hybrid",
                    "distance": 0.2,
                    "relevance_score": 8.0,
                    "match_reason": "teste",
                }
            ],
        }

    monkeypatch.setattr(agent, "build_rag_probe", fake_probe)

    run = rag_lab.run_rag_eval(settings)
    last = rag_lab.last_eval_run(settings)

    assert run["total"] == 1
    assert run["passed"] == 1
    assert run["failed"] == 0
    assert last["result"]["cases"][0]["sources"] == ["skills/hard-skills.md"]


def test_rag_eval_detects_forbidden_terms(monkeypatch, tmp_path: Path):
    settings = Settings(_env_file=None, EVENTS_DB_PATH=tmp_path / "events.sqlite3")
    monkeypatch.setattr(
        rag_lab,
        "load_rag_eval_cases",
        lambda _settings: [
            {
                "id": "forbidden",
                "question": "Quais hard skills?",
                "active_context": "stack",
                "expected_sources": ["skills/hard-skills.md"],
                "forbidden_terms": ["TensorFlow"],
                "min_docs": 1,
            }
        ],
    )
    monkeypatch.setattr(
        agent,
        "build_rag_probe",
        lambda *_args, **_kwargs: {
            "evidence": [
                {
                    "source": "skills/hard-skills.md",
                    "title": "Hard skills",
                    "category": "skills",
                    "summary": "",
                    "excerpt": "TensorFlow apareceu indevidamente.",
                    "match_reason": "",
                }
            ],
            "took_ms": 1,
            "retrieval_query": "hard skills",
        },
    )

    run = rag_lab.run_rag_eval(settings)

    assert run["passed"] == 0
    assert run["failed"] == 1
    assert run["cases"][0]["forbidden_terms_detected"] == ["TensorFlow"]
