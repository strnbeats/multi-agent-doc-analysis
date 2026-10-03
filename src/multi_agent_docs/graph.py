from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from llm.client import ask_llm

from ingestion.loader import load_pdf

class State(TypedDict):
    text: str
    analysis: str
    summary: str


def analyzer(state: State):
    print("ANALYZER получил текст:")
    print(state["text"])

    prompt = f"""
Проанализируй следующий текст документа.

Текст:
{state["text"]}

Дай краткий анализ содержания.
"""

    analysis = ask_llm(prompt)

    return {
        "analysis": analysis
    }


def summary(state: State):
    print("SUMMARY получил анализ:")
    print(state["analysis"])

    prompt = f"""
Сделай краткое содержание анализа документа.

Анализ:
{state["analysis"]}

Сформулируй краткое содержание в 2-4 предложениях.
"""

    summary_text = ask_llm(prompt)

    return {
        "summary": summary_text
    }


graph = StateGraph(State)

graph.add_node("analyzer", analyzer)
graph.add_node("summary", summary)

graph.add_edge(START, "analyzer")
graph.add_edge("analyzer", "summary")
graph.add_edge("summary", END)

app = graph.compile()


if __name__ == "__main__":
    text = load_pdf("data/raw/load.pdf")

    test_state = {
        "text": text,
        "analysis": "",
        "summary": ""
    }

    result = app.invoke(test_state)

    print("\nРезультат:")
    print(result)