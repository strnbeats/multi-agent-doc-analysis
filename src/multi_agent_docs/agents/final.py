import json


def final_agent(state):
    prompt = f"""
Сформируй итоговый результат анализа документа.

АНАЛИЗ:
{state["analysis"]}

КРАТКОЕ СОДЕРЖАНИЕ:
{state["summary"]}

ПРОВЕРКА:
{json.dumps(state["fact_check"], ensure_ascii=False)}

Включи краткое содержание, основные идеи, результат проверки, сомнительные
утверждения и общий вывод. Не добавляй внешнюю информацию.
"""
    answer = state["llm"].ask(prompt)
    state["token_usage"].add("Final", answer.usage)
    return {"final": answer.content, "token_usage": state["token_usage"]}
