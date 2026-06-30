import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.domain.models import PanelSpec
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.providers.base import BaseProvider
from ai_validation_swarm.providers.factory import build_provider
from ai_validation_swarm.providers.mock import MockProvider
from ai_validation_swarm.storage.files import save_persona
from ai_validation_swarm.validation.runner import run_validation


class FlakyProvider(BaseProvider):
    model_version = "flaky-provider/v1"

    def __init__(self, *, fail_once_ids: set[str] | None = None, fail_always_ids: set[str] | None = None) -> None:
        self.delegate = MockProvider()
        self.fail_once_ids = fail_once_ids or set()
        self.fail_always_ids = fail_always_ids or set()
        self.attempts: dict[str, int] = {}

    def persona_response(self, persona, brief, protocol_id):
        persona_id = persona.profile.synthetic_user_id
        self.attempts[persona_id] = self.attempts.get(persona_id, 0) + 1
        attempt = self.attempts[persona_id]

        if persona_id in self.fail_always_ids:
            raise RuntimeError(f"Permanent failure for {persona_id}")
        if persona_id in self.fail_once_ids and attempt == 1:
            raise RuntimeError(f"Transient failure for {persona_id}")
        return self.delegate.persona_response(persona, brief, protocol_id)

    def skeptic_review(self, brief, personas, responses):
        return self.delegate.skeptic_review(brief, personas, responses)

    def sensitive_audit(self, brief, personas, responses):
        return self.delegate.sensitive_audit(brief, personas, responses)

    def planner(self, brief, summary, findings):
        return self.delegate.planner(brief, summary, findings)


class ValidationRunTest(unittest.TestCase):
    def _assign_axes(self, persona, index: int) -> None:
        trust_styles = [
            "needs evidence and verification before trusting",
            "leans on institution and expert-backed guidance",
            "open to collaborative guidance with some proof",
        ]
        control_preferences = [
            "guided with support",
            "self-serve and independent",
            "hybrid with optional support",
        ]
        complexity_levels = [
            "low complexity tolerance",
            "moderate complexity tolerance",
            "high detail tolerance",
        ]
        decision_tempos = [
            "fast decisions",
            "measured decisions",
            "slow and deliberate",
        ]
        persona.profile.human_difference_axes = {
            "trust_style": trust_styles[index % len(trust_styles)],
            "control_preference": control_preferences[index % len(control_preferences)],
            "complexity_tolerance": complexity_levels[index % len(complexity_levels)],
            "decision_tempo": decision_tempos[index % len(decision_tempos)],
            "financial_attention_cadence": ["daily attention", "event-driven review", "occasional check-in"][index % 3],
            "relationship_to_money": ["security oriented", "progress and growth oriented", "practical constraint aware"][index % 3],
            "risk_orientation": ["conservative downside aware", "measured trade-off aware", "open to upside with guardrails"][index % 3],
            "need_for_explanation": ["high plain-language explanation need", "moderate explanation need", "low explanation need"][index % 3],
            "life_load": ["high life load", "moderate life load", "low life load"][index % 3],
            "fragmentation_reality": ["multiple fragmented tools", "some fragmentation across tools", "single centralized workflow"][index % 3],
            "guidance_preference": ["guided support", "hybrid optional expert review", "self-serve independent path"][index % 3],
            "reflection_style": ["example and trade-off driven", "systematic framework driven", "intuition and feeling driven"][index % 3],
        }

    def test_run_validation_writes_report_and_audit(self) -> None:
        personas = generate_personas(count=20, random_seed=31)
        provider = build_provider("mock")
        brief_path = Path("data/briefs/sample_brief.json")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            persona_dir = tmp_root / "personas"
            run_dir = tmp_root / "runs"
            for index, persona in enumerate(personas):
                self._assign_axes(persona, index)
                save_persona(persona, persona_dir)

            archived = run_validation(
                brief_path=brief_path,
                persona_dir=persona_dir,
                panel_spec=PanelSpec(
                    panel_type="mainstream",
                    sample_size=2,
                    random_seed=7,
                    filters={"location_type": "urban_core"},
                    preset_name="mainstream",
                ),
                provider=provider,
                run_root=run_dir,
            )

            report = (archived / "report.md").read_text(encoding="utf-8")
            sampling = (archived / "sampling.json").read_text(encoding="utf-8")
            run_payload = json.loads((archived / "run.json").read_text(encoding="utf-8"))
            run_contract = json.loads((archived / "run_contract.json").read_text(encoding="utf-8"))
            aggregation = json.loads((archived / "aggregation.json").read_text(encoding="utf-8"))
            skeptic = json.loads((archived / "skeptic.json").read_text(encoding="utf-8"))
            report_json = json.loads((archived / "report.json").read_text(encoding="utf-8"))
            run_index = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
            self.assertIn("## 19. Disclaimer", report)
            self.assertTrue((archived / "audit.json").exists())
            self.assertTrue((archived / "summary.json").exists())
            self.assertTrue((archived / "stage_results.json").exists())
            self.assertTrue((archived / "errors.json").exists())
            self.assertTrue((archived / "aggregation.json").exists())
            self.assertTrue((archived / "report.json").exists())
            self.assertIn("location_type", sampling)
            self.assertEqual(run_payload["status"], "completed")
            self.assertEqual(run_payload["successful_response_count"], 2)
            self.assertEqual(run_payload["failed_response_count"], 0)
            self.assertIn("risk_map", aggregation)
            self.assertIn("assumption_risk_map", aggregation)
            self.assertEqual(skeptic["review_version"], "skeptic-review/v1")
            self.assertIsInstance(skeptic["challenged_assumptions"], list)
            self.assertIn("Top Buying Triggers", report)
            self.assertEqual(report_json["report_version"], "report/v1")
            self.assertTrue(report_json["panel_rationale"])
            self.assertIn("human_difference_axis_coverage", report_json["panel_explainability"])
            self.assertEqual(
                report_json["panel_explainability"]["human_difference_axis_coverage"]["selected_panel"]["persona_with_axes_count"],
                run_payload["successful_response_count"],
            )
            self.assertEqual(run_index["run_count"], 1)
            self.assertEqual(run_index["runs"][0]["run_id"], run_payload["run_id"])
            self.assertEqual(run_contract["contract_version"], "shared-run-contract/v1")
            self.assertEqual(run_contract["request"]["run_kind"], "validation_run")
            self.assertEqual(run_contract["request"]["brief_id"], run_payload["brief_id"])
            self.assertEqual(run_contract["result"]["primary_artifact_path"], str(archived / "run.json"))
            self.assertIn("run_contract.json", run_contract["result"]["artifact_paths"])
            metadata_db = run_dir / "metadata.sqlite3"
            self.assertTrue(metadata_db.exists())
            with closing(sqlite3.connect(metadata_db)) as connection:
                run_row = connection.execute(
                    "SELECT run_kind, status, primary_artifact_path FROM run_records WHERE run_id = ?",
                    (run_payload["run_id"],),
                ).fetchone()
                artifact_count = connection.execute(
                    "SELECT COUNT(*) FROM artifact_records WHERE run_id = ?",
                    (run_payload["run_id"],),
                ).fetchone()[0]
            self.assertEqual(run_row[0], "validation_run")
            self.assertEqual(run_row[1], "completed")
            self.assertEqual(run_row[2], str(archived / "run.json"))
            self.assertGreaterEqual(artifact_count, len(run_contract["result"]["artifact_paths"]))

    def test_run_validation_handles_partial_persona_failures_with_retries(self) -> None:
        personas = generate_personas(count=16, random_seed=31)
        brief_path = Path("data/briefs/sample_brief.json")
        mainstream_ids = [
            persona.profile.synthetic_user_id for persona in personas if persona.seed.panel_role == "mainstream"
        ]
        provider = FlakyProvider(
            fail_once_ids={mainstream_ids[0]},
            fail_always_ids={mainstream_ids[1]},
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            persona_dir = tmp_root / "personas"
            run_dir = tmp_root / "runs"
            for index, persona in enumerate(personas):
                self._assign_axes(persona, index)
                save_persona(persona, persona_dir)

            archived = run_validation(
                brief_path=brief_path,
                persona_dir=persona_dir,
                panel_spec=PanelSpec(
                    panel_type="mainstream",
                    sample_size=2,
                    random_seed=7,
                    preset_name="mainstream",
                ),
                provider=provider,
                run_root=run_dir,
                max_retries=1,
            )

            run_payload = json.loads((archived / "run.json").read_text(encoding="utf-8"))
            response_records = json.loads((archived / "raw_responses.json").read_text(encoding="utf-8"))
            stage_results = json.loads((archived / "stage_results.json").read_text(encoding="utf-8"))
            aggregation = json.loads((archived / "aggregation.json").read_text(encoding="utf-8"))
            report_json = json.loads((archived / "report.json").read_text(encoding="utf-8"))
            report = (archived / "report.md").read_text(encoding="utf-8")

            self.assertEqual(run_payload["status"], "partial_failed")
            self.assertEqual(run_payload["successful_response_count"], 1)
            self.assertEqual(run_payload["failed_response_count"], 1)
            self.assertGreaterEqual(run_payload["error_count"], 2)
            self.assertEqual(stage_results["persona_responses"]["status"], "partial_failed")
            self.assertEqual(stage_results["aggregation"]["status"], "succeeded")
            self.assertIn("partial failures", report)
            self.assertEqual(aggregation["run_status"], "partial_failed")
            self.assertEqual(report_json["run_status"], "partial_failed")
            self.assertTrue(report_json["panel_explainability"]["selection_rationale_by_persona"])

            by_id = {record["synthetic_user_id"]: record for record in response_records}
            self.assertEqual(by_id[mainstream_ids[0]]["status"], "succeeded")
            self.assertEqual(by_id[mainstream_ids[0]]["attempt_count"], 2)
            self.assertEqual(len(by_id[mainstream_ids[0]]["errors"]), 1)
            self.assertIsNotNone(by_id[mainstream_ids[0]]["response"])

            self.assertEqual(by_id[mainstream_ids[1]]["status"], "failed")
            self.assertEqual(by_id[mainstream_ids[1]]["attempt_count"], 2)
            self.assertEqual(len(by_id[mainstream_ids[1]]["errors"]), 2)
            self.assertIsNone(by_id[mainstream_ids[1]]["response"])


if __name__ == "__main__":
    unittest.main()
