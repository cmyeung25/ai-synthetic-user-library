import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.saas.market_config import load_market_distribution_config


class MarketConfigTest(unittest.TestCase):
    def test_load_market_distribution_config_accepts_sample_configs(self) -> None:
        first = load_market_distribution_config(Path("configs/markets/default_b2b_saas.json"))
        second = load_market_distribution_config(Path("configs/markets/hk_smb_ops.json"))

        self.assertEqual(first.market_id, "default_b2b_saas")
        self.assertIn("panel_role", first.weights)
        self.assertEqual(second.default_locale, "zh-HK")
        self.assertIn("trust_threshold", second.weights)

    def test_load_market_distribution_config_rejects_invalid_weight_total(self) -> None:
        invalid_payload = """
{
  "config_version": "market-distribution/v1",
  "market_id": "broken",
  "display_name": "Broken",
  "default_locale": "en",
  "target_population": "Broken sample",
  "weights": {
    "panel_role": {
      "mainstream": 0.70,
      "skeptic": 0.20
    }
  }
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text(invalid_payload, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_market_distribution_config(path)


if __name__ == "__main__":
    unittest.main()
