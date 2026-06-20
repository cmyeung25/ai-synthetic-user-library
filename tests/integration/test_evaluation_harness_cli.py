import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.cli.main import main
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.storage.files import save_persona


class EvaluationHarnessCliTest(unittest.TestCase):
    def test_run_evaluation_and_compare_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            output_root = temp_root / "evaluations"
            persona_root = temp_root / "personas"
            for persona in generate_personas(count=30, random_seed=11):
                save_persona(persona, persona_root)

            run_stream = io.StringIO()
            with redirect_stdout(run_stream):
                run_exit = main(
                    [
                        "run-evaluation",
                        "--suite",
                        "fixtures/evaluation/suite.json",
                        "--data-dir",
                        str(persona_root),
                        "--provider",
                        "mock",
                        "--output-dir",
                        str(output_root),
                        "--repeat-count",
                        "2",
                    ]
                )

            self.assertEqual(run_exit, 0)
            self.assertIn("Evaluation suite archived at", run_stream.getvalue())

            evaluation_dirs = [path for path in output_root.iterdir() if path.is_dir()]
            self.assertEqual(len(evaluation_dirs), 1)
            evaluation_dir = evaluation_dirs[0]

            summary = json.loads((evaluation_dir / "summary.json").read_text(encoding="utf-8"))
            rubric = (evaluation_dir / "manual_rubric.md").read_text(encoding="utf-8")

            self.assertEqual(summary["overall_status"], "passed")
            self.assertEqual(summary["fixture_count"], 6)
            self.assertEqual(summary["repeat_count"], 2)
            self.assertIn("Manual Review Rubric", rubric)
            self.assertTrue((evaluation_dir / "suite.json").exists())

            fixtures_by_id = {fixture["fixture_id"]: fixture for fixture in summary["fixtures"]}
            self.assertTrue(all(fixture["status"] == "passed" for fixture in fixtures_by_id.values()))
            self.assertTrue(all(fixture["deterministic_match"] for fixture in fixtures_by_id.values()))
            self.assertIn("privacy_risk", fixtures_by_id["privacy_sensitive_product"]["audit_categories"])
            self.assertIn("high_stakes_decision_risk", fixtures_by_id["high_stakes_parenting"]["audit_categories"])

            comparison_output = evaluation_dir / "comparison.json"
            compare_stream = io.StringIO()
            with redirect_stdout(compare_stream):
                compare_exit = main(
                    [
                        "compare-evaluations",
                        "--baseline",
                        str(evaluation_dir / "summary.json"),
                        "--candidate",
                        str(evaluation_dir / "summary.json"),
                        "--output",
                        str(comparison_output),
                    ]
                )

            self.assertEqual(compare_exit, 0)
            comparison = json.loads(comparison_output.read_text(encoding="utf-8"))
            self.assertEqual(comparison["changed_fixture_count"], 0)
            self.assertEqual(comparison["unchanged_fixture_count"], 6)
            self.assertIn("Compared 6 fixtures; 0 changed, 6 unchanged.", compare_stream.getvalue())


if __name__ == "__main__":
    unittest.main()
