from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    text: str
    analysis: str
    summary: str


def analyzer(state: State):
    print("Я получил текст:")
    print(state["text"])

    return {
        "analysis": "Анализ пока тестовый"
    }


graph = StateGraph(State)

graph.add_node("analyzer", analyzer)
graph.add_edge(START, "analyzer")
graph.add_edge("analyzer", END)

app = graph.compile()


if __name__ == "__main__":
    test_state = {
        "text": "Это тестовый текст документа.",
        "analysis": "",
        "summary": ""
    }

    result = app.invoke(test_state)

    print("\nРезультат:")
    print(result)