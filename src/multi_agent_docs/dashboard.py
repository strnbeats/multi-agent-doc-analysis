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


STATUS_LABELS = {
    "queued": "В очереди",
    "running": "Выполняется",
    "completed": "Завершён",
    "failed": "Ошибка анализа",
}


def render_document(record: DocumentDetail) -> View:
    status = record.status.value
    message = f"{status} — {STATUS_LABELS[status]}"
    if record.error_message:
        message += f": {record.error_message}"
    results = record.results
    return View(
        record.id, message,
        results.analysis if results else "",
        results.summary if results else "",
        json.dumps(results.fact_check.model_dump(), ensure_ascii=False, indent=2) if results else "",
        results.final if results else "",
        record.token_usage.model_dump(exclude={"by_agent"}),
        {name: usage.model_dump() for name, usage in record.token_usage.by_agent.items()},
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
        status_output = gr.Textbox(label="Статус", interactive=False)
        with gr.Tab("Итог"):
            final_output = gr.Markdown()
        with gr.Tab("Анализ"):
            analysis_output = gr.Markdown()
        with gr.Tab("Краткое содержание"):
            summary_output = gr.Markdown()
        with gr.Tab("Факты"):
            fact_output = gr.Textbox(label="Структурированная проверка", lines=12, interactive=False)
        with gr.Tab("Статистика токенов"):
            token_output = gr.JSON(label="Общий расход")
            agent_output = gr.JSON(label="Расход по агентам")
        outputs = [document_id, status_output, analysis_output, summary_output, fact_output, final_output, token_output, agent_output]
        analyze_button.click(analyze_file, inputs=file_input, outputs=outputs)
        refresh_button.click(refresh, inputs=document_id, outputs=outputs)
    return demo


if __name__ == "__main__":
    build_dashboard().queue().launch(
        server_name=os.getenv("DASHBOARD_HOST", "127.0.0.1"),
        server_port=int(os.getenv("DASHBOARD_PORT", "7860")),
        share=False,
    )
