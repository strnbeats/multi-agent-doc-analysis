from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


def _int_setting(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} должен быть положительным числом")
    return value


@dataclass(frozen=True)
class Settings:
    database_path: Path
    upload_dir: Path
    max_upload_bytes: int
    max_document_tokens: int
    chunk_target_tokens: int
    chunk_overlap_tokens: int
    gigachat_credentials: str | None
    gigachat_scope: str
    gigachat_model: str
    gigachat_verify_ssl: bool

    def __post_init__(self) -> None:
        if self.chunk_overlap_tokens >= self.chunk_target_tokens:
            raise ValueError("CHUNK_OVERLAP_TOKENS должен быть меньше CHUNK_TARGET_TOKENS")

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            database_path=Path(os.getenv("DATABASE_PATH", "data/app.db")),
            upload_dir=Path(os.getenv("UPLOAD_DIR", "data/jobs")),
            max_upload_bytes=_int_setting("MAX_UPLOAD_BYTES", 100 * 1024 * 1024),
            max_document_tokens=_int_setting("MAX_DOCUMENT_TOKENS", 250_000),
            chunk_target_tokens=_int_setting("CHUNK_TARGET_TOKENS", 8_000),
            chunk_overlap_tokens=_int_setting("CHUNK_OVERLAP_TOKENS", 300),
            gigachat_credentials=os.getenv("GIGACHAT_CREDENTIALS"),
            gigachat_scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
            gigachat_model=os.getenv("GIGACHAT_MODEL", "GigaChat-3-Ultra"),
            gigachat_verify_ssl=os.getenv("GIGACHAT_VERIFY_SSL", "true").lower()
            in {"1", "true", "yes"},
        )
