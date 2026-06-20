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


if __name__ == "__main__":
    unittest.main()
