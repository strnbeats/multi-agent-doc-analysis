from src.multi_agent_docs.database.db import SessionLocal
from src.multi_agent_docs.database.repository import (
    create_analysis,
    create_document,
    create_token_usage,
)


db = SessionLocal()

document = create_document(
    db=db,
    filename="test.pdf",
    file_type="pdf",
    file_size=12345,
)

print("Document ID:", document.id)


analysis = create_analysis(
    db=db,
    document_id=document.id,
    analysis="Документ посвящён тестированию базы данных.",
    summary="Тестовый документ.",
    facts="База данных содержит таблицу documents.",
    final_result="Анализ успешно сохранён.",
)

print("Analysis ID:", analysis.id)
print("Document ID:", analysis.document_id)
print("Status:", analysis.status)


analyzer_usage = create_token_usage(
    db=db,
    analysis_id=analysis.id,
    agent_name="Analyzer",
    input_tokens=4147,
    output_tokens=1000,
)

print(
    "Analyzer:",
    analyzer_usage.input_tokens,
    analyzer_usage.output_tokens,
    analyzer_usage.total_tokens,
)


summary_usage = create_token_usage(
    db=db,
    analysis_id=analysis.id,
    agent_name="Summary",
    input_tokens=1229,
    output_tokens=400,
)

print(
    "Summary:",
    summary_usage.input_tokens,
    summary_usage.output_tokens,
    summary_usage.total_tokens,
)


fact_checker_usage = create_token_usage(
    db=db,
    analysis_id=analysis.id,
    agent_name="FactChecker",
    input_tokens=4698,
    output_tokens=1482,
)

print(
    "FactChecker:",
    fact_checker_usage.input_tokens,
    fact_checker_usage.output_tokens,
    fact_checker_usage.total_tokens,
)


final_usage = create_token_usage(
    db=db,
    analysis_id=analysis.id,
    agent_name="Final",
    input_tokens=2969,
    output_tokens=950,
)

print(
    "Final:",
    final_usage.input_tokens,
    final_usage.output_tokens,
    final_usage.total_tokens,
)


db.close()