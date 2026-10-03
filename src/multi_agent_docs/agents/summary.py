from ..llm.client import ask_llm


def summary(state):
    prompt = f"""
Сделай краткое содержание анализа документа.

Анализ:
{state["analysis"]}

Сформулируй содержание в 2-4 предложениях.
"""

    summary_text = ask_llm(prompt)

    return {
        "summary": summary_text
    }