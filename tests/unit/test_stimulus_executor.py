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
    ScriptedClickablePrototypeExecutor,
    StimulusExecutionError,
)


class StimulusExecutorTest(unittest.TestCase):
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
