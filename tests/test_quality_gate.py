from multi_agent_docs.agents.quality_gate import quality_gate


def complete_state():
    return {
        "analysis": "Основная тема документа.",
        "summary": "Краткое содержание документа.",
        "facts": (
            "ПОДТВЕРЖДЕНО: факт A.\n"
            "НЕ ПОДТВЕРЖДЕНО: факт B.\n"
            "ПРОТИВОРЕЧИТ: факт C."
        ),
        "revision_count": 0,
    }


def test_quality_gate_passes_complete_result():
    result = quality_gate(complete_state())

    assert result["quality_ok"] is True
    assert result["quality_feedback"] == ""
    assert result["retry_fact_checker"] is False
    assert result["revision_count"] == 0


def test_quality_gate_detects_missing_status():
    state = complete_state()
    state["facts"] = "ПОДТВЕРЖДЕНО: факт A."

    result = quality_gate(state)

    assert result["quality_ok"] is False
    assert "НЕ ПОДТВЕРЖДЕНО" in result["quality_feedback"]
    assert "ПРОТИВОРЕЧИТ" in result["quality_feedback"]
    assert result["retry_fact_checker"] is True
    assert result["revision_count"] == 1


def test_quality_gate_detects_empty_analysis():
    state = complete_state()
    state["analysis"] = ""

    result = quality_gate(state)

    assert result["quality_ok"] is False
    assert "Analyzer" in result["quality_feedback"]
    assert result["retry_fact_checker"] is False


def test_quality_gate_does_not_retry_twice():
    state = complete_state()
    state["facts"] = "ПОДТВЕРЖДЕНО: факт A."
    state["revision_count"] = 1

    result = quality_gate(state)

    assert result["quality_ok"] is False
    assert result["retry_fact_checker"] is False
    assert result["revision_count"] == 1


def test_quality_gate_does_not_retry_if_summary_is_empty():
    state = complete_state()
    state["summary"] = ""
    state["facts"] = "ПОДТВЕРЖДЕНО: факт A."

    result = quality_gate(state)

    assert result["quality_ok"] is False
    assert result["retry_fact_checker"] is False