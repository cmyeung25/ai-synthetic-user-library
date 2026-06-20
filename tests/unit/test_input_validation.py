import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.domain.models import PanelSpec
from ai_validation_swarm.domain.validators import (
    InputValidationError,
    validate_founder_brief_payload,
    validate_panel_spec,
)


class InputValidationTest(unittest.TestCase):
    def test_validate_founder_brief_payload_accepts_valid_payload(self) -> None:
        brief = validate_founder_brief_payload(
            {
                "brief_id": "brief_test",
                "project_name": "Test Project",
                "problem_statement": "Users lose follow-up tasks.",
                "target_market": "Independent consultants.",
                "offered_solution": "AI follow-up assistant.",
                "validation_goal": "Check resonance.",
                "assumptions": ["Users feel the pain strongly."],
            }
        )
        self.assertEqual(brief.brief_id, "brief_test")
        self.assertEqual(brief.assumptions, ["Users feel the pain strongly."])

    def test_validate_founder_brief_payload_rejects_missing_and_extra_fields(self) -> None:
        with self.assertRaises(InputValidationError) as context:
            validate_founder_brief_payload(
                {
                    "brief_id": "brief_test",
                    "project_name": "",
                    "problem_statement": "Users lose follow-up tasks.",
                    "target_market": "Independent consultants.",
                    "unexpected_field": True,
                }
            )

        message = str(context.exception)
        self.assertIn("Missing required field 'offered_solution'", message)
        self.assertIn("Unexpected field 'unexpected_field'", message)
        self.assertIn("'project_name' must not be empty", message)

    def test_validate_panel_spec_rejects_invalid_values(self) -> None:
        with self.assertRaises(InputValidationError) as context:
            validate_panel_spec(
                PanelSpec(
                    panel_type="mainstream",
                    sample_size=0,
                    random_seed=-1,
                    filters={"location_type": ["urban_core", ""]},
                ),
                allowed_panel_types={"mainstream"},
            )

        message = str(context.exception)
        self.assertIn("'sample_size' must be greater than 0", message)
        self.assertIn("'random_seed' must be 0 or greater", message)
        self.assertIn("Sampling filter 'location_type[1]' must be a non-empty string", message)


if __name__ == "__main__":
    unittest.main()
