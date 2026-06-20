import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.domain.models import FounderBrief
from ai_validation_swarm.providers.mock import MockProvider


class MockProviderTest(unittest.TestCase):
    def test_sensitive_audit_avoids_ai_substring_false_positive(self) -> None:
        provider = MockProvider()
        brief = FounderBrief(
            brief_id="budget_fixture",
            project_name="Lean Task Board",
            problem_statement="Small operators lose recurring admin tasks across scattered notes and reminders.",
            target_market="Cost-conscious operators and coordinators.",
            offered_solution="A simple workflow board that keeps recurring tasks in one place.",
            validation_goal="Test whether a lightweight workflow product feels worth paying for in a budget-constrained audience.",
            pricing_hypothesis="$19 monthly subscription.",
            landing_page_text="Keep recurring admin tasks visible without adding another heavy tool.",
        )

        findings = provider.sensitive_audit(brief, [], [])
        categories = [finding.category for finding in findings]

        self.assertNotIn("privacy_risk", categories)
        self.assertEqual(categories, ["reporting_risk"])


if __name__ == "__main__":
    unittest.main()
