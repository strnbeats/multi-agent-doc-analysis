from contextlib import asynccontextmanager
import logging
from pathlib import Path
import tempfile

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse

from .api_schemas import (
    AcceptedAnalysis,
    AnalysisResults,
    DocumentDetail,
    DocumentListItem,
    DocumentListResponse,
    ErrorResponse,
    HealthResponse,
    TokenUsageResponse,
)
from .bootstrap import create_analysis_service
from .errors import AppError, StorageError, UnsupportedFormatError
from .models import NeuroslopResult, TokenCount

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Создать сервис на старте и корректно остановить его при завершении."""
    service = create_analysis_service()
    service.initialize()
    app.state.analysis_service = service
    try:
        yield
    finally:
        service.shutdown()


app = FastAPI(
    title="Multi-Agent Document Analysis",
    description="Асинхронный API анализа PDF и TXT документов",
    version="0.2.0",
    lifespan=lifespan,
)


def _service(request: Request):
    """Получить бизнес-сервис из состояния FastAPI."""
    return request.app.state.analysis_service


def _error(error: AppError, status_code: int) -> HTTPException:
    """Преобразовать прикладную ошибку в безопасную HTTP-ошибку."""
    return HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": error.public_message},
    )


def _list_item(record) -> DocumentListItem:
    """Преобразовать запись БД в облегчённый элемент истории."""
    return DocumentListItem(
        id=record.id,
        filename=record.filename,
        created_at=record.created_at,
        updated_at=record.updated_at,
        status=record.status,
        neuroslop_probability=record.neuroslop,
        token_usage=TokenCount(
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            total_tokens=record.total_tokens,
        ),
        error_code=record.error_code,
        error_message=record.error_message,
    )


def _detail(record) -> DocumentDetail:
    """Преобразовать запись БД в полный публичный ответ API."""
    stored = record.result or {}
    fact_check = stored.get("fact_check")
    results = None
    neuroslop = None
    by_agent = stored.get("token_usage_by_agent", {})
    if record.status == "completed" and fact_check:
        results = AnalysisResults(
            analysis=stored["analysis"],
            summary=stored["summary"],
            fact_check=fact_check,
            final=stored["final"],
        )
        neuroslop = NeuroslopResult.model_validate(fact_check["neuroslop"])
    return DocumentDetail(
        id=record.id,
        filename=record.filename,
        created_at=record.created_at,
        updated_at=record.updated_at,
        status=record.status,
        neuroslop=neuroslop,
        results=results,
        token_usage=TokenUsageResponse(
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            total_tokens=record.total_tokens,
            by_agent=by_agent,
        ),
        error_code=record.error_code,
        error_message=record.error_message,
    )


@app.get("/", include_in_schema=False)
def root():
    """Вернуть краткую информацию о backend и ссылку на Swagger."""
    return {"message": "Multi-Agent Document Analysis API", "docs": "/docs"}


@app.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse}},
    tags=["system"],
)
def health(request: Request):
    """Проверить доступность базы и фонового worker."""
    if not _service(request).is_healthy():
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return HealthResponse(status="ok")


@app.post(
    "/analyze",
    response_model=AcceptedAnalysis,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    tags=["analysis"],
)
async def analyze_document(request: Request, file: UploadFile = File(...)):
    """Принять документ, ограничить загрузку и поставить анализ в очередь."""
    service = _service(request)
    filename = Path(file.filename or "").name
    if not filename:
        raise HTTPException(status_code=400, detail={"code": "missing_filename", "message": "Файл не имеет имени"})
    extension = Path(filename).suffix.lower()
    allowed_types = {
        ".pdf": {"application/pdf", "application/octet-stream"},
        ".txt": {"text/plain", "application/octet-stream"},
    }
    if extension not in allowed_types:
        raise _error(UnsupportedFormatError(), 415)
    if file.content_type and file.content_type not in allowed_types[extension]:
        raise _error(UnsupportedFormatError("Тип содержимого не соответствует расширению файла"), 415)

    service.settings.upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = None
    size = 0
    try:
        with tempfile.NamedTemporaryFile(
            dir=service.settings.upload_dir,
            prefix="analysis-",
            suffix=extension,
            delete=False,
        ) as target:
            temp_path = Path(target.name)
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > service.settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail={"code": "upload_too_large", "message": "Файл превышает лимит 100 МБ"},
                    )
                target.write(chunk)
        if size == 0:
            raise HTTPException(
                status_code=400,
                detail={"code": "empty_document", "message": "Загружен пустой файл"},
            )
        record = service.submit(temp_path, filename)
        temp_path = None
        return AcceptedAnalysis(
            id=record.id,
            filename=record.filename,
            created_at=record.created_at,
            status=record.status,
        )
    except HTTPException:
        raise
    except UnsupportedFormatError as error:
        raise _error(error, 415) from error
    except AppError as error:
        status_code = 500 if isinstance(error, StorageError) else 400
        raise _error(error, status_code) from error
    except Exception as error:
        logger.exception("Unexpected upload error")
        raise HTTPException(
            status_code=500,
            detail={"code": "internal_error", "message": "Внутренняя ошибка backend"},
        ) from error
    finally:
        await file.close()
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@app.get("/documents", response_model=DocumentListResponse, tags=["documents"])
def list_documents(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Вернуть отсортированную страницу истории анализов."""
    try:
        records, total = _service(request).list_documents(limit, offset)
        return DocumentListResponse(
            items=[_list_item(record) for record in records],
            total=total,
            limit=limit,
            offset=offset,
        )
    except AppError as error:
        raise _error(error, 500) from error


@app.get(
    "/documents/{document_id}",
    response_model=DocumentDetail,
    responses={404: {"model": ErrorResponse}},
    tags=["documents"],
)
def get_document(document_id: int, request: Request):
    """Вернуть состояние и результат конкретного анализа."""
    try:
        record = _service(request).get_document(document_id)
    except AppError as error:
        raise _error(error, 500) from error
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Анализ не найден"},
        )
    return _detail(record)
