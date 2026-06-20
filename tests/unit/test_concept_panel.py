from __future__ import annotations

import unittest

from ai_validation_swarm.facilitator.concept_panel import _render_summary, _summary_payload


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
                "key_insights": ["First insight。','Second insight"],
            },
            "quality": {"scores": {"overall": 4}},
        }]

        summary = _summary_payload("test_run", interviews)

        self.assertEqual(len(summary["assumption_matrix"]), 8)
        self.assertEqual(
            summary["additional_persona_specific_findings"][0]["finding"],
            "core 9",
        )
        markdown = _render_summary(summary, interviews)
        self.assertIn("## Additional Persona-Specific Risks", markdown)
        self.assertIn("- First insight。", markdown)
        self.assertIn("- Second insight", markdown)


if __name__ == "__main__":
    unittest.main()
