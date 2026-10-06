def summary(state):
    prompt = f"""
Сделай краткое содержание анализа документа в 2–4 предложениях.

Анализ:
{state["analysis"]}
"""
    answer = state["llm"].ask(prompt)
    state["token_usage"].add("Summary", answer.usage)
    return {"summary": answer.content, "token_usage": state["token_usage"]}
