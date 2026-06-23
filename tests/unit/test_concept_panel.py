from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import ai_validation_swarm.facilitator.concept_panel as concept_panel_module
from ai_validation_swarm.facilitator.concept_panel import (
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
        self.assertEqual(summary["personas"][0]["top_likely_drivers"][0]["driver_type"], "trust_pattern")
        self.assertEqual(
            summary["additional_persona_specific_findings"][0]["finding"],
            "core 9",
        )
        markdown = _render_summary(summary, interviews)
        self.assertIn("# Go Out La! Synthetic Persona Panel", markdown)
        self.assertIn("## Common Likely Drivers", markdown)
        self.assertIn("Needs confidence before acting", markdown)
        self.assertIn("Convenience versus control", markdown)
        self.assertIn("## Additional Persona-Specific Risks", markdown)
        self.assertIn("- First insight", markdown)
        self.assertIn("- Second insight", markdown)

    def test_concept_panel_default_turn_policy_uses_soft_12_hard_16(self) -> None:
        self.assertEqual(
            _resolve_concept_panel_turn_policy(),
            (12, 16),
        )
        self.assertEqual(
            _resolve_concept_panel_turn_policy(max_turns=9),
            (9, 9),
        )

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
                (folder / "insight_report.json").write_text(json.dumps(insight), encoding="utf-8")
                (folder / "quality_evaluation.json").write_text(json.dumps(quality), encoding="utf-8")
                (folder / "persona_driver_trace.json").write_text(json.dumps(trace), encoding="utf-8")

                class Session:
                    interview_id = "observed_test"
                    persona_name = "Test Persona"
                    status = "completed"
                    last_error = ""

                return folder, Session()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona_dir = root / "data" / "personas" / "su_9999" / "v5"
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
            summary = json.loads((run_dir / "panel_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["soft_turn_limit"], 12)
            self.assertEqual(manifest["hard_turn_limit"], 16)
            self.assertEqual(manifest["max_turns"], 16)
            self.assertEqual(summary["common_likely_drivers"][0]["driver"], "Needs simple proof first")


if __name__ == "__main__":
    unittest.main()
