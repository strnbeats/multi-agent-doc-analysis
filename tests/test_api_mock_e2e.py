import time

import pytest
from fastapi.testclient import TestClient

from multi_agent_docs.bootstrap import create_analysis_service
from multi_agent_docs.database.db import Database
from multi_agent_docs.database.repository import DocumentRepository
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
    expected_metadata = {"file_type": "txt", "size_bytes": len("Полный тест API".encode("utf-8"))}

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
        assert detail["filename"] == "document.txt"
        assert detail["metadata"] == expected_metadata

        history = client.get("/documents", params={"limit": 10, "offset": 0})
        assert history.status_code == 200
        assert history.json()["total"] == 1
        assert history.json()["items"][0]["status"] == "completed"

    assert not list(settings.upload_dir.glob("analysis-*"))
    reopened_repository = DocumentRepository(Database(settings.database_path))
    stored = reopened_repository.get_by_id(accepted.json()["id"])
    assert stored.result["metadata"] == expected_metadata


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


@pytest.mark.parametrize(
    ("filename", "content_type", "file_type"),
    [
        ("report.DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
        ("report.docx", "application/zip", "docx"),
        ("page.HTM", "text/html; charset=utf-8", "html"),
        ("notes.md", "text/markdown", "md"),
        ("notes.MARKDOWN", "text/plain", "md"),
        ("export.csv", "text/csv; charset=utf-8", "csv"),
        ("export.CSV", "application/vnd.ms-excel", "csv"),
    ],
)
def test_api_analyzes_additional_formats(
    monkeypatch, settings, docx_payload, filename, content_type, file_type
):
    payloads = {
        "docx": docx_payload,
        "html": "<h1>Статья</h1><p>Содержательный текст статьи.</p>".encode("utf-8"),
        "md": "# Заметка\n\nСодержательный **текст** заметки.".encode("utf-8"),
        "csv": "\ufeffТовар;Цена\r\nКнига;350\r\n".encode("utf-8"),
    }
    payload = payloads[file_type]
    service = create_analysis_service(settings)
    monkeypatch.setattr("multi_agent_docs.main.create_analysis_service", lambda: service)
    with TestClient(app) as client:
        accepted = client.post("/analyze", files={"file": (filename, payload, content_type)})
        assert accepted.status_code == 202, accepted.text
        detail = _wait_for_terminal_state(client, accepted.json()["id"])
        assert detail["status"] == "completed", detail
        assert detail["filename"] == filename
        assert detail["metadata"] == {"file_type": file_type, "size_bytes": len(payload)}
        assert detail["results"]["analysis"].startswith("Mock-анализ")
        assert detail["token_usage"]["total_tokens"] > 0
    assert not list(settings.upload_dir.glob("analysis-*"))
    stored = DocumentRepository(Database(settings.database_path)).get_by_id(accepted.json()["id"])
    assert stored.result["metadata"] == detail["metadata"]


@pytest.mark.parametrize(
    ("filename", "payload", "content_type", "error_code"),
    [
        ("broken.docx", b"not a word document", "application/octet-stream", "corrupt_document"),
        ("empty.html", b"<script>hidden()</script>", "text/html", "empty_document"),
        ("empty.md", b"---\n", "text/markdown", "empty_document"),
        ("empty.csv", b'"",""\n', "text/csv", "empty_document"),
        ("broken.csv", b'Name,Value\n"unclosed', "text/csv", "corrupt_document"),
        ("broken.md", b"\x00binary", "text/plain", "corrupt_document"),
    ],
)
def test_api_rejects_invalid_additional_formats(
    monkeypatch, settings, filename, payload, content_type, error_code
):
    service = create_analysis_service(settings)
    monkeypatch.setattr("multi_agent_docs.main.create_analysis_service", lambda: service)
    with TestClient(app) as client:
        response = client.post("/analyze", files={"file": (filename, payload, content_type)})
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == error_code
        assert client.get("/documents").json()["total"] == 0
        assert not list(settings.upload_dir.glob("analysis-*"))


def test_api_rejects_oversized_unpacked_docx(monkeypatch, settings, docx_payload):
    service = create_analysis_service(settings)
    monkeypatch.setattr("multi_agent_docs.main.create_analysis_service", lambda: service)
    monkeypatch.setattr("multi_agent_docs.ingestion.additional_formats._MAX_DOCX_UNPACKED_BYTES", 100)
    with TestClient(app) as client:
        response = client.post(
            "/analyze", files={"file": ("large.docx", docx_payload, "application/octet-stream")}
        )
        assert response.status_code == 413
        assert response.json()["detail"]["code"] == "document_too_large"


def test_openapi_describes_additional_file_types(monkeypatch, settings):
    service = create_analysis_service(settings)
    monkeypatch.setattr("multi_agent_docs.main.create_analysis_service", lambda: service)
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
    file_types = schema["components"]["schemas"]["DocumentMetadata"]["properties"]["file_type"]["enum"]
    assert set(file_types) == {"pdf", "txt", "docx", "html", "md", "csv"}
