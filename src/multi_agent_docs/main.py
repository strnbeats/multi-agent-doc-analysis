from pathlib import Path
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException

from .runner import run_document
from .llm import client

app = FastAPI(
    title="Multi-Agent Document Analysis",
    description="API для анализа PDF и TXT документов",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "Multi-Agent Document Analysis API"
    }


@app.post("/analyze")
def analyze_document(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Файл не имеет имени"
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in [".pdf", ".txt"]:
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только PDF и TXT"
        )

    with tempfile.NamedTemporaryFile(
        suffix=extension,
        delete=False
    ) as temp_file:

        temp_file.write(file.file.read())
        temp_path = temp_file.name

    try:
        result = run_document(temp_path)

        return {
            "filename": file.filename,
            "analysis": result["analysis"],
            "summary": result["summary"],
            "facts": result["facts"],
            "final": result["final"],

            "token_usage": {
                "total_input": client.total_input_tokens,
                "total_output": client.total_output_tokens,
                "total": client.total_tokens,
                "by_agent": client.token_usage
            }
}

    finally:
        Path(temp_path).unlink(missing_ok=True)