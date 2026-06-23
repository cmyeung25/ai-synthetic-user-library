import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.personas.v5_panels import (
    HK_RETAIL_BANK_PORTFOLIO_HEALTH_CHECK,
    build_hk_retail_bank_portfolio_health_check_panel,
    build_v5_panel_preset,
)


class PersonaV5LegacyPanelPresetTest(unittest.TestCase):
    def test_legacy_hk_bank_panel_preset_builds_seven_personas_with_required_sections(self) -> None:
        panel = build_hk_retail_bank_portfolio_health_check_panel(starting_id=1301)
        self.assertEqual(panel["preset_name"], HK_RETAIL_BANK_PORTFOLIO_HEALTH_CHECK)
        self.assertEqual(panel["persona_count"], 7)
        self.assertEqual(panel["personas"][0]["persona_id"], "su_1301")
        self.assertEqual(panel["personas"][-1]["persona_id"], "su_1307")
        axis_signatures = set()
        for persona in panel["personas"]:
            guide = persona["guide"]
            self.assertIn("human_difference_axes", guide["required_profile_sections"])
            self.assertIn("portfolio_health_check", guide["concept_output_contracts"])
            self.assertIn("control_preference", guide["preferred"])
            self.assertIn("trust_style", guide["preferred"])
            axis_signatures.add(
                (
                    guide["preferred"]["control_preference"],
                    guide["preferred"]["trust_style"],
                    guide["preferred"]["fragmentation_reality"],
                )
            )
        self.assertEqual(len(axis_signatures), 7)

    def test_legacy_panel_dispatch_rejects_unknown_preset(self) -> None:
        with self.assertRaises(ValueError):
            build_v5_panel_preset("unknown_preset")


if __name__ == "__main__":
    unittest.main()
