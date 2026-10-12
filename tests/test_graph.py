
from unittest.mock import patch

from multi_agent_docs.graph import app


def test_full_graph():
    initial_state = {
        "text": "Компания открылась в 2020 году.",
        "analysis": "",
        "summary": "",
        "facts": "",
        "final": "",
    }

    with (
        patch(
            "multi_agent_docs.agents.analyzer.ask_llm",
            return_value="Анализ документа.",
        ),
        patch(
            "multi_agent_docs.agents.summary.ask_llm",
            return_value="Краткое содержание.",
        ),
        patch(
            "multi_agent_docs.agents.fact_checker.ask_llm",
            return_value="Проверка завершена.",
        ),
        patch(
            "multi_agent_docs.agents.final.ask_llm",
            return_value="Итоговый отчёт.",
        ),
    ):
        result = app.invoke(initial_state)

    assert result["analysis"] == "Анализ документа."
    assert result["summary"] == "Краткое содержание."
    assert result["facts"] == "Проверка завершена."
    assert result["final"] == "Итоговый отчёт."