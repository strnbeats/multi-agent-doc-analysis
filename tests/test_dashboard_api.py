import json

import httpx
import pytest
from fastapi.testclient import TestClient

from multi_agent_docs.bootstrap import create_analysis_service
from multi_agent_docs.dashboard import refresh_document, watch_analysis
from multi_agent_docs.main import app


TIMESTAMP = "2026-10-28T00:00:00Z"


def detail(status):
    result = {
        "id": 42, "filename": "document.txt", "status": status,
        "created_at": TIMESTAMP, "updated_at": TIMESTAMP,
        "token_usage": {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30,
                        "by_agent": {"Analyzer": {"total_tokens": 30}}},
    }
    if status == "completed":
        result["results"] = {
            "analysis": "Анализ", "summary": "Краткое содержание", "final": "Итог",
            "fact_check": {"verification_summary": "Проверено", "doubtful_claims": ["Неизвестно"],
                           "contradictions": [], "neuroslop": {"probability": .2, "explanation": "Эвристика"}},
        }
    if status == "failed":
        result.update(error_code="gigachat_error", error_message="Ошибка модели")
    return result


@pytest.mark.parametrize("terminal", ["completed", "failed"])
def test_dashboard_submits_once_and_polls_states(tmp_path, terminal):
    path = tmp_path / "document.txt"
    path.write_text("DOCUMENT_PAYLOAD", encoding="utf-8")
    calls = []
    states = iter(["running", terminal])

    def handle(request):
        calls.append((request.method, request.url.path))
        if request.method == "POST":
            assert request.url.path == "/analyze"
            body = request.read()
            assert b'DOCUMENT_PAYLOAD' in body and b'filename="document.txt"' in body
            return httpx.Response(202, json={"id": 42, "filename": path.name,
                                          "created_at": TIMESTAMP, "status": "queued"})
        assert request.url.path == "/documents/42"
        return httpx.Response(200, json=detail(next(states)))

    views = list(watch_analysis(str(path), "http://api.test", poll_interval=0,
                                transport=httpx.MockTransport(handle)))
    assert [view.status.split(" — ")[0] for view in views] == ["queued", "running", terminal]
    assert all(view.document_id == 42 for view in views)
    assert calls == [("POST", "/analyze"), ("GET", "/documents/42"), ("GET", "/documents/42")]
    if terminal == "completed":
        assert views[-1].final == "Итог"
        assert json.loads(views[-1].fact_check)["doubtful_claims"] == ["Неизвестно"]
        assert views[-1].token_usage["total_tokens"] == 30
        assert views[-1].by_agent["Analyzer"]["total_tokens"] == 30
    else:
        assert "Ошибка модели" in views[-1].status
        assert views[-1].final == ""


def test_timeout_retains_id_and_refresh_does_not_resubmit(tmp_path):
    path = tmp_path / "document.txt"
    path.write_text("document")
    posts = []

    def handle(request):
        if request.method == "POST":
            posts.append(request)
            return httpx.Response(202, json={"id": 42, "filename": path.name,
                                          "created_at": TIMESTAMP, "status": "queued"})
        return httpx.Response(200, json=detail("running"))

    views = list(watch_analysis(str(path), "http://api.test", max_wait=0,
                                transport=httpx.MockTransport(handle)))
    assert views[-1].document_id == 42
    assert "Ожидание остановлено" in views[-1].status
    refreshed = refresh_document(42, "http://api.test", transport=httpx.MockTransport(handle))
    assert refreshed.status.startswith("running")
    assert len(posts) == 1


def test_poll_connection_error_keeps_accepted_id(tmp_path):
    path = tmp_path / "document.txt"
    path.write_text("document")

    def handle(request):
        if request.method == "POST":
            return httpx.Response(202, json={"id": 42, "filename": path.name,
                                          "created_at": TIMESTAMP, "status": "queued"})
        raise httpx.ConnectError("private transport details", request=request)

    views = list(watch_analysis(str(path), "http://api.test", transport=httpx.MockTransport(handle)))
    assert views[-1].document_id == 42
    assert "повторная загрузка" in views[-1].status
    assert "private transport" not in views[-1].status


@pytest.mark.parametrize("response", [
    httpx.Response(415, json={"detail": {"code": "unsupported_format", "message": "Неподдерживаемый формат"}}),
    httpx.Response(200, text="not json"),
    httpx.Response(200, json={"unexpected": True}),
    httpx.Response(502, text="proxy error"),
])
def test_refresh_handles_http_and_contract_errors(response):
    view = refresh_document(42, "http://api.test", transport=httpx.MockTransport(lambda _: response))
    assert view.document_id == 42
    assert view.final == ""
    if response.status_code == 415:
        assert view.status == "Неподдерживаемый формат"
    elif response.status_code == 502:
        assert "502" in view.status
    else:
        assert "несовместимого формата" in view.status


def test_no_upload_and_invalid_id_do_not_contact_api():
    def unexpected(request):
        pytest.fail("Network should not be used")

    transport = httpx.MockTransport(unexpected)
    assert "выберите" in list(watch_analysis(None, "http://api.test", transport=transport))[0].status
    assert refresh_document(None, "http://api.test", transport=transport).document_id is None
    assert refresh_document(1.5, "http://api.test", transport=transport).document_id is None


def test_dashboard_uses_real_backend_pipeline(monkeypatch, settings, tmp_path):
    service = create_analysis_service(settings)
    monkeypatch.setattr("multi_agent_docs.main.create_analysis_service", lambda: service)
    path = tmp_path / "source.txt"
    path.write_text("Документ через UI и общий backend.", encoding="utf-8")
    with TestClient(app) as backend:
        def bridge(request):
            response = backend.request(request.method, request.url.path,
                                       content=request.read(), headers=dict(request.headers))
            return httpx.Response(response.status_code, content=response.content,
                                  headers=dict(response.headers))

        views = list(watch_analysis(str(path), "http://api.test", poll_interval=.01,
                                    transport=httpx.MockTransport(bridge)))
        assert views[-1].status.startswith("completed"), views[-1]
        assert views[-1].analysis.startswith("Mock-анализ")
        assert views[-1].token_usage["total_tokens"] == 120
        assert backend.get("/documents").json()["total"] == 1
        assert not list(settings.upload_dir.glob("analysis-*"))
