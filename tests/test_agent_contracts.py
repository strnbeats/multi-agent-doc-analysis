"""Интерфейсные проверки: эталон не обновляется автоматически при запуске CI."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from multi_agent_docs.agent_contracts import NODE_CONTRACTS, agent_node
from multi_agent_docs.contract_manifest import NODE_FUNCTIONS, _structural_schema, build_manifest, describe_signature
from multi_agent_docs.errors import PipelineError
from multi_agent_docs.graph import route_review
from multi_agent_docs.llm.client import GigaChatClient, LLMClient
from multi_agent_docs.llm.mock_client import MockLLMClient
from multi_agent_docs.models import TokenCount, TokenUsage


BASELINE = Path(__file__).parents[1] / "contracts" / "v1.json"
LLM_NODES = [name for name, spec in NODE_CONTRACTS.items() if spec.usage_agent]


def state():
    fact_check = dict(verification_summary="Проверено", doubtful_claims=[], contradictions=[],
                      neuroslop=dict(probability=.2, explanation="Эвристика"))
    return dict(text="Исходный документ.", analysis="Анализ.", summary="Сводка.",
                final="Отчёт.", fact_check=deepcopy(fact_check), final_review=fact_check,
                source_chunks=[dict(chunk_id="chunk_0001", text="Исходный документ.")],
                llm=MockLLMClient(), token_usage=TokenUsage())


def test_interfaces_match_reviewed_v1_baseline():
    expected = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert build_manifest() == expected, (
        "Изменился контракт агентов. Не обновляйте эталон автоматически: "
        "согласуйте изменение интерфейса, совместимость и tests с ответственными."
    )


def test_schema_comparison_preserves_property_names_and_literal_defaults():
    schema = {"title": "Display name", "description": "Documentation",
              "properties": {"description": {"type": "string", "default": ""},
                             "options": {"type": "object", "default": {"title": "value"}}}}
    normalized = _structural_schema(schema)
    assert "title" not in normalized and "description" not in normalized
    assert normalized["properties"]["description"] == {"type": "string", "default": ""}
    assert normalized["properties"]["options"]["default"] == {"title": "value"}


@pytest.mark.parametrize("implementation", [GigaChatClient, MockLLMClient])
@pytest.mark.parametrize("method", ["ask", "count_tokens"])
def test_real_and_mock_clients_implement_same_interface(implementation, method):
    assert describe_signature(getattr(implementation, method)) == describe_signature(getattr(LLMClient, method))


@pytest.mark.parametrize("name", NODE_CONTRACTS)
def test_existing_nodes_return_only_owned_fields(name):
    source = state()
    before = deepcopy({key: value for key, value in source.items() if key not in {"llm", "token_usage"}})
    result = NODE_FUNCTIONS[name](source)
    assert set(result) == set(NODE_CONTRACTS[name].output_type.__required_keys__)
    assert {key: value for key, value in source.items() if key not in {"llm", "token_usage"}} == before


MISSING_INPUTS = [(name, key) for name, spec in NODE_CONTRACTS.items()
                  for key in sorted(spec.input_type.__required_keys__)]


@pytest.mark.parametrize("name,key", MISSING_INPUTS)
def test_missing_required_input_fails_at_node_boundary(name, key):
    source = state()
    del source[key]
    with pytest.raises(PipelineError, match="контракт"):
        NODE_FUNCTIONS[name](source)


@pytest.mark.parametrize("name", LLM_NODES)
def test_renamed_or_extra_output_is_rejected(name):
    @agent_node(name)
    def broken(source):
        return {"renamed_result": "неверное поле", "token_usage": source["token_usage"]}

    with pytest.raises(PipelineError, match="поля результата"):
        broken(state())


@pytest.mark.parametrize("bad_value", [None, 42, {"text": "не строка"}])
def test_summary_format_change_is_rejected(bad_value):
    @agent_node("summary")
    def broken(source):
        return {"summary": bad_value, "token_usage": source["token_usage"]}

    with pytest.raises(PipelineError, match="тип результата summary"):
        broken(state())


def test_fact_check_cannot_be_renamed_to_legacy_facts_or_extended_silently():
    @agent_node("fact_checker")
    def broken(source):
        payload = state()["fact_check"]
        payload["new_status"] = "passed"
        return {"fact_check": payload, "token_usage": source["token_usage"]}

    with pytest.raises(PipelineError, match="тип результата fact_check"):
        broken(state())


def test_undeclared_inputs_are_not_available_and_nested_inputs_are_isolated():
    @agent_node("final")
    def isolated(source):
        assert "text" not in source
        source["fact_check"]["doubtful_claims"].append("внутренняя правка")
        return {"final": "Отчёт", "token_usage": source["token_usage"]}

    original = state()
    isolated(original)
    assert original["fact_check"]["doubtful_claims"] == []


def test_agent_cannot_rewrite_other_agents_usage():
    @agent_node("summary")
    def broken(source):
        source["token_usage"].add("Analyzer", TokenCount(total_tokens=1))
        return {"summary": "Сводка", "token_usage": source["token_usage"]}

    original = state()
    with pytest.raises(PipelineError, match="статистика другого агента"):
        broken(original)
    assert original["token_usage"].by_agent == {}


def test_agent_cannot_reset_accumulated_usage():
    @agent_node("summary")
    def broken(source):
        return {"summary": "Сводка", "token_usage": TokenUsage()}

    original = state()
    original["token_usage"].add("Analyzer", TokenCount(total_tokens=10))
    with pytest.raises(PipelineError, match="контракт"):
        broken(original)


def test_agent_cannot_change_total_without_its_usage_label():
    @agent_node("summary")
    def broken(source):
        source["token_usage"].total_tokens += 10
        return {"summary": "Сводка", "token_usage": source["token_usage"]}

    with pytest.raises(PipelineError, match="расход не совпадает"):
        broken(state())


def test_valid_node_returns_accumulated_usage_without_mutating_callers_state():
    original = state()
    original["token_usage"].add("Analyzer", TokenCount(input_tokens=7, output_tokens=3, total_tokens=10))
    result = NODE_FUNCTIONS["summary"](original)
    assert original["token_usage"].total_tokens == 10
    assert result["token_usage"].total_tokens == 40
    assert result["token_usage"].by_agent["Analyzer"].total_tokens == 10
    assert result["token_usage"].by_agent["Summary"].total_tokens == 30


@pytest.mark.parametrize("key", ["doubtful_claims", "contradictions"])
def test_final_quality_route_uses_final_review_not_primary_check(key):
    source = state()
    source["final_review"][key] = ["Замечание к итогу"]
    assert route_review(source) == "needs_review"
    source["final_review"][key] = []
    source["fact_check"][key] = ["Замечание к анализу"]
    assert route_review(source) == "no_flags"
