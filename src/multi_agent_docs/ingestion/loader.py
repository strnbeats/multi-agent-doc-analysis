from pathlib import Path
from pypdf import PdfReader


def load_pdf(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Файл должен быть PDF")

    reader = PdfReader(path)
    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    return "\n".join(pages)