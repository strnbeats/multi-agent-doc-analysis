
import gradio as gr

from .runner import run_document
from .llm import client

from pathlib import Path
import tempfile


def analyze_file(file_path):
    if not file_path:
        raise gr.Error("Сначала загрузи PDF или TXT файл.")

    extension = Path(file_path).suffix.lower()

    if extension not in [".pdf", ".txt"]:
        raise gr.Error("Поддерживаются только PDF и TXT.")

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=extension,
            delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(Path(file_path).read_bytes())

        client.total_input_tokens = 0
        client.total_output_tokens = 0
        client.total_tokens = 0
        client.token_usage = {}

        result = run_document(str(temp_path))

        token_data = {
            "Входные токены": client.total_input_tokens,
            "Выходные токены": client.total_output_tokens,
            "Всего токенов": client.total_tokens,
        }

        agent_data = [
            {
                "Агент": agent,
                "Входные токены": usage["input"],
                "Выходные токены": usage["output"],
                "Всего токенов": usage["total"],
            }
            for agent, usage in client.token_usage.items()
        ]

        return (
            result.get("analysis", ""),
            result.get("summary", ""),
            result.get("facts", ""),
            result.get("final", ""),
            token_data,
            agent_data,
        )

    except Exception as error:
        raise gr.Error(f"Не удалось обработать документ: {error}")

    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)


with gr.Blocks(title="Multi-Agent Document Dashboard") as demo:
    gr.Markdown(
        "# Multi-Agent Document Analyzer\n"
        "### Анализ документов с помощью нескольких ИИ-агентов"
    )

    with gr.Row():
        file_input = gr.File(
            label="Загрузи документ",
            file_types=[".pdf", ".txt"],
            type="filepath",
        )

        analyze_button = gr.Button(
            "Запустить анализ",
            variant="primary",
        )

    with gr.Tab("Итог"):
        final_output = gr.Markdown(label="Итоговый результат")

    with gr.Tab("Анализ"):
        analysis_output = gr.Markdown(label="Анализ документа")

    with gr.Tab("Краткое содержание"):
        summary_output = gr.Markdown(label="Краткое содержание")

    with gr.Tab("Факты"):
        facts_output = gr.Markdown(label="Извлечённые факты")

    with gr.Tab("Статистика токенов"):
        token_output = gr.JSON(label="Общее использование токенов")
        agent_output = gr.JSON(label="Использование по агентам")

    analyze_button.click(
        fn=analyze_file,
        inputs=file_input,
        outputs=[
            analysis_output,
            summary_output,
            facts_output,
            final_output,
            token_output,
            agent_output,
        ],
    )


if __name__ == "__main__":
    demo.launch()
