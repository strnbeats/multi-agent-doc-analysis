from ..llm.client import ask_llm


def analyzer(state):
    prompt = f"""
Проанализируй следующий текст документа.

Текст:
{state["text"]}

Выдели:
1. Основную тему
2. Ключевые идеи
3. Важные факты
4. Краткий анализ содержания
"""

    analysis = ask_llm(prompt)

    return {
        "analysis": analysis
    }