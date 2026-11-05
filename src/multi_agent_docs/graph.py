from langgraph.graph import END, START, StateGraph

from .agent_contracts import (
    AgentState as State, FinalVerificationInput, FinalVerificationOutput,
    ReviewInput, ReviewOutput, SourceChunk, SourceInput, SourceOutput, agent_node,
)
from .agents.analyzer import analyzer
from .agents.fact_checker import fact_checker
from .agents.final import final_agent
from .agents.summary import summary
from .models import TokenUsage
from .errors import PipelineError


@agent_node("prepare_sources")
def prepare_sources(state: SourceInput) -> SourceOutput:
    """Положить весь входной текст в один элемент source_chunks.

    Этот узел не разбивает текст: разбиение выполняет ingestion.chunking.
    chunk_0001 — локальный идентификатор контейнера, без страниц, смещений,
    ссылок на исходный файл или проверяемых цитат.
    """
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

@agent_node("verify_final")
def verify_final(state: FinalVerificationInput) -> FinalVerificationOutput:
    review_state = dict(state)
    review_state["text"] = state["source_chunks"][0]["text"]
    review_state["analysis"] = state["final"]
    review_state["token_usage"] = TokenUsage()

    reviewed = fact_checker(review_state)

    usage = state["token_usage"]
    usage.add("Final Verification", reviewed["token_usage"])

    return {
        # Реализация проверки пока общая, но контракт итогового проверяющего
        # самостоятельный: оценка нейрослопа исходника в него не входит.
        "final_review": {
            "verification_summary": reviewed["fact_check"]["verification_summary"],
            "doubtful_claims": reviewed["fact_check"]["doubtful_claims"],
            "contradictions": reviewed["fact_check"]["contradictions"],
        },
        "token_usage": usage,
    }


def route_review(state: State):
    review = state["final_review"]

    if review["doubtful_claims"] or review["contradictions"]:
        return "needs_review"

    return "no_flags"


@agent_node("mark_no_flags")
def mark_no_flags(state: ReviewInput) -> ReviewOutput:
    review = dict(state["final_review"])
    review["status"] = "no_flags"

    return {"final_review": review}


@agent_node("mark_needs_review")
def mark_needs_review(state: ReviewInput) -> ReviewOutput:
    review = dict(state["final_review"])
    review["status"] = "needs_review"

    return {"final_review": review}


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
builder.add_node("verify_final", verify_final)
builder.add_node("mark_no_flags", mark_no_flags)
builder.add_node("mark_needs_review", mark_needs_review)

builder.add_edge(START, "prepare_sources")
builder.add_edge("prepare_sources", "analyzer")
builder.add_edge("analyzer", "summary")
builder.add_edge("summary", "fact_checker")
builder.add_edge("fact_checker", "final")
builder.add_edge("final", "verify_final")
builder.add_conditional_edges(
    "verify_final",
    route_review,
    {
        "no_flags": "mark_no_flags",
        "needs_review": "mark_needs_review",
    }
)
builder.add_edge("mark_no_flags", END)
builder.add_edge("mark_needs_review", END)

app = builder.compile()

chunk_app = _compile(
    [("analyzer", analyzer), ("fact_checker", fact_checker)],
    [("analyzer", "fact_checker")],
)

synthesis_app = _compile(
    [("summary", summary), ("final", final_agent)],
    [("summary", "final")],
)
