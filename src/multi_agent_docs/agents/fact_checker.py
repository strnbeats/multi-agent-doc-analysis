import json
from typing import Any, Dict

from pydantic import ValidationError

from ..errors import PipelineError
from ..models import FactCheckResult


def _json_payload(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("Ожидался JSON-объект")
    return value


def _parse_result(text: str) -> FactCheckResult:
    return FactCheckResult.model_validate(_json_payload(text))


def fact_checker(state):
    prompt = f"""
Проверь анализ относительно исходного текста и отдельно оцени вероятность того,
что ИСХОДНЫЙ ТЕКСТ является низкокачественным, шаблонным AI-контентом
(нейрослопом). Это эвристическая оценка, а не доказательство авторства.

ИСХОДНЫЙ ТЕКСТ:
{state["text"]}

АНАЛИЗ:
{state["analysis"]}

Верни только JSON без Markdown строго такой структуры:
{{
  "verification_summary": "краткий результат внутренней проверки",
  "doubtful_claims": ["сомнительные или неподтверждённые утверждения"],
  "contradictions": ["обнаруженные противоречия"],
  "neuroslop": {{
    "probability": 0.0,
    "explanation": "объяснение оценки исходного текста"
  }}
}}
probability должна быть числом от 0 до 1. Не используй внешние источники.
"""
    answer = state["llm"].ask(prompt)
    state["token_usage"].add("Fact Checker", answer.usage)

    try:
        result = _parse_result(answer.content)
    except (json.JSONDecodeError, ValidationError, ValueError):
        repair = state["llm"].ask(
            "Исправь ответ и верни только валидный JSON без Markdown со структурой: "
            "{\"verification_summary\": string, \"doubtful_claims\": string[], "
            "\"contradictions\": string[], \"neuroslop\": "
            "{\"probability\": number от 0 до 1, \"explanation\": string}}. "
            f"Не меняй смысл исходного ответа:\n\n{answer.content}"
        )
        state["token_usage"].add("Fact Checker", repair.usage)
        try:
            result = _parse_result(repair.content)
        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            raise PipelineError("Fact Checker вернул некорректный JSON") from error

    return {
        "fact_check": result.model_dump(),
        "token_usage": state["token_usage"],
    }
