from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from .agents.analyzer import analyzer
from .agents.summary import summary
from .agents.fact_checker import fact_checker
from .agents.quality_gate import quality_gate
from .agents.final import final_agent


class State(TypedDict):
    text: str
    analysis: str
    summary: str
    facts: str
    final: str
    quality_ok: bool
    quality_feedback: str
    retry_fact_checker: bool
    revision_count: int


def route_after_quality_gate(state: State) -> str:
    if state["retry_fact_checker"]:
        return "fact_checker"

    return "final"


graph = StateGraph(State)

graph.add_node("analyzer", analyzer)
graph.add_node("summary", summary)
graph.add_node("fact_checker", fact_checker)
graph.add_node("quality_gate", quality_gate)
graph.add_node("final", final_agent)

graph.add_edge(START, "analyzer")
graph.add_edge("analyzer", "summary")
graph.add_edge("summary", "fact_checker")
graph.add_edge("fact_checker", "quality_gate")

graph.add_conditional_edges(
    "quality_gate",
    route_after_quality_gate,
    {
        "fact_checker": "fact_checker",
        "final": "final",
    },
)

graph.add_edge("final", END)

app = graph.compile()