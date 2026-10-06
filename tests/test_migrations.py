import sqlite3

from multi_agent_docs.database.db import Database
from multi_agent_docs.database.migrations import downgrade_database, upgrade_database


def test_migrations_upgrade_and_downgrade(settings):
    """Alembic создаёт версию, таблицу и индексы и умеет откатываться."""
    database = Database(settings.database_path)
    database.initialize()
    with database.connect() as connection:
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        indexes = {
            row[1] for row in connection.execute("PRAGMA index_list('documents')").fetchall()
        }
    assert version == "0001"
    assert {"ix_documents_created_at", "ix_documents_status"} <= indexes

    downgrade_database(settings.database_path)
    with sqlite3.connect(settings.database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert "documents" not in tables

    upgrade_database(settings.database_path)
    assert database.is_healthy()


def test_migration_adopts_legacy_documents_table(settings):
    """Первая ревизия сохраняет таблицу, созданную старой версией приложения."""
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute(
            """
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                neuroslop REAL,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                error_code TEXT,
                error_message TEXT
            )
            """
        )
        connection.execute(
            "INSERT INTO documents(filename, created_at, updated_at, status) VALUES ('old.txt', '2026-01-01', '2026-01-01', 'completed')"
        )

    Database(settings.database_path).initialize()
    with sqlite3.connect(settings.database_path) as connection:
        assert connection.execute("SELECT filename FROM documents").fetchone()[0] == "old.txt"
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0001"
