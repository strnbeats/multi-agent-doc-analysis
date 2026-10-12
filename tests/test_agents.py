from unittest.mock import patch

from multi_agent_docs.agents.analyzer import analyzer
from multi_agent_docs.agents.summary import summary
from multi_agent_docs.agents.fact_checker import fact_checker
from multi_agent_docs.agents.final import final_agent


def test_analyzer():
    state = {"text": "Компания открылась в 2020 году."}

    with patch(
        "multi_agent_docs.agents.analyzer.ask_llm",
        return_value="Тема: открытие компании.",
    ) as mock_llm:
        result = analyzer(state)

    assert result == {"analysis": "Тема: открытие компании."}
    mock_llm.assert_called_once()
    assert mock_llm.call_args.kwargs["user_content"].endswith(
        state["text"]
    )


def test_summary():
    state = {"analysis": "Компания открылась в 2020 году."}

    with patch(
        "multi_agent_docs.agents.summary.ask_llm",
        return_value="Компания открылась в 2020 году.",
    ):
        result = summary(state)

    assert "summary" in result
    assert result["summary"] == "Компания открылась в 2020 году."


def test_fact_checker():
    state = {
        "text": "Компания открылась в 2020 году.",
        "analysis": "Компания открылась в 2020 году.",
        "summary": "Компания открылась в 2020 году.",
    }

    with patch(
        "multi_agent_docs.agents.fact_checker.ask_llm",
        return_value="Утверждение подтверждено текстом.",
    ) as mock_llm:
        result = fact_checker(state)

    assert result == {"facts": "Утверждение подтверждено текстом."}
    assert "2020" in mock_llm.call_args.kwargs["user_content"]


def test_final_agent():
    state = {
        "analysis": "Тема: компания.",
        "summary": "Компания открылась в 2020 году.",
        "facts": "Утверждение подтверждено текстом.",
    }

    with patch(
        "multi_agent_docs.agents.final.ask_llm",
        return_value="Итоговый отчёт.",
    ) as mock_llm:
        result = final_agent(state)

    assert result == {"final": "Итоговый отчёт."}
    assert "РЕЗУЛЬТАТ ПРОВЕРКИ" in (
        mock_llm.call_args.kwargs["user_content"]
    )