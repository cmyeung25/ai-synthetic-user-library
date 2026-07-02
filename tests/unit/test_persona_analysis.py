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
from ai_validation_swarm.personas.analysis import build_persona_library_summary
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.storage.files import save_persona


class PersonaAnalysisTest(unittest.TestCase):
    def test_build_persona_library_summary_reports_key_coverage(self) -> None:
        personas = generate_personas(count=100, random_seed=53)
        summary = build_persona_library_summary(personas)

        self.assertEqual(summary["library_size"], 100)
        self.assertEqual(summary["unique_name_count"], 100)
        self.assertEqual(summary["distinct_counts"]["panel_role"], 9)
        self.assertEqual(summary["distinct_counts"]["gender"], 3)
        self.assertGreaterEqual(summary["distinct_counts"]["location"], 10)
        self.assertTrue(summary["coverage_checks"]["all_names_unique"])
        self.assertTrue(summary["coverage_checks"]["all_panel_roles_covered"])
        self.assertTrue(summary["coverage_checks"]["all_locale_packs_covered"])
        self.assertTrue(summary["coverage_checks"]["all_life_stages_covered"])
        self.assertTrue(summary["coverage_checks"]["all_family_structures_covered"])
        self.assertEqual(summary["human_difference_axis_summary"]["persona_with_axes_count"], 0)

    def test_build_persona_library_summary_reports_human_difference_axis_gaps(self) -> None:
        personas = generate_personas(count=3, random_seed=71)
        personas[0].profile.human_difference_axes = {
            "control_preference": "Hybrid; wants room to decide but appreciates structure.",
            "trust_style": "Evidence first with cautious benefit of the doubt.",
            "complexity_tolerance": "Moderate; will engage if the detail clearly helps.",
            "decision_tempo": "Measured; gathers enough signal before acting.",
            "financial_attention_cadence": "Periodic with event-driven spikes.",
            "relationship_to_money": "Practical security with some growth ambition.",
            "risk_orientation": "Open to measured risk when the downside is understandable.",
            "need_for_explanation": "High enough to want plain-language framing.",
            "life_load": "Moderate; daily life leaves limited room for unnecessary friction.",
            "fragmentation_reality": "Some assets and information live across more than one place.",
            "guidance_preference": "Hybrid self-serve plus optional expert clarification.",
            "reflection_style": "Explains decisions through recent examples and trade-offs.",
        }
        personas[0].profile.relational_defense_model = {"default_trust_posture": "guarded_until_proven_safe"}
        personas[0].profile.communication_behavior_model = {"clarification_tendency": "high_when_abstract"}
        personas[0].profile.behavior_generation_rules = [{"when": {"human_difference_axes.life_load": "high"}, "then": "asks for a shorter path", "because": "time is scarce", "source": "human_difference_axes"}]

        personas[1].profile.human_difference_axes = {
            "control_preference": "Guided; prefers a few explicit steps and recommended defaults.",
            "trust_style": "Verify first and look for clear proof before relying on claims.",
            "complexity_tolerance": "Low; prefers the useful point without extra detail.",
            "decision_tempo": "Deliberate; slows down when consequences feel sticky.",
            "financial_attention_cadence": "Event-driven around salary, bills, and major decisions.",
            "relationship_to_money": "Money is mainly a security buffer before anything else.",
            "risk_orientation": "Conservative; wants downside explained before moving.",
            "need_for_explanation": "High; needs translation into plain language and examples.",
            "life_load": "High; routine work and family pressure leave little room for friction.",
            "fragmentation_reality": "Highly fragmented across multiple accounts and records.",
            "guidance_preference": "Guided with optional expert reassurance.",
            "reflection_style": "Uses concrete examples more than abstract frameworks.",
        }
        personas[1].profile.relational_defense_model = {"default_trust_posture": "guarded_until_proven_safe"}
        personas[1].profile.communication_behavior_model = {"clarification_tendency": "high_when_abstract"}
        personas[1].profile.behavior_generation_rules = [{"when": {"human_difference_axes.complexity_tolerance": "low"}, "then": "asks for a simpler explanation", "because": "dense flows raise friction", "source": "human_difference_axes"}]

        personas[2].profile.human_difference_axes = {
            "control_preference": "Self-serve; wants to decide independently unless the stakes rise.",
            "trust_style": "Open to credible institutions but still checks core claims.",
        }

        summary = build_persona_library_summary(personas)
        axis_summary = summary["human_difference_axis_summary"]

        self.assertEqual(axis_summary["persona_with_axes_count"], 3)
        self.assertEqual(axis_summary["behavior_model_coverage"]["relational_defense_model"]["persona_count"], 2)
        self.assertEqual(
            axis_summary["axis_coverage"]["trust_style"]["bucket_distribution"],
            {
                "institution_led": 1,
                "verify_first": 2,
            },
        )
        self.assertEqual(
            axis_summary["axis_coverage"]["complexity_tolerance"]["coverage_status"],
            "partial_presence",
        )
        self.assertTrue(
            any(
                item["axis"] == "complexity_tolerance" and item["gap_type"] == "partial_presence"
                for item in axis_summary["coverage_gaps"]
            )
        )

    def test_build_persona_library_summary_tolerates_legacy_missing_profile_fields(self) -> None:
        persona = generate_personas(count=1, random_seed=83)[0]
        del persona.profile.basic_identity["locale_pack"]
        del persona.profile.basic_identity["life_stage"]
        del persona.profile.basic_identity["family_structure"]
        del persona.profile.economic_profile["purchase_authority_type"]
        del persona.profile.economic_profile["cash_flow_volatility"]
        persona.profile.behavior_profile.pop("workflow_maturity", None)

        summary = build_persona_library_summary([persona])

        self.assertEqual(summary["library_size"], 1)
        self.assertEqual(
            summary["distributions"]["locale_pack"],
            {persona.seed.locale_pack: 1},
        )
        self.assertEqual(
            summary["distributions"]["family_structure"],
            {persona.seed.household_structure: 1},
        )
        self.assertEqual(
            summary["distributions"]["purchase_authority_type"],
            {persona.seed.purchase_authority_type: 1},
        )

    def test_summarize_personas_cli_writes_json(self) -> None:
        personas = generate_personas(count=24, random_seed=11)
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "personas"
            output_path = Path(tmp) / "summary.json"
            for persona in personas:
                save_persona(persona, base_dir)

            stream = io.StringIO()
            with redirect_stdout(stream):
                exit_code = main(
                    [
                        "summarize-personas",
                        "--data-dir",
                        str(base_dir),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("Persona summary written", stream.getvalue())
            summary = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["library_size"], 24)
            self.assertEqual(summary["unique_name_count"], 24)


if __name__ == "__main__":
    unittest.main()
