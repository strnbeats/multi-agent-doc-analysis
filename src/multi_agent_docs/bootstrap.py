from __future__ import annotations

from .config import Settings
from .database.db import Database
from .database.repository import DocumentRepository
from .llm.mock_client import MockLLMClient
from .services.analysis_service import AnalysisService


def create_analysis_service(settings: Settings | None = None) -> AnalysisService:
    """Собрать сервис с реальным или mock LLM согласно APP_MODE."""
    settings = settings or Settings.from_env()
    database = Database(settings.database_path)
    repository = DocumentRepository(database)
    if settings.app_mode == "mock":
        return AnalysisService(repository, settings, llm_factory=MockLLMClient)
    return AnalysisService(repository, settings)
