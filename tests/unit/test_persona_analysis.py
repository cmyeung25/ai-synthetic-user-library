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
        self.assertEqual(summary["distinct_counts"]["panel_role"], 8)
        self.assertEqual(summary["distinct_counts"]["gender"], 3)
        self.assertGreaterEqual(summary["distinct_counts"]["location"], 10)
        self.assertTrue(summary["coverage_checks"]["all_names_unique"])
        self.assertTrue(summary["coverage_checks"]["all_panel_roles_covered"])
        self.assertTrue(summary["coverage_checks"]["all_locale_packs_covered"])
        self.assertTrue(summary["coverage_checks"]["all_life_stages_covered"])
        self.assertTrue(summary["coverage_checks"]["all_family_structures_covered"])

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
