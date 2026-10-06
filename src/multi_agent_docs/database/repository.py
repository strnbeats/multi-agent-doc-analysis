from sqlalchemy.orm import Session

from .models import Analysis, Document, TokenUsage


def create_document(
    db: Session,
    filename: str,
    file_type: str,
    file_size: int,
) -> Document:
    document = Document(
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        status="pending",
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def update_document_status(
    db: Session,
    document_id: int,
    status: str,
    error: str | None = None,
) -> Document:
    document = db.get(Document, document_id)

    if document is None:
        raise ValueError(
            f"Document with id={document_id} not found"
        )

    document.status = status
    document.error = error

    db.commit()
    db.refresh(document)

    return document


def create_analysis(
    db: Session,
    document_id: int,
    analysis: str,
    summary: str,
    facts: str,
    final_result: str,
) -> Analysis:
    analysis_record = Analysis(
        document_id=document_id,
        status="completed",
        analysis=analysis,
        summary=summary,
        facts=facts,
        final_result=final_result,
    )

    db.add(analysis_record)
    db.commit()
    db.refresh(analysis_record)

    return analysis_record


def update_analysis(
    db: Session,
    analysis_id: int,
    analysis: str,
    summary: str,
    facts: str,
    final_result: str,
) -> Analysis:
    analysis_record = db.get(Analysis, analysis_id)

    if analysis_record is None:
        raise ValueError(
            f"Analysis with id={analysis_id} not found"
        )

    analysis_record.analysis = analysis
    analysis_record.summary = summary
    analysis_record.facts = facts
    analysis_record.final_result = final_result
    analysis_record.status = "completed"

    db.commit()
    db.refresh(analysis_record)

    return analysis_record


def create_token_usage(
    db: Session,
    analysis_id: int,
    agent_name: str,
    input_tokens: int,
    output_tokens: int,
) -> TokenUsage:
    total_tokens = input_tokens + output_tokens

    token_usage = TokenUsage(
        analysis_id=analysis_id,
        agent_name=agent_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )

    db.add(token_usage)
    db.commit()
    db.refresh(token_usage)

    return token_usage