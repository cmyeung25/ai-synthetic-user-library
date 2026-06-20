import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.evaluation.comparison import compare_evaluation_payloads


class EvaluationComparisonTest(unittest.TestCase):
    def test_compare_evaluation_payloads_detects_changed_fixture(self) -> None:
        baseline = {
            "suite_id": "core-quality-gate-v1",
            "fixtures": [
                {
                    "fixture_id": "fixture_a",
                    "status": "passed",
                    "report_fingerprint": "aaa",
                    "score_snapshot": {"problem_resonance": 4.0},
                    "audit_categories": ["privacy_risk"],
                    "failed_gates": [],
                }
            ],
        }
        candidate = {
            "suite_id": "core-quality-gate-v1",
            "fixtures": [
                {
                    "fixture_id": "fixture_a",
                    "status": "failed",
                    "report_fingerprint": "bbb",
                    "score_snapshot": {"problem_resonance": 3.0},
                    "audit_categories": ["privacy_risk", "reporting_risk"],
                    "failed_gates": ["deterministic_rerun"],
                }
            ],
        }

        comparison = compare_evaluation_payloads(baseline, candidate)

        self.assertEqual(comparison["changed_fixture_count"], 1)
        self.assertEqual(comparison["unchanged_fixture_count"], 0)
        self.assertEqual(comparison["fixtures"][0]["status"], "changed")
        self.assertTrue(comparison["fixtures"][0]["fingerprint_changed"])
        self.assertEqual(comparison["fixtures"][0]["score_deltas"]["problem_resonance"], -1.0)
        self.assertEqual(comparison["fixtures"][0]["added_audit_categories"], ["reporting_risk"])
        self.assertEqual(comparison["fixtures"][0]["added_failed_gates"], ["deterministic_rerun"])


if __name__ == "__main__":
    unittest.main()
