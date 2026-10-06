from pathlib import Path

import pytest

from multi_agent_docs.errors import CorruptDocumentError, DocumentTooLargeError, EmptyDocumentError
from multi_agent_docs.ingestion.chunking import count_document_tokens, split_document
from multi_agent_docs.ingestion.loader import load_document

from conftest import FakeLLM


def test_loads_utf8_txt(tmp_path: Path):
    path = tmp_path / "sample.txt"
    path.write_text("Первый абзац.\n\nВторой абзац.", encoding="utf-8")
    assert "Второй" in load_document(str(path))


@pytest.mark.parametrize("payload", [b"", b"\x00binary", b"\xff\xfe"])
def test_rejects_invalid_txt(tmp_path: Path, payload: bytes):
    path = tmp_path / "invalid.txt"
    path.write_bytes(payload)
    with pytest.raises((EmptyDocumentError, CorruptDocumentError)):
        load_document(str(path))


def test_rejects_fake_pdf(tmp_path: Path):
    path = tmp_path / "fake.pdf"
    path.write_text("not a pdf")
    with pytest.raises(CorruptDocumentError):
        load_document(str(path))


def test_chunking_and_token_cap():
    llm = FakeLLM()
    text = "\n\n".join(["слово " * 20 for _ in range(8)])
    chunks = split_document(text, llm, target_tokens=35, overlap_tokens=2)
    assert len(chunks) > 1
    assert all(tokens <= 35 for _, tokens in chunks)
    with pytest.raises(DocumentTooLargeError):
        count_document_tokens(text, llm, maximum=50)

