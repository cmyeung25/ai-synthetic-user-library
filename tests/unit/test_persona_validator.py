import io
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
from ai_validation_swarm.personas.validator import PersonaArtifactValidationError, validate_personas
from ai_validation_swarm.storage.files import save_persona


class PersonaValidatorTest(unittest.TestCase):
    def test_validate_personas_accepts_clean_generated_library(self) -> None:
        personas = generate_personas(count=16, random_seed=13)
        issues = validate_personas(personas)
        self.assertEqual(issues, [])

    def test_validate_personas_detects_low_level_inconsistencies(self) -> None:
        personas = generate_personas(count=8, random_seed=19)
        personas[0].profile.basic_identity["gender"] = "woman"
        personas[0].profile.basic_identity["name"] = "Marcus Chan"
        personas[1].profile.basic_identity["family_structure"] = "living with parents"
        personas[1].profile.basic_identity["household_size"] = 1
        personas[2].profile.basic_identity["name"] = personas[3].profile.basic_identity["name"]
        personas[4].profile.basic_identity["location"] = "Hong Kong"
        personas[4].profile.basic_identity["language"] = ["Malay"]
        personas[5].audit["synthetic_only_disclaimer"] = ""
        personas[6].decision_policy["trust_requirements"] = []

        issues = validate_personas(personas)
        check_names = {issue.check_name for issue in issues}

        self.assertIn("name_gender", check_names)
        self.assertIn("household_size", check_names)
        self.assertIn("duplicate_name", check_names)
        self.assertIn("location_language", check_names)
        self.assertIn("missing_disclaimer", check_names)
        self.assertIn("required_field", check_names)

    def test_validate_personas_accepts_new_household_shapes(self) -> None:
        personas = generate_personas(count=3, random_seed=37)
        personas[0].profile.basic_identity["family_structure"] = "living with roommates"
        personas[0].profile.basic_identity["household_size"] = 3
        personas[1].profile.basic_identity["family_structure"] = "single parent with one child"
        personas[1].profile.basic_identity["household_size"] = 2
        personas[1].profile.basic_identity["marital_status"] = "single"
        personas[2].profile.basic_identity["family_structure"] = "multi-generational household"
        personas[2].profile.basic_identity["household_size"] = 5

        issues = validate_personas(personas)
        check_names = {issue.check_name for issue in issues}

        self.assertNotIn("family_structure", check_names)
        self.assertNotIn("household_size", check_names)

    def test_validate_personas_accepts_structured_fairness_profile(self) -> None:
        persona = generate_personas(count=1, random_seed=41)[0]
        persona.profile.sensitive_reality_layer["fairness_and_inclusion_profile"] = {
            "preference": "Practical access and correction controls."
        }
        self.assertEqual(validate_personas([persona]), [])

    def test_validate_personas_requires_complete_banking_context_when_present(self) -> None:
        persona = generate_personas(count=1, random_seed=43)[0]
        persona.profile.banking_context = {
            "bank_relationship": "Primary retail bank customer.",
            "investment_experience": "Basic fund and ETF exposure.",
        }
        issues = validate_personas([persona])
        self.assertTrue(any(issue.check_name == "required_field" and "banking_context" in issue.message for issue in issues))

    def test_validate_personas_accepts_list_values_in_banking_context(self) -> None:
        persona = generate_personas(count=1, random_seed=47)[0]
        persona.profile.banking_context = {
            "bank_relationship": "Primary retail bank customer.",
            "investment_experience": "Basic but growing.",
            "investment_products_held": ["ETF", "fund"],
            "investable_assets_band": "HKD 50k-200k",
            "monthly_income_band": "HKD 25k-30k",
            "primary_financial_goal": "Grow savings carefully.",
            "current_investment_decision_process": "Idea first, verify later.",
            "relationship_manager_usage": "Rare.",
            "digital_banking_usage": "High.",
            "trust_in_bank": "Moderate.",
            "trust_in_blackrock_or_institutional_brand": "Cautiously positive.",
            "risk_understanding_level": "Basic.",
            "portfolio_complexity": "Simple but fragmented.",
            "external_asset_fragmentation": "Some outside-bank holdings.",
            "data_sharing_comfort": "Conditional.",
            "advisory_preference": "Self-serve first.",
            "fee_sensitivity": "High.",
            "past_bad_investment_experience": "One prior regret.",
            "suitability_sensitivity": "Meaningful.",
        }
        self.assertEqual(validate_personas([persona]), [])

    def test_validate_personas_cli_returns_zero_for_clean_library(self) -> None:
        import tempfile

        personas = generate_personas(count=8, random_seed=23)
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            for persona in personas:
                save_persona(persona, data_dir)

            stream = io.StringIO()
            with redirect_stdout(stream):
                exit_code = main(["validate-personas", "--data-dir", str(data_dir)])

        self.assertEqual(exit_code, 0)
        self.assertIn("Validation passed", stream.getvalue())

    def test_save_persona_rejects_invalid_artifact_before_write(self) -> None:
        import tempfile

        persona = generate_personas(count=1, random_seed=29)[0]
        persona.profile.basic_identity["name"] = ""

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PersonaArtifactValidationError) as context:
                save_persona(persona, Path(tmp))

        self.assertIn("required_field", str(context.exception))


if __name__ == "__main__":
    unittest.main()
