import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..errors import StorageError
from ..models import DocumentRecord, DocumentStatus, TokenUsage
from .db import Database


def utc_now() -> datetime:
    """Вернуть текущее время UTC для записей базы."""
    return datetime.now(timezone.utc)


class DocumentRepository:
    def __init__(self, database: Database):
        """Привязать repository к SQLite-подключению."""
        self.database = database

    def initialize(self) -> None:
        """Применить миграции и подготовить базу."""
        try:
            self.database.initialize()
        except sqlite3.Error as error:
            raise StorageError() from error

    def create(self, filename: str) -> DocumentRecord:
        """Создать запись анализа в статусе queued."""
        now = utc_now().isoformat()
        try:
            with self.database.connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO documents(filename, created_at, updated_at, status) VALUES (?, ?, ?, ?)",
                    (filename, now, now, DocumentStatus.QUEUED.value),
                )
                document_id = cursor.lastrowid
            return self.get_by_id(document_id)  # type: ignore[arg-type]
        except sqlite3.Error as error:
            raise StorageError() from error

    def mark_running(self, document_id: int) -> None:
        """Перевести анализ в статус running."""
        self._update_status(document_id, DocumentStatus.RUNNING)

    def complete(
        self,
        document_id: int,
        result: Dict[str, Any],
        neuroslop: float,
        usage: TokenUsage,
    ) -> None:
        """Сохранить успешный результат и статистику токенов."""
        now = utc_now().isoformat()
        try:
            with self.database.connect() as connection:
                connection.execute(
                    """
                    UPDATE documents
                    SET status = ?, updated_at = ?, result = ?, neuroslop = ?,
                        input_tokens = ?, output_tokens = ?, total_tokens = ?,
                        error_code = NULL, error_message = NULL
                    WHERE id = ?
                    """,
                    (
                        DocumentStatus.COMPLETED.value,
                        now,
                        json.dumps(result, ensure_ascii=False),
                        neuroslop,
                        usage.input_tokens,
                        usage.output_tokens,
                        usage.total_tokens,
                        document_id,
                    ),
                )
        except (sqlite3.Error, TypeError, ValueError) as error:
            raise StorageError() from error

    def fail(self, document_id: int, error_code: str, error_message: str) -> None:
        """Сохранить безопасную ошибку завершения анализа."""
        now = utc_now().isoformat()
        try:
            with self.database.connect() as connection:
                connection.execute(
                    """
                    UPDATE documents
                    SET status = ?, updated_at = ?, error_code = ?, error_message = ?
                    WHERE id = ?
                    """,
                    (DocumentStatus.FAILED.value, now, error_code, error_message, document_id),
                )
        except sqlite3.Error as error:
            raise StorageError() from error

    def mark_interrupted(self) -> int:
        """Пометить незавершённые после рестарта задачи ошибкой."""
        now = utc_now().isoformat()
        try:
            with self.database.connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE documents
                    SET status = 'failed', updated_at = ?, error_code = 'backend_restarted',
                        error_message = 'Анализ прерван перезапуском backend'
                    WHERE status IN ('queued', 'running')
                    """,
                    (now,),
                )
                return cursor.rowcount
        except sqlite3.Error as error:
            raise StorageError() from error

    def get_by_id(self, document_id: int) -> Optional[DocumentRecord]:
        """Получить анализ по идентификатору."""
        try:
            with self.database.connect() as connection:
                row = connection.execute(
                    "SELECT * FROM documents WHERE id = ?", (document_id,)
                ).fetchone()
            return self._to_record(row) if row else None
        except (sqlite3.Error, ValueError, TypeError) as error:
            raise StorageError() from error

    def get_all(self, limit: int, offset: int) -> Tuple[List[DocumentRecord], int]:
        """Получить страницу истории и общее число записей."""
        try:
            with self.database.connect() as connection:
                total = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
                rows = connection.execute(
                    """
                    SELECT * FROM documents
                    ORDER BY created_at DESC, id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
            return [self._to_record(row) for row in rows], total
        except (sqlite3.Error, ValueError, TypeError) as error:
            raise StorageError() from error

    def is_healthy(self) -> bool:
        """Проверить доступность слоя хранения."""
        try:
            return self.database.is_healthy()
        except sqlite3.Error:
            return False

    def _update_status(self, document_id: int, status: DocumentStatus) -> None:
        """Обновить статус и время изменения записи."""
        try:
            with self.database.connect() as connection:
                connection.execute(
                    "UPDATE documents SET status = ?, updated_at = ? WHERE id = ?",
                    (status.value, utc_now().isoformat(), document_id),
                )
        except sqlite3.Error as error:
            raise StorageError() from error

    @staticmethod
    def _to_record(row: sqlite3.Row) -> DocumentRecord:
        """Преобразовать SQLite-строку в доменную модель."""
        data = dict(row)
        data["result"] = json.loads(data["result"]) if data["result"] else None
        return DocumentRecord.model_validate(data)
