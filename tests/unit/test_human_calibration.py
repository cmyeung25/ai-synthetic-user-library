from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ai_validation_swarm.evaluation.human_calibration import (
    attach_human_calibration,
    extract_synthetic_signals,
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

    def test_external_benchmark_definition_path_is_resolved_from_suite(self) -> None:
        suite = load_human_benchmark_suite(Path("fixtures/human_calibration/external_suite.json"))
        benchmark = suite["benchmarks"][0]

        self.assertEqual(benchmark["benchmark_id"], "inbox_coach_followup_real_study_sample")
        self.assertEqual(benchmark["source"]["source_type"], "real_human_study")
        self.assertTrue(str(benchmark["benchmark_definition_path"]).endswith("inbox_coach_followup_real_study_sample.json"))

    def test_external_real_human_benchmark_can_reach_candidate_replacement_ready(self) -> None:
        suite = load_human_benchmark_suite(Path("fixtures/human_calibration/external_suite.json"))
        benchmark = suite["benchmarks"][0]
        run_dir = Path("fixtures/human_calibration/runs/inbox_coach_sample")

        with tempfile.TemporaryDirectory() as tmp:
            copied_run = Path(tmp) / "run"
            shutil.copytree(run_dir, copied_run)
            payload = attach_human_calibration(run_dir=copied_run, benchmark=benchmark)

        self.assertEqual(payload["human_benchmark"]["source_type"], "real_human_study")
        self.assertTrue(str(payload["human_benchmark"]["benchmark_definition_path"]).endswith(".json"))
        self.assertEqual(payload["replacement_readiness"]["status"], "candidate_replacement_ready")
        self.assertEqual(payload["readiness_projection"]["status"], "candidate_scope_ready")
        self.assertEqual(payload["miss_attribution"]["status"], "miss_detected")
        self.assertEqual(payload["miss_attribution"]["primary_cause_id"], "synthesis_ranking_gap")

    def test_review_findings_can_be_mapped_into_human_outcome_signals(self) -> None:
        suite = load_human_benchmark_suite(Path("fixtures/human_calibration/external_review_findings_suite.json"))
        benchmark = suite["benchmarks"][0]
        run_dir = Path("fixtures/human_calibration/runs/inbox_coach_sample")

        with tempfile.TemporaryDirectory() as tmp:
            copied_run = Path(tmp) / "run"
            shutil.copytree(run_dir, copied_run)
            payload = attach_human_calibration(run_dir=copied_run, benchmark=benchmark)

        self.assertEqual(payload["benchmark_id"], "inbox_coach_followup_review_findings_sample")
        self.assertEqual(payload["human_benchmark"]["outcome_count"], 3)
        self.assertEqual(payload["replacement_readiness"]["status"], "candidate_replacement_ready")
        self.assertEqual(payload["readiness_projection"]["coverage"]["benchmark_origin"], "external_definition")
        self.assertEqual(
            [item["source"] for item in payload["human_outcome_signals"]],
            [
                "human_outcomes.review_findings",
                "human_outcomes.review_findings",
                "human_outcomes.review_findings",
            ],
        )
        self.assertEqual(
            [item["signal_id"] for item in payload["human_outcome_signals"]],
            [
                "objection:uncertain_roi",
                "trust_gap:proof_that_it_fits_existing_habits",
                "risk:privacy_risk",
            ],
        )

    def test_browser_trace_signals_are_extracted_for_calibration(self) -> None:
        run_dir = Path("fixtures/human_calibration/runs/browser_trace_permission_dropoff_sample")

        signals = extract_synthetic_signals(run_dir)

        self.assertEqual(
            [item["category"] for item in signals],
            ["task_failure", "abandonment", "trust_gap"],
        )
        self.assertEqual(
            [item["source"] for item in signals],
            ["observed_action_trace", "observed_action_trace", "observed_action_trace"],
        )
        self.assertIn("permission", signals[2]["terms"])

    def test_browser_trace_benchmark_can_align_to_human_outcomes(self) -> None:
        suite = load_human_benchmark_suite(Path("fixtures/human_calibration/external_browser_trace_suite.json"))
        benchmark = suite["benchmarks"][0]
        run_dir = Path("fixtures/human_calibration/runs/browser_trace_permission_dropoff_sample")

        with tempfile.TemporaryDirectory() as tmp:
            copied_run = Path(tmp) / "run"
            shutil.copytree(run_dir, copied_run)
            payload = attach_human_calibration(run_dir=copied_run, benchmark=benchmark)

        self.assertEqual(payload["run"]["research_stage"], "prototype_validation")
        self.assertEqual(payload["human_benchmark"]["outcome_count"], 3)
        self.assertEqual(payload["prediction_accuracy"]["true_positive"], 3)
        self.assertEqual(payload["prediction_accuracy"]["false_positive"], 0)
        self.assertEqual(payload["replacement_readiness"]["status"], "candidate_replacement_ready")
        self.assertEqual(payload["readiness_projection"]["status"], "candidate_scope_ready")
        self.assertEqual(payload["miss_attribution"]["status"], "fully_aligned")

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
        self.assertEqual(payload["readiness_projection"]["status"], "high_stakes_gate")

    def test_mixed_external_suite_projects_aggregate_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = run_human_calibration_suite(
                suite_path=Path("fixtures/human_calibration/mixed_external_suite.json"),
                output_root=Path(tmp),
            )

            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))

        projection = summary["readiness_projection"]
        self.assertEqual(projection["status"], "scoped_external_readiness_available")
        self.assertEqual(projection["candidate_scope_count"], 1)
        self.assertEqual(projection["high_stakes_gate_count"], 1)
        self.assertEqual(projection["threshold_gap_count"], 1)
        self.assertEqual(projection["external_benchmark_count"], 3)
        self.assertIn("high_stakes_human_review_required", projection["gate_reasons"])
        self.assertIn("precision_below_threshold", projection["gate_reasons"])

    def test_human_calibration_can_attribute_likely_miss_sources(self) -> None:
        benchmark = {
            "benchmark_id": "prototype_calibration_gap_case",
            "name": "Prototype calibration gap case",
            "research_stage": "prototype_validation",
            "evidence_type": "observed_action_trace",
            "source": {
                "source_type": "real_human_study",
                "review_method": "manual_review",
            },
            "human_panel": {
                "participant_count": 4,
                "segment": "prototype reviewers",
            },
            "human_outcomes": {
                "signals": [
                    {
                        "category": "trust_gap",
                        "label": "Need tighter permission scope",
                        "terms": ["permission", "scope", "trust"],
                    },
                    {
                        "category": "adoption_trigger",
                        "label": "Proof that it fits existing review habits",
                        "terms": ["proof", "habit", "fit"],
                    },
                ]
            },
            "thresholds": {
                "min_precision": 0.7,
                "min_recall": 0.7,
                "min_alignment_score": 70,
                "replacement_readiness_min_score": 85,
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            (run_dir / "run.json").write_text(
                json.dumps(
                    {
                        "run_id": "run_attr_case_001",
                        "status": "completed",
                        "selected_persona_ids": ["su_attr_01"],
                        "interview_mode": "prototype_validation",
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "report.json").write_text(
                json.dumps(
                    {
                        "report_version": "report/v1",
                        "run_id": "run_attr_case_001",
                        "run_status": "completed",
                        "panel_spec": {
                            "panel_type": "prototype_validation",
                            "sample_size": 1,
                            "random_seed": 17,
                            "filters": {},
                            "preset_name": "prototype-validation",
                        },
                        "objection_clusters": [
                            {
                                "objection": "automation worry",
                                "count": 1,
                                "share_pct": 100.0,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "run_contract.json").write_text(
                json.dumps(
                    {
                        "contract_version": "shared-run-contract/v1",
                        "request": {
                            "run_id": "run_attr_case_001",
                            "run_kind": "facilitated_interview",
                            "entrypoint": "run-facilitated-interview",
                            "created_at": "2026-06-29T00:00:00+00:00",
                            "interview_mode": "prototype_validation",
                        },
                        "result": {
                            "run_id": "run_attr_case_001",
                            "run_kind": "facilitated_interview",
                            "status": "completed",
                            "started_at": "2026-06-29T00:00:00+00:00",
                            "output_path": str(run_dir),
                            "selected_persona_ids": ["su_attr_01"],
                            "metadata": {
                                "coverage_status": {
                                    "coverage_complete": False,
                                    "depth_complete": False,
                                    "missing": ["task_outcome"],
                                    "depth_missing": ["decision_tradeoff"],
                                }
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "stimulus_analysis.json").write_text(
                json.dumps(
                    {
                        "analysis_type": "live_app_browser_trace",
                        "interpretation_risks": ["The permission prompt may be too abstract before value is proven."],
                        "missing_context": ["The rationale for broad permission access is not explicit."],
                    }
                ),
                encoding="utf-8",
            )

            payload = attach_human_calibration(run_dir=run_dir, benchmark=benchmark)

        attribution = payload["miss_attribution"]
        self.assertEqual(attribution["status"], "miss_detected")
        self.assertEqual(attribution["primary_cause_id"], "persona_coverage_gap")
        cause_ids = [item["cause_id"] for item in attribution["likely_causes"]]
        self.assertIn("persona_coverage_gap", cause_ids)
        self.assertIn("facilitator_behavior_gap", cause_ids)
        self.assertIn("stimulus_interpretation_gap", cause_ids)
        self.assertIn("synthesis_ranking_gap", cause_ids)
        persona_cause = next(item for item in attribution["likely_causes"] if item["cause_id"] == "persona_coverage_gap")
        self.assertEqual(persona_cause["confidence"], "high")
        self.assertEqual(persona_cause["evidence"]["synthetic_sample_size"], 1)
        self.assertEqual(persona_cause["evidence"]["human_participant_count"], 4)

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
            self.assertTrue(
                any(item["id"] == "external_benchmark_readiness" for item in reliability["calibration_records"])
            )
            self.assertTrue(
                any(item["id"] == "calibration_miss_attribution" for item in reliability["calibration_records"])
            )
            self.assertTrue(
                any(item["id"] == "external_benchmark_gap" for item in reliability["missing_context"])
            )
            self.assertFalse(
                any(item["id"] == "human_validation_gap" for item in reliability["missing_context"])
            )


if __name__ == "__main__":
    unittest.main()
