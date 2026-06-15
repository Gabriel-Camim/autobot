from config import Settings
from job_scans import create_job_scan, finish_job_scan, get_job_scan, list_job_scans


def test_job_scan_list_and_detail_preserve_full_description(tmp_path):
    settings = Settings(_env_file=None, EVENTS_DB_PATH=tmp_path / "events.sqlite3", DATABASE_URL="")
    description = "Vaga de IA aplicada com Python, FastAPI e automações. " * 20

    scan_id = create_job_scan(
        settings,
        job_title="AI Automation Analyst",
        company="Empresa Teste",
        job_description=description,
        visitor_id="visitor-1",
        session_id="session-1",
        visitor_identity={"name": "Recrutador", "company": "Empresa Teste"},
    )
    finish_job_scan(
        settings,
        scan_id,
        summary="Fit forte para IA aplicada.",
        analysis_text="Fit estimado: 82/100",
        analysis={"fit_score": 82},
        metrics={"model": "test-model", "total_ms": 120},
        sources=[{"source": "knowledge/skills/stack.md"}],
        docs=["knowledge/skills/stack.md"],
        fit_score=82,
        model="test-model",
    )

    scans = list_job_scans(settings, visitor_id="visitor-1")
    assert scans[0]["id"] == scan_id
    assert scans[0]["job_description_chars"] == len(description)
    assert "job_description" not in scans[0]

    detail = get_job_scan(settings, scan_id)
    assert detail["job_description"] == description
    assert detail["fit_score"] == 82
    assert detail["visitor_identity"]["name"] == "Recrutador"
