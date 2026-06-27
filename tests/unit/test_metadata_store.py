import sqlite3
import tempfile
import unittest
from contextlib import closing
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.storage.files import rebuild_persona_metadata_index, save_persona, write_json


class MetadataStoreTest(unittest.TestCase):
    def test_save_persona_updates_sqlite_metadata_index(self) -> None:
        persona = generate_personas(count=1, random_seed=91)[0]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_dir = root / "personas"
            folder = save_persona(persona, base_dir)

            metadata_db = base_dir / "metadata.sqlite3"
            self.assertTrue(metadata_db.exists())
            with closing(sqlite3.connect(metadata_db)) as connection:
                persona_row = connection.execute(
                    """
                    SELECT panel_role, locale_pack, skill_version, profile_json_path
                    FROM persona_records
                    WHERE synthetic_user_id = ?
                    """,
                    (persona.profile.synthetic_user_id,),
                ).fetchone()

            self.assertEqual(persona_row[0], persona.seed.panel_role)
            self.assertEqual(persona_row[1], persona.seed.locale_pack)
            self.assertEqual(persona_row[2], persona.skill_version)
            self.assertEqual(persona_row[3], str(folder / "profile.json"))

            with closing(sqlite3.connect(metadata_db)) as connection:
                selection_row = connection.execute(
                    """
                    SELECT price_sensitivity, trust_style, market_tags_json, active
                    FROM persona_selection_records
                    WHERE synthetic_user_id = ?
                    """,
                    (persona.profile.synthetic_user_id,),
                ).fetchone()
                trait_rows = connection.execute(
                    """
                    SELECT trait_key, trait_value, source_kind
                    FROM persona_trait_assignments
                    WHERE synthetic_user_id = ?
                    ORDER BY trait_key, trait_value
                    """,
                    (persona.profile.synthetic_user_id,),
                ).fetchall()

            self.assertEqual(selection_row[0], persona.profile.economic_profile["price_sensitivity"])
            self.assertEqual(selection_row[1], persona.seed.trust_threshold)
            self.assertEqual(selection_row[3], 1)
            self.assertIn(f"locale:{persona.seed.locale_pack}", json.loads(selection_row[2]))
            self.assertIn(("panel_role", persona.seed.panel_role, "seed"), trait_rows)
            self.assertIn(("locale_pack", persona.seed.locale_pack, "seed"), trait_rows)

    def test_rebuild_persona_metadata_index_persists_selection_traits_and_similarity_edges(self) -> None:
        persona = generate_personas(count=1, random_seed=17)[0]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_dir = root / "personas"
            folder = base_dir / persona.profile.synthetic_user_id / "v5_1"
            folder.mkdir(parents=True)
            write_json(folder / "profile.json", persona.profile.to_dict())
            write_json(folder / "audit.json", persona.to_audit_payload())
            (folder / "persona.md").write_text(persona.narrative, encoding="utf-8")
            write_json(
                folder / "quality_report.json",
                {
                    "scores": {
                        "overall": 4,
                        "consistency": 4,
                        "plausibility": 3,
                    }
                },
            )
            write_json(
                folder / "duplicate_report.json",
                {
                    "synthetic_user_id": persona.profile.synthetic_user_id,
                    "compared_against": ["su_0999"],
                    "overall_similarity_score": 0.31,
                    "high_similarity_dimensions": ["life_arc_similarity"],
                    "distinctiveness_score": 0.69,
                    "pair_reports": [
                        {
                            "persona_id": "su_0999",
                            "overall_similarity_score": 0.31,
                            "dimensions": {
                                "life_arc_similarity": 0.57,
                                "objection_language_similarity": 0.22,
                            },
                        }
                    ],
                },
            )

            indexed = rebuild_persona_metadata_index(base_dir)

            self.assertEqual(indexed, 1)
            metadata_db = base_dir / "metadata.sqlite3"
            with closing(sqlite3.connect(metadata_db)) as connection:
                selection_row = connection.execute(
                    """
                    SELECT occupation_band, quality_score, uniqueness_score
                    FROM persona_selection_records
                    WHERE synthetic_user_id = ?
                    """,
                    (persona.profile.synthetic_user_id,),
                ).fetchone()
                market_tag_rows = connection.execute(
                    """
                    SELECT trait_value
                    FROM persona_trait_assignments
                    WHERE synthetic_user_id = ? AND trait_key = 'market_tag'
                    ORDER BY trait_value
                    """,
                    (persona.profile.synthetic_user_id,),
                ).fetchall()
                similarity_row = connection.execute(
                    """
                    SELECT target_persona_id, similarity_score, distinctiveness_score
                    FROM persona_similarity_edges
                    WHERE source_persona_id = ?
                    """,
                    (persona.profile.synthetic_user_id,),
                ).fetchone()

            self.assertEqual(selection_row[0], persona.seed.occupation_band)
            self.assertEqual(selection_row[1], 4.0)
            self.assertEqual(selection_row[2], 0.69)
            self.assertIn((f"locale:{persona.seed.locale_pack}",), market_tag_rows)
            self.assertEqual(similarity_row[0], "su_0999")
            self.assertEqual(similarity_row[1], 0.31)
            self.assertEqual(similarity_row[2], 0.69)


if __name__ == "__main__":
    unittest.main()
