REQUIRED_STATUSES = (
    "ПОДТВЕРЖДЕНО",
    "НЕ ПОДТВЕРЖДЕНО",
    "ПРОТИВОРЕЧИТ",
)


def quality_gate(state):
    analysis = state.get("analysis", "").strip()
    summary = state.get("summary", "").strip()
    facts = state.get("facts", "").strip()
    revision_count = state.get("revision_count", 0)

    problems = []

    if not analysis:
        problems.append("Analyzer не вернул анализ документа.")

    if not summary:
        problems.append("Summary не вернул краткое содержание.")

    missing_statuses = []

    if not facts:
        problems.append("Fact Checker не вернул результат проверки.")
        missing_statuses = list(REQUIRED_STATUSES)
    else:
        missing_statuses = [
            status
            for status in REQUIRED_STATUSES
            if status not in facts
        ]

        if missing_statuses:
            problems.append(
                "В результате проверки отсутствуют статусы: "
                + ", ".join(missing_statuses)
            )

    retry_fact_checker = (
        bool(analysis)
        and bool(summary)
        and bool(missing_statuses)
        and revision_count < 1
    )

    return {
        "quality_ok": not problems,
        "quality_feedback": "\n".join(problems),
        "retry_fact_checker": retry_fact_checker,
        "revision_count": (
            revision_count + 1
            if retry_fact_checker
            else revision_count
        ),
    }