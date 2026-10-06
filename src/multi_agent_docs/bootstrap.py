from __future__ import annotations

from .config import Settings
from .database.db import Database
from .database.repository import DocumentRepository
from .services.analysis_service import AnalysisService


def create_analysis_service(settings: Settings | None = None) -> AnalysisService:
    settings = settings or Settings.from_env()
    database = Database(settings.database_path)
    repository = DocumentRepository(database)
    return AnalysisService(repository, settings)
