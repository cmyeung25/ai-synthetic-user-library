from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from ai_validation_swarm.evaluation.human_calibration import (
    attach_human_calibration,
    load_human_benchmark_suite,
    run_human_calibration_suite,
)
from ai_validation_swarm.saas.evidence_query import _build_evidence_reliability


class HumanCalibrationTests(unittest.TestCase):
    def test_fixture_benchmark_attaches_prediction_accuracy_and_boundary(self) -> None:
        suite = load_human_benchmark_suite(Path("fixtures/human_calibration/suite.json"))
        benchmark = suite["benchmarks"][0]
        run_dir = Path("fixtures/human_calibration/runs/inbox_coach_sample")

        with tempfile.TemporaryDirectory() as tmp:
            copied_run = Path(tmp) / "run"
            shutil.copytree(run_dir, copied_run)
            payload = attach_human_calibration(run_dir=copied_run, benchmark=benchmark)

            self.assertEqual(payload["contract_version"], "human-calibration/v1")
            self.assertEqual(payload["benchmark_id"], "inbox_coach_followup_fixture")
            self.assertGreaterEqual(payload["prediction_accuracy"]["alignment_score"], 80)
            self.assertEqual(payload["prediction_accuracy"]["recall"], 1.0)
            self.assertEqual(payload["replacement_readiness"]["status"], "calibrated_fixture_only")
            self.assertIn("not replacement-grade proof", payload["replacement_readiness"]["boundary"])
            self.assertTrue((copied_run / "human_calibration.json").exists())
            self.assertTrue((copied_run / "human_calibration.md").exists())

    def test_human_calibration_suite_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = run_human_calibration_suite(
                suite_path=Path("fixtures/human_calibration/suite.json"),
                output_root=Path(tmp),
            )
            self.assertTrue((output_dir / "summary.json").exists())
            self.assertTrue((output_dir / "summary.md").exists())

    def test_high_stakes_benchmark_remains_gated(self) -> None:
        suite = load_human_benchmark_suite(Path("fixtures/human_calibration/suite.json"))
        benchmark = dict(suite["benchmarks"][0])
        benchmark["high_stakes_domain"] = True
        run_dir = Path("fixtures/human_calibration/runs/inbox_coach_sample")

        with tempfile.TemporaryDirectory() as tmp:
            payload = attach_human_calibration(
                run_dir=run_dir,
                benchmark=benchmark,
                output_path=Path(tmp) / "high_stakes_calibration.json",
            )

        self.assertEqual(payload["replacement_readiness"]["status"], "high_stakes_human_review_required")
        self.assertTrue(payload["replacement_readiness"]["high_stakes_gate"])

    def test_evidence_reliability_projects_attached_human_calibration(self) -> None:
        suite = load_human_benchmark_suite(Path("fixtures/human_calibration/suite.json"))
        benchmark = suite["benchmarks"][0]
        run_dir = Path("fixtures/human_calibration/runs/inbox_coach_sample")

        with tempfile.TemporaryDirectory() as tmp:
            copied_run = Path(tmp) / "run"
            shutil.copytree(run_dir, copied_run)
            attach_human_calibration(run_dir=copied_run, benchmark=benchmark)

            reliability = _build_evidence_reliability(
                run_record={
                    "run_id": "run_human_calibration_fixture_001",
                    "run_kind": "validation_run",
                    "brief_id": "brief_inbox_coach_v1",
                    "research_goal": "Test follow-up workflow",
                    "interview_mode": "concept_validation",
                    "finished_at": "2026-06-29T00:00:00+00:00",
                    "output_path": str(copied_run),
                    "primary_artifact_path": str(copied_run / "report.json"),
                },
                selected_result={
                    "id": "query-report",
                    "artifact_id": "artifact-report",
                    "family": "output",
                    "kind": "report",
                    "title": "Report",
                    "summary": "uncertain ROI and proof of fit",
                    "artifact_path": str(copied_run / "report.json"),
                    "artifact_rel_path": "report.json",
                },
                replay_sequence=[{"id": "step-1", "title": "Review report", "timestamp": "00:01"}],
                replay_focus={"id": "step-1", "title": "Review report", "timestamp": "00:01"},
                comparison_context={"comparison_candidates": []},
                cross_run_comparison={"comparison_run_count": 0, "candidate_runs": []},
            )

            self.assertIsNotNone(reliability["human_calibration"])
            self.assertTrue(
                any(item["id"] == "human_benchmark_alignment" for item in reliability["calibration_records"])
            )
            self.assertFalse(
                any(item["id"] == "human_validation_gap" for item in reliability["missing_context"])
            )


if __name__ == "__main__":
    unittest.main()
