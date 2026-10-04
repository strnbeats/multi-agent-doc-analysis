from .graph import app
from .ingestion.loader import load_document
from .llm import client


def run_document(file_path: str):

    text = load_document(file_path)

    initial_state = {
        "text": text,
        "analysis": "",
        "summary": "",
        "facts": "",
        "final": ""
    }

    result = app.invoke(initial_state)

    return result


if __name__ == "__main__":

    file_path = "data/raw/load.pdf"

    result = run_document(file_path)

    print("\n=== АНАЛИЗ ===")
    print(result["analysis"])

    print("\n=== КРАТКОЕ СОДЕРЖАНИЕ ===")
    print(result["summary"])

    print("\n=== ПРОВЕРКА ФАКТОВ ===")
    print(result["facts"])

    print("\n=== ФИНАЛЬНЫЙ РЕЗУЛЬТАТ ===")
    print(result["final"])

    print("\n==============================")
    print(f"TOTAL INPUT TOKENS: {client.total_input_tokens}")
    print(f"TOTAL OUTPUT TOKENS: {client.total_output_tokens}")
    print(f"TOTAL TOKENS: {client.total_tokens}")
    print("==============================")

    print("\n=== TOKEN USAGE BY AGENT ===")

    for agent, usage in client.token_usage.items():
        print(
            f"{agent}: "
            f"input={usage['input']} | "
            f"output={usage['output']} | "
            f"total={usage['total']}"
        )