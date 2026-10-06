from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .models import DocumentStatus, FactCheckResult, NeuroslopResult, TokenCount


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    detail: ErrorDetail


class AcceptedAnalysis(BaseModel):
    id: int
    filename: str
    created_at: datetime
    status: DocumentStatus


class TokenUsageResponse(TokenCount):
    by_agent: Dict[str, TokenCount] = Field(default_factory=dict)


class AnalysisResults(BaseModel):
    analysis: str
    summary: str
    fact_check: FactCheckResult
    final: str


class DocumentListItem(BaseModel):
    id: int
    filename: str
    created_at: datetime
    updated_at: datetime
    status: DocumentStatus
    neuroslop_probability: Optional[float] = None
    token_usage: TokenCount
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class DocumentListResponse(BaseModel):
    items: List[DocumentListItem]
    total: int
    limit: int
    offset: int


class DocumentDetail(BaseModel):
    id: int
    filename: str
    created_at: datetime
    updated_at: datetime
    status: DocumentStatus
    neuroslop: Optional[NeuroslopResult] = None
    results: Optional[AnalysisResults] = None
    token_usage: TokenUsageResponse
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
