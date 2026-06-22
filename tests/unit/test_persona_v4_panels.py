import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.personas.v4_panels import (
    HK_RETAIL_BANK_PORTFOLIO_HEALTH_CHECK,
    build_hk_retail_bank_portfolio_health_check_panel,
    build_v4_panel_preset,
)


class PersonaV4PanelPresetTest(unittest.TestCase):
    def test_hk_bank_panel_preset_builds_seven_personas_with_required_sections(self) -> None:
        panel = build_hk_retail_bank_portfolio_health_check_panel(starting_id=1301)
        self.assertEqual(panel["preset_name"], HK_RETAIL_BANK_PORTFOLIO_HEALTH_CHECK)
        self.assertEqual(panel["persona_count"], 7)
        self.assertEqual(panel["personas"][0]["persona_id"], "su_1301")
        self.assertEqual(panel["personas"][-1]["persona_id"], "su_1307")
        for persona in panel["personas"]:
            guide = persona["guide"]
            self.assertIn("banking_context", guide["required_profile_sections"])
            self.assertIn("portfolio_health_check", guide["concept_output_contracts"])

    def test_panel_dispatch_rejects_unknown_preset(self) -> None:
        with self.assertRaises(ValueError):
            build_v4_panel_preset("unknown_preset")


if __name__ == "__main__":
    unittest.main()
