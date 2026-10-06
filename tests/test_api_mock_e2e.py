import time

from fastapi.testclient import TestClient

from multi_agent_docs.bootstrap import create_analysis_service
from multi_agent_docs.main import app


def _wait_for_terminal_state(client: TestClient, document_id: int) -> dict:
    """Дождаться завершения фонового mock-анализа."""
    deadline = time.time() + 3
    while time.time() < deadline:
        response = client.get(f"/documents/{document_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.01)
    raise AssertionError("Mock-анализ не завершился вовремя")


def test_full_api_pipeline_with_mock_agents(monkeypatch, settings):
    """Пройти HTTP → service → runner → LangGraph → mock LLM → SQLite."""
    service = create_analysis_service(settings)
    monkeypatch.setattr("multi_agent_docs.main.create_analysis_service", lambda: service)

    with TestClient(app) as client:
        accepted = client.post(
            "/analyze",
            files={"file": ("document.txt", "Полный тест API", "text/plain")},
        )
        assert accepted.status_code == 202
        assert accepted.json()["status"] == "queued"

        detail = _wait_for_terminal_state(client, accepted.json()["id"])
        assert detail["status"] == "completed"
        assert detail["results"]["analysis"].startswith("Mock-анализ")
        assert detail["results"]["summary"].startswith("Краткое mock")
        assert detail["results"]["final"].startswith("Итоговый mock")
        assert detail["neuroslop"]["probability"] == 0.15
        assert detail["token_usage"]["total_tokens"] == 120

        history = client.get("/documents", params={"limit": 10, "offset": 0})
        assert history.status_code == 200
        assert history.json()["total"] == 1
        assert history.json()["items"][0]["status"] == "completed"


def test_mock_api_validation_and_public_errors(monkeypatch, settings):
    """Проверить основные HTTP-ошибки без запуска внешней модели."""
    service = create_analysis_service(settings)
    monkeypatch.setattr("multi_agent_docs.main.create_analysis_service", lambda: service)

    with TestClient(app) as client:
        assert client.get("/documents/999999").status_code == 404
        assert client.get("/documents", params={"limit": 101}).status_code == 422
        bad_pdf = client.post(
            "/analyze",
            files={"file": ("broken.pdf", b"not-pdf", "application/pdf")},
        )
        assert bad_pdf.status_code == 400
        assert bad_pdf.json()["detail"]["code"] == "corrupt_document"
        wrong_type = client.post(
            "/analyze",
            files={"file": ("document.txt", b"text", "image/png")},
        )
        assert wrong_type.status_code == 415
        assert "traceback" not in wrong_type.text.lower()
