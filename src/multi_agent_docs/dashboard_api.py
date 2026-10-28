"""HTTP-клиент интерфейса: анализ исполняет только backend."""
from __future__ import annotations

import mimetypes
from pathlib import Path

import httpx

from .api_schemas import AcceptedAnalysis, DocumentDetail


class DashboardError(Exception):
    """Сообщение для пользователя интерфейса."""


class AnalysisAPI:
    def __init__(self, base_url: str, *, transport=None):
        self.client = httpx.Client(base_url=base_url.rstrip("/"), timeout=30, transport=transport)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def _request(self, method: str, path: str, model, **kwargs):
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.RequestError as error:
            raise DashboardError("Не удалось связаться с API. Проверьте, что backend запущен.") from error
        if response.is_error:
            message = f"API вернул HTTP {response.status_code}"
            try:
                detail = response.json().get("detail")
                if isinstance(detail, dict) and isinstance(detail.get("message"), str):
                    message = detail["message"]
            except (ValueError, AttributeError):
                pass
            raise DashboardError(message)
        try:
            return model.model_validate(response.json())
        except ValueError as error:
            raise DashboardError("API вернул ответ несовместимого формата.") from error

    def submit(self, file_path: str) -> AcceptedAnalysis:
        path = Path(file_path)
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        try:
            with path.open("rb") as source:
                return self._request("POST", "/analyze", AcceptedAnalysis,
                                     files={"file": (path.name, source, mime)})
        except OSError as error:
            raise DashboardError("Не удалось прочитать загруженный файл.") from error

    def get_document(self, document_id: int) -> DocumentDetail:
        return self._request("GET", f"/documents/{document_id}", DocumentDetail)
