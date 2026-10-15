from pathlib import Path
from stat import S_ISREG
from typing import Dict

from ..errors import ExtractionError, UnsupportedFormatError
from ..models import DocumentMetadata, DocumentType


_FILE_TYPES: Dict[str, DocumentType] = {".pdf": "pdf", ".txt": "txt"}


def detect_file_type(file_path: str) -> DocumentType:
    """Определить поддерживаемый тип по расширению без учёта регистра."""
    file_type = _FILE_TYPES.get(Path(file_path).suffix.lower())
    if file_type is None:
        raise UnsupportedFormatError()
    return file_type


def get_document_metadata(file_path: str) -> DocumentMetadata:
    """Прочитать тип и размер исходного файла в байтах."""
    path = Path(file_path)
    file_type = detect_file_type(file_path)
    try:
        file_stat = path.stat()
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Файл не найден: {path}") from error
    except OSError as error:
        raise ExtractionError() from error
    if not S_ISREG(file_stat.st_mode):
        raise ExtractionError()
    return DocumentMetadata(file_type=file_type, size_bytes=file_stat.st_size)
