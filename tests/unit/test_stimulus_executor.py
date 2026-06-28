import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.facilitator.stimulus_executor import (
    BROWSER_BEHAVIOR_EXECUTOR_VERSION,
    BrowserBehaviorTraceExecutor,
    ScriptedClickablePrototypeExecutor,
    StimulusExecutionError,
)


class StimulusExecutorTest(unittest.TestCase):
    def test_browser_behavior_executor_normalizes_browser_events_to_observed_trace(self) -> None:
        payload = {
            "trace_version": "browser-behavior-trace/v1",
            "prototype_label": "Hosted Evidence Workspace",
            "trace_label": "browser-review-run",
            "driver": "playwright",
            "session": {
                "start_url": "http://127.0.0.1:4173/prototype.html",
                "final_url": "http://127.0.0.1:4173/prototype.html#evidence",
                "viewport": {"width": 1280, "height": 800},
            },
            "events": [
                {
                    "type": "navigation",
                    "url": "http://127.0.0.1:4173/prototype.html",
                    "page_title": "Prototype",
                    "timestamp_ms": 0,
                },
                {
                    "type": "click",
                    "selector": "[data-action='open-evidence']",
                    "target": "open evidence button",
                    "page_title": "Prototype",
                    "timestamp_ms": 420,
                    "duration_ms": 35,
                },
                {
                    "type": "click",
                    "selector": "[data-action='confirm-review']",
                    "target": "confirm review button",
                    "page_title": "Evidence Drawer",
                    "timestamp_ms": 900,
                    "result": "success",
                },
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "browser-trace.json"
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            executor = BrowserBehaviorTraceExecutor()
            result = executor.execute(
                artifact_path=artifact,
                payload=payload,
                prototype_task="Review one recommendation and decide whether to act on it.",
            )

        self.assertEqual(result["executor_version"], BROWSER_BEHAVIOR_EXECUTOR_VERSION)
        self.assertEqual(result["stimulus_analysis"]["analysis_type"], "browser_clickable_trace")
        self.assertEqual(result["stimulus_analysis"]["safety_gate"]["status"], "allowed")
        self.assertEqual(result["stimulus_analysis"]["event_count"], 3)
        self.assertEqual(result["observed_action_trace"]["trace_version"], "observed-action-trace/v1")
        self.assertEqual(result["observed_action_trace"]["actions"][0]["action"], "navigate")
        self.assertEqual(
            result["observed_action_trace"]["actions"][1]["raw_metadata"]["selector"],
            "[data-action='open-evidence']",
        )
        self.assertIn("instrumented synthetic task run", result["observed_action_trace"]["missing_signals"][0])

    def test_browser_behavior_executor_blocks_credentialed_or_destructive_events(self) -> None:
        payload = {
            "capture_kind": "browser_session",
            "credentialed_session": True,
            "events": [
                {
                    "type": "click",
                    "selector": "#delete-account",
                    "target": "delete account",
                    "url": "https://bank.example.com/settings",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "blocked-browser-trace.json"
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            executor = BrowserBehaviorTraceExecutor()
            with self.assertRaises(StimulusExecutionError) as context:
                executor.execute(
                    artifact_path=artifact,
                    payload=payload,
                    prototype_task="Delete the account.",
                )

        message = str(context.exception)
        self.assertIn("blocked by safety gate", message)
        self.assertIn("credentialed_session", message)
        self.assertIn("delete", message)

    def test_scripted_clickable_executor_emits_observed_action_trace(self) -> None:
        payload = {
            "prototype_label": "Evidence Review Prototype",
            "start_screen": "review",
            "screens": [
                {
                    "id": "review",
                    "label": "Review Workspace",
                    "actions": [
                        {"id": "open_summary", "target": "summary panel", "next_screen": "review"},
                        {"id": "open_evidence", "target": "evidence drawer", "next_screen": "evidence"},
                    ],
                },
                {
                    "id": "evidence",
                    "label": "Evidence Drawer",
                    "actions": [
                        {
                            "id": "request_permission",
                            "target": "permission modal",
                            "next_screen": "permission",
                            "result": "stopped",
                            "terminal": True,
                        }
                    ],
                },
                {
                    "id": "permission",
                    "label": "Permission Modal",
                    "actions": [{"id": "close_modal", "target": "permission modal", "next_screen": "review"}],
                },
            ],
            "task_script": ["open_summary", "open_evidence", "request_permission"],
        }

        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "clickable-manifest.json"
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            executor = ScriptedClickablePrototypeExecutor()
            result = executor.execute(
                artifact_path=artifact,
                payload=payload,
                prototype_task="Review one recommendation and decide whether to act on it.",
            )

        self.assertEqual(result["stimulus_analysis"]["analysis_type"], "clickable_manifest")
        self.assertEqual(result["stimulus_analysis"]["task_step_count"], 3)
        self.assertEqual(result["observed_action_trace"]["task_outcome"], "partial_success")
        self.assertEqual(result["observed_action_trace"]["actions"][1]["target"], "evidence drawer")
        self.assertEqual(result["observed_action_trace"]["drop_off_point"], "permission modal")

    def test_scripted_clickable_executor_rejects_missing_action_on_current_screen(self) -> None:
        payload = {
            "start_screen": "review",
            "screens": [
                {
                    "id": "review",
                    "actions": [{"id": "open_summary", "target": "summary panel"}],
                }
            ],
            "task_script": ["open_evidence"],
        }

        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "clickable-manifest.json"
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            executor = ScriptedClickablePrototypeExecutor()
            with self.assertRaises(StimulusExecutionError) as context:
                executor.execute(
                    artifact_path=artifact,
                    payload=payload,
                    prototype_task="Review one recommendation and decide whether to act on it.",
                )

        self.assertIn("Action 'open_evidence' is not available on screen 'review'", str(context.exception))


if __name__ == "__main__":
    unittest.main()
