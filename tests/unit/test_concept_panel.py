from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import closing

import ai_validation_swarm.facilitator.concept_panel as concept_panel_module
from ai_validation_swarm.facilitator.concept_panel import (
    _compare_facilitator_learning_effect_payload,
    _facilitator_audit_learning_report_payload,
    _facilitator_audit_panel_payload,
    _render_facilitator_audit_panel,
    _render_facilitator_audit_learning_report,
    _render_facilitator_learning_effect_report,
    aggregate_facilitator_audit_runs,
    compare_facilitator_learning_effects,
    _render_summary,
    _summary_payload,
    _resolve_concept_panel_turn_policy,
)


class ConceptPanelSummaryTests(unittest.TestCase):
    def test_extra_assumptions_are_reported_as_persona_specific_findings(self) -> None:
        assumptions = [
            {"assumption": f"core {index}", "status": "supported", "rationale": "evidence"}
            for index in range(1, 10)
        ]
        interviews = [{
            "persona_id": "su_0004",
            "persona_name": "Ethan Lee",
            "interview_id": "observed_test",
            "coverage_status": {
                "depth_requirements": ["threshold_probe", "contrast_probe", "driver_deepening_probe"],
                "depth_missing": ["contrast_probe", "driver_deepening_probe"],
                "depth_complete": False,
            },
            "report": {
                "problem_evidence": {"strength": "strong"},
                "assumption_validation": assumptions,
                "key_insights": ["First insight??,'Second insight"],
            },
            "quality": {"scores": {"overall": 4}},
            "persona_driver_trace": {
                "likely_drivers": [
                    {
                        "driver": "Needs confidence before acting",
                        "driver_type": "trust_pattern",
                        "why_it_matters_here": "He checks whether the workflow feels reliable enough to trust.",
                        "confidence": "medium",
                    }
                ],
                "unspoken_constraints": [
                    {
                        "constraint": "Does not want another system to maintain",
                        "why_likely": "Extra setup would feel like more work.",
                        "confidence": "medium",
                    }
                ],
                "value_tensions": [
                    {
                        "tension": "Convenience versus control",
                        "side_a": "Wants lighter workflow",
                        "side_b": "Still wants to verify important details",
                        "confidence": "medium",
                    }
                ],
                "missed_follow_up_questions": [
                    {
                        "question": "What would have made you trust the workflow sooner?",
                        "priority": "high",
                    }
                ],
            },
            "facilitator_audit_feedback": {
                "facilitator_feedback_tags": [
                    {
                        "tag": "missed_high_signal_clue",
                        "severity": "medium",
                        "why_it_matters": "A verification clue was not turned into a causal probe.",
                        "observed_pattern": "The facilitator moved on after a manual check description.",
                    }
                ],
                "summary": {
                    "overall_assessment": "Coverage was acceptable but the facilitator moved on before extracting the avoided failure.",
                    "primary_failure_mode": "coverage_over_depth",
                    "depth_vs_coverage_assessment": "A strong verification clue was present but not pursued.",
                },
                "high_value_missed_followups": [
                    {
                        "trigger_type": "manual_reconciliation",
                        "priority": "high",
                        "participant_signal": "He kept checking whether things were reliable enough to trust.",
                        "missed_followup_question": "What mistake were you trying to avoid by checking again?",
                        "generic_learning": "When a participant manually rechecks something, ask what failure that behavior is protecting against.",
                    }
                ],
                "likely_misclassified_driver_patterns": [
                    {
                        "observed_surface_frame": "wants better planning tools",
                        "possible_underlying_driver": "wants confidence restoration before acting",
                        "why_the_surface_frame_is_weak": "The examples focused on verification rather than planning breadth.",
                        "generic_learning": "Do not treat a requested tool improvement as the root driver until the avoided mistake is explicit.",
                    }
                ],
                "prompt_adjustments": [
                    {
                        "adjustment_type": "followup_trigger_rule",
                        "text": "If a participant mentions a manual verification step, ask what failure it protects against before moving on.",
                        "reuse_scope": "global",
                        "safe_for_global_reuse": True,
                    }
                ],
                "carry_forward_rules": [
                    {
                        "rule_id": "linger_on_manual_verification",
                        "rule": "When a participant describes manual verification, ask what concrete mistake or avoided failure that behavior is protecting against.",
                        "source_tags": ["missed_high_signal_clue"],
                        "confidence": "medium",
                        "safe_for_global_reuse": True,
                    }
                ],
                "blocked_feedback": [
                    {
                        "blocked_item": "Probe Aladdin trust concerns directly in Hong Kong retail-bank interviews.",
                        "block_reason": "project_specific_conclusion",
                    }
                ],
            },
        }]

        summary = _summary_payload(
            "test_run",
            interviews,
            topic_label="Go Out La!",
            language="Natural Cantonese Traditional Chinese",
            core_assumption_count=8,
        )

        self.assertEqual(len(summary["assumption_matrix"]), 8)
        self.assertEqual(summary["topic"], "Go Out La!")
        self.assertEqual(summary["driver_type_counts"]["trust_pattern"], 1)
        self.assertEqual(summary["common_likely_drivers"][0]["driver"], "Needs confidence before acting")
        self.assertEqual(summary["facilitator_primary_failure_modes"][0]["failure_mode"], "coverage_over_depth")
        self.assertEqual(summary["depth_completion_counts"]["incomplete"], 1)
        self.assertEqual(summary["common_missing_depth_probes"][0]["probe_type"], "contrast_probe")
        self.assertEqual(summary["common_missed_high_value_followups"][0]["trigger_type"], "manual_reconciliation")
        self.assertEqual(
            summary["common_likely_misclassified_drivers"][0]["possible_underlying_driver"],
            "wants confidence restoration before acting",
        )
        self.assertEqual(summary["personas"][0]["top_likely_drivers"][0]["driver_type"], "trust_pattern")
        self.assertEqual(summary["personas"][0]["facilitator_primary_failure_mode"], "coverage_over_depth")
        self.assertFalse(summary["personas"][0]["depth_complete"])
        self.assertEqual(summary["personas"][0]["missing_depth_probes"], ["contrast_probe", "driver_deepening_probe"])
        self.assertEqual(
            summary["additional_persona_specific_findings"][0]["finding"],
            "core 9",
        )
        markdown = _render_summary(summary, interviews)
        self.assertIn("# Go Out La! Synthetic Persona Panel", markdown)
        self.assertIn("## Common Likely Drivers", markdown)
        self.assertIn("## Facilitator Audit Patterns", markdown)
        self.assertIn("## Common Missing Depth Probes", markdown)
        self.assertIn("## Common Missed High-Value Follow-Ups", markdown)
        self.assertIn("## Common Likely Misclassified Drivers", markdown)
        self.assertIn("Needs confidence before acting", markdown)
        self.assertIn("Convenience versus control", markdown)
        self.assertIn("coverage_over_depth", markdown)
        self.assertIn("Missing depth probes: Contrast / Non-Use Probe, Driver-Deepening Probe", markdown)
        self.assertIn("What mistake were you trying to avoid by checking again?", markdown)
        self.assertIn("## Additional Persona-Specific Risks", markdown)
        self.assertIn("- First insight", markdown)
        self.assertIn("- Second insight", markdown)

        audit_panel = _facilitator_audit_panel_payload(
            "test_run",
            interviews,
            topic_label="Go Out La!",
            summary=summary,
        )
        self.assertEqual(audit_panel["ready_for_global_rule_count"], 0)
        self.assertEqual(audit_panel["distilled_carry_forward_rules"][0]["candidate_strength"], "weak")
        self.assertEqual(audit_panel["blocked_feedback_patterns"][0]["block_reason"], "project_specific_conclusion")
        audit_markdown = _render_facilitator_audit_panel(audit_panel)
        self.assertIn("## Distilled Carry-Forward Rules", audit_markdown)
        self.assertIn("## Blocked Feedback Patterns", audit_markdown)
        self.assertIn("When a participant describes manual verification", audit_markdown)

    def test_concept_panel_default_turn_policy_uses_soft_12_hard_16(self) -> None:
        self.assertEqual(
            _resolve_concept_panel_turn_policy(),
            (12, 16),
        )
        self.assertEqual(
            _resolve_concept_panel_turn_policy(max_turns=9),
            (9, 9),
        )

    def test_facilitator_audit_panel_requires_multiple_personas_before_global_candidate(self) -> None:
        interviews = []
        for persona_id, persona_name in [("su_0001", "Ava"), ("su_0002", "Ben")]:
            interviews.append({
                "persona_id": persona_id,
                "persona_name": persona_name,
                "interview_id": f"observed_{persona_id}",
                "report": {},
                "quality": {"scores": {"overall": 4}},
                "persona_driver_trace": {},
                "facilitator_audit_feedback": {
                    "summary": {
                        "overall_assessment": "The facilitator stopped at verification language.",
                        "primary_failure_mode": "coverage_over_depth",
                        "depth_vs_coverage_assessment": "A concrete verification clue was not converted into a causal probe.",
                    },
                    "high_value_missed_followups": [],
                    "likely_misclassified_driver_patterns": [],
                    "prompt_adjustments": [],
                    "carry_forward_rules": [
                        {
                            "rule_id": "linger_on_manual_verification",
                            "rule": "When a participant describes manual verification, ask what concrete mistake or avoided failure that behavior is protecting against.",
                            "source_tags": ["missed_high_signal_clue"],
                            "confidence": "medium",
                            "safe_for_global_reuse": True,
                        }
                    ],
                    "blocked_feedback": [],
                },
            })
        summary = _summary_payload(
            "test_run",
            interviews,
            topic_label="Test Topic",
            language="Natural Cantonese Traditional Chinese",
            core_assumption_count=8,
        )
        audit_panel = _facilitator_audit_panel_payload(
            "test_run",
            interviews,
            topic_label="Test Topic",
            summary=summary,
        )
        self.assertEqual(audit_panel["ready_for_global_rule_count"], 1)
        self.assertEqual(audit_panel["ready_for_global_candidate_rules"][0]["candidate_strength"], "medium")

    def test_cross_run_facilitator_audit_learning_report_requires_multiple_runs(self) -> None:
        payload_one = {
            "run_id": "run_one",
            "topic": "Topic A",
            "audited_persona_count": 3,
            "ready_for_global_rule_count": 1,
            "blocked_feedback_count": 1,
            "top_failure_modes": [{
                "failure_mode": "coverage_over_depth",
                "persona_count": 3,
                "personas": ["Ava", "Ben", "Cara"],
                "example_assessment": "The facilitator moved on too early.",
            }],
            "recurring_feedback_tags": [{
                "tag": "missed_high_signal_clue",
                "severity": "medium",
                "support_persona_count": 3,
                "observed_pattern": "Moved on after a verification clue.",
                "why_it_matters": "Missed the avoided failure.",
            }],
            "common_missed_high_value_followups": [{
                "question": "What mistake were you trying to avoid?",
                "trigger_type": "manual_reconciliation",
                "persona_count": 3,
                "generic_learning": "Ask what failure a verification behavior is protecting against.",
            }],
            "common_likely_misclassified_drivers": [{
                "possible_underlying_driver": "needs confidence restoration",
                "observed_surface_frame": "wants better planning tools",
                "persona_count": 3,
                "generic_learning": "Do not treat a tool request as root cause too fast.",
            }],
            "distilled_carry_forward_rules": [{
                "rule_id": "linger_on_manual_verification",
                "rule": "When a participant describes manual verification, ask what concrete mistake or avoided failure that behavior is protecting against.",
                "source_tags": ["missed_high_signal_clue"],
                "confidence": "medium",
                "support_persona_count": 3,
                "candidate_strength": "medium",
                "safe_for_global_reuse": True,
            }],
            "blocked_feedback_patterns": [{
                "blocked_item": "Probe Aladdin trust concerns directly.",
                "block_reason": "project_specific_conclusion",
                "support_persona_count": 1,
            }],
        }
        payload_two = {
            **payload_one,
            "run_id": "run_two",
            "topic": "Topic B",
            "blocked_feedback_count": 0,
        }
        report = _facilitator_audit_learning_report_payload(
            label="Facilitator Audit Learning Report",
            audit_panels=[payload_one, payload_two],
        )
        self.assertEqual(report["run_count"], 2)
        self.assertEqual(report["total_audited_personas"], 6)
        self.assertEqual(report["human_review_candidates"][0]["rule_id"], "linger_on_manual_verification")
        self.assertEqual(report["human_review_candidates"][0]["candidate_strength"], "strong")
        markdown = _render_facilitator_audit_learning_report(report)
        self.assertIn("## Cross-Run Carry-Forward Rules", markdown)
        self.assertIn("## Human Review Candidates", markdown)

    def test_aggregate_facilitator_audit_runs_writes_report_files(self) -> None:
        panel_payload = {
            "run_id": "run_one",
            "topic": "Topic A",
            "audited_persona_count": 2,
            "ready_for_global_rule_count": 1,
            "blocked_feedback_count": 0,
            "top_failure_modes": [],
            "recurring_feedback_tags": [],
            "common_missed_high_value_followups": [],
            "common_likely_misclassified_drivers": [],
            "distilled_carry_forward_rules": [{
                "rule_id": "linger_on_manual_verification",
                "rule": "When a participant describes manual verification, ask what concrete mistake or avoided failure that behavior is protecting against.",
                "source_tags": ["missed_high_signal_clue"],
                "confidence": "medium",
                "support_persona_count": 2,
                "candidate_strength": "medium",
                "safe_for_global_reuse": True,
            }],
            "blocked_feedback_patterns": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_one = root / "run_one"
            run_two = root / "run_two"
            run_one.mkdir(parents=True, exist_ok=True)
            run_two.mkdir(parents=True, exist_ok=True)
            (run_one / "facilitator_audit_panel.json").write_text(json.dumps(panel_payload), encoding="utf-8")
            second = dict(panel_payload)
            second["run_id"] = "run_two"
            (run_two / "facilitator_audit_panel.json").write_text(json.dumps(second), encoding="utf-8")
            output_dir = root / "learning_report"
            output = aggregate_facilitator_audit_runs(
                run_dirs=[run_one, run_two],
                output_dir=output_dir,
                label="Learning Report",
            )
            self.assertEqual(output, output_dir)
            report = json.loads((output_dir / "facilitator_audit_learning_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["run_count"], 2)
            self.assertTrue((output_dir / "facilitator_audit_learning_report.md").exists())
            self.assertEqual(report["human_review_candidates"][0]["rule_id"], "linger_on_manual_verification")

    def test_compare_facilitator_learning_effect_payload_detects_quality_and_rule_usage_deltas(self) -> None:
        baseline_runs = [{
            "panel_summary": {"average_quality_score": 3.0},
            "audit_panel": {
                "top_failure_modes": [{"failure_mode": "coverage_over_depth", "persona_count": 3}],
                "common_missed_high_value_followups": [{"question": "What mistake were you trying to avoid?", "persona_count": 3}],
            },
            "interviews": [{"approved_learning_rule_ids": []}],
        }]
        candidate_runs = [{
            "panel_summary": {"average_quality_score": 4.0},
            "audit_panel": {
                "top_failure_modes": [{"failure_mode": "coverage_over_depth", "persona_count": 1}],
                "common_missed_high_value_followups": [{"question": "What mistake were you trying to avoid?", "persona_count": 1}],
            },
            "interviews": [{"approved_learning_rule_ids": ["linger_on_manual_verification"]}],
        }]
        report = _compare_facilitator_learning_effect_payload(
            label="Effect Report",
            baseline_runs=baseline_runs,
            candidate_runs=candidate_runs,
        )
        self.assertEqual(report["quality_score_delta"], 1.0)
        self.assertEqual(report["approved_rule_usage_counts"]["linger_on_manual_verification"], 1)
        self.assertEqual(report["failure_mode_deltas"][0]["delta"], -2)
        self.assertEqual(report["effect_assessment"], "improved")
        markdown = _render_facilitator_learning_effect_report(report)
        self.assertIn("## Approved Rule Usage", markdown)
        self.assertIn("## Failure Mode Deltas", markdown)

    def test_compare_facilitator_learning_effects_writes_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_run = root / "baseline_run"
            candidate_run = root / "candidate_run"
            (baseline_run / "interviews" / "i1").mkdir(parents=True, exist_ok=True)
            (candidate_run / "interviews" / "i1").mkdir(parents=True, exist_ok=True)
            (baseline_run / "panel_summary.json").write_text(json.dumps({"average_quality_score": 3.0}), encoding="utf-8")
            (candidate_run / "panel_summary.json").write_text(json.dumps({"average_quality_score": 4.0}), encoding="utf-8")
            (baseline_run / "facilitator_audit_panel.json").write_text(
                json.dumps({
                    "top_failure_modes": [{"failure_mode": "coverage_over_depth", "persona_count": 3}],
                    "common_missed_high_value_followups": [],
                }),
                encoding="utf-8",
            )
            (candidate_run / "facilitator_audit_panel.json").write_text(
                json.dumps({
                    "top_failure_modes": [{"failure_mode": "coverage_over_depth", "persona_count": 1}],
                    "common_missed_high_value_followups": [],
                }),
                encoding="utf-8",
            )
            (baseline_run / "interviews" / "i1" / "interview.json").write_text(
                json.dumps({"approved_learning_rule_ids": []}),
                encoding="utf-8",
            )
            (candidate_run / "interviews" / "i1" / "interview.json").write_text(
                json.dumps({"approved_learning_rule_ids": ["linger_on_manual_verification"]}),
                encoding="utf-8",
            )
            output_dir = root / "effect_report"
            output = compare_facilitator_learning_effects(
                baseline_run_dirs=[baseline_run],
                candidate_run_dirs=[candidate_run],
                output_dir=output_dir,
                label="Effect Report",
            )
            self.assertEqual(output, output_dir)
            report = json.loads((output_dir / "facilitator_learning_effect_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["quality_score_delta"], 1.0)
            self.assertTrue((output_dir / "facilitator_learning_effect_report.md").exists())

    def test_run_concept_panel_persists_default_turn_policy_in_manifest(self) -> None:
        class FakeRuntime:
            last_start_kwargs: dict[str, object] | None = None

            def __init__(self, **kwargs):
                self.session_dir = kwargs["session_dir"]

            def start(self, **kwargs):
                FakeRuntime.last_start_kwargs = kwargs
                folder = self.session_dir / "observed_test"
                folder.mkdir(parents=True, exist_ok=True)
                insight = {
                    "problem_evidence": {"strength": "medium"},
                    "assumption_validation": [],
                    "key_insights": [],
                    "pricing_signal": {},
                    "retention_risk": {},
                    "next_experiment": "Test with a real concierge flow.",
                }
                quality = {"scores": {"overall": 4}}
                trace = {
                    "likely_drivers": [
                        {
                            "driver": "Needs simple proof first",
                            "driver_type": "core_value",
                            "why_it_matters_here": "Will not trust abstract value alone.",
                            "confidence": "medium",
                        }
                    ],
                    "unspoken_constraints": [],
                    "value_tensions": [],
                    "missed_follow_up_questions": [],
                }
                audit = {
                    "facilitator_feedback_tags": [
                        {
                            "tag": "missed_high_signal_clue",
                            "severity": "medium",
                            "why_it_matters": "A verification clue was not turned into a causal probe.",
                            "observed_pattern": "The facilitator moved on after a manual check description.",
                        }
                    ],
                    "summary": {
                        "overall_assessment": "Coverage was fine but one high-signal clue was missed.",
                        "primary_failure_mode": "coverage_over_depth",
                        "depth_vs_coverage_assessment": "The facilitator moved on instead of probing the protected-against failure.",
                    },
                    "high_value_missed_followups": [
                        {
                            "trigger_type": "manual_reconciliation",
                            "priority": "high",
                            "participant_signal": "The participant wanted simple proof first.",
                            "missed_followup_question": "What mistake were you trying to avoid before trusting it?",
                            "generic_learning": "Ask what failure a verification behavior is protecting against.",
                        }
                    ],
                    "likely_misclassified_driver_patterns": [],
                    "prompt_adjustments": [
                        {
                            "adjustment_type": "followup_trigger_rule",
                            "text": "If a participant mentions a manual verification step, ask what failure it protects against before moving on.",
                            "reuse_scope": "global",
                            "safe_for_global_reuse": True,
                        }
                    ],
                    "carry_forward_rules": [
                        {
                            "rule_id": "linger_on_manual_verification",
                            "rule": "When a participant describes manual verification, ask what concrete mistake or avoided failure that behavior is protecting against.",
                            "source_tags": ["missed_high_signal_clue"],
                            "confidence": "medium",
                            "safe_for_global_reuse": True,
                        }
                    ],
                    "blocked_feedback": [],
                }
                (folder / "insight_report.json").write_text(json.dumps(insight), encoding="utf-8")
                (folder / "quality_evaluation.json").write_text(json.dumps(quality), encoding="utf-8")
                (folder / "persona_driver_trace.json").write_text(json.dumps(trace), encoding="utf-8")
                (folder / "facilitator_audit_feedback.json").write_text(json.dumps(audit), encoding="utf-8")

                class Session:
                    interview_id = "observed_test"
                    persona_name = "Test Persona"
                    status = "completed"
                    last_error = ""

                return folder, Session()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona_dir = root / "data" / "personas" / "su_9999" / "v5_1"
            persona_dir.mkdir(parents=True, exist_ok=True)
            (persona_dir / "profile.json").write_text("{}", encoding="utf-8")
            output_dir = root / "experiments"
            original_runtime = concept_panel_module.ObserverControlledInterviewRuntime
            concept_panel_module.ObserverControlledInterviewRuntime = FakeRuntime
            try:
                run_dir = concept_panel_module.run_concept_panel(
                    data_dir=root / "data" / "personas",
                    output_dir=output_dir,
                    facilitator_provider=object(),
                    persona_provider=object(),
                    quality_provider=object(),
                    research_goal="Validate a concept.",
                    product_context="A neutral concept test.",
                    topic_label="Test Topic",
                    persona_ids=["su_9999"],
                )
            finally:
                concept_panel_module.ObserverControlledInterviewRuntime = original_runtime

            self.assertEqual(FakeRuntime.last_start_kwargs["soft_turn_limit"], 12)
            self.assertEqual(FakeRuntime.last_start_kwargs["hard_turn_limit"], 16)
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            run_contract = json.loads((run_dir / "run_contract.json").read_text(encoding="utf-8"))
            summary = json.loads((run_dir / "panel_summary.json").read_text(encoding="utf-8"))
            audit_panel = json.loads((run_dir / "facilitator_audit_panel.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["soft_turn_limit"], 12)
            self.assertEqual(manifest["hard_turn_limit"], 16)
            self.assertEqual(manifest["max_turns"], 16)
            self.assertEqual(run_contract["request"]["run_kind"], "concept_panel")
            self.assertEqual(run_contract["request"]["entrypoint"], "run-concept-panel")
            self.assertEqual(run_contract["result"]["status"], "completed")
            self.assertIn("panel_summary.json", run_contract["result"]["artifact_paths"])
            metadata_db = output_dir / "metadata.sqlite3"
            self.assertTrue(metadata_db.exists())
            with closing(sqlite3.connect(metadata_db)) as connection:
                run_row = connection.execute(
                    "SELECT run_kind, status FROM run_records WHERE run_id = ?",
                    (manifest["run_id"],),
                ).fetchone()
            self.assertEqual(run_row, ("concept_panel", "completed"))
            self.assertEqual(summary["common_likely_drivers"][0]["driver"], "Needs simple proof first")
            self.assertEqual(summary["facilitator_primary_failure_modes"][0]["failure_mode"], "coverage_over_depth")
            self.assertEqual(audit_panel["distilled_carry_forward_rules"][0]["rule_id"], "linger_on_manual_verification")
            self.assertTrue((run_dir / "facilitator_audit_panel.md").exists())


if __name__ == "__main__":
    unittest.main()
