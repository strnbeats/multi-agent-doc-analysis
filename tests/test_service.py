import time
from pathlib import Path

from multi_agent_docs.database.db import Database
from multi_agent_docs.database.repository import DocumentRepository
from multi_agent_docs.models import FactCheckResult, PipelineResult, TokenCount, TokenUsage
from multi_agent_docs.services.analysis_service import AnalysisService
from multi_agent_docs.errors import LLMError

from conftest import FakeLLM


def _result() -> PipelineResult:
    usage = TokenUsage()
    usage.add("Analyzer", TokenCount(input_tokens=10, output_tokens=5, total_tokens=15))
    return PipelineResult(
        analysis="Анализ",
        summary="Резюме",
        fact_check=FactCheckResult(
            verification_summary="Проверено",
            doubtful_claims=[],
            contradictions=[],
            neuroslop={"probability": 0.2, "explanation": "Объяснение"},
        ),
        final="Итог",
        token_usage=usage,
    )


def test_service_processes_and_deletes_file(settings):
    repository = DocumentRepository(Database(settings.database_path))
    calls = []

    def runner(path, llm, active_settings):
        calls.append(path)
        return _result()

    service = AnalysisService(repository, settings, runner=runner, llm_factory=FakeLLM)
    service.initialize()
    path = settings.upload_dir / "analysis-test.txt"
    path.write_text("Документ", encoding="utf-8")
    record = service.submit(path, "document.txt")
    deadline = time.time() + 2
    while time.time() < deadline:
        stored = service.get_document(record.id)
        if stored and stored.status in {"completed", "failed"}:
            break
        time.sleep(0.01)
    service.shutdown()

    assert stored is not None
    assert stored.status == "completed"
    assert stored.neuroslop == 0.2
    assert calls
    assert not path.exists()


def test_service_persists_safe_failure(settings):
    repository = DocumentRepository(Database(settings.database_path))

    def failing_runner(path, llm, active_settings):
        raise LLMError()

    service = AnalysisService(
        repository, settings, runner=failing_runner, llm_factory=FakeLLM
    )
    service.initialize()
    path = settings.upload_dir / "analysis-failure.txt"
    path.write_text("Документ", encoding="utf-8")
    record = service.submit(path, "document.txt")
    deadline = time.time() + 2
    while time.time() < deadline:
        stored = service.get_document(record.id)
        if stored and stored.status == "failed":
            break
        time.sleep(0.01)
    service.shutdown()
    assert stored is not None
    assert stored.error_code == "gigachat_error"
    assert "traceback" not in (stored.error_message or "").lower()
    assert not path.exists()
