import csv
from io import StringIO
from pathlib import Path
from zipfile import ZipFile

from bs4 import BeautifulSoup
from docx import Document
from docx.text.paragraph import Paragraph
from markdown_it import MarkdownIt

from ..errors import (
    CorruptDocumentError,
    DocumentTooLargeError,
    EmptyDocumentError,
    ExtractionError,
    UnsupportedFormatError,
)
from ..models import DocumentType
from .metadata import detect_file_type


_MAX_DOCX_UNPACKED_BYTES = 100 * 1024 * 1024


def _checked_path(file_path: str, expected_type: DocumentType) -> Path:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")
    if detect_file_type(file_path) != expected_type:
        raise UnsupportedFormatError()
    return path


def _read_text_bytes(path: Path) -> bytes:
    try:
        content = path.read_bytes()
    except OSError as error:
        raise ExtractionError() from error
    if b"\x00" in content:
        raise CorruptDocumentError()
    return content


def _read_utf8(path: Path) -> str:
    try:
        return _read_text_bytes(path).decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CorruptDocumentError("Текстовый документ должен быть в кодировке UTF-8") from error


def _nonempty(text: str) -> str:
    if not text.strip():
        raise EmptyDocumentError()
    return text.strip("\r\n")


def _visible_html_text(markup) -> str:
    """Извлечь текст с границами блоков, ссылками и описаниями картинок."""
    soup = BeautifulSoup(markup, "html.parser")
    if soup.contains_replacement_characters:
        raise CorruptDocumentError("Не удалось определить кодировку HTML")
    if soup.head is not None:
        soup.head.decompose()
    for tag in soup.find_all(["script", "style", "noscript", "template"]):
        if tag.parent is not None:
            tag.decompose()
    for image in soup.find_all("img"):
        image.replace_with(image.get("alt", ""))
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href and href != link.get_text():
            link.append(f" ({href})")
    for line_break in soup.find_all("br"):
        line_break.replace_with("\n")
    block_tags = [
        "p", "div", "section", "article", "header", "footer", "blockquote",
        "h1", "h2", "h3", "h4", "h5", "h6", "li", "pre",
    ]
    for block in soup.find_all(block_tags):
        block.insert_before("\n\n")
        block.insert_after("\n\n")
    for row in reversed(soup.find_all("tr")):
        cells = row.find_all(["td", "th"], recursive=False)
        text = "\t".join(cell.get_text().strip() for cell in cells)
        row.replace_with(f"\n\n{text}\n\n")
    root = soup.body if soup.body is not None else soup
    return _nonempty(root.get_text())


def load_html(file_path: str) -> str:
    """Извлечь текст сохранённой HTML-страницы без выполнения её кода."""
    path = _checked_path(file_path, "html")
    return _visible_html_text(_read_text_bytes(path))


def load_markdown(file_path: str) -> str:
    """Разобрать Markdown, сохранив текст, таблицы, ссылки и блоки кода."""
    path = _checked_path(file_path, "md")
    markdown = MarkdownIt("commonmark").enable(["table", "strikethrough"])
    return _visible_html_text(markdown.render(_read_utf8(path)))


def load_csv(file_path: str) -> str:
    """Прочитать UTF-8 CSV с разделителями запятая, точка с запятой, таб или |."""
    path = _checked_path(file_path, "csv")
    text = _read_utf8(path)
    _nonempty(text)
    try:
        dialect = csv.Sniffer().sniff(text[:65536], delimiters=",;\t|")
    except csv.Error:
        dialect = "excel"
    try:
        rows = csv.reader(StringIO(text, newline=""), dialect=dialect, strict=True)
        lines = [
            "\t".join(row)
            for row in rows
            if any(cell.strip() for cell in row)
        ]
    except csv.Error as error:
        raise CorruptDocumentError("Некорректная структура CSV") from error
    if not lines:
        raise EmptyDocumentError()
    return "\n".join(lines)


def _docx_container_text(container) -> str:
    """Обойти абзацы и таблицы, включая вложенные, в порядке документа."""
    parts = []
    for block in container.iter_inner_content():
        if isinstance(block, Paragraph):
            parts.append(block.text)
        else:
            for row in block.rows:
                parts.append("\t".join(_docx_container_text(cell) for cell in row.cells))
    return "\n".join(parts)


def load_docx(file_path: str) -> str:
    """Извлечь основной текст и таблицы Word с ограничением размера архива."""
    path = _checked_path(file_path, "docx")
    try:
        with ZipFile(path) as package:
            if sum(part.file_size for part in package.infolist()) > _MAX_DOCX_UNPACKED_BYTES:
                raise DocumentTooLargeError("Распакованный DOCX превышает лимит 100 МБ")
        text = _docx_container_text(Document(str(path)))
    except DocumentTooLargeError:
        raise
    except OSError as error:
        raise ExtractionError() from error
    except Exception as error:
        raise CorruptDocumentError() from error
    return _nonempty(text)
