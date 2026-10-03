from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from .agents.analyzer import analyzer
from .agents.summary import summary
from .ingestion.loader import load_document


class State(TypedDict):
    text: str
    analysis: str
    summary: str


graph = StateGraph(State)

graph.add_node("analyzer", analyzer)
graph.add_node("summary", summary)

graph.add_edge(START, "analyzer")
graph.add_edge("analyzer", "summary")
graph.add_edge("summary", END)

app = graph.compile()


if __name__ == "__main__":
    file_path = "data/raw/load.pdf"

    text = load_document(file_path)

    initial_state = {
        "text": text,
        "analysis": "",
        "summary": ""
    }

    result = app.invoke(initial_state)

    print("\n=== АНАЛИЗ ===")
    print(result["analysis"])

    print("\n=== КРАТКОЕ СОДЕРЖАНИЕ ===")
    print(result["summary"])