import random
from pathlib import Path

from ai_validation_swarm.personas.generator import build_seed, enrich_seed
from ai_validation_swarm.personas.v2 import migrate_personas_to_v2


def build_legacy_v2_fixtures(output_dir: Path) -> None:
    fixtures = []

    daniel_rng = random.Random(101)
    daniel_seed = build_seed(index=0, rng=daniel_rng, panel_role="mainstream")
    daniel_seed.age_band = "25-34"
    daniel_seed.occupation_band = "program_management"
    daniel_seed.occupation_title = "program manager"
    daniel_seed.life_stage = "early_career_specialist"
    daniel_seed.purchase_authority_type = "workflow_tool_evaluator"
    daniel = enrich_seed(seed=daniel_seed, index=0, rng=daniel_rng)
    daniel.profile.basic_identity.update(
        {
            "name": "Daniel Chan",
            "age": 28,
            "gender": "man",
            "location": "Penang",
            "language": ["English", "Mandarin"],
            "occupation": "program manager",
            "family_structure": "living with parents",
            "household_size": 3,
            "life_stage": "early_career_specialist",
        }
    )
    daniel.profile.technology_profile["ai_familiarity"] = "medium"
    daniel.profile.economic_profile["purchase_authority_type"] = "workflow_tool_evaluator"
    fixtures.append(daniel)

    jordan_rng = random.Random(202)
    jordan_seed = build_seed(index=1, rng=jordan_rng, panel_role="skeptic")
    jordan_seed.age_band = "55-64"
    jordan_seed.occupation_band = "operations"
    jordan_seed.occupation_title = "operations manager"
    jordan_seed.life_stage = "mature_operator"
    jordan_seed.purchase_authority_type = "department_budget_recommender"
    jordan = enrich_seed(seed=jordan_seed, index=1, rng=jordan_rng)
    jordan.profile.basic_identity.update(
        {
            "name": "Jordan Chan",
            "age": 59,
            "gender": "non-binary",
            "location": "Kuala Lumpur",
            "language": ["English", "Malay"],
            "occupation": "operations manager",
            "family_structure": "living with parents",
            "household_size": 3,
            "life_stage": "mature_operator",
        }
    )
    jordan.profile.technology_profile["ai_familiarity"] = "low"
    jordan.profile.economic_profile["purchase_authority_type"] = "department_budget_recommender"
    fixtures.append(jordan)

    migrate_personas_to_v2(personas=fixtures, output_dir=output_dir, random_seed_offset=700)
