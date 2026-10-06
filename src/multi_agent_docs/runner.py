from .graph import app
from .ingestion.loader import load_document
from .llm import client
from .database.db import SessionLocal
from .database.repository import (
    create_analysis,
    create_document,
    create_token_usage,
    update_analysis,
    update_document_status,
)

def run_document(file_path: str):

    db = SessionLocal()

    document = None

    try:
        text = load_document(file_path)

        file_name = file_path.split("/")[-1]

        document = create_document(
            db=db,
            filename=file_name,
            file_type=file_name.split(".")[-1],
            file_size=0,
        )

        print(f"Document created: {document.id}")

        update_document_status(
            db=db,
            document_id=document.id,
            status="processing",
        )

        analysis = create_analysis(
            db=db,
            document_id=document.id,
            analysis="",
            summary="",
            facts="",
            final_result="",
        )

        analysis.status = "processing"
        db.commit()

        print(f"Analysis created: {analysis.id}")

        initial_state = {
            "text": text,
            "analysis": "",
            "summary": "",
            "facts": "",
            "final": "",
        }

        result = app.invoke(initial_state)

        update_analysis(
            db=db,
            analysis_id=analysis.id,
            analysis=result["analysis"],
            summary=result["summary"],
            facts=result["facts"],
            final_result=result["final"],
        )

        for agent_name, usage in client.token_usage.items():
            create_token_usage(
                db=db,
                analysis_id=analysis.id,
                agent_name=agent_name,
                input_tokens=usage["input"],
                output_tokens=usage["output"],
            )

        update_document_status(
            db=db,
            document_id=document.id,
            status="completed",
        )

        print(f"Analysis completed: {analysis.id}")

        return result

    except Exception as e:

        if document is not None:
            update_document_status(
                db=db,
                document_id=document.id,
                status="failed",
                error=str(e),
            )

        print(f"Analysis failed: {e}")

        raise

    finally:
        db.close()

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