"""Описание интерфейсов для сравнения с зафиксированным эталоном contracts/v1.json."""
import inspect
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from . import agent_contracts as contracts
from . import graph, models, orchestration, runner
from .agents.analyzer import analyzer
from .agents.fact_checker import fact_checker
from .agents.final import final_agent
from .agents.summary import summary
from .api_schemas import AnalysisResults
from .llm.client import LLMClient


NODE_FUNCTIONS = {
    "analyzer": analyzer, "summary": summary, "fact_checker": fact_checker,
    "final": final_agent, "verify_final": graph.verify_final,
    "prepare_sources": graph.prepare_sources,
    "mark_no_flags": graph.mark_no_flags, "mark_needs_review": graph.mark_needs_review,
}


def describe_type(annotation):
    if annotation is Any:
        return "Any"
    origin = get_origin(annotation)
    if origin is Literal:
        return {"literal": list(get_args(annotation))}
    if origin:
        name = "union" if origin is Union else origin.__name__
        return {name: [describe_type(arg) for arg in get_args(annotation)]}
    return annotation.__name__


def describe_signature(function):
    hints = get_type_hints(function)
    parameters = []
    for name, parameter in inspect.signature(function).parameters.items():
        if name == "self":
            continue
        item = {"name": name, "kind": parameter.kind.name,
                "type": describe_type(hints[name])}
        if parameter.default is not inspect.Parameter.empty:
            item["default"] = parameter.default
        parameters.append(item)
    return {"parameters": parameters, "returns": describe_type(hints["return"])}


def describe_record(record):
    return {
        "required": sorted(record.__required_keys__),
        "optional": sorted(record.__optional_keys__),
        "fields": {name: describe_type(value) for name, value in get_type_hints(record).items()},
    }


def _structural_schema(value):
    # Изменение описания/заголовка не является изменением формата данных.
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in {"title", "description", "$comment"}:
                continue
            if key in {"properties", "$defs", "definitions", "patternProperties"}:
                # Название поля "description" — часть контракта, а не метаданные.
                result[key] = {name: _structural_schema(schema) for name, schema in item.items()}
            elif key in {"default", "const", "enum", "examples"}:
                result[key] = item
            else:
                result[key] = _structural_schema(item)
        return result
    if isinstance(value, list):
        return [_structural_schema(item) for item in value]
    return value


def build_manifest():
    records = [
        contracts.AgentState, contracts.SourceChunk, contracts.NeuroslopPayload,
        contracts.FactCheckPayload, contracts.FinalReviewDraft, contracts.FinalReviewState,
        orchestration.WorkflowState, orchestration.DocumentChunk, orchestration.ChunkResult,
    ]
    schemas = [models.DocumentMetadata, models.TokenCount, models.TokenUsage,
               models.LLMAnswer, models.FactCheckResult, models.FinalReview,
               models.PipelineResult, AnalysisResults]
    nodes = {}
    for name, spec in contracts.NODE_CONTRACTS.items():
        function = NODE_FUNCTIONS[name]
        nodes[name] = {
            "input": describe_record(spec.input_type), "output": describe_record(spec.output_type),
            "usage_agent": spec.usage_agent,
            "signature": describe_signature(function),
            "runtime_guard": getattr(function, "agent_contract", None),
        }
    graphs = {"short": graph.app, "chunk": graph.chunk_app,
              "synthesis": graph.synthesis_app, "document": runner.document_app}
    return {
        "version": contracts.CONTRACT_VERSION,
        "nodes": nodes,
        "records": {record.__name__: describe_record(record) for record in records},
        "schemas": {model.__name__: _structural_schema(model.model_json_schema()) for model in schemas},
        "llm": {name: describe_signature(getattr(LLMClient, name)) for name in ("ask", "count_tokens")},
        "graphs": {name: sorted(
            [{"source": edge.source, "target": edge.target, "conditional": edge.conditional}
             for edge in app.get_graph().edges], key=lambda edge: (edge["source"], edge["target"])
        ) for name, app in graphs.items()},
    }
