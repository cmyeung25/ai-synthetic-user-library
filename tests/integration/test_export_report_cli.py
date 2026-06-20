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
from ai_validation_swarm.domain.models import PanelSpec
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.providers.factory import build_provider
from ai_validation_swarm.storage.files import save_persona
from ai_validation_swarm.validation.runner import run_validation


class ExportReportCliTest(unittest.TestCase):
    def test_export_report_supports_markdown_json_and_csv(self) -> None:
        personas = generate_personas(count=16, random_seed=31)
        provider = build_provider("mock")
        brief_path = Path("data/briefs/sample_brief.json")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            persona_dir = tmp_root / "personas"
            run_root = tmp_root / "runs"
            export_dir = tmp_root / "exports"
            for persona in personas:
                save_persona(persona, persona_dir)

            archived = run_validation(
                brief_path=brief_path,
                persona_dir=persona_dir,
                panel_spec=PanelSpec(
                    panel_type="mainstream",
                    sample_size=2,
                    random_seed=7,
                    preset_name="mainstream",
                ),
                provider=provider,
                run_root=run_root,
            )

            markdown_output = export_dir / "sample_report.md"
            stream = io.StringIO()
            with redirect_stdout(stream):
                markdown_exit = main(["export-report", "--run-path", str(archived), "--output", str(markdown_output)])

            json_output = export_dir / "sample_report.json"
            with redirect_stdout(io.StringIO()):
                json_exit = main(["export-report", "--run-path", str(archived), "--output", str(json_output)])

            csv_output = export_dir / "sample_report.csv"
            with redirect_stdout(io.StringIO()):
                csv_exit = main(["export-report", "--run-path", str(archived), "--output", str(csv_output)])

            self.assertEqual(markdown_exit, 0)
            self.assertEqual(json_exit, 0)
            self.assertEqual(csv_exit, 0)
            self.assertIn("Exported report", stream.getvalue())

            self.assertEqual(
                markdown_output.read_text(encoding="utf-8"),
                (archived / "report.md").read_text(encoding="utf-8"),
            )

            report_payload = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertEqual(report_payload["report_version"], "report/v1")
            self.assertEqual(report_payload["run_id"], json.loads((archived / "run.json").read_text(encoding="utf-8"))["run_id"])

            csv_payload = csv_output.read_text(encoding="utf-8")
            self.assertIn("section,key,value,severity,reference", csv_payload)
            self.assertIn("scores", csv_payload)
            self.assertIn("planner", csv_payload)


if __name__ == "__main__":
    unittest.main()
