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


def load_txt(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    if path.suffix.lower() != ".txt":
        raise ValueError("Файл должен быть TXT")

    return path.read_text(encoding="utf-8")


def load_document(file_path: str) -> str:
    path = Path(file_path)

    if path.suffix.lower() == ".pdf":
        return load_pdf(file_path)

    if path.suffix.lower() == ".txt":
        return load_txt(file_path)

    raise ValueError("Поддерживаются только PDF и TXT")