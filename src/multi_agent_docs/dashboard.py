"""Gradio-вкладки из dashboard/70b7028, адаптированные под фоновый HTTP API."""
from __future__ import annotations

import json
import os
import time
from typing import NamedTuple

from .api_schemas import DocumentDetail
from .dashboard_api import AnalysisAPI, DashboardError


class View(NamedTuple):
    document_id: int | None
    status: str
    analysis: str = ""
    summary: str = ""
    fact_check: str = ""
    final: str = ""
    token_usage: dict | None = None
    by_agent: dict | None = None
    final_review_status: str = ""
    final_review_doubtful_claims: str = ""
    final_review_contradictions: str = ""


STATUS_LABELS = {
    "queued": "В очереди",
    "running": "Выполняется",
    "completed": "Завершён",
    "failed": "Ошибка анализа",
}

FINAL_REVIEW_LABELS = {
    "not_evaluated": "Итоговый отчёт не проверен",
    "no_flags": "Проверяющая модель не отметила замечаний",
    "needs_review": "Требуется проверка итогового отчёта: есть замечания",
}


def render_document(record: DocumentDetail) -> View:
    status = record.status.value
    message = f"{status} — {STATUS_LABELS[status]}"
    if record.error_message:
        message += f": {record.error_message}"
    results = record.results
    review_status = ""
    review_doubts = ""
    review_contradictions = ""
    if results is not None:
        review = results.final_review
        if review is None:
            review_status = "Итоговый отчёт не проверен"
        else:
            review_status = f"{review.status} — {FINAL_REVIEW_LABELS[review.status]}"
            review_doubts = "\n".join(
                f"• {claim}" for claim in review.doubtful_claims
            ) or "Не отмечены"
            review_contradictions = "\n".join(
                f"• {claim}" for claim in review.contradictions
            ) or "Не отмечены"

    return View(
        document_id=record.id,
        status=message,
        analysis=results.analysis if results else "",
        summary=results.summary if results else "",
        fact_check=json.dumps(results.fact_check.model_dump(), ensure_ascii=False, indent=2) if results else "",
        final=results.final if results else "",
        token_usage=record.token_usage.model_dump(exclude={"by_agent"}),
        by_agent={name: usage.model_dump() for name, usage in record.token_usage.by_agent.items()},
        final_review_status=review_status,
        final_review_doubtful_claims=review_doubts,
        final_review_contradictions=review_contradictions,
    )


def watch_analysis(file_path, base_url, *, poll_interval=.5, max_wait=300, transport=None):
    """Отправить один POST и показывать статусы; остановка ожидания не отменяет задачу."""
    if not file_path:
        yield View(None, "Сначала выберите документ.")
        return
    document_id = None
    try:
        with AnalysisAPI(base_url, transport=transport) as api:
            accepted = api.submit(file_path)
            document_id = accepted.id
            yield View(document_id, f"{accepted.status.value} — {STATUS_LABELS[accepted.status.value]}")
            deadline = time.monotonic() + max_wait
            while True:
                record = api.get_document(document_id)
                yield render_document(record)
                if record.status.value in {"completed", "failed"}:
                    return
                if time.monotonic() >= deadline:
                    yield View(document_id, f"{record.status.value} — Ожидание остановлено. Нажмите «Обновить по ID».")
                    return
                time.sleep(poll_interval)
    except DashboardError as error:
        hint = " Сохраните ID и обновите статус; повторная загрузка создаст новую задачу." if document_id else ""
        yield View(document_id, f"{error}{hint}")


def refresh_document(document_id, base_url, *, transport=None):
    if document_id is None or document_id < 1 or int(document_id) != document_id:
        return View(None, "Укажите положительный целочисленный ID анализа.")
    try:
        with AnalysisAPI(base_url, transport=transport) as api:
            return render_document(api.get_document(int(document_id)))
    except DashboardError as error:
        return View(int(document_id), str(error))


def build_dashboard():
    # Gradio остаётся необязательной зависимостью backend и offline-тестов клиента.
    import gradio as gr

    def analyze_file(file_path):
        yield from watch_analysis(file_path, os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))

    def refresh(document_id):
        return refresh_document(document_id, os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))

    with gr.Blocks(title="Multi-Agent Document Dashboard") as demo:
        gr.Markdown("# Анализ документов\nЗагрузите документ и дождитесь результата анализа.")
        file_input = gr.File(label="Документ", file_types=[".pdf", ".txt", ".docx", ".html", ".htm", ".md", ".markdown", ".csv"], type="filepath")
        with gr.Row():
            analyze_button = gr.Button("Запустить анализ", variant="primary")
            refresh_button = gr.Button("Обновить по ID")
        document_id = gr.Number(label="ID анализа", precision=0)
        status_output = gr.Textbox(label="Статус выполнения", interactive=False)
        with gr.Tab("Итог"):
            review_status_output = gr.Textbox(
                label="Проверка итогового отчёта", interactive=False,
            )
            review_doubts_output = gr.Textbox(
                label="Сомнительные утверждения итогового отчёта",
                lines=4, interactive=False,
            )
            review_contradictions_output = gr.Textbox(
                label="Противоречия итогового отчёта",
                lines=4, interactive=False,
            )
            final_output = gr.Markdown()
        with gr.Tab("Анализ"):
            analysis_output = gr.Markdown()
        with gr.Tab("Краткое содержание"):
            summary_output = gr.Markdown()
        with gr.Tab("Факты"):
            fact_output = gr.Textbox(label="Первичная проверка анализа и сводки", lines=12, interactive=False)
        with gr.Tab("Статистика токенов"):
            token_output = gr.JSON(label="Общий расход")
            agent_output = gr.JSON(label="Расход по агентам")
        # Порядок соответствует полям View: оба обработчика возвращают все поля.
        outputs = [
            document_id, status_output, analysis_output, summary_output,
            fact_output, final_output, token_output, agent_output,
            review_status_output, review_doubts_output, review_contradictions_output,
        ]
        analyze_button.click(analyze_file, inputs=file_input, outputs=outputs)
        refresh_button.click(refresh, inputs=document_id, outputs=outputs)
    return demo


if __name__ == "__main__":
    build_dashboard().queue().launch(
        server_name=os.getenv("DASHBOARD_HOST", "127.0.0.1"),
        server_port=int(os.getenv("DASHBOARD_PORT", "7860")),
        share=False,
    )
