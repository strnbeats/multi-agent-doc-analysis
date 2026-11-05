from dataclasses import replace
from pathlib import Path
import time
import json
import pytest

from fastapi.testclient import TestClient

from multi_agent_docs.api_schemas import AnalysisResults
from multi_agent_docs.bootstrap import create_analysis_service
from multi_agent_docs.database.db import Database
from multi_agent_docs.database.repository import DocumentRepository
from multi_agent_docs.llm.mock_client import MockLLMClient
from multi_agent_docs.main import app
from multi_agent_docs.runner import run_document


def test_short_pipeline_returns_final_review(tmp_path: Path, settings):
    path = tmp_path / "document.txt"
    path.write_text("Строительство дома занимает 30 дней.", encoding="utf-8")

    result = run_document(str(path), MockLLMClient(), settings)

    assert result.final_review is not None
    assert result.final_review.verification_summary == "Mock-проверка завершена"
    assert result.final_review.doubtful_claims == []
    assert result.final_review.contradictions == []
    assert result.final_review.status == "no_flags"


def test_multi_chunk_review_is_explicitly_absent(tmp_path: Path, settings):
    path = tmp_path / "large.txt"
    path.write_text(
        "\n\n".join(["один два три четыре"] * 8),
        encoding="utf-8",
    )
    chunk_settings = replace(settings, chunk_target_tokens=8, chunk_overlap_tokens=1)

    result = run_document(str(path), MockLLMClient(), chunk_settings)

    assert result.final_review is None


def test_legacy_result_without_review_is_accepted():
    legacy = {
        "analysis": "Анализ",
        "summary": "Сводка",
        "fact_check": {
            "verification_summary": "Проверено",
            "doubtful_claims": [],
            "contradictions": [],
            "neuroslop": {
                "probability": 0.15,
                "explanation": "Эвристическая оценка",
            },
        },
        "final": "Итог",
    }

    result = AnalysisResults.model_validate(legacy)

    assert result.final_review is None


def test_final_review_survives_storage_and_api(monkeypatch, settings):
    service = create_analysis_service(settings)
    monkeypatch.setattr(
        "multi_agent_docs.main.create_analysis_service",
        lambda: service,
    )

    with TestClient(app) as client:
        accepted = client.post(
            "/analyze",
            files={
                "file": (
                    "document.txt",
                    "Строительство дома занимает 30 дней.".encode("utf-8"),
                    "text/plain",
                )
            },
        )
        assert accepted.status_code == 202
        document_id = accepted.json()["id"]

        deadline = time.monotonic() + 3
        while True:
            response = client.get(f"/documents/{document_id}")
            assert response.status_code == 200
            detail = response.json()
            if detail["status"] in {"completed", "failed"}:
                break
            if time.monotonic() >= deadline:
                raise AssertionError("Mock-анализ не завершился вовремя")
            time.sleep(0.01)

        assert detail["status"] == "completed", detail
        review = detail["results"]["final_review"]
        assert review["verification_summary"] == "Mock-проверка завершена"
        assert review["doubtful_claims"] == []
        assert review["contradictions"] == []

    repository = DocumentRepository(Database(settings.database_path))
    stored = repository.get_by_id(document_id)
    assert stored.result["final_review"] == review

@pytest.mark.parametrize(
    "field",
    ["doubtful_claims", "contradictions"],
)
def test_report_with_flags_needs_review(tmp_path: Path, settings, field):
    class FlaggedLLM(MockLLMClient):
        def ask(self, prompt, *, system_prompt=""):
            answer = super().ask(prompt, system_prompt=system_prompt)

            if "Верни только JSON" in prompt:
                payload = json.loads(answer.content)
                payload[field] = ["Тестовое замечание"]
                answer.content = json.dumps(payload, ensure_ascii=False)

            return answer

    path = tmp_path / "document.txt"
    path.write_text("Строительство занимает 30 дней.", encoding="utf-8")

    result = run_document(str(path), FlaggedLLM(), settings)

    assert result.final_review is not None
    assert result.final_review.status == "needs_review"
    assert getattr(result.final_review, field) == ["Тестовое замечание"]


@pytest.mark.parametrize(
    "initial_has_flags, expected_status",
    [(False, "needs_review"), (True, "no_flags")],
)
def test_final_review_is_independent_of_initial_check(
    tmp_path: Path, settings, initial_has_flags, expected_status
):
    class DifferentChecksLLM(MockLLMClient):
        def __init__(self):
            self.check_calls = 0

        def ask(self, prompt, *, system_prompt=""):
            answer = super().ask(prompt, system_prompt=system_prompt)
            if "Верни только JSON" in prompt:
                self.check_calls += 1
                assert self.check_calls <= 2
                initial = self.check_calls == 1
                has_flags = initial_has_flags if initial else not initial_has_flags
                label = "Первичная" if initial else "Итоговая"
                payload = json.loads(answer.content)
                payload["verification_summary"] = f"{label} проверка"
                payload["doubtful_claims"] = [f"{label}: сомнение"] if has_flags else []
                payload["contradictions"] = [f"{label}: противоречие"] if has_flags else []
                answer.content = json.dumps(payload, ensure_ascii=False)
            return answer

    path = tmp_path / "document.txt"
    path.write_text("Строительство дома занимает 30 дней.", encoding="utf-8")
    llm = DifferentChecksLLM()

    result = run_document(str(path), llm, settings)

    assert llm.check_calls == 2
    assert result.final_review is not None
    assert result.final_review.status == expected_status
    assert result.fact_check.verification_summary == "Первичная проверка"
    assert result.final_review.verification_summary == "Итоговая проверка"
    assert result.fact_check.doubtful_claims == (
        ["Первичная: сомнение"] if initial_has_flags else []
    )
    assert result.fact_check.contradictions == (
        ["Первичная: противоречие"] if initial_has_flags else []
    )
    assert result.final_review.doubtful_claims == (
        [] if initial_has_flags else ["Итоговая: сомнение"]
    )
    assert result.final_review.contradictions == (
        [] if initial_has_flags else ["Итоговая: противоречие"]
    )
