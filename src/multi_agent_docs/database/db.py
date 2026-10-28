import sqlite3
from pathlib import Path

from .migrations import upgrade_database


class Database:
    def __init__(self, path: Path):
        """Сохранить путь к SQLite-файлу."""
        self.path = path

    def connect(self) -> sqlite3.Connection:
        """Открыть настроенное SQLite-подключение."""
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        """Применить миграции и настроить журнал SQLite."""
        upgrade_database(self.path)
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")

    def is_healthy(self) -> bool:
        """Проверить, что SQLite принимает запросы."""
        with self.connect() as connection:
            return connection.execute("SELECT 1").fetchone()[0] == 1
