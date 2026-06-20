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
from ai_validation_swarm.personas.v3 import RAW_ENUM_TOKENS
from ai_validation_swarm.storage.files import read_json
from tests.unit.persona_fixture_factory import build_legacy_v2_fixtures


class PersonaV31Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp_path = Path(cls._tmp.name)
        cls.source_dir = cls.tmp_path / "source_v2"
        cls.output_dir = cls.tmp_path / "personas"
        cls.source_dir.mkdir(parents=True, exist_ok=True)

        build_legacy_v2_fixtures(cls.source_dir)

        with redirect_stdout(io.StringIO()):
            cls.generate_v3_exit_code = main(
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

        cls.v3_snapshots: dict[str, dict[str, str]] = {}
        for persona_id in ("su_0001", "su_0002"):
            v3_dir = cls.output_dir / persona_id / "v3"
            cls.v3_snapshots[persona_id] = {
                path.name: path.read_text(encoding="utf-8")
                for path in v3_dir.iterdir()
                if path.is_file() and path.suffix in {".md", ".json"}
            }

        stream = io.StringIO()
        with redirect_stdout(stream):
            cls.generate_v3_1_exit_code = main(
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
                ]
            )
        cls.generate_v3_1_output = stream.getvalue()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _v3_dir(self, persona_id: str) -> Path:
        return self.output_dir / persona_id / "v3"

    def _v3_1_dir(self, persona_id: str) -> Path:
        return self.output_dir / persona_id / "v3_1"

    def _profile(self, persona_id: str) -> dict:
        return read_json(self._v3_1_dir(persona_id) / "profile.json")

    def _audit(self, persona_id: str) -> dict:
        return read_json(self._v3_1_dir(persona_id) / "audit.json")

    def _diversity(self, persona_id: str) -> dict:
        return read_json(self._v3_1_dir(persona_id) / "diversity_report.json")

    def test_v3_1_required_files_exist(self) -> None:
        self.assertEqual(self.generate_v3_exit_code, 0)
        self.assertEqual(self.generate_v3_1_exit_code, 0)
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
            "v3_to_v3_1_diff.md",
        }
        for persona_id in ("su_0001", "su_0002"):
            self.assertTrue(required.issubset({path.name for path in self._v3_1_dir(persona_id).iterdir()}))

    def test_life_arc_summary_archetype_specific(self) -> None:
        daniel = self._profile("su_0001")["canonical_biography"]["life_arc_summary"]
        jordan = self._profile("su_0002")["canonical_biography"]["life_arc_summary"]
        self.assertIn("small, reversible experiments", daniel)
        self.assertIn("workplace credibility", daniel)
        self.assertIn("month two", jordan)
        self.assertIn("disclosure", jordan)
        self.assertNotIn("Their life has been shaped less by dramatic turning points", daniel)
        self.assertNotIn("Their life has been shaped less by dramatic turning points", jordan)

    def test_sensitive_scenario_salience_exists(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            salience = self._profile(persona_id)["sensitive_scenario_salience"]
            self.assertEqual(len(salience), 8)
            self.assertTrue(all(isinstance(value, int) for value in salience.values()))

    def test_sensitive_scenarios_sorted_by_salience(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            profile = self._profile(persona_id)
            salience = profile["sensitive_scenario_salience"]
            ordered_keys = [
                key
                for key, _score in sorted(salience.items(), key=lambda item: (-item[1], item[0]))
            ]
            markdown = (self._v3_1_dir(persona_id) / "sensitive_scenarios.md").read_text(encoding="utf-8")
            positions = [markdown.index(f"## {key} (salience:") for key in ordered_keys]
            self.assertEqual(positions, sorted(positions))

        daniel_top3 = [
            key
            for key, _score in sorted(
                self._profile("su_0001")["sensitive_scenario_salience"].items(),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        ]
        jordan_top3 = [
            key
            for key, _score in sorted(
                self._profile("su_0002")["sensitive_scenario_salience"].items(),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        ]
        self.assertNotEqual(daniel_top3, jordan_top3)

    def test_non_work_purchase_scenes_minimum_two(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            scenes = self._profile(persona_id)["canonical_biography"]["non_work_purchase_scenes"]
            self.assertGreaterEqual(len(scenes), 2)

    def test_non_work_scenes_have_product_research_impact(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            scenes = self._profile(persona_id)["canonical_biography"]["non_work_purchase_scenes"]
            self.assertTrue(all(scene["current_product_research_impact"] for scene in scenes))

    def test_hidden_contradictions_persona_specific(self) -> None:
        daniel = self._profile("su_0001")["contradiction_map"]
        jordan = self._profile("su_0002")["contradiction_map"]
        self.assertGreaterEqual(len(daniel), 3)
        self.assertGreaterEqual(len(jordan), 3)
        self.assertNotEqual(
            json.dumps(daniel, ensure_ascii=False, sort_keys=True),
            json.dumps(jordan, ensure_ascii=False, sort_keys=True),
        )
        self.assertTrue(any("publicly champion" in item["contradiction"] for item in daniel))
        self.assertTrue(any("public identity signal" in item["contradiction"] or "backup notes" in item["contradiction"] for item in jordan))

    def test_sensitive_similarity_below_threshold(self) -> None:
        report = self._diversity("su_0001")
        top_pair = report["pair_reports"][0]
        self.assertLess(top_pair["dimensions"]["sensitive_topic_reaction_similarity"], 0.60)

    def test_v3_to_v3_1_diff_exists(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            diff_text = (self._v3_1_dir(persona_id) / "v3_to_v3_1_diff.md").read_text(encoding="utf-8")
            self.assertIn("## Added Archetype Life Arc Rewrite", diff_text)
            self.assertIn("## Sensitive Salience Added", diff_text)
            self.assertIn("## Non-Work Scenes Added", diff_text)

    def test_no_v3_files_overwritten(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            current_snapshot = {
                path.name: path.read_text(encoding="utf-8")
                for path in self._v3_dir(persona_id).iterdir()
                if path.is_file() and path.suffix in {".md", ".json"}
            }
            self.assertEqual(self.v3_snapshots[persona_id], current_snapshot)

    def test_cross_domain_reaction_has_non_work_reference(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            model = self._profile(persona_id)["cross_domain_product_reaction_model"]
            self.assertTrue(all(block.get("non_work_purchase_scene_reference") for block in model.values()))

    def test_audit_contains_v3_1_scores(self) -> None:
        required_scores = {
            "non_work_lived_scene_quality",
            "sensitive_salience_specificity",
            "archetype_life_arc_distinctiveness",
            "cross_domain_non_work_diversity",
        }
        for persona_id in ("su_0001", "su_0002"):
            scores = self._audit(persona_id)["audit"]["quality_audit"]["scores"]
            self.assertTrue(required_scores.issubset(scores.keys()))

    def test_audit_not_all_perfect(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            quality_audit = self._audit(persona_id)["audit"]["quality_audit"]
            scores = quality_audit["scores"]
            self.assertFalse(all(value == 5 for value in scores.values()))
            self.assertGreaterEqual(len(quality_audit["weaknesses"]), 3)
            self.assertGreaterEqual(len(quality_audit["required_improvements"]), 3)

    def test_daniel_jordan_v3_1_similarity_thresholds(self) -> None:
        report = self._diversity("su_0001")
        top_pair = report["pair_reports"][0]
        self.assertLess(report["overall_similarity_score"], 0.50)
        self.assertLess(top_pair["dimensions"]["objection_language_similarity"], 0.55)
        self.assertLess(top_pair["dimensions"]["cross_domain_reaction_similarity"], 0.65)
        self.assertLess(top_pair["dimensions"]["life_arc_similarity"], 0.55)
        self.assertLess(top_pair["dimensions"]["hidden_contradiction_similarity"], 0.50)

    def test_no_raw_enum_leakage_in_readable_markdown_files(self) -> None:
        for persona_id in ("su_0001", "su_0002"):
            for markdown_path in self._v3_1_dir(persona_id).glob("*.md"):
                text = markdown_path.read_text(encoding="utf-8")
                for token in RAW_ENUM_TOKENS:
                    self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
