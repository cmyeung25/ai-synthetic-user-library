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
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.personas.v2 import (
    PROMPT_VERSIONS,
    RAW_ENUM_TOKENS,
    _build_rendered_artifacts,
    _decade_ranges_for_age,
    load_v2_prompt_texts,
    upgrade_persona_to_v2,
    validate_v2_persona_folder,
    write_v2_persona_folder,
)
from ai_validation_swarm.storage.files import load_personas, read_json, save_persona


class PersonaV2Test(unittest.TestCase):
    def test_upgrade_persona_to_v2_populates_required_sections(self) -> None:
        persona = generate_personas(count=1, random_seed=41)[0]

        upgraded = upgrade_persona_to_v2(persona, random_seed=41)
        rendered = _build_rendered_artifacts(upgraded)
        expected_chapters = len(_decade_ranges_for_age(upgraded.profile.basic_identity["age"]))

        self.assertEqual(upgraded.skill_version, "v2")
        self.assertEqual(
            len(upgraded.profile.canonical_biography["decade_timeline"]),
            expected_chapters,
        )
        self.assertGreaterEqual(len(upgraded.profile.contradiction_map), 4)
        self.assertTrue(upgraded.profile.pricing_logic["free_trial_required"])
        self.assertTrue(upgraded.profile.interests_and_hobbies["interest_depth"])
        self.assertIn("## Example Responses", rendered["persona.skill.md"])
        self.assertIn("## Media Diet & Product Discovery", rendered["biography.md"])

        combined_text = "\n".join(rendered.values())
        for token in RAW_ENUM_TOKENS:
            self.assertNotIn(token, combined_text)

    def test_write_v2_persona_folder_writes_full_artifact_set(self) -> None:
        persona = generate_personas(count=1, random_seed=43)[0]
        upgraded = upgrade_persona_to_v2(persona, random_seed=43)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            output_dir = tmp_path / "output"
            save_persona(persona, source_dir)

            folder = write_v2_persona_folder(
                upgraded,
                base_dir=output_dir,
                random_seed=43,
                source_folder=source_dir / persona.profile.synthetic_user_id,
                migration_notes=["test migration"],
            )

            expected_files = {
                "profile.json",
                "audit.json",
                "persona.md",
                "biography.md",
                "research_kernel.md",
                "persona.skill.md",
                "generation_notes.json",
            }
            self.assertTrue(expected_files.issubset({path.name for path in folder.iterdir()}))
            self.assertTrue((folder / "legacy_v1" / "profile.json").exists())
            self.assertTrue((folder / "legacy_v1" / "audit.json").exists())
            self.assertTrue((folder / "legacy_v1" / "persona.md").exists())

            generation_notes = read_json(folder / "generation_notes.json")
            self.assertEqual(generation_notes["generator_version"], "persona-generator/v2")
            self.assertEqual(generation_notes["prompt_versions"], PROMPT_VERSIONS)

            audit = validate_v2_persona_folder(folder)
            self.assertEqual(audit["missing_fields"], [])
            self.assertEqual(audit["consistency_warnings"], [])

    def test_v2_cli_migrates_selected_personas_and_validates(self) -> None:
        personas = generate_personas(count=3, random_seed=47)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "personas_v1"
            output_dir = tmp_path / "personas_v2"
            for persona in personas:
                save_persona(persona, input_dir)

            migrate_stream = io.StringIO()
            with redirect_stdout(migrate_stream):
                migrate_exit = main(
                    [
                        "migrate-personas-v2",
                        "--input-dir",
                        str(input_dir),
                        "--output-dir",
                        str(output_dir),
                        "--persona-id",
                        "su_0001",
                        "--persona-id",
                        "su_0002",
                    ]
                )

            self.assertEqual(migrate_exit, 0)
            self.assertIn("Migrated 2 personas", migrate_stream.getvalue())

            loaded = load_personas(output_dir)
            self.assertEqual(len(loaded), 2)
            self.assertTrue(all(persona.skill_version == "v2" for persona in loaded))

            validate_stream = io.StringIO()
            with redirect_stdout(validate_stream):
                validate_exit = main(["validate-personas-v2", "--data-dir", str(output_dir)])

            self.assertEqual(validate_exit, 0)
            self.assertIn("V2 validation passed", validate_stream.getvalue())

    def test_v2_prompts_are_version_controlled(self) -> None:
        prompts = load_v2_prompt_texts()

        self.assertEqual(set(prompts.keys()), set(PROMPT_VERSIONS))
        self.assertTrue(all(text for text in prompts.values()))


if __name__ == "__main__":
    unittest.main()
