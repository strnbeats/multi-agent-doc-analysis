import time

from fastapi.testclient import TestClient

from multi_agent_docs.database.db import Database
from multi_agent_docs.database.repository import DocumentRepository
from multi_agent_docs.main import app
from multi_agent_docs.models import FactCheckResult, PipelineResult, TokenUsage
from multi_agent_docs.services.analysis_service import AnalysisService

from conftest import FakeLLM


def test_api_background_flow(monkeypatch, settings):
    repository = DocumentRepository(Database(settings.database_path))

    def runner(path, llm, active_settings):
        return PipelineResult(
            analysis="Анализ",
            summary="Резюме",
            fact_check=FactCheckResult(
                verification_summary="Проверено",
                neuroslop={"probability": 0.1, "explanation": "Похоже на авторский текст"},
            ),
            final="Итог",
            token_usage=TokenUsage(),
        )

    service = AnalysisService(repository, settings, runner=runner, llm_factory=FakeLLM)
    monkeypatch.setattr("multi_agent_docs.main.create_analysis_service", lambda: service)

    with TestClient(app) as client:
        response = client.post(
            "/analyze",
            files={"file": ("document.txt", "Тестовый документ", "text/plain")},
        )
        assert response.status_code == 202
        document_id = response.json()["id"]
        deadline = time.time() + 2
        while time.time() < deadline:
            detail = client.get(f"/documents/{document_id}")
            if detail.json()["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)
        assert detail.status_code == 200
        assert detail.json()["status"] == "completed"
        assert detail.json()["neuroslop"]["probability"] == 0.1
        history = client.get("/documents?limit=50&offset=0")
        assert history.status_code == 200
        assert history.json()["total"] == 1
        assert client.get("/documents/99999").status_code == 404
        assert client.get("/health").json() == {"status": "ok"}
        assert "/analyze" in client.get("/openapi.json").json()["paths"]


def test_api_rejects_bad_uploads(monkeypatch, settings):
    service = AnalysisService(
        DocumentRepository(Database(settings.database_path)),
        settings,
        llm_factory=FakeLLM,
    )
    monkeypatch.setattr("multi_agent_docs.main.create_analysis_service", lambda: service)
    with TestClient(app) as client:
        unsupported = client.post(
            "/analyze", files={"file": ("image.png", b"data", "image/png")}
        )
        assert unsupported.status_code == 415
        empty = client.post(
            "/analyze", files={"file": ("empty.txt", b"", "text/plain")}
        )
        assert empty.status_code == 400


def test_api_enforces_upload_limit(monkeypatch, settings):
    settings = settings.__class__(
        **{**settings.__dict__, "max_upload_bytes": 3}
    )
    service = AnalysisService(
        DocumentRepository(Database(settings.database_path)),
        settings,
        llm_factory=FakeLLM,
    )
    monkeypatch.setattr("multi_agent_docs.main.create_analysis_service", lambda: service)
    with TestClient(app) as client:
        response = client.post(
            "/analyze", files={"file": ("large.txt", b"1234", "text/plain")}
        )
        assert response.status_code == 413
        assert response.json()["detail"]["code"] == "upload_too_large"
