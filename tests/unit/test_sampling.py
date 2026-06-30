import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.domain.models import PanelSpec
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.sampling.engine import sample_personas


class SamplingTest(unittest.TestCase):
    def _assign_axes(self, personas_by_id: dict[str, object], persona_id: str, *, trust_style: str, control_preference: str, complexity_tolerance: str, decision_tempo: str) -> None:
        personas_by_id[persona_id].profile.human_difference_axes = {
            "trust_style": trust_style,
            "control_preference": control_preference,
            "complexity_tolerance": complexity_tolerance,
            "decision_tempo": decision_tempo,
        }

    def test_sampling_is_deterministic_for_same_seed(self) -> None:
        personas = generate_personas(count=24, random_seed=21)
        panel_spec = PanelSpec(panel_type="mainstream", sample_size=3, random_seed=99)
        sample_a = sample_personas(personas, panel_spec)
        sample_b = sample_personas(personas, panel_spec)
        self.assertEqual(
            [persona.profile.synthetic_user_id for persona in sample_a.personas],
            [persona.profile.synthetic_user_id for persona in sample_b.personas],
        )

    def test_sampling_supports_filters_and_explainability(self) -> None:
        personas = generate_personas(count=32, random_seed=27)
        panel_spec = PanelSpec(
            panel_type="mainstream",
            sample_size=3,
            random_seed=5,
            filters={"location_type": "urban_core"},
            preset_name="mainstream",
        )
        result = sample_personas(personas, panel_spec)

        self.assertTrue(result.personas)
        self.assertTrue(all(persona.seed.location_type == "urban_core" for persona in result.personas))
        self.assertEqual(result.explainability["panel_type"], "mainstream")
        self.assertEqual(result.explainability["filters"], {"location_type": "urban_core"})
        self.assertIn("Eligible candidates moved from", result.rationale)

    def test_sampling_exposes_panel_explainability_and_gap_projection(self) -> None:
        personas = generate_personas(count=32, random_seed=27)
        panel_spec = PanelSpec(panel_type="mainstream", sample_size=3, random_seed=5, preset_name="mainstream")

        initial_result = sample_personas(personas, panel_spec)
        selected_ids = [persona.profile.synthetic_user_id for persona in initial_result.personas]
        eligible_ids = [persona.profile.synthetic_user_id for persona in personas if persona.seed.panel_role == "mainstream"]
        omitted_ids = [persona_id for persona_id in eligible_ids if persona_id not in selected_ids]

        personas_by_id = {persona.profile.synthetic_user_id: persona for persona in personas}
        self._assign_axes(
            personas_by_id,
            omitted_ids[0],
            trust_style="prefers institution and expert-backed signals before acting",
            control_preference="self-serve and independent",
            complexity_tolerance="high detail tolerance",
            decision_tempo="slow and deliberate",
        )
        self._assign_axes(
            personas_by_id,
            selected_ids[0],
            trust_style="needs evidence and verification before trusting",
            control_preference="guided with support",
            complexity_tolerance="low complexity tolerance",
            decision_tempo="fast decisions",
        )
        self._assign_axes(
            personas_by_id,
            selected_ids[1],
            trust_style="needs evidence and verification before trusting",
            control_preference="guided with support",
            complexity_tolerance="low complexity tolerance",
            decision_tempo="measured decisions",
        )
        self._assign_axes(
            personas_by_id,
            selected_ids[2],
            trust_style="needs evidence and verification before trusting",
            control_preference="hybrid autonomy with review",
            complexity_tolerance="moderate complexity tolerance",
            decision_tempo="slow and deliberate",
        )

        result = sample_personas(personas, panel_spec)

        explainability = result.explainability
        undercovered_by_axis = {record["axis"]: record for record in explainability["undercovered_axes"]}
        trust_gap = undercovered_by_axis["trust_style"]
        self.assertEqual(trust_gap["coverage_status"], "missing_eligible_patterns")
        self.assertEqual(trust_gap["missing_buckets"], ["institution_led"])

        hotspots_by_axis = {record["axis"]: record for record in explainability["similarity_hotspots"]}
        self.assertEqual(hotspots_by_axis["trust_style"]["bucket"], "verify_first")
        self.assertEqual(hotspots_by_axis["trust_style"]["persona_count"], 3)

        rationale_by_persona = {
            record["synthetic_user_id"]: record for record in explainability["selection_rationale_by_persona"]
        }
        self.assertEqual(len(rationale_by_persona), 3)
        hybrid_rationale = rationale_by_persona[selected_ids[2]]
        self.assertTrue(any(item["axis"] == "control_preference" for item in hybrid_rationale["axis_contributions"]))
        self.assertIn("adds panel coverage", hybrid_rationale["inclusion_reason"])
        self.assertIn("Human-difference coverage still looks thin on", result.rationale)


if __name__ == "__main__":
    unittest.main()
