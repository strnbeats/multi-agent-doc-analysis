import json

from ..models import LLMAnswer, TokenCount


class MockLLMClient:
    """Детерминированная локальная замена GigaChat для тестового API."""

    def count_tokens(self, text: str) -> int:
        """Приблизительно посчитать токены без сетевого запроса."""
        return max(1, len(text.split()))

    def ask(self, prompt: str) -> LLMAnswer:
        """Вернуть предсказуемый ответ подходящего для агента формата."""
        usage = TokenCount(input_tokens=20, output_tokens=10, total_tokens=30)
        if "Верни только JSON" in prompt or "Исправь ответ" in prompt:
            content = json.dumps(
                {
                    "verification_summary": "Mock-проверка завершена",
                    "doubtful_claims": [],
                    "contradictions": [],
                    "neuroslop": {
                        "probability": 0.15,
                        "explanation": "Тестовая эвристическая оценка",
                    },
                },
                ensure_ascii=False,
            )
        elif "итоговый результат" in prompt.lower():
            content = "Итоговый mock-результат анализа."
        elif "краткое содержание" in prompt.lower():
            content = "Краткое mock-содержание документа."
        elif "объедини" in prompt.lower() or "сведи" in prompt.lower():
            content = "Объединённый mock-результат."
        else:
            content = "Mock-анализ документа без обращения к GigaChat."
        return LLMAnswer(content=content, usage=usage)
