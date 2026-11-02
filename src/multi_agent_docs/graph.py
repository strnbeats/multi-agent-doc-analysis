from typing import Any, Dict, TypedDict

from langgraph.graph import END, START, StateGraph

from .agents.analyzer import analyzer
from .agents.fact_checker import fact_checker
from .agents.final import final_agent
from .agents.summary import summary
from .llm.client import LLMClient
from .models import DocumentMetadata, TokenUsage
from .errors import PipelineError


class SourceChunk(TypedDict):
    chunk_id: str
    text: str

class State(TypedDict):
    text: str
    metadata: DocumentMetadata
    analysis: str
    summary: str
    fact_check: Dict[str, Any]
    final: str
    llm: Any
    token_usage: TokenUsage
    source_chunks: list[SourceChunk]



def prepare_sources(state: State):
    text = state["text"]

    if not text.strip():
        raise PipelineError("Документ не содержит текста")

    return {
        "source_chunks": [
            {
                "chunk_id": "chunk_0001",
                "text": text
            }
        ]
    }


def _compile(nodes, edges):
    """Собрать линейный LangGraph из узлов и переходов."""
    graph = StateGraph(State)
    for name, function in nodes:
        graph.add_node(name, function)
    graph.add_edge(START, nodes[0][0])
    for source, target in edges:
        graph.add_edge(source, target)
    graph.add_edge(nodes[-1][0], END)
    return graph.compile()


builder = StateGraph(State)

builder.add_node("prepare_sources", prepare_sources)
builder.add_node("analyzer", analyzer)
builder.add_node("summary", summary)
builder.add_node("fact_checker", fact_checker)
builder.add_node("final", final_agent)

builder.add_edge(START, "prepare_sources")
builder.add_edge("prepare_sources", "analyzer")
builder.add_edge("analyzer", "summary")
builder.add_edge("summary", "fact_checker")
builder.add_edge("fact_checker", "final")
builder.add_edge("final", END)

app = builder.compile()

chunk_app = _compile(
    [("analyzer", analyzer), ("fact_checker", fact_checker)],
    [("analyzer", "fact_checker")],
)

synthesis_app = _compile(
    [("summary", summary), ("final", final_agent)],
    [("summary", "final")],
)
