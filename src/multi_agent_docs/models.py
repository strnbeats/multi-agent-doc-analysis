from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TokenCount(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class TokenUsage(TokenCount):
    by_agent: Dict[str, TokenCount] = Field(default_factory=dict)

    def add(self, agent_name: str, usage: TokenCount) -> None:
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.total_tokens += usage.total_tokens
        current = self.by_agent.setdefault(agent_name, TokenCount())
        current.input_tokens += usage.input_tokens
        current.output_tokens += usage.output_tokens
        current.total_tokens += usage.total_tokens


class LLMAnswer(BaseModel):
    content: str
    usage: TokenCount


class NeuroslopResult(BaseModel):
    probability: float = Field(ge=0.0, le=1.0)
    explanation: str = Field(min_length=1)


class FactCheckResult(BaseModel):
    verification_summary: str
    doubtful_claims: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    neuroslop: NeuroslopResult


class PipelineResult(BaseModel):
    analysis: str
    summary: str
    fact_check: FactCheckResult
    final: str
    token_usage: TokenUsage


class DocumentRecord(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    filename: str
    created_at: datetime
    updated_at: datetime
    status: DocumentStatus
    result: Optional[Dict[str, Any]] = None
    neuroslop: Optional[float] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None

