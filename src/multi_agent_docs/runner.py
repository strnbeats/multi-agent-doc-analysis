from __future__ import annotations

from typing import Dict, Iterable, List

from .config import Settings
from .graph import app, chunk_app, synthesis_app
from .ingestion.chunking import count_document_tokens, split_document
from .ingestion.loader import load_document
from .llm.client import LLMClient, get_default_client
from .models import FactCheckResult, PipelineResult, TokenUsage


def _state(text: str, llm: LLMClient, usage: TokenUsage) -> Dict:
    """Создать начальное состояние LangGraph для одного запуска."""
    return {
        "text": text,
        "analysis": "",
        "summary": "",
        "fact_check": {},
        "final": "",
        "llm": llm,
        "token_usage": usage,
    }


def _merge_usage(target: TokenUsage, source: TokenUsage) -> None:
    """Объединить статистику токенов нескольких графов."""
    for agent, usage in source.by_agent.items():
        target.add(agent, usage)


def _reduce_texts(
    values: Iterable[str],
    instruction: str,
    llm: LLMClient,
    usage: TokenUsage,
    agent_name: str,
) -> str:
    """Иерархически свести текстовые результаты группами до одного."""
    current = [value for value in values if value.strip()]
    if not current:
        return ""
    while len(current) > 1:
        reduced: List[str] = []
        for index in range(0, len(current), 6):
            group = current[index : index + 6]
            answer = llm.ask(
                f"{instruction}\n\n" + "\n\n--- ФРАГМЕНТ ---\n\n".join(group)
            )
            usage.add(agent_name, answer.usage)
            reduced.append(answer.content)
        current = reduced
    return current[0]


def _unique(values: Iterable[str]) -> List[str]:
    """Удалить пустые строки и повторы с сохранением порядка."""
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def run_document(
    file_path: str,
    llm: LLMClient | None = None,
    settings: Settings | None = None,
) -> PipelineResult:
    """Загрузить документ и выполнить одно- или многочанковый pipeline."""
    settings = settings or Settings.from_env()
    llm = llm or get_default_client()
    text = load_document(file_path)
    count_document_tokens(text, llm, settings.max_document_tokens)
    chunks = split_document(
        text,
        llm,
        settings.chunk_target_tokens,
        settings.chunk_overlap_tokens,
    )

    if len(chunks) <= 1:
        result = app.invoke(_state(text, llm, TokenUsage()))
        return PipelineResult(
            analysis=result["analysis"],
            summary=result["summary"],
            fact_check=FactCheckResult.model_validate(result["fact_check"]),
            final=result["final"],
            token_usage=result["token_usage"],
        )

    usage = TokenUsage()
    partial_analyses: List[str] = []
    partial_checks: List[tuple[FactCheckResult, int]] = []
    for chunk_text, chunk_tokens in chunks:
        partial = chunk_app.invoke(_state(chunk_text, llm, TokenUsage()))
        _merge_usage(usage, partial["token_usage"])
        partial_analyses.append(partial["analysis"])
        partial_checks.append(
            (FactCheckResult.model_validate(partial["fact_check"]), chunk_tokens)
        )

    analysis = _reduce_texts(
        partial_analyses,
        "Объедини анализы частей одного документа. Удали повторы, сохрани важные факты и не добавляй внешнюю информацию.",
        llm,
        usage,
        "Analysis Reducer",
    )
    verification = _reduce_texts(
        [item.verification_summary for item, _ in partial_checks],
        "Сведи результаты внутренней проверки частей документа в одно краткое заключение.",
        llm,
        usage,
        "Fact Check Reducer",
    )
    explanation = _reduce_texts(
        [item.neuroslop.explanation for item, _ in partial_checks],
        "Объедини объяснения эвристической оценки нейрослопа для частей исходного документа. Не утверждай авторство текста как доказанный факт.",
        llm,
        usage,
        "Fact Check Reducer",
    )
    weighted_probability = sum(
        item.neuroslop.probability * tokens for item, tokens in partial_checks
    ) / max(sum(tokens for _, tokens in partial_checks), 1)
    fact_check = FactCheckResult(
        verification_summary=verification,
        doubtful_claims=_unique(
            claim for item, _ in partial_checks for claim in item.doubtful_claims
        ),
        contradictions=_unique(
            claim for item, _ in partial_checks for claim in item.contradictions
        ),
        neuroslop={
            "probability": min(max(weighted_probability, 0.0), 1.0),
            "explanation": explanation,
        },
    )
    synthesis_state = _state("", llm, usage)
    synthesis_state["analysis"] = analysis
    synthesis_state["fact_check"] = fact_check.model_dump()
    synthesis = synthesis_app.invoke(synthesis_state)
    return PipelineResult(
        analysis=analysis,
        summary=synthesis["summary"],
        fact_check=fact_check,
        final=synthesis["final"],
        token_usage=synthesis["token_usage"],
    )


if __name__ == "__main__":
    output = run_document("data/raw/load.pdf")
    print(output.model_dump_json(indent=2))
