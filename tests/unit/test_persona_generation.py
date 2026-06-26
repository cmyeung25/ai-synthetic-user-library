import random
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.personas.generator import FIRST_NAMES_BY_GENDER, build_seed, enrich_seed, generate_personas
from ai_validation_swarm.personas.seed_coherence import (
    LIFE_STAGE_OPTIONS,
    PURCHASE_AUTHORITY_TYPES,
    choose_life_stage,
    life_stage_candidates,
    occupation_title_for_band,
    choose_purchase_authority,
)
from ai_validation_swarm.storage.files import load_personas, save_persona


class PersonaGenerationTest(unittest.TestCase):
    def test_early_batch_rotates_surnames_while_preserving_gender_name_match(self) -> None:
        personas = generate_personas(count=3, random_seed=3)
        surnames = [persona.profile.basic_identity["name"].split()[-1] for persona in personas]
        self.assertEqual(len(set(surnames)), 3)
        for persona in personas:
            identity = persona.profile.basic_identity
            self.assertIn(identity["name"].split()[0], FIRST_NAMES_BY_GENDER[identity["gender"]])

    def test_age_45_to_54_is_not_labeled_late_career(self) -> None:
        for occupation_band in (
            "operations",
            "client_service",
            "program_management",
            "compliance_ops",
            "customer_success",
        ):
            candidates = life_stage_candidates(
                age_band="45-54",
                occupation_band=occupation_band,
                household_structure="living with partner",
                panel_role="mainstream",
            )
            self.assertNotIn("late_career_specialist", candidates)

    def test_generate_personas_has_stable_ids_and_artifacts(self) -> None:
        personas = generate_personas(count=24, random_seed=17)
        self.assertEqual(len(personas), 24)
        self.assertEqual(personas[0].profile.synthetic_user_id, "su_0001")
        self.assertTrue(personas[0].decision_policy["trust_requirements"])
        self.assertGreaterEqual(len({persona.profile.basic_identity["gender"] for persona in personas}), 3)
        self.assertEqual(
            len({persona.profile.basic_identity["name"] for persona in personas}),
            len(personas),
        )
        for persona in personas:
            identity = persona.profile.basic_identity
            economic = persona.profile.economic_profile
            first_name = identity["name"].split()[0]
            gender = identity["gender"]
            self.assertIn(first_name, FIRST_NAMES_BY_GENDER[gender])
            family_structure = identity["family_structure"]
            if family_structure == "living alone":
                self.assertEqual(identity["household_size"], 1)
                self.assertEqual(identity["marital_status"], "single")
            elif family_structure == "living with partner":
                self.assertEqual(identity["household_size"], 2)
                self.assertEqual(identity["marital_status"], "married")
            elif family_structure == "living with partner and one child":
                self.assertEqual(identity["household_size"], 3)
                self.assertEqual(identity["marital_status"], "married")
            elif family_structure == "living with parents":
                self.assertGreaterEqual(identity["household_size"], 2)
                self.assertEqual(identity["marital_status"], "single")
            elif family_structure == "living with roommates":
                self.assertGreaterEqual(identity["household_size"], 2)
            elif family_structure == "single parent with one child":
                self.assertEqual(identity["household_size"], 2)
                self.assertEqual(identity["marital_status"], "single")
            elif family_structure == "multi-generational household":
                self.assertGreaterEqual(identity["household_size"], 4)
            else:
                self.fail(f"Unexpected family_structure {family_structure}")

            self.assertIn(identity["life_stage"], LIFE_STAGE_OPTIONS)
            self.assertIn(economic["purchase_authority_type"], PURCHASE_AUTHORITY_TYPES)
            self.assertEqual(persona.seed.occupation_title, identity["occupation"])
            self.assertNotIn("_", persona.profile.life_story["current_daily_routine"])
            self.assertNotIn("_", persona.profile.life_story["education_journey"])

            age = identity["age"]
            occupation = identity["occupation"]
            authority = economic["purchase_authority_type"]
            life_stage = identity["life_stage"]
            if occupation == "small business owner":
                self.assertIn(
                    life_stage,
                    {
                        "early_adult_small_business_builder",
                        "mid_career_operator",
                        "regional_business_builder",
                        "senior_operator",
                        "late_career_specialist",
                    },
                )
                self.assertIn(
                    authority,
                    {"owner_decider", "owner_with_family_consultation", "owner_with_staff_input"},
                )
            if occupation == "startup founder":
                self.assertIn(
                    life_stage,
                    {"young_operator_founder", "regional_business_builder", "senior_operator", "late_career_specialist"},
                )
                self.assertIn(
                    authority,
                    {"owner_decider", "owner_with_business_partner_input", "owner_with_family_consultation"},
                )
            if occupation == "operations manager" and age >= 55:
                self.assertIn(life_stage, {"mature_operator", "retention_skeptic"})
            if age <= 34:
                self.assertNotIn(life_stage, {"mature_operator", "retention_skeptic", "late_career_specialist"})
            if authority.startswith("owner_"):
                self.assertIn(occupation, {"small business owner", "startup founder"})

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            for persona in personas:
                save_persona(persona, base_dir)
            loaded = load_personas(base_dir)
            self.assertEqual(len(loaded), 24)
            self.assertEqual(loaded[0].profile.basic_identity["name"], personas[0].profile.basic_identity["name"])

    def test_generate_personas_supports_hundred_unique_names(self) -> None:
        personas = generate_personas(count=100, random_seed=31)
        names = [persona.profile.basic_identity["name"] for persona in personas]
        self.assertEqual(len(set(names)), 100)
        self.assertTrue(all(persona.seed.locale_pack for persona in personas))
        self.assertTrue(all(persona.seed.life_stage for persona in personas))

    def test_upstream_seed_coherence_catches_extreme_user_small_business_case(self) -> None:
        rng = random.Random(211 + 2)
        seed = build_seed(index=2, rng=rng, panel_role="extreme_user")
        seed.age_band = "25-34"
        seed.occupation_band = "small_business"
        seed.occupation_title = occupation_title_for_band(seed.occupation_band)
        seed.household_structure = "living with parents"
        seed.life_stage = choose_life_stage(
            rng=rng,
            age_band=seed.age_band,
            occupation_band=seed.occupation_band,
            household_structure=seed.household_structure,
            panel_role=seed.panel_role,
        )
        seed.purchase_authority_type = choose_purchase_authority(
            rng=rng,
            age_band=seed.age_band,
            occupation_band=seed.occupation_band,
            household_structure=seed.household_structure,
            panel_role=seed.panel_role,
        )
        self.assertEqual(seed.occupation_title, "small business owner")
        persona = enrich_seed(seed=seed, index=2, rng=rng)
        self.assertEqual(persona.profile.basic_identity["occupation"], "small business owner")
        self.assertIn(persona.profile.basic_identity["age"], range(25, 35))
        self.assertEqual(persona.profile.basic_identity["life_stage"], "early_adult_small_business_builder")
        self.assertIn(
            persona.profile.economic_profile["purchase_authority_type"],
            {"owner_decider", "owner_with_family_consultation"},
        )


if __name__ == "__main__":
    unittest.main()
