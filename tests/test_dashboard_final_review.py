"""Проверки представления качества отдельно от статуса выполнения."""

import importlib.util
import json
import os
import unittest
from unittest.mock import patch

import httpx

from multi_agent_docs.api_schemas import DocumentDetail
from multi_agent_docs.dashboard import (
    View,
    build_dashboard,
    refresh_document,
    render_document,
)


def make_review(status):
    flagged = status == "needs_review"
    return {
        "status": status,
        "verification_summary": "Проверка итогового отчёта",
        "doubtful_claims": ["Итоговое сомнение"] if flagged else [],
        "contradictions": ["Итоговое противоречие"] if flagged else [],
    }


def make_detail(review, *, initial_has_flags=False):
    return {
        "id": 42,
        "filename": "document.txt",
        "status": "completed",
        "created_at": "2026-11-03T00:00:00Z",
        "updated_at": "2026-11-03T00:00:00Z",
        "token_usage": {"total_tokens": 150, "by_agent": {}},
        "results": {
            "analysis": "Анализ",
            "summary": "Сводка",
            "final": "Итоговый отчёт",
            "fact_check": {
                "verification_summary": "Первичная проверка",
                "doubtful_claims": ["Первичное сомнение"] if initial_has_flags else [],
                "contradictions": ["Первичное противоречие"] if initial_has_flags else [],
                "neuroslop": {"probability": 0.2, "explanation": "Эвристика"},
            },
            "final_review": review,
        },
    }


def refresh_payload(payload):
    return refresh_document(
        42, "http://api.test",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload)),
    )


class FinalReviewDashboardTests(unittest.TestCase):
    def test_quality_uses_final_review_and_keeps_execution_completed(self):
        for status, initial_has_flags in [
            ("needs_review", False), ("no_flags", True),
        ]:
            with self.subTest(status=status):
                view = refresh_payload(make_detail(
                    make_review(status), initial_has_flags=initial_has_flags,
                ))
                self.assertEqual(view.status, "completed — Завершён")
                self.assertTrue(view.final_review_status.startswith(f"{status} — "))
                primary = json.loads(view.fact_check)
                self.assertEqual(primary["doubtful_claims"], (
                    ["Первичное сомнение"] if initial_has_flags else []
                ))
                self.assertEqual(primary["contradictions"], (
                    ["Первичное противоречие"] if initial_has_flags else []
                ))
                if status == "needs_review":
                    self.assertIn("Итоговое сомнение", view.final_review_doubtful_claims)
                    self.assertIn("Итоговое противоречие", view.final_review_contradictions)
                    self.assertNotIn("Первичное", view.final_review_doubtful_claims)
                else:
                    self.assertEqual(view.final_review_doubtful_claims, "Не отмечены")
                    self.assertEqual(view.final_review_contradictions, "Не отмечены")

    def test_none_and_legacy_missing_review_display_warning(self):
        for include_field in [True, False]:
            with self.subTest(include_field=include_field):
                payload = make_detail(None)
                if not include_field:
                    del payload["results"]["final_review"]
                view = refresh_payload(payload)
                self.assertEqual(view.status, "completed — Завершён")
                self.assertEqual(view.final_review_status, "Итоговый отчёт не проверен")
                self.assertEqual(view.final_review_doubtful_claims, "")
                self.assertEqual(view.final_review_contradictions, "")

    def test_not_evaluated_is_not_shown_as_passed(self):
        view = refresh_payload(make_detail(make_review("not_evaluated")))
        self.assertIn("Итоговый отчёт не проверен", view.final_review_status)
        self.assertNotIn("no_flags", view.final_review_status)

    def test_running_task_has_no_quality_verdict(self):
        payload = make_detail(None)
        payload["status"] = "running"
        payload["results"] = None
        view = refresh_payload(payload)
        self.assertTrue(view.status.startswith("running"))
        self.assertEqual(view.final_review_status, "")
        self.assertEqual(view.final_review_doubtful_claims, "")
        self.assertEqual(view.final_review_contradictions, "")

    def test_unchecked_result_clears_previous_issue_fields(self):
        previous = refresh_payload(make_detail(make_review("needs_review")))
        self.assertTrue(previous.final_review_doubtful_claims)
        self.assertTrue(previous.final_review_contradictions)
        current = refresh_payload(make_detail(None))
        self.assertEqual(current.final_review_status, "Итоговый отчёт не проверен")
        self.assertEqual(current.final_review_doubtful_claims, "")
        self.assertEqual(current.final_review_contradictions, "")

    @unittest.skipUnless(importlib.util.find_spec("gradio"), "Установите extra dashboard")
    def test_gradio_events_bind_warning_to_visible_quality_component(self):
        with patch.dict(os.environ, {"GRADIO_ANALYTICS_ENABLED": "False"}):
            demo = build_dashboard()
        config = demo.config
        components = {component["id"]: component for component in config["components"]}

        def component_id(label):
            return next(
                key for key, component in components.items()
                if component.get("props", {}).get("label") == label
            )

        quality_id = component_id("Проверка итогового отчёта")
        status_id = component_id("Статус выполнения")
        doubts_id = component_id("Сомнительные утверждения итогового отчёта")
        contradictions_id = component_id("Противоречия итогового отчёта")
        bindings = [
            dependency for dependency in config["dependencies"]
            if quality_id in dependency.get("outputs", [])
        ]
        self.assertEqual(len(bindings), 2)  # загрузка и обновление по ID
        view = render_document(DocumentDetail.model_validate(make_detail(None)))
        for binding in bindings:
            self.assertEqual(len(binding["outputs"]), len(View._fields))
            displayed = dict(zip(binding["outputs"], view))
            self.assertEqual(displayed[quality_id], "Итоговый отчёт не проверен")
            self.assertTrue(displayed[status_id].startswith("completed"))
            self.assertEqual(displayed[doubts_id], "")
            self.assertEqual(displayed[contradictions_id], "")
