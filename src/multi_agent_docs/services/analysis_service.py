import logging
from pathlib import Path
from queue import Queue
from threading import Event, Thread
from typing import Callable, List, Optional, Tuple

from ..config import Settings
from ..database.repository import DocumentRepository
from ..errors import AppError, PipelineError, UnsupportedFormatError
from ..ingestion.loader import validate_document
from ..llm.client import LLMClient, get_default_client
from ..models import DocumentRecord, PipelineResult
from ..runner import run_document

logger = logging.getLogger(__name__)

Runner = Callable[[str, LLMClient, Settings], PipelineResult]


class AnalysisService:
    def __init__(
        self,
        repository: DocumentRepository,
        settings: Settings,
        runner: Runner = run_document,
        llm_factory: Callable[[], LLMClient] = get_default_client,
    ):
        """Собрать бизнес-сервис с repository, runner и LLM-фабрикой."""
        self.repository = repository
        self.settings = settings
        self.runner = runner
        self.llm_factory = llm_factory
        self._queue: Queue[Optional[Tuple[int, Path]]] = Queue()
        self._stop = Event()
        self._worker: Optional[Thread] = None

    def initialize(self) -> None:
        """Подготовить БД, временный каталог и фоновый worker."""
        self.repository.initialize()
        self.repository.mark_interrupted()
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        for stale_file in self.settings.upload_dir.glob("analysis-*"):
            try:
                if stale_file.is_file():
                    stale_file.unlink()
            except OSError:
                logger.exception("Could not delete stale upload %s", stale_file)
        self._stop.clear()
        self._worker = Thread(target=self._worker_loop, name="analysis-worker", daemon=True)
        self._worker.start()

    def shutdown(self) -> None:
        """Остановить приём фоновых задач и дождаться worker."""
        self._stop.set()
        self._queue.put(None)
        if self._worker:
            self._worker.join(timeout=5)

    def submit(self, file_path: Path, original_filename: str) -> DocumentRecord:
        """Проверить файл, зарегистрировать задачу и поставить её в очередь."""
        extension = file_path.suffix.lower()
        if extension not in {".pdf", ".txt"}:
            raise UnsupportedFormatError()
        validate_document(str(file_path))
        record = self.repository.create(original_filename)
        self._queue.put((record.id, file_path))
        return record

    def get_document(self, document_id: int) -> Optional[DocumentRecord]:
        """Вернуть одну запись истории."""
        return self.repository.get_by_id(document_id)

    def list_documents(self, limit: int, offset: int) -> Tuple[List[DocumentRecord], int]:
        """Вернуть страницу истории анализов."""
        return self.repository.get_all(limit, offset)

    def is_healthy(self) -> bool:
        """Проверить repository и состояние фонового worker."""
        return (
            self.repository.is_healthy()
            and self._worker is not None
            and self._worker.is_alive()
        )

    def _worker_loop(self) -> None:
        """Последовательно выполнять задачи очереди и сохранять результат."""
        while not self._stop.is_set():
            item = self._queue.get()
            if item is None:
                self._queue.task_done()
                break
            document_id, file_path = item
            try:
                self.repository.mark_running(document_id)
                output = self.runner(str(file_path), self.llm_factory(), self.settings)
                result = {
                    "analysis": output.analysis,
                    "summary": output.summary,
                    "fact_check": output.fact_check.model_dump(),
                    "final": output.final,
                    "token_usage_by_agent": {
                        name: value.model_dump()
                        for name, value in output.token_usage.by_agent.items()
                    },
                }
                self.repository.complete(
                    document_id,
                    result,
                    output.fact_check.neuroslop.probability,
                    output.token_usage,
                )
            except AppError as error:
                logger.exception("Analysis %s failed: %s", document_id, error.code)
                self._safe_fail(document_id, error.code, error.public_message)
            except Exception:
                logger.exception("Unexpected error while processing analysis %s", document_id)
                error = PipelineError()
                self._safe_fail(document_id, error.code, error.public_message)
            finally:
                try:
                    file_path.unlink(missing_ok=True)
                except OSError:
                    logger.exception("Could not delete temporary file %s", file_path)
                self._queue.task_done()

    def _safe_fail(self, document_id: int, code: str, message: str) -> None:
        """Попытаться сохранить ошибку, не завершая worker."""
        try:
            self.repository.fail(document_id, code, message)
        except AppError:
            logger.exception("Could not persist failure for analysis %s", document_id)
