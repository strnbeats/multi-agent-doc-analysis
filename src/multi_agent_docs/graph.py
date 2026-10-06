from typing import Any, Dict, TypedDict

from langgraph.graph import END, START, StateGraph

from .agents.analyzer import analyzer
from .agents.fact_checker import fact_checker
from .agents.final import final_agent
from .agents.summary import summary
from .llm.client import LLMClient
from .models import TokenUsage


class State(TypedDict):
    text: str
    analysis: str
    summary: str
    fact_check: Dict[str, Any]
    final: str
    llm: Any
    token_usage: TokenUsage


def _compile(nodes, edges):
    graph = StateGraph(State)
    for name, function in nodes:
        graph.add_node(name, function)
    graph.add_edge(START, nodes[0][0])
    for source, target in edges:
        graph.add_edge(source, target)
    graph.add_edge(nodes[-1][0], END)
    return graph.compile()


app = _compile(
    [("analyzer", analyzer), ("summary", summary), ("fact_checker", fact_checker), ("final", final_agent)],
    [("analyzer", "summary"), ("summary", "fact_checker"), ("fact_checker", "final")],
)

chunk_app = _compile(
    [("analyzer", analyzer), ("fact_checker", fact_checker)],
    [("analyzer", "fact_checker")],
)

synthesis_app = _compile(
    [("summary", summary), ("final", final_agent)],
    [("summary", "final")],
)
