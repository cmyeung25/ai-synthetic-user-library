import io
import json
import random
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
from ai_validation_swarm.personas.generator import build_seed, enrich_seed
from ai_validation_swarm.personas.v2 import migrate_personas_to_v2
from ai_validation_swarm.personas.v3_1_1 import READABLE_MARKDOWN_FILES, lint_markdown_cleanliness
from ai_validation_swarm.storage.files import read_json
from tests.unit.persona_fixture_factory import build_legacy_v2_fixtures


class PersonaV311Test(unittest.TestCase):
    @staticmethod
    def _build_raw_persona(persona_id: str, *, random_seed: int, panel_role: str):
        index = int(persona_id.split("_")[-1]) - 1
        rng = random.Random(random_seed + index)
        seed = build_seed(index=index, rng=rng, panel_role=panel_role)
        return enrich_seed(seed=seed, index=index, rng=rng)

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp_path = Path(cls._tmp.name)
        cls.source_dir = cls.tmp_path / "source_v2"
        cls.output_dir = cls.tmp_path / "personas"
        cls.source_dir.mkdir(parents=True, exist_ok=True)

        build_legacy_v2_fixtures(cls.source_dir)

        migrate_personas_to_v2(
            personas=[
                cls._build_raw_persona("su_0003", random_seed=211, panel_role="extreme_user"),
                cls._build_raw_persona("su_0004", random_seed=347, panel_role="privacy_sensitive"),
            ],
            output_dir=cls.source_dir,
            random_seed_offset=900,
        )

        with redirect_stdout(io.StringIO()):
            main(
                [
                    "generate-v3-persona",
                    "--source-dir",
                    str(cls.source_dir),
                    "--output-dir",
                    str(cls.output_dir),
                    "--compare-against",
                    str(cls.output_dir),
                    "--persona-id",
                    "su_0001",
                    "--persona-id",
                    "su_0002",
                    "--persona-id",
                    "su_0003",
                ]
            )
            main(
                [
                    "generate-v3-1-persona",
                    "--source-dir",
                    str(cls.output_dir),
                    "--output-dir",
                    str(cls.output_dir),
                    "--compare-against",
                    str(cls.output_dir),
                    "--persona-id",
                    "su_0001",
                    "--persona-id",
                    "su_0002",
                    "--persona-id",
                    "su_0003",
                ]
            )

        cls.v3_1_snapshots: dict[str, dict[str, str]] = {}
        for persona_id in ("su_0001", "su_0002", "su_0003"):
            folder = cls.output_dir / persona_id / "v3_1"
            cls.v3_1_snapshots[persona_id] = {
                path.name: path.read_text(encoding="utf-8")
                for path in folder.iterdir()
                if path.is_file() and path.suffix in {".md", ".json"}
            }

        stream = io.StringIO()
        with redirect_stdout(stream):
            cls.generate_exit_code = main(
                [
                    "generate-v3-1-1-persona",
                    "--source-dir",
                    str(cls.output_dir),
                    "--output-dir",
                    str(cls.output_dir),
                    "--compare-against",
                    str(cls.output_dir),
                    "--persona-id",
                    "su_0001",
                    "--persona-id",
                    "su_0002",
                    "--persona-id",
                    "su_0003",
                ]
            )
        cls.generate_output = stream.getvalue()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _v3_1_dir(self, persona_id: str) -> Path:
        return self.output_dir / persona_id / "v3_1"

    def _v3_1_1_dir(self, persona_id: str) -> Path:
        return self.output_dir / persona_id / "v3_1_1"

    def _profile(self, persona_id: str) -> dict:
        return read_json(self._v3_1_1_dir(persona_id) / "profile.json")

    def _audit(self, persona_id: str) -> dict:
        return read_json(self._v3_1_1_dir(persona_id) / "audit.json")

    def _generate_direct_generic_fixture(self) -> Path:
        direct_source = self.tmp_path / "source_v2_direct"
        direct_output = self.tmp_path / "personas_direct_generic"
        if not (direct_source / "su_0004").exists():
            migrate_personas_to_v2(
                personas=[self._build_raw_persona("su_0004", random_seed=347, panel_role="privacy_sensitive")],
                output_dir=direct_source,
                random_seed_offset=950,
            )
        with redirect_stdout(io.StringIO()):
            exit_code = main(
                [
                    "generate-persona-to-target",
                    "--target-version",
                    "v3_1_1",
                    "--source-dir",
                    str(direct_source),
                    "--output-dir",
                    str(direct_output),
                    "--compare-against",
                    str(self.output_dir),
                    "--persona-id",
                    "su_0004",
                    "--against-persona-id",
                    "su_0001",
                    "--against-persona-id",
                    "su_0002",
                    "--against-persona-id",
                    "su_0003",
                ]
            )
        self.assertEqual(exit_code, 0)
        return direct_output

    def test_v3_1_1_required_files_exist(self) -> None:
        self.assertEqual(self.generate_exit_code, 0)
        required = {
            "profile.json",
            "audit.json",
            "biography.md",
            "research_kernel.md",
            "persona.skill.md",
            "generation_notes.json",
            "diversity_report.json",
            "local_grounding.md",
            "sensitive_scenarios.md",
            "v3_1_to_v3_1_1_diff.md",
            "polish_report.json",
        }
        for persona_id in ("su_0001", "su_0002", "su_0003"):
            self.assertTrue(required.issubset({path.name for path in self._v3_1_1_dir(persona_id).iterdir()}))

    def test_v3_1_files_not_overwritten(self) -> None:
        for persona_id in ("su_0001", "su_0002", "su_0003"):
            current_snapshot = {
                path.name: path.read_text(encoding="utf-8")
                for path in self._v3_1_dir(persona_id).iterdir()
                if path.is_file() and path.suffix in {".md", ".json"}
            }
            self.assertEqual(self.v3_1_snapshots[persona_id], current_snapshot)

    def test_no_raw_python_dict_in_markdown(self) -> None:
        for persona_id in ("su_0001", "su_0002", "su_0003"):
            for filename in READABLE_MARKDOWN_FILES:
                text = (self._v3_1_1_dir(persona_id) / filename).read_text(encoding="utf-8")
                self.assertEqual(lint_markdown_cleanliness(text)["raw_python_dict_patterns"], 0)

    def test_no_raw_json_object_leakage_in_markdown(self) -> None:
        for persona_id in ("su_0001", "su_0002", "su_0003"):
            for filename in READABLE_MARKDOWN_FILES:
                text = (self._v3_1_1_dir(persona_id) / filename).read_text(encoding="utf-8")
                self.assertEqual(lint_markdown_cleanliness(text)["raw_json_object_leakage"], 0)

    def test_formative_events_rendered_cleanly(self) -> None:
        biography = (self._v3_1_1_dir("su_0001") / "biography.md").read_text(encoding="utf-8")
        self.assertIn("## Formative Events", biography)
        self.assertIn("- 0-9 - Ordinary reliability lessons", biography)
        self.assertIn("Impact:", biography)
        self.assertNotIn("{'age_range'", biography)

    def test_no_double_punctuation_in_skill_examples(self) -> None:
        for persona_id in ("su_0001", "su_0002", "su_0003"):
            text = (self._v3_1_1_dir(persona_id) / "persona.skill.md").read_text(encoding="utf-8")
            self.assertEqual(lint_markdown_cleanliness(text)["double_punctuation"], 0)

    def test_ai_capitalized_in_skill_examples(self) -> None:
        for persona_id in ("su_0001", "su_0002", "su_0003"):
            text = (self._v3_1_1_dir(persona_id) / "persona.skill.md").read_text(encoding="utf-8")
            self.assertEqual(lint_markdown_cleanliness(text)["lowercase_ai"], 0)

    def test_response_variants_exist(self) -> None:
        for persona_id in ("su_0001", "su_0002", "su_0003"):
            text = (self._v3_1_1_dir(persona_id) / "persona.skill.md").read_text(encoding="utf-8")
            self.assertIn("## Response Variants", text)
            self.assertIn("### Full Research Response", text)
            self.assertIn("### Short Interview Response", text)
            self.assertIn("### Low-Attention Response", text)
            self.assertIn("### Polite Fake Interest Response", text)
            self.assertIn("### Genuine Trial Interest Response", text)
            self.assertIn("### Hard Rejection Response", text)

    def test_low_attention_response_exists(self) -> None:
        audit = self._audit("su_0001")["audit"]["example_response_quality"]
        self.assertTrue(audit["low_attention_variants_present"])

    def test_polite_fake_interest_response_exists(self) -> None:
        audit = self._audit("su_0002")["audit"]["example_response_quality"]
        self.assertTrue(audit["polite_fake_interest_present"])

    def test_hard_rejection_response_exists(self) -> None:
        for persona_id in ("su_0001", "su_0002", "su_0003"):
            audit = self._audit(persona_id)["audit"]["example_response_quality"]
            self.assertTrue(audit["hard_rejection_present"])

    def test_example_responses_not_identical_template(self) -> None:
        daniel = (self._v3_1_1_dir("su_0001") / "persona.skill.md").read_text(encoding="utf-8")
        jordan = (self._v3_1_1_dir("su_0002") / "persona.skill.md").read_text(encoding="utf-8")
        self.assertIn("Show me one recurring handoff", daniel)
        self.assertIn("week three", jordan)
        self.assertNotIn("I understand the pitch. That is not the part I doubt.", daniel)

    def test_persona_voiceprint_still_present(self) -> None:
        daniel = self._profile("su_0001")["persona_voiceprint"]
        jordan = self._profile("su_0002")["persona_voiceprint"]
        sam = self._profile("su_0003")["persona_voiceprint"]
        self.assertTrue(daniel["what_they_repeat_when_skeptical"])
        self.assertTrue(jordan["what_they_repeat_when_skeptical"])
        self.assertTrue(sam["what_they_repeat_when_skeptical"])

    def test_polish_report_exists(self) -> None:
        for persona_id in ("su_0001", "su_0002", "su_0003"):
            report = read_json(self._v3_1_1_dir(persona_id) / "polish_report.json")
            self.assertEqual(report["target_version"], "v3_1_1")
            self.assertIn("before_after_checks", report)

    def test_v3_1_to_v3_1_1_diff_exists(self) -> None:
        for persona_id in ("su_0001", "su_0002", "su_0003"):
            diff_text = (self._v3_1_1_dir(persona_id) / "v3_1_to_v3_1_1_diff.md").read_text(encoding="utf-8")
            self.assertIn("## Renderer Fixes", diff_text)
            self.assertIn("## Example Response Polish", diff_text)
            self.assertIn("## No Schema Change", diff_text)

    def test_generic_fallback_sensitive_scenarios_present(self) -> None:
        profile = self._profile("su_0003")
        scenarios = profile["sensitive_scenario_reactions"]
        self.assertGreaterEqual(len(scenarios), 8)
        self.assertTrue(scenarios["identity_disclosure"]["what_reduces_trust"])
        self.assertTrue(scenarios["privacy_and_data"]["what_builds_trust"])

    def test_generic_fallback_non_work_purchase_scenes_present(self) -> None:
        profile = self._profile("su_0003")
        scenes = profile["canonical_biography"]["non_work_purchase_scenes"]
        biography = (self._v3_1_1_dir("su_0003") / "biography.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(len(scenes), 2)
        self.assertIn(scenes[0]["scene_title"], biography)

    def test_generic_fallback_biography_rewrites_placeholder_scenes(self) -> None:
        profile = self._profile("su_0003")
        biography = (self._v3_1_1_dir("su_0003") / "biography.md").read_text(encoding="utf-8")
        self.assertNotIn("Their life has been shaped less by dramatic turning points", biography)
        self.assertNotIn("A formative 20-29 scene", biography)
        self.assertEqual(profile["panel_role_profile"]["behavioural_archetype"], "ambitious_signal_seeker")
        self.assertIn("visible win", biography)

    def test_generic_archetype_profile_is_diversified(self) -> None:
        profile = self._profile("su_0003")
        voice = profile["persona_voiceprint"]
        self.assertEqual(profile["panel_role_profile"]["behavioural_archetype"], "ambitious_signal_seeker")
        self.assertIn("visible win", voice["what_they_repeat_when_skeptical"].lower())
        self.assertGreaterEqual(len(profile["contradiction_map"]), 4)

    def test_generate_persona_to_target_v3_1_1_from_v2_source(self) -> None:
        target_output = self.tmp_path / "direct_target_personas"
        with redirect_stdout(io.StringIO()):
            exit_code = main(
                [
                    "generate-persona-to-target",
                    "--target-version",
                    "v3_1_1",
                    "--source-dir",
                    str(self.source_dir),
                    "--output-dir",
                    str(target_output),
                    "--compare-against",
                    str(self.output_dir),
                    "--persona-id",
                    "su_0003",
                    "--against-persona-id",
                    "su_0001",
                    "--against-persona-id",
                    "su_0002",
                ]
            )
        self.assertEqual(exit_code, 0)
        self.assertTrue((target_output / "su_0003" / "v3_1_1" / "profile.json").exists())
        self.assertTrue((target_output / "su_0003" / "v3_1_1" / "persona.skill.md").exists())

    def test_direct_target_generic_output_has_no_name_leakage(self) -> None:
        direct_output = self._generate_direct_generic_fixture()
        direct_profile = read_json(direct_output / "su_0004" / "v3_1_1" / "profile.json")
        direct_name = direct_profile["basic_identity"]["name"]
        other_name = self._profile("su_0003")["basic_identity"]["name"]
        biography = (direct_output / "su_0004" / "v3_1_1" / "biography.md").read_text(encoding="utf-8")
        skill = (direct_output / "su_0004" / "v3_1_1" / "persona.skill.md").read_text(encoding="utf-8")
        self.assertIn(direct_name, biography)
        self.assertIn(direct_name, skill)
        self.assertNotIn(other_name, biography)
        self.assertNotIn(other_name, skill)

    def test_direct_target_generic_archetype_and_grounding_are_specific(self) -> None:
        direct_output = self._generate_direct_generic_fixture()
        profile = read_json(direct_output / "su_0004" / "v3_1_1" / "profile.json")
        self.assertEqual(profile["panel_role_profile"]["behavioural_archetype"], "privacy_narrow_trialist")
        local_grounding = profile["local_grounding_layer"]
        self.assertGreaterEqual(len(local_grounding["common_apps_or_services"]), 4)
        self.assertNotIn("messaging apps", local_grounding["common_apps_or_services"])
        self.assertNotIn("search", local_grounding["common_apps_or_services"])


if __name__ == "__main__":
    unittest.main()
