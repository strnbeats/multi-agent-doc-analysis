import re
from typing import List, Tuple

from ..errors import DocumentTooLargeError
from ..llm.client import LLMClient


def _rough_blocks(text: str, chars: int = 24_000) -> List[str]:
    """Разделить текст на безопасные блоки для token-count API."""
    return [text[index : index + chars] for index in range(0, len(text), chars)]


def count_document_tokens(text: str, llm: LLMClient, maximum: int) -> int:
    """Посчитать токены блоками и сразу остановиться при превышении лимита."""
    total = 0
    for block in _rough_blocks(text):
        total += llm.count_tokens(block)
        if total > maximum:
            raise DocumentTooLargeError(
                f"Документ превышает лимит {maximum} токенов"
            )
    return total


def split_document(
    text: str,
    llm: LLMClient,
    target_tokens: int,
    overlap_tokens: int,
) -> List[Tuple[str, int]]:
    """Разбить документ на ограниченные по токенам чанки с перекрытием."""
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
    if not paragraphs:
        return []

    target_chars = target_tokens * 3
    overlap_chars = overlap_tokens * 3
    raw_chunks: List[str] = []
    current = ""
    for paragraph in paragraphs:
        pieces = [paragraph[i : i + target_chars] for i in range(0, len(paragraph), target_chars)]
        for piece in pieces:
            candidate = f"{current}\n\n{piece}".strip()
            if current and len(candidate) > target_chars:
                raw_chunks.append(current)
                overlap = current[-overlap_chars:] if overlap_chars else ""
                current = f"{overlap}\n\n{piece}".strip()
            else:
                current = candidate
    if current:
        raw_chunks.append(current)

    chunks: List[Tuple[str, int]] = []

    def append_sized(value: str) -> None:
        """Рекурсивно уменьшить чанк до целевого числа токенов."""
        value = value.strip()
        if not value:
            return
        tokens = llm.count_tokens(value)
        if tokens <= target_tokens or len(value) < 2:
            chunks.append((value, tokens))
            return
        middle = len(value) // 2
        append_sized(value[:middle])
        append_sized(value[middle:])

    for chunk in raw_chunks:
        append_sized(chunk)
    return chunks
