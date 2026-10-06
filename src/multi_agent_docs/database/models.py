from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    filename: Mapped[str] = mapped_column(
        String(255)
    )

    file_type: Mapped[str] = mapped_column(
        String(50)
    )

    file_size: Mapped[int] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow
    )

    status: Mapped[str] = mapped_column(
        String(50)
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id")
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow
    )

    status: Mapped[str] = mapped_column(
        String(50)
    )

    analysis: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    facts: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    final_result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id: Mapped[int] = mapped_column(primary_key=True)

    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id")
    )

    agent_name: Mapped[str] = mapped_column(
        String(100)
    )

    input_tokens: Mapped[int] = mapped_column()

    output_tokens: Mapped[int] = mapped_column()

    total_tokens: Mapped[int] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow
    )