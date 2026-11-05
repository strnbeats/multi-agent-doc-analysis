"""Версия 1 интерфейсов узлов. Промпты и формулировки ответов не фиксируются."""
from copy import deepcopy
from dataclasses import dataclass
from functools import wraps
from types import MappingProxyType
from typing import Any, Dict, List, Literal, TypedDict

from pydantic import ValidationError

from .errors import PipelineError
from .llm.client import LLMClient
from .models import DocumentMetadata, FactCheckResult, FinalReview, TokenCount, TokenUsage


CONTRACT_VERSION = 1
ReviewStatus = Literal["not_evaluated", "no_flags", "needs_review"]


class SourceChunk(TypedDict):
    chunk_id: str
    text: str


class NeuroslopPayload(TypedDict):
    probability: float
    explanation: str


class FactCheckPayload(TypedDict):
    verification_summary: str
    doubtful_claims: List[str]
    contradictions: List[str]
    neuroslop: NeuroslopPayload


class FinalReviewDraft(TypedDict):
    """Отдельный результат проверки отчёта: без оценки нейрослопа документа."""

    verification_summary: str
    doubtful_claims: List[str]
    contradictions: List[str]


class FinalReviewState(FinalReviewDraft):
    status: ReviewStatus


class RuntimeInput(TypedDict):
    llm: LLMClient
    token_usage: TokenUsage


class AnalyzerInput(RuntimeInput):
    text: str


class AnalyzerOutput(TypedDict):
    analysis: str
    token_usage: TokenUsage


class SummaryInput(RuntimeInput):
    analysis: str


class SummaryOutput(TypedDict):
    summary: str
    token_usage: TokenUsage


class _FactCheckerRequired(RuntimeInput):
    text: str
    analysis: str


class FactCheckerInput(_FactCheckerRequired, total=False):
    summary: str


class FactCheckerOutput(TypedDict):
    fact_check: FactCheckPayload
    token_usage: TokenUsage


class FinalInput(RuntimeInput):
    analysis: str
    summary: str
    fact_check: FactCheckPayload


class FinalOutput(TypedDict):
    final: str
    token_usage: TokenUsage


class _FinalVerificationRequired(RuntimeInput):
    source_chunks: List[SourceChunk]
    final: str


class FinalVerificationInput(_FinalVerificationRequired, total=False):
    summary: str


class FinalVerificationOutput(TypedDict):
    final_review: FinalReviewDraft
    token_usage: TokenUsage


class SourceInput(TypedDict):
    text: str


class SourceOutput(TypedDict):
    source_chunks: List[SourceChunk]


class ReviewInput(TypedDict):
    final_review: FinalReviewDraft


class ReviewOutput(TypedDict):
    final_review: FinalReviewState


class AgentState(TypedDict):
    text: str
    metadata: DocumentMetadata
    analysis: str
    summary: str
    fact_check: Dict[str, Any]
    final: str
    llm: LLMClient
    token_usage: TokenUsage
    source_chunks: List[SourceChunk]
    final_review: Dict[str, Any]


@dataclass(frozen=True)
class NodeContract:
    input_type: type
    output_type: type
    usage_agent: str = ""


NODE_CONTRACTS = MappingProxyType({
    "analyzer": NodeContract(AnalyzerInput, AnalyzerOutput, "Analyzer"),
    "summary": NodeContract(SummaryInput, SummaryOutput, "Summary"),
    "fact_checker": NodeContract(FactCheckerInput, FactCheckerOutput, "Fact Checker"),
    "final": NodeContract(FinalInput, FinalOutput, "Final"),
    "verify_final": NodeContract(FinalVerificationInput, FinalVerificationOutput, "Final Verification"),
    "prepare_sources": NodeContract(SourceInput, SourceOutput),
    "mark_no_flags": NodeContract(ReviewInput, ReviewOutput),
    "mark_needs_review": NodeContract(ReviewInput, ReviewOutput),
})


def _validate_field(name, value, *, review_has_status=False):
    if name in {"text", "analysis", "summary", "final"}:
        return isinstance(value, str)
    if name == "llm":
        return callable(getattr(value, "ask", None))
    if name == "token_usage":
        return isinstance(value, TokenUsage)
    if name == "source_chunks":
        return isinstance(value, list) and bool(value) and all(
            isinstance(chunk, dict) and set(chunk) == {"chunk_id", "text"}
            and isinstance(chunk["chunk_id"], str) and isinstance(chunk["text"], str)
            for chunk in value
        )
    if name in {"fact_check", "final_review"}:
        if not isinstance(value, dict):
            return False
        payload_type = FactCheckPayload if name == "fact_check" else FinalReviewDraft
        expected = set(payload_type.__required_keys__)
        if review_has_status:
            expected.add("status")
        if set(value) != expected:
            return False
        if review_has_status and value["status"] not in {"not_evaluated", "no_flags", "needs_review"}:
            return False
        try:
            if name == "fact_check":
                if not isinstance(value["neuroslop"], dict) or set(value["neuroslop"]) != {"probability", "explanation"}:
                    return False
                FactCheckResult.model_validate(value, strict=True)
            else:
                checked = dict(value)
                checked.setdefault("status", "not_evaluated")
                FinalReview.model_validate(checked, strict=True)
        except ValidationError:
            return False
        return True
    return False


def agent_node(name):
    """Ограничить чтение объявленными входами, а запись — объявленным patch."""
    contract = NODE_CONTRACTS[name]

    def decorate(function):
        @wraps(function)
        def checked(state):
            required = contract.input_type.__required_keys__
            allowed = required | contract.input_type.__optional_keys__
            if not isinstance(state, dict) or not required <= state.keys():
                raise PipelineError(f"Нарушен контракт {name}: отсутствуют обязательные входы")
            for key in allowed & state.keys():
                if not _validate_field(key, state[key]):
                    raise PipelineError(f"Нарушен контракт {name}: неверный тип входа {key}")
            # Содержимое документа/проверки не должно меняться через общие ссылки.
            inputs = {key: state[key] if key == "llm" else deepcopy(state[key])
                      for key in allowed & state.keys()}
            previous = inputs["token_usage"].model_copy(deep=True) if contract.usage_agent else None
            result = function(inputs)
            if not isinstance(result, dict) or set(result) != set(contract.output_type.__required_keys__):
                raise PipelineError(f"Нарушен контракт {name}: изменены поля результата")
            for key, value in result.items():
                if not _validate_field(key, value, review_has_status=contract.output_type is ReviewOutput):
                    raise PipelineError(f"Нарушен контракт {name}: неверный тип результата {key}")
            if previous is not None:
                current = result["token_usage"]
                other_names = (previous.by_agent.keys() | current.by_agent.keys()) - {contract.usage_agent}
                if any(previous.by_agent.get(agent) != current.by_agent.get(agent) for agent in other_names):
                    raise PipelineError(f"Нарушен контракт {name}: изменена статистика другого агента")
                if any(getattr(current, field) < getattr(previous, field)
                       for field in ("input_tokens", "output_tokens", "total_tokens")):
                    raise PipelineError(f"Нарушен контракт {name}: сброшена статистика токенов")
                old_own = previous.by_agent.get(contract.usage_agent, TokenCount())
                new_own = current.by_agent.get(contract.usage_agent, TokenCount())
                if any(getattr(current, field) - getattr(previous, field)
                       != getattr(new_own, field) - getattr(old_own, field)
                       for field in ("input_tokens", "output_tokens", "total_tokens")):
                    raise PipelineError(f"Нарушен контракт {name}: расход не совпадает со статистикой агента")
            return result

        checked.agent_contract = name
        return checked

    return decorate
