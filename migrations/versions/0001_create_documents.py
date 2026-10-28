"""Создать таблицу истории анализов.

Revision ID: 0001
Revises: None
"""
from typing import Optional, Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Optional[str] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создать documents и индексы, сохранив совместимость со старой SQLite."""
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "documents" not in inspector.get_table_names():
        op.create_table(
            "documents",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("filename", sa.Text(), nullable=False),
            sa.Column("created_at", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("result", sa.Text(), nullable=True),
            sa.Column("neuroslop", sa.Float(), nullable=True),
            sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_code", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.CheckConstraint(
                "status IN ('queued', 'running', 'completed', 'failed')",
                name="ck_documents_status",
            ),
            sa.CheckConstraint(
                "neuroslop IS NULL OR (neuroslop >= 0 AND neuroslop <= 1)",
                name="ck_documents_neuroslop",
            ),
            sa.CheckConstraint("input_tokens >= 0", name="ck_documents_input_tokens"),
            sa.CheckConstraint("output_tokens >= 0", name="ck_documents_output_tokens"),
            sa.CheckConstraint("total_tokens >= 0", name="ck_documents_total_tokens"),
        )

    inspector = sa.inspect(connection)
    indexes = {item["name"] for item in inspector.get_indexes("documents")}
    if "ix_documents_created_at" not in indexes:
        op.create_index("ix_documents_created_at", "documents", ["created_at", "id"])
    if "ix_documents_status" not in indexes:
        op.create_index("ix_documents_status", "documents", ["status"])


def downgrade() -> None:
    """Удалить таблицу истории вместе с индексами."""
    connection = op.get_bind()
    if "documents" in sa.inspect(connection).get_table_names():
        op.drop_table("documents")
