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
from ai_validation_swarm.personas.v3 import RAW_ENUM_TOKENS, _specific_chapter_scene
from ai_validation_swarm.storage.files import read_json
from tests.unit.persona_fixture_factory import build_legacy_v2_fixtures


class PersonaV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp_path = Path(cls._tmp.name)
        cls.source_dir = cls.tmp_path / "source_v2"
        cls.output_dir = cls.tmp_path / "personas"
        cls.source_dir.mkdir(parents=True, exist_ok=True)

        build_legacy_v2_fixtures(cls.source_dir)

        stream = io.StringIO()
        with redirect_stdout(stream):
            exit_code = main(
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
                ]
            )
        cls.generate_output = stream.getvalue()
        cls.generate_exit_code = exit_code

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _v3_dir(self, persona_id: str) -> Path:
        return self.output_dir / persona_id / "v3"

    def _profile(self, persona_id: str) -> dict:
        return read_json(self._v3_dir(persona_id) / "profile.json")

    def _audit(self, persona_id: str) -> dict:
        return read_json(self._v3_dir(persona_id) / "audit.json")

    def _diversity(self, persona_id: str) -> dict:
        return read_json(self._v3_dir(persona_id) / "diversity_report.json")

    def test_required_v3_files_exist(self) -> None:
        self.assertEqual(self.generate_exit_code, 0)
        required_files = {
            "profile.json",
            "audit.json",
            "persona.md",
            "biography.md",
            "research_kernel.md",
            "persona.skill.md",
            "generation_notes.json",
            "diversity_report.json",
            "local_grounding.md",
            "sensitive_scenarios.md",
            "v2_to_v3_diff.md",
        }
        for persona_id in ("su_0001", "su_0002"):
            self.assertTrue(required_files.issubset({path.name for path in self._v3_dir(persona_id).iterdir()}))

    def test_no_enum_leakage_in_biography(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            biography = (self._v3_dir(persona_id) / "biography.md").read_text(encoding="utf-8")
            for token in RAW_ENUM_TOKENS:
                self.assertNotIn(token, biography)

    def test_decade_has_specific_scene(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            profile = self._profile(persona_id)
            chapters = profile["canonical_biography"]["decade_timeline"]
            self.assertGreaterEqual(len(chapters), 3)
            self.assertTrue(all(chapter.get("specific_scene") for chapter in chapters))

    def test_specific_chapter_scene_falls_back_for_uncovered_decade(self) -> None:
        seed = build_seed(index=1, rng=random.Random(31), panel_role="mainstream")
        persona = enrich_seed(seed=seed, index=1, rng=random.Random(32))
        persona.profile.basic_identity["age"] = 31
        persona.profile.basic_identity["occupation"] = "program manager"
        persona.profile.basic_identity["location"] = "Hong Kong"
        persona.profile.technology_profile["ai_familiarity"] = "medium"

        scene = _specific_chapter_scene(persona, "30-39")

        self.assertIn("specific_scene", scene)
        self.assertIn("30-39", scene["specific_scene"])
        self.assertEqual(scene["formative_level"], "medium")

    def test_local_grounding_layer_exists(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            layer = self._profile(persona_id)["local_grounding_layer"]
            self.assertIn("trust_cues_in_this_market", layer)
            self.assertTrue(layer["trust_cues_in_this_market"])

    def test_sensitive_scenario_layer_exists(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            layer = self._profile(persona_id)["sensitive_scenario_reactions"]
            self.assertIn("identity_disclosure", layer)
            self.assertIn("privacy_and_data", layer)
            self.assertIn("workplace_visibility", layer)

    def test_persona_voiceprint_exists(self) -> None:
        daniel = self._profile("su_0001")["persona_voiceprint"]
        jordan = self._profile("su_0002")["persona_voiceprint"]
        self.assertTrue(daniel["what_they_repeat_when_skeptical"])
        self.assertTrue(jordan["what_they_repeat_when_skeptical"])
        self.assertNotEqual(daniel["example_hard_rejection"], jordan["example_hard_rejection"])

    def test_quality_audit_not_all_perfect(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            quality_audit = self._audit(persona_id)["audit"]["quality_audit"]
            scores = quality_audit["scores"]
            self.assertFalse(all(value == 5 for value in scores.values()))
            self.assertGreaterEqual(len(quality_audit["weaknesses"]), 3)
            self.assertGreaterEqual(len(quality_audit["required_improvements"]), 3)

    def test_diversity_report_exists(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            report = self._diversity(persona_id)
            self.assertIn("overall_similarity_score", report)
            self.assertIn("distinctiveness_score", report)

    def test_daniel_jordan_similarity_below_threshold(self) -> None:
        report = self._diversity("su_0001")
        self.assertLess(report["overall_similarity_score"], 0.65)

    def test_cross_domain_reactions_not_identical(self) -> None:
        daniel = self._profile("su_0001")["cross_domain_product_reaction_model"]
        jordan = self._profile("su_0002")["cross_domain_product_reaction_model"]
        self.assertNotEqual(
            json.dumps(daniel, ensure_ascii=False, sort_keys=True),
            json.dumps(jordan, ensure_ascii=False, sort_keys=True),
        )
        report = self._diversity("su_0001")
        top_pair = report["pair_reports"][0]
        self.assertLess(top_pair["dimensions"]["cross_domain_reaction_similarity"], 0.65)

    def test_objection_language_not_identical(self) -> None:
        daniel = self._profile("su_0001")["objection_language_style"]
        jordan = self._profile("su_0002")["objection_language_style"]
        self.assertNotEqual(
            json.dumps(daniel, ensure_ascii=False, sort_keys=True),
            json.dumps(jordan, ensure_ascii=False, sort_keys=True),
        )
        report = self._diversity("su_0001")
        top_pair = report["pair_reports"][0]
        self.assertLess(top_pair["dimensions"]["objection_language_similarity"], 0.55)

    def test_v2_to_v3_diff_exists(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            diff_text = (self._v3_dir(persona_id) / "v2_to_v3_diff.md").read_text(encoding="utf-8")
            self.assertIn("## Added Lived Scenes", diff_text)
            self.assertIn("## Diversified Voice", diff_text)

    def test_acceptance_scores_and_warnings(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            quality_audit = self._audit(persona_id)["audit"]["quality_audit"]
            scores = quality_audit["scores"]
            self.assertGreaterEqual(scores["local_grounding"], 4)
            self.assertGreaterEqual(scores["sensitive_topic_readiness"], 4)
            self.assertGreaterEqual(len(quality_audit["warnings"]), 1)


if __name__ == "__main__":
    unittest.main()
