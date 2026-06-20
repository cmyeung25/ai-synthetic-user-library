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


class ValidateBriefCliTest(unittest.TestCase):
    def test_validate_brief_cli_accepts_valid_brief(self) -> None:
        stream = io.StringIO()
        with redirect_stdout(stream):
            exit_code = main(["validate-brief", "--brief", "data/briefs/sample_brief.json"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Founder brief is valid", stream.getvalue())

    def test_validate_brief_cli_rejects_invalid_brief(self) -> None:
        invalid_payload = {
            "brief_id": "broken",
            "project_name": "",
            "problem_statement": "Something vague",
            "target_market": "Founders"
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid_brief.json"
            path.write_text(json.dumps(invalid_payload), encoding="utf-8")

            stream = io.StringIO()
            with redirect_stdout(stream):
                exit_code = main(["validate-brief", "--brief", str(path)])

        self.assertEqual(exit_code, 1)
        output = stream.getvalue()
        self.assertIn("Input validation failed", output)
        self.assertIn("Missing required field 'offered_solution'", output)


if __name__ == "__main__":
    unittest.main()
