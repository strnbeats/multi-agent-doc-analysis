from multi_agent_docs.database.db import Database
from multi_agent_docs.database.repository import DocumentRepository
from multi_agent_docs.models import TokenCount, TokenUsage


def test_repository_lifecycle_and_pagination(settings):
    repository = DocumentRepository(Database(settings.database_path))
    repository.initialize()
    first = repository.create("first.txt")
    second = repository.create("second.txt")
    repository.mark_running(first.id)
    usage = TokenUsage()
    usage.add("Analyzer", TokenCount(input_tokens=4, output_tokens=2, total_tokens=6))
    repository.complete(first.id, {"analysis": "ok"}, 0.4, usage)
    repository.fail(second.id, "pipeline_error", "Ошибка обработки документа")

    completed = repository.get_by_id(first.id)
    assert completed is not None
    assert completed.status == "completed"
    assert completed.result == {"analysis": "ok"}
    assert completed.total_tokens == 6

    items, total = repository.get_all(limit=1, offset=0)
    assert total == 2
    assert len(items) == 1
    assert items[0].id == second.id
    assert repository.get_by_id(99999) is None


def test_repository_marks_interrupted_jobs_failed(settings):
    repository = DocumentRepository(Database(settings.database_path))
    repository.initialize()
    record = repository.create("queued.txt")
    assert repository.mark_interrupted() == 1
    restored = repository.get_by_id(record.id)
    assert restored is not None
    assert restored.status == "failed"
    assert restored.error_code == "backend_restarted"

