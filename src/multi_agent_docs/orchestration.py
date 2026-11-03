"""Управление обработкой документа: выбор пути, цикл по чанкам и сведение."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .errors import PipelineError
from .models import DocumentMetadata, FactCheckResult, TokenUsage


class DocumentChunk(TypedDict):
    chunk_id: str
    text: str
    token_count: int


class ChunkResult(TypedDict):
    chunk_id: str
    token_count: int
    analysis: str
    fact_check: Dict[str, Any]


class WorkflowState(TypedDict):
    text: str
    metadata: DocumentMetadata
    llm: Any
    chunks: list[DocumentChunk]
    chunk_index: int
    chunk_results: list[ChunkResult]
    analysis: str
    summary: str
    fact_check: Dict[str, Any]
    final: str
    final_review: Optional[Dict[str, Any]]
    token_usage: TokenUsage


def prepare_document(state: WorkflowState):
    """Начать новый проход и проверить подготовленные исходные фрагменты."""
    if not state["text"].strip():
        raise PipelineError("Документ не содержит текста")
    if not state["chunks"] or any(
        not chunk["text"].strip() for chunk in state["chunks"]
    ):
        raise PipelineError("Не удалось подготовить фрагменты документа")

    return {
        "chunk_index": 0,
        "chunk_results": [],
        "analysis": "",
        "summary": "",
        "fact_check": {},
        "final": "",
        "final_review": None,
        "token_usage": TokenUsage(),
    }


def choose_document_path(state: WorkflowState):
    """Для одного фрагмента использовать полный исходный текст."""
    return "single" if len(state["chunks"]) == 1 else "multiple"


def choose_next_chunk(state: WorkflowState):
    """Индекс увеличивается после обработки каждого фрагмента."""
    if state["chunk_index"] < len(state["chunks"]):
        return "next"
    return "reduce"


def _agent_state(text: str, state: WorkflowState, usage: TokenUsage):
    """Передать подграфу только его входные поля и отдельный счётчик."""
    return {
        "text": text,
        "metadata": state["metadata"],
        "analysis": "",
        "summary": "",
        "fact_check": {},
        "final": "",
        "llm": state["llm"],
        "token_usage": usage,
    }


def _result_fields(result):
    """Не переносить внутреннее состояние подграфа в управляющий граф."""
    return {
        "analysis": result["analysis"],
        "summary": result["summary"],
        "fact_check": result["fact_check"],
        "final": result["final"],
        "final_review": result.get("final_review"),
        "token_usage": result["token_usage"],
    }


def _merge_usage(target: TokenUsage, source: TokenUsage) -> None:
    for agent, usage in source.by_agent.items():
        target.add(agent, usage)


def _reduce_texts(
    values: Iterable[str],
    instruction: str,
    llm: Any,
    usage: TokenUsage,
    agent_name: str,
) -> str:
    """Иерархически свести результаты группами, как в прежнем runner."""
    current = [value for value in values if value.strip()]
    if not current:
        return ""
    while len(current) > 1:
        reduced: list[str] = []
        for index in range(0, len(current), 6):
            group = current[index : index + 6]
            answer = llm.ask(
                f"{instruction}\n\n" + "\n\n--- ФРАГМЕНТ ---\n\n".join(group)
            )
            usage.add(agent_name, answer.usage)
            reduced.append(answer.content)
        current = reduced
    return current[0]


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def reduce_results(state: WorkflowState):
    """Объединить анализы и проверки после обработки всех фрагментов."""
    partials = state["chunk_results"]
    if len(partials) != len(state["chunks"]):
        raise PipelineError("Обработаны не все фрагменты документа")

    checks = [
        (FactCheckResult.model_validate(item["fact_check"]), item["token_count"])
        for item in partials
    ]
    usage = state["token_usage"].model_copy(deep=True)
    llm = state["llm"]

    analysis = _reduce_texts(
        (item["analysis"] for item in partials),
        "Объедини анализы частей одного документа. Удали повторы, сохрани важные факты и не добавляй внешнюю информацию.",
        llm,
        usage,
        "Analysis Reducer",
    )
    verification = _reduce_texts(
        (item.verification_summary for item, _ in checks),
        "Сведи результаты внутренней проверки частей документа в одно краткое заключение.",
        llm,
        usage,
        "Fact Check Reducer",
    )
    explanation = _reduce_texts(
        (item.neuroslop.explanation for item, _ in checks),
        "Объедини объяснения эвристической оценки нейрослопа для частей исходного документа. Не утверждай авторство текста как доказанный факт.",
        llm,
        usage,
        "Fact Check Reducer",
    )
    weighted_probability = sum(
        item.neuroslop.probability * tokens for item, tokens in checks
    ) / max(sum(tokens for _, tokens in checks), 1)

    fact_check = FactCheckResult(
        verification_summary=verification,
        doubtful_claims=_unique(
            claim for item, _ in checks for claim in item.doubtful_claims
        ),
        contradictions=_unique(
            claim for item, _ in checks for claim in item.contradictions
        ),
        neuroslop={
            "probability": min(max(weighted_probability, 0.0), 1.0),
            "explanation": explanation,
        },
    )
    return {
        "analysis": analysis,
        "fact_check": fact_check.model_dump(),
        "token_usage": usage,
    }


def build_document_graph(single_graph, chunk_graph, synthesis_graph):
    """Собрать управляющий граф из существующих специализированных графов."""

    def run_single_document(state: WorkflowState):
        # Проверка короткого документа получает исходник без обрезки и strip().
        result = single_graph.invoke(
            _agent_state(state["text"], state, TokenUsage())
        )
        return _result_fields(result)

    def process_chunk(state: WorkflowState):
        index = state["chunk_index"]
        if not 0 <= index < len(state["chunks"]):
            raise PipelineError("Некорректный индекс фрагмента документа")
        chunk = state["chunks"][index]
        partial = chunk_graph.invoke(
            _agent_state(chunk["text"], state, TokenUsage())
        )
        checked = FactCheckResult.model_validate(partial["fact_check"])

        # Агенты меняют свой счётчик; общий расход сливаем ровно один раз.
        usage = state["token_usage"].model_copy(deep=True)
        _merge_usage(usage, partial["token_usage"])
        item: ChunkResult = {
            "chunk_id": chunk["chunk_id"],
            "token_count": chunk["token_count"],
            "analysis": partial["analysis"],
            "fact_check": checked.model_dump(),
        }
        return {
            "chunk_index": index + 1,
            "chunk_results": [*state["chunk_results"], item],
            "token_usage": usage,
        }

    def synthesize_document(state: WorkflowState):
        synthesis_state = _agent_state(
            "", state, state["token_usage"].model_copy(deep=True)
        )
        synthesis_state["analysis"] = state["analysis"]
        synthesis_state["fact_check"] = state["fact_check"]
        result = synthesis_graph.invoke(synthesis_state)
        # Для длинного документа отдельная проверка final ещё не реализована.
        # Проверку по сжатому анализу нельзя выдавать за проверку по исходнику.
        return _result_fields(result)

    builder = StateGraph(WorkflowState)
    builder.add_node("prepare_document", prepare_document)
    builder.add_node("single_document", run_single_document)
    builder.add_node("process_chunk", process_chunk)
    builder.add_node("reduce_results", reduce_results)
    builder.add_node("synthesis", synthesize_document)

    builder.add_edge(START, "prepare_document")
    builder.add_conditional_edges(
        "prepare_document",
        choose_document_path,
        {"single": "single_document", "multiple": "process_chunk"},
    )
    builder.add_edge("single_document", END)
    builder.add_conditional_edges(
        "process_chunk",
        choose_next_chunk,
        {"next": "process_chunk", "reduce": "reduce_results"},
    )
    builder.add_edge("reduce_results", "synthesis")
    builder.add_edge("synthesis", END)
    return builder.compile()
