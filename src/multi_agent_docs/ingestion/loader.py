from pathlib import Path
from pypdf import PdfReader

from ..errors import CorruptDocumentError, EmptyDocumentError, ExtractionError, UnsupportedFormatError


def load_pdf(file_path: str) -> str:
    """Проверить PDF и извлечь непустой текст всех страниц."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    if path.suffix.lower() != ".pdf":
        raise UnsupportedFormatError()

    try:
        with path.open("rb") as source:
            if source.read(5) != b"%PDF-":
                raise CorruptDocumentError()
    except OSError as error:
        raise ExtractionError() from error

    try:
        reader = PdfReader(path)
        pages = []

        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
    except Exception as error:
        raise CorruptDocumentError() from error

    result = "\n\n".join(pages).strip()
    if not result:
        raise EmptyDocumentError()
    return result


def load_txt(file_path: str) -> str:
    """Прочитать непустой UTF-8 TXT и отклонить бинарный файл."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    if path.suffix.lower() != ".txt":
        raise UnsupportedFormatError()

    try:
        content = path.read_bytes()
        if b"\x00" in content:
            raise CorruptDocumentError()
        text = content.decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise CorruptDocumentError("TXT должен быть в кодировке UTF-8") from error
    except OSError as error:
        raise ExtractionError() from error
    if not text:
        raise EmptyDocumentError()
    return text


def load_document(file_path: str) -> str:
    """Выбрать загрузчик документа по поддерживаемому расширению."""
    path = Path(file_path)

    if path.suffix.lower() == ".pdf":
        return load_pdf(file_path)

    if path.suffix.lower() == ".txt":
        return load_txt(file_path)

    raise UnsupportedFormatError()


def validate_document(file_path: str) -> None:
    """Убедиться, что документ корректен и содержит текст."""
    load_document(file_path)
