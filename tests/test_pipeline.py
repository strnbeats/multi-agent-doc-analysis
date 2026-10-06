from pathlib import Path
from dataclasses import replace

import pytest

from multi_agent_docs.errors import PipelineError
from multi_agent_docs.runner import run_document

from conftest import FakeLLM


def test_pipeline_returns_structured_result(tmp_path: Path, settings):
    path = tmp_path / "document.txt"
    path.write_text("Короткий содержательный документ.", encoding="utf-8")
    result = run_document(str(path), FakeLLM(), settings)
    assert result.fact_check.neuroslop.probability == 0.25
    assert result.token_usage.total_tokens == 60
    assert set(result.token_usage.by_agent) == {"Analyzer", "Summary", "Fact Checker", "Final"}


def test_fact_checker_retries_once_and_fails(tmp_path: Path, settings):
    path = tmp_path / "document.txt"
    path.write_text("Текст для проверки.", encoding="utf-8")
    with pytest.raises(PipelineError):
        run_document(str(path), FakeLLM(invalid_fact_checks=2), settings)


def test_fact_checker_repairs_json_once(tmp_path: Path, settings):
    path = tmp_path / "document.txt"
    path.write_text("Текст для проверки.", encoding="utf-8")
    result = run_document(str(path), FakeLLM(invalid_fact_checks=1), settings)
    assert result.fact_check.verification_summary == "Проверено"
    assert result.token_usage.by_agent["Fact Checker"].total_tokens == 30


def test_pipeline_reduces_multiple_chunks(tmp_path: Path, settings):
    path = tmp_path / "large.txt"
    path.write_text("\n\n".join(["один два три четыре" for _ in range(8)]), encoding="utf-8")
    chunk_settings = replace(settings, chunk_target_tokens=8, chunk_overlap_tokens=1)
    result = run_document(str(path), FakeLLM(), chunk_settings)
    assert result.analysis
    assert result.summary
    assert "Analysis Reducer" in result.token_usage.by_agent
    assert result.fact_check.neuroslop.probability == 0.25
