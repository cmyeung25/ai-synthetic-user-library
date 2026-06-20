import copy
import io
import json
import random
import shutil
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
from ai_validation_swarm.personas.consistency_validator_v3_1_2 import build_consistency_report_v3_1_2
from ai_validation_swarm.personas.generator import build_seed, enrich_seed
from ai_validation_swarm.personas.v2 import migrate_personas_to_v2
from ai_validation_swarm.personas.v3_1_2 import _build_generation_status, validate_v3_1_2_persona_library
from ai_validation_swarm.storage.files import load_persona, read_json, write_json
from tests.unit.persona_fixture_factory import build_legacy_v2_fixtures


class PersonaV312Test(unittest.TestCase):
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
            personas=[cls._build_raw_persona("su_0003", random_seed=211, panel_role="extreme_user")],
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
            main(
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

        stream = io.StringIO()
        with redirect_stdout(stream):
            cls.generate_exit_code = main(
                [
                    "generate-v3-1-2-persona",
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

    def _v3_1_2_dir(self, persona_id: str) -> Path:
        return self.output_dir / persona_id / "v3_1_2"

    def _profile(self, persona_id: str) -> dict:
        return read_json(self._v3_1_2_dir(persona_id) / "profile.json")

    def _audit(self, persona_id: str) -> dict:
        return read_json(self._v3_1_2_dir(persona_id) / "audit.json")

    def _consistency(self, persona_id: str) -> dict:
        return read_json(self._v3_1_2_dir(persona_id) / "consistency_report.json")

    def _semantic(self, persona_id: str) -> dict:
        return read_json(self._v3_1_2_dir(persona_id) / "semantic_mapping_report.json")

    def _diversity(self, persona_id: str) -> dict:
        return read_json(self._v3_1_2_dir(persona_id) / "diversity_report.json")

    def test_v3_1_2_required_files_exist(self) -> None:
        self.assertEqual(self.generate_exit_code, 0)
        required = {
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
            "polish_report.json",
            "consistency_report.json",
            "semantic_mapping_report.json",
            "v3_1_1_to_v3_1_2_diff.md",
        }
        for persona_id in ("su_0001", "su_0002", "su_0003"):
            self.assertTrue(required.issubset({path.name for path in self._v3_1_2_dir(persona_id).iterdir()}))

    def test_generation_status_exists(self) -> None:
        profile = self._profile("su_0003")
        audit = self._audit("su_0003")
        notes = read_json(self._v3_1_2_dir("su_0003") / "generation_notes.json")
        self.assertIn("generation_status", profile)
        self.assertIn("generation_status", audit["audit"])
        self.assertIn("generation_status", notes)

    def test_age_life_stage_consistency(self) -> None:
        profile = self._profile("su_0003")
        self.assertEqual(profile["basic_identity"]["age"], 26)
        self.assertEqual(profile["basic_identity"]["life_stage"], "early_adult_small_business_builder")
        self.assertNotEqual(profile["basic_identity"]["life_stage"], "late_career_practical_buyer")

    def test_occupation_purchase_authority_consistency(self) -> None:
        profile = self._profile("su_0003")
        authority = profile["economic_profile"]["purchase_authority_type"]
        self.assertIn(authority, {"owner_decider", "owner_with_family_consultation"})
        self.assertNotEqual(authority, "manager_approver")
        self.assertEqual(profile["behavior_profile"]["manager_approval_dependence"], "low")

    def test_small_business_owner_has_business_context(self) -> None:
        profile = self._profile("su_0003")
        context = profile["small_business_context"]
        self.assertEqual(context["business_type"], "content-led microbusiness")
        self.assertGreaterEqual(len(context["daily_business_tasks"]), 4)
        self.assertGreaterEqual(len(context["what_visible_win_means"]), 4)

    def test_gender_pronoun_consistency(self) -> None:
        profile = self._profile("su_0003")
        identity_language = profile["identity_language"]
        self.assertEqual(profile["basic_identity"]["gender"], "non-binary")
        self.assertEqual(identity_language["pronoun_preference"], "they/them")
        self.assertIn("they/them", identity_language["narration_pronoun_style"])

    def test_consistency_report_exists(self) -> None:
        report = self._consistency("su_0003")
        self.assertIn(report["status"], {"pass", "warning"})
        self.assertEqual(report["hard_fail_reasons"], [])

    def test_sensitive_semantic_mapping_report_exists(self) -> None:
        report = self._semantic("su_0003")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["failed_fields"], [])

    def test_privacy_reducer_not_generic_objection(self) -> None:
        profile = self._profile("su_0003")
        reducer = profile["sensitive_scenario_reactions"]["privacy_and_data"]["what_reduces_trust"].lower()
        self.assertNotIn("visible win", reducer)
        self.assertNotIn("what does this replace", reducer)

    def test_health_reducer_not_boundary_rule(self) -> None:
        profile = self._profile("su_0003")
        reducer = profile["sensitive_scenario_reactions"]["health_or_wellbeing_sensitivity"]["what_reduces_trust"].lower()
        self.assertNotIn("third-party data", reducer)
        self.assertNotIn("without a clear reason", reducer)

    def test_cross_domain_archetype_specific_for_visible_win_user(self) -> None:
        profile = self._profile("su_0003")
        model = profile["cross_domain_product_reaction_model"]
        self.assertIn("small_business_growth_product", model)
        self.assertIn("first week", model["generic_new_product"]["first_question"].lower())
        self.assertIn("leads", model["small_business_growth_product"]["first_question"].lower())
        self.assertIn("visible business result", model["small_business_growth_product"]["likely_objection"].lower())

    def test_non_work_scene_at_least_one_true_life_scene(self) -> None:
        profile = self._profile("su_0003")
        scenes = profile["canonical_biography"]["non_work_purchase_scenes"]
        text = " ".join(scene["specific_scene"] for scene in scenes).lower()
        self.assertGreaterEqual(len(scenes), 3)
        self.assertTrue(any(token in text for token in ("camera", "weekend", "wellbeing", "street market")))

    def test_audit_ingests_consistency_report(self) -> None:
        audit = self._audit("su_0003")["audit"]
        consistency = self._consistency("su_0003")
        self.assertEqual(audit["consistency_report_summary"]["status"], consistency["status"])
        self.assertEqual(audit["generation_status"]["status"], self._profile("su_0003")["generation_status"]["status"])

    def test_audit_ingests_diversity_report(self) -> None:
        audit = self._audit("su_0003")["audit"]
        diversity = self._diversity("su_0003")
        self.assertEqual(audit["diversity_summary"]["overall_similarity_score"], diversity["overall_similarity_score"])

    def test_quality_audit_not_all_perfect_and_has_weaknesses(self) -> None:
        quality = self._audit("su_0003")["audit"]["quality_audit"]
        self.assertFalse(all(value == 5 for value in quality["scores"].values()))
        self.assertGreaterEqual(len(quality["weaknesses"]), 3)
        self.assertGreaterEqual(len(quality["required_improvements"]), 3)

    def test_no_profile_contradictions_in_su_0003(self) -> None:
        profile = self._profile("su_0003")
        self.assertEqual(profile["basic_identity"]["occupation"], "small business owner")
        self.assertNotEqual(profile["basic_identity"]["life_stage"], "late_career_practical_buyer")
        self.assertNotEqual(profile["economic_profile"]["purchase_authority_type"], "manager_approver")

    def test_failed_consistency_blocks_library_entry(self) -> None:
        persona = load_persona(self._v3_1_2_dir("su_0003"))
        persona.profile.basic_identity["life_stage"] = "late_career_practical_buyer"
        persona.profile.economic_profile["purchase_authority_type"] = "manager_approver"
        consistency = build_consistency_report_v3_1_2(persona)
        status = _build_generation_status(
            consistency_report=consistency,
            diversity_report={"overall_similarity_score": 0.1},
            semantic_report={"status": "pass", "warnings": []},
            polish_report={"remaining_known_limitations": []},
        )
        self.assertEqual(status["status"], "failed_consistency")
        self.assertFalse(status["can_enter_library"])

    def test_diversity_hard_fail_blocks_acceptance(self) -> None:
        status = _build_generation_status(
            consistency_report={"status": "pass", "hard_fail_reasons": [], "warnings": []},
            diversity_report={"overall_similarity_score": 0.91},
            semantic_report={"status": "pass", "warnings": []},
            polish_report={"remaining_known_limitations": []},
        )
        self.assertEqual(status["status"], "failed_distinctiveness")
        self.assertFalse(status["can_enter_library"])

    def test_regeneration_loop_runs_on_failed_candidate_and_saves_rejected_candidate(self) -> None:
        compare_dir = self.tmp_path / "compare_clone"
        clone_dir = compare_dir / "su_9000" / "v3_1_1"
        clone_dir.mkdir(parents=True, exist_ok=True)
        for filename in ("profile.json", "audit.json", "persona.md"):
            shutil.copy2(self.output_dir / "su_0003" / "v3_1_1" / filename, clone_dir / filename)

        clone_profile = read_json(clone_dir / "profile.json")
        clone_profile["basic_identity"]["synthetic_user_id"] = "su_9000"
        write_json(clone_dir / "profile.json", clone_profile)

        clone_audit = read_json(clone_dir / "audit.json")
        clone_audit["seed"]["seed_id"] = "seed_9000"
        write_json(clone_dir / "audit.json", clone_audit)

        rejected_output = self.tmp_path / "rejected_case"
        with redirect_stdout(io.StringIO()):
            exit_code = main(
                [
                    "generate-v3-1-2-persona",
                    "--source-dir",
                    str(self.output_dir),
                    "--output-dir",
                    str(rejected_output),
                    "--compare-against",
                    str(compare_dir),
                    "--persona-id",
                    "su_0003",
                    "--against-persona-id",
                    "su_9000",
                    "--max-attempts",
                    "1",
                ]
            )
        self.assertEqual(exit_code, 0)
        rejected_root = rejected_output / "rejected" / "su_0003"
        self.assertTrue(rejected_root.exists())
        latest = sorted(rejected_root.iterdir())[-1]
        failure_report = read_json(latest / "failure_report.json")
        self.assertEqual(failure_report["status"], "failed_regeneration")
        self.assertFalse(failure_report["generation_status"]["can_enter_library"])
        self.assertFalse((rejected_output / "su_0003" / "v3_1_2").exists())

    def test_validate_personas_v3_1_2(self) -> None:
        report = validate_v3_1_2_persona_library(self.output_dir)
        self.assertEqual(report["library_size"], 3)
        self.assertEqual(report["issue_count"], 0)


if __name__ == "__main__":
    unittest.main()
