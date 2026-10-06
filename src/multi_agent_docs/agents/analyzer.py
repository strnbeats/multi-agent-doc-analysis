def analyzer(state):
    """Построить содержательный анализ переданного фрагмента документа."""
    prompt = f"""
Проанализируй следующий текст документа. Работай только с предоставленным текстом.

Текст:
{state["text"]}

Выдели основную тему, ключевые идеи, важные факты и кратко оцени содержание.
Не добавляй сведения, которых нет в тексте.
"""
    answer = state["llm"].ask(prompt)
    state["token_usage"].add("Analyzer", answer.usage)
    return {"analysis": answer.content, "token_usage": state["token_usage"]}
