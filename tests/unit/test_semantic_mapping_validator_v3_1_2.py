import random
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.personas.generator import build_seed, enrich_seed
from ai_validation_swarm.personas.semantic_mapping_validator_v3_1_2 import build_semantic_mapping_report_v3_1_2
from ai_validation_swarm.personas.v3_1_2 import _repair_semantic_mapping, upgrade_persona_to_v3_1_2


class SemanticMappingValidatorV312Test(unittest.TestCase):
    def test_identity_disclosure_repair_uses_disclosure_control_vocabulary(self) -> None:
        rng = random.Random(11 + 3)
        seed = build_seed(index=3, rng=rng, panel_role="inclusion")
        persona = enrich_seed(seed=seed, index=3, rng=rng)
        upgraded = upgrade_persona_to_v3_1_2(persona, random_seed=203)

        upgraded.profile.sensitive_scenario_reactions["identity_disclosure"]["what_reduces_trust"] = (
            "Being asked to become legible before the product has become useful."
        )

        fixes: list[str] = []
        _repair_semantic_mapping(upgraded, fixes)
        report = build_semantic_mapping_report_v3_1_2(upgraded, auto_fixes_applied=fixes)

        repaired = upgraded.profile.sensitive_scenario_reactions["identity_disclosure"]["what_reduces_trust"].lower()
        self.assertEqual(report["status"], "pass")
        self.assertIn("forced labels", repaired)
        self.assertIn("binary", repaired)
        self.assertIn("disclosure", repaired)
        self.assertIn("control", repaired)


if __name__ == "__main__":
    unittest.main()
