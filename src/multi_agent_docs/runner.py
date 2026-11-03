from __future__ import annotations

from .config import Settings
from .graph import app, chunk_app, synthesis_app
from .ingestion.chunking import count_document_tokens, split_document
from .ingestion.loader import load_document
from .ingestion.metadata import get_document_metadata
from .llm.client import LLMClient, get_default_client
from .models import FactCheckResult, FinalReview, PipelineResult, TokenUsage
from .orchestration import WorkflowState, build_document_graph


# Один вход для обоих сценариев; существующие графы работают как подграфы.
document_app = build_document_graph(app, chunk_app, synthesis_app)


def run_document(
    file_path: str,
    llm: LLMClient | None = None,
    settings: Settings | None = None,
) -> PipelineResult:
    """Загрузить файл, подготовить фрагменты и запустить управляющий граф."""
    settings = settings or Settings.from_env()
    llm = llm or get_default_client()
    metadata = get_document_metadata(file_path)
    text = load_document(file_path)
    count_document_tokens(text, llm, settings.max_document_tokens)
    chunks = split_document(
        text,
        llm,
        settings.chunk_target_tokens,
        settings.chunk_overlap_tokens,
    )

    initial_state: WorkflowState = {
        "text": text,
        "metadata": metadata,
        "llm": llm,
        "chunks": [
            {
                "chunk_id": f"chunk_{index:04d}",
                "text": chunk_text,
                "token_count": chunk_tokens,
            }
            for index, (chunk_text, chunk_tokens) in enumerate(chunks, start=1)
        ],
        "chunk_index": 0,
        "chunk_results": [],
        "analysis": "",
        "summary": "",
        "fact_check": {},
        "final": "",
        "final_review": None,
        "token_usage": TokenUsage(),
    }
    # Это лимит шагов графа, а не глубина стека Python. Один проход цикла
    # обрабатывает один чанк; запас покрывает подготовку и финальные узлы.
    result = document_app.invoke(
        initial_state,
        config={"recursion_limit": max(25, len(chunks) + 10)},
    )
    review = result.get("final_review")
    return PipelineResult(
        analysis=result["analysis"],
        summary=result["summary"],
        fact_check=FactCheckResult.model_validate(result["fact_check"]),
        final=result["final"],
        token_usage=result["token_usage"],
        metadata=result["metadata"],
        final_review=FinalReview.model_validate(review) if review is not None else None,
    )


if __name__ == "__main__":
    output = run_document("data/raw/load.pdf")
    print(output.model_dump_json(indent=2))
