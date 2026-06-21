import io
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
from ai_validation_swarm.personas.v3_2 import SectionBatchedV32SynthesisAdapter
from ai_validation_swarm.personas.v3_3 import (
    FullPassRepairV33SynthesisAdapter,
    generate_v3_3_personas,
    validate_v3_3_persona_folder,
)
from ai_validation_swarm.storage.files import read_json
from tests.unit.test_persona_v3_2 import FixtureSynthesisAdapter


class PersonaV33Test(unittest.TestCase):
    def test_v3_3_direct_generation_writes_v3_3_folder(self) -> None:
        adapter = FullPassRepairV33SynthesisAdapter(
            FixtureSynthesisAdapter(),
            SectionBatchedV32SynthesisAdapter(FixtureSynthesisAdapter(), batch_size=1),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = generate_v3_3_personas(
                persona_ids=["su_0040"],
                output_dir=root,
                adapter=adapter,
                random_seed_offset=40,
            )
            self.assertEqual(paths, [root / "su_0040" / "v3_3"])
            self.assertTrue(validate_v3_3_persona_folder(paths[0])["valid"])
            notes = read_json(paths[0] / "generation_notes.json")
            self.assertEqual(notes["generator_version"], "persona-generator/v3.3")
            self.assertEqual(notes["generation_mode"], "single_pass_primary_with_targeted_repair_fallback")

    def test_v3_3_repair_fallback_repairs_failed_section(self) -> None:
        primary = FixtureSynthesisAdapter(omit_first_hobby_depth=True)
        repair_inner = FixtureSynthesisAdapter()
        progress: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = FullPassRepairV33SynthesisAdapter(
                primary,
                SectionBatchedV32SynthesisAdapter(
                    repair_inner,
                    batch_size=1,
                    cache_dir=root / "cache",
                    progress_writer=progress.append,
                ),
                progress_writer=progress.append,
            )
            paths = generate_v3_3_personas(
                persona_ids=["su_0041"],
                output_dir=root,
                adapter=adapter,
                random_seed_offset=41,
                progress_writer=progress.append,
            )
            self.assertTrue(validate_v3_3_persona_folder(paths[0])["valid"])
            self.assertEqual(len(primary.calls), 1)
            self.assertGreaterEqual(len(repair_inner.calls), 1)
            notes = read_json(paths[0] / "generation_notes.json")
            repair_metadata = notes["adapter_metadata"]["repair_fallback"]
            self.assertTrue(repair_metadata["applied"])
            self.assertIn("lifestyle_and_hobbies", repair_metadata["repaired_sections"])
            self.assertTrue(any("repair fallback sections=" in message for message in progress))

    def test_v3_3_resume_state_skips_completed_repair_sections(self) -> None:
        primary = FixtureSynthesisAdapter(omit_first_hobby_depth=True)
        repair_inner = FixtureSynthesisAdapter()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = FullPassRepairV33SynthesisAdapter(
                primary,
                SectionBatchedV32SynthesisAdapter(
                    repair_inner,
                    batch_size=1,
                    cache_dir=root / "cache",
                ),
                state_dir=root / "resume",
            )
            paths = generate_v3_3_personas(
                persona_ids=["su_0042"],
                output_dir=root,
                adapter=adapter,
                random_seed_offset=42,
            )
            first_primary_calls = len(primary.calls)
            first_repair_calls = len(repair_inner.calls)
            self.assertTrue(validate_v3_3_persona_folder(paths[0])["valid"])

            primary_after = FixtureSynthesisAdapter(omit_first_hobby_depth=True)
            repair_after = FixtureSynthesisAdapter()
            resumed = FullPassRepairV33SynthesisAdapter(
                primary_after,
                SectionBatchedV32SynthesisAdapter(
                    repair_after,
                    batch_size=1,
                    cache_dir=root / "cache",
                ),
                state_dir=root / "resume",
            )
            paths2 = generate_v3_3_personas(
                persona_ids=["su_0042"],
                output_dir=root,
                adapter=resumed,
                random_seed_offset=42,
            )

            self.assertEqual(paths, paths2)
            self.assertEqual(first_primary_calls, 1)
            self.assertGreaterEqual(first_repair_calls, 1)
            self.assertEqual(len(primary_after.calls), 0)
            self.assertEqual(len(repair_after.calls), 0)

    def test_cli_exposes_v3_3_commands(self) -> None:
        stream = io.StringIO()
        with redirect_stdout(stream):
            exit_code = main(["validate-personas-v3-3", "--data-dir", str(ROOT / "does-not-exist")])
        self.assertEqual(exit_code, 1)
        self.assertIn("No V3.3 personas found", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
