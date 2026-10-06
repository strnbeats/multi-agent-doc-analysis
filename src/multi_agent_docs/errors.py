from __future__ import annotations


class AppError(Exception):
    code = "application_error"
    public_message = "Ошибка приложения"

    def __init__(self, message: str | None = None):
        """Создать ошибку с безопасным публичным сообщением."""
        super().__init__(message or self.public_message)
        self.public_message = message or self.public_message


class UnsupportedFormatError(AppError):
    code = "unsupported_format"
    public_message = "Поддерживаются только PDF и TXT"


class EmptyDocumentError(AppError):
    code = "empty_document"
    public_message = "Документ пуст или не содержит извлекаемого текста"


class CorruptDocumentError(AppError):
    code = "corrupt_document"
    public_message = "Файл повреждён или не соответствует заявленному формату"


class DocumentTooLargeError(AppError):
    code = "document_too_large"
    public_message = "Документ превышает допустимый объём анализа"


class ExtractionError(AppError):
    code = "extraction_error"
    public_message = "Не удалось извлечь текст из документа"


class LLMError(AppError):
    code = "gigachat_error"
    public_message = "Ошибка при обращении к языковой модели"


class PipelineError(AppError):
    code = "pipeline_error"
    public_message = "Ошибка обработки документа"


class StorageError(AppError):
    code = "storage_error"
    public_message = "Ошибка хранилища"
