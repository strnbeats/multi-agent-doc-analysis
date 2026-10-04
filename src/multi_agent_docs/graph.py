from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from .llm import client

from .agents.analyzer import analyzer
from .agents.summary import summary
from .ingestion.loader import load_document
from .agents.fact_checker import fact_checker
from .agents.final import final_agent


class State(TypedDict):
    text: str
    analysis: str
    summary: str
    facts: str
    final: str


graph = StateGraph(State)

graph.add_node("analyzer", analyzer)
graph.add_node("summary", summary)
graph.add_node("fact_checker", fact_checker)
graph.add_node("final", final_agent)

graph.add_edge(START, "analyzer")
graph.add_edge("analyzer", "summary")
graph.add_edge("summary", "fact_checker")
graph.add_edge("fact_checker", "final")
graph.add_edge("final", END)

app = graph.compile()


if __name__ == "__main__":
    file_path = "data/raw/load.pdf"

    text = load_document(file_path)

    initial_state = {
        "text": text,
        "analysis": "",
        "summary": "",
        "facts": "",
        "final": ""
    }

    result = app.invoke(initial_state)

    print("\n=== АНАЛИЗ ===")
    print(result["analysis"])

    print("\n=== КРАТКОЕ СОДЕРЖАНИЕ ===")
    print(result["summary"])

    print("\n=== ПРОВЕРКА ФАКТОВ ===")
    print(result["facts"])

    print("\n=== ФИНАЛЬНЫЙ РЕЗУЛЬТАТ ===")
    print(result["final"])
    print("\n==============================")
    print(f"TOTAL INPUT TOKENS: {client.total_input_tokens}")
    print(f"TOTAL OUTPUT TOKENS: {client.total_output_tokens}")
    print(f"TOTAL TOKENS: {client.total_tokens}")
    print("==============================")