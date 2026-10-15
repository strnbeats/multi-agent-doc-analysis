from pathlib import Path

import pytest

from multi_agent_docs.errors import ExtractionError, UnsupportedFormatError
from multi_agent_docs.ingestion.loader import load_document
from multi_agent_docs.ingestion.metadata import detect_file_type, get_document_metadata


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("report.pdf", "pdf"), ("REPORT.PDF", "pdf"), ("заметки.txt", "txt"), ("notes.TxT", "txt")],
)
def test_detects_supported_type(filename, expected):
    assert detect_file_type(filename) == expected


@pytest.mark.parametrize("filename", ["report", "report.docx", "report.txt.bak"])
def test_rejects_unsupported_type(filename):
    with pytest.raises(UnsupportedFormatError):
        detect_file_type(filename)


def test_directory_name_does_not_determine_file_type(tmp_path: Path):
    path = tmp_path / "archive.pdf" / "notes.txt"
    assert detect_file_type(str(path)) == "txt"


def test_metadata_uses_original_utf8_byte_size(tmp_path: Path):
    payload = "  Привет, мир!\r\n\r\n".encode("utf-8")
    path = tmp_path / "notes.TxT"
    path.write_bytes(payload)
    metadata = get_document_metadata(str(path))
    assert metadata.file_type == "txt"
    assert metadata.size_bytes == len(payload)
    assert metadata.size_bytes > len(load_document(str(path)))


def test_pdf_metadata_uses_file_size():
    path = Path(__file__).parents[1] / "data" / "raw" / "load.pdf"
    metadata = get_document_metadata(str(path))
    assert metadata.file_type == "pdf"
    assert metadata.size_bytes == len(path.read_bytes())


def test_metadata_rejects_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        get_document_metadata(str(tmp_path / "missing.txt"))


def test_metadata_rejects_directory(tmp_path: Path):
    path = tmp_path / "folder.txt"
    path.mkdir()
    with pytest.raises(ExtractionError):
        get_document_metadata(str(path))


def test_metadata_wraps_filesystem_errors(tmp_path: Path, monkeypatch):
    def denied_stat(self):
        raise PermissionError("Permission denied")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "stat", denied_stat)
        with pytest.raises(ExtractionError) as caught:
            get_document_metadata(str(tmp_path / "denied.txt"))
    assert isinstance(caught.value.__cause__, PermissionError)
