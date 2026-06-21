import copy
import io
import random
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.cli.main import main
from ai_validation_swarm.domain.models import PersonaSeed
from ai_validation_swarm.personas.generator import build_seed, enrich_seed
from ai_validation_swarm.personas.v3_1_2 import upgrade_persona_to_v3_1_2
from ai_validation_swarm.personas.v3_2 import (
    PersonaSynthesisRequest,
    PersonaSynthesisResult,
    SectionBatchedV32SynthesisAdapter,
    _normalize_sections_payload,
    build_v3_2_output_schema,
    generate_v3_2_personas,
    load_v3_2_prompt_texts,
    validate_v3_2_persona_folder,
)
from ai_validation_swarm.personas.v3_2_sections import (
    DEFAULT_V3_2_REGISTRY,
    PersonaSectionRegistry,
    PersonaSectionSpec,
)
from ai_validation_swarm.storage.files import read_json


class FixtureSynthesisAdapter:
    def __init__(
        self,
        *,
        omit_first_hobby_depth: bool = False,
        malformed_first_biography: bool = False,
        override_protected_economics: bool = False,
    ) -> None:
        self.calls = []
        self.omit_first_hobby_depth = omit_first_hobby_depth
        self.malformed_first_biography = malformed_first_biography
        self.override_protected_economics = override_protected_economics

    def synthesize(self, request):
        self.calls.append(copy.deepcopy(request))
        index = int(request.synthetic_user_id[3:]) - 1
        seed = PersonaSeed(**request.seed)
        template = enrich_seed(seed=seed, index=index, rng=random.Random(request.random_seed + 991))
        template.profile.basic_identity = copy.deepcopy(request.identity_anchors)
        candidate = upgrade_persona_to_v3_1_2(template, random_seed=request.random_seed)
        sections = {}
        for spec in request.sections:
            payload = {}
            for target in spec.targets:
                if target.startswith("extensions."):
                    payload[target] = {"enabled": True, "ordinary_scene": "A quiet weekend routine shapes this preference."}
                elif target == "childhood_environment":
                    payload[target] = {
                        "family_structure_and_stability": "A generally stable household with ordinary changes in adult availability.",
                        "caregiver_dynamics": "Caregivers were practical and caring, but did not always explain decisions.",
                        "emotional_climate": "Mostly calm, with disagreement handled after people cooled down.",
                        "money_environment": "Everyday spending was discussed through trade-offs rather than shame.",
                        "authority_and_rules": "Rules were accepted when adults could explain their purpose.",
                        "conflict_repair_pattern": "Repair happened through practical gestures and later conversation.",
                        "responsibility_expectations": "Small chores increased gradually with age.",
                        "belonging_and_identity": "Belonging came from being useful without needing to be exceptional.",
                        "early_technology_environment": "Shared household devices made turn-taking and maintenance visible.",
                        "ordinary_childhood_scenes": [
                            {"age": 7, "setting": "home", "scene": "Sorted shopping receipts with a caregiver.", "lesson_at_the_time": "Small records can prevent arguments.", "adult_echo": "Looks for understandable records."},
                            {"age": 10, "setting": "school", "scene": "Shared one computer with classmates.", "lesson_at_the_time": "A system must work for several skill levels.", "adult_echo": "Checks shared-user usability."},
                            {"age": 13, "setting": "neighborhood", "scene": "Compared repair and replacement with a local shop.", "lesson_at_the_time": "Cheapest and best value differ.", "adult_echo": "Considers durability and support."},
                        ],
                        "beliefs_carried_forward": ["rules need reasons", "repair can beat replacement", "shared tools need clear turns"],
                        "adult_decision_links": [
                            {"childhood_pattern": "Shared devices", "adult_value_or_assumption": "Access should be understandable.", "product_judgment_effect": "Tests role clarity.", "limits_of_inference": "Does not imply dislike of personal devices."},
                            {"childhood_pattern": "Receipt sorting", "adult_value_or_assumption": "Records can reduce conflict.", "product_judgment_effect": "Values readable history.", "limits_of_inference": "Does not imply enthusiasm for surveillance."},
                            {"childhood_pattern": "Repair comparison", "adult_value_or_assumption": "Durability is part of price.", "product_judgment_effect": "Checks support and ownership.", "limits_of_inference": "May still buy novelty in other categories."},
                            {"childhood_pattern": "Explained rules", "adult_value_or_assumption": "Authority should state purpose.", "product_judgment_effect": "Challenges unexplained defaults.", "limits_of_inference": "Can follow urgent rules before full explanation."},
                        ],
                        "uncertainty_notes": "These are plausible influences, not deterministic causes of adult behavior.",
                    }
                else:
                    payload[target] = copy.deepcopy(getattr(candidate.profile, target))
            sections[spec.name] = payload
        hobbies = sections.get("lifestyle_and_hobbies", {}).get("interests_and_hobbies", {})
        if self.omit_first_hobby_depth and request.attempt == 1:
            hobbies["interest_depth"] = {}
        biography = sections.get("biography", {}).get("canonical_biography", {})
        if self.malformed_first_biography and request.attempt == 1:
            biography["formative_events"][0].pop("age_range", None)
            biography["non_work_purchase_scenes"][0].pop("decision_context", None)
        if self.override_protected_economics:
            economics = sections["economics_and_pricing"]["economic_profile"]
            economics.update(
                {
                    "purchase_authority_type": "owner_decider",
                    "employment_stability": "invented",
                    "cash_flow_volatility": "invented",
                    "switching_cost": "invented",
                }
            )
        return PersonaSynthesisResult(
            sections=sections,
            decision_policy=copy.deepcopy(candidate.decision_policy),
            response_style=copy.deepcopy(candidate.response_style),
            narrative=candidate.narrative,
            rationale="Deterministic fixture for V3.2 contract testing only.",
            provider="fixture",
            model="fixture-v3.2",
            prompt_versions=["persona-synthesis/v3_2.md"],
            raw_metadata={"fixture": True},
        )


class FlakyBatchFixtureAdapter(FixtureSynthesisAdapter):
    def __init__(self) -> None:
        super().__init__()
        self._seen: dict[tuple[str, str], int] = {}

    def synthesize(self, request):
        key = (request.synthetic_user_id, ",".join(section.name for section in request.sections))
        self._seen[key] = self._seen.get(key, 0) + 1
        if self._seen[key] == 1:
            self.calls.append(copy.deepcopy(request))
            return PersonaSynthesisResult(
                sections={},
                decision_policy={},
                response_style={},
                narrative="",
                rationale="first attempt intentionally incomplete",
                provider="fixture",
                model="fixture-v3.2",
                prompt_versions=["persona-synthesis/v3_2.md"],
                raw_metadata={"fixture": True, "incomplete_once": True},
            )
        return super().synthesize(request)


class PersonaV32Test(unittest.TestCase):
    def test_default_registry_assigns_narrative_sections_to_llm(self) -> None:
        sections = DEFAULT_V3_2_REGISTRY.enabled()
        self.assertIn("lifestyle_and_hobbies", {section.name for section in sections})
        self.assertIn("childhood_environment", {section.name for section in sections})
        self.assertTrue(all(section.owner == "llm" for section in sections))
        lifestyle = DEFAULT_V3_2_REGISTRY.get("lifestyle_and_hobbies")
        self.assertIn("interests_and_hobbies", lifestyle.targets)

    def test_registry_accepts_future_extension_without_pipeline_change(self) -> None:
        registry = PersonaSectionRegistry(DEFAULT_V3_2_REGISTRY.enabled())
        registry.register(
            PersonaSectionSpec(
                name="pet_context",
                targets=("extensions.pet_context",),
                prompt_version="lifestyle-hobbies/v3_2.md",
            )
        )
        self.assertEqual(registry.get("pet_context").targets, ("extensions.pet_context",))

    def test_registry_rejects_rule_owned_profile_targets(self) -> None:
        registry = PersonaSectionRegistry(DEFAULT_V3_2_REGISTRY.enabled())
        with self.assertRaisesRegex(ValueError, "rule-owned profile fields"):
            registry.register(
                PersonaSectionSpec(
                    name="identity_rewrite",
                    targets=("basic_identity",),
                    prompt_version="persona-synthesis/v3_2.md",
                )
            )

    def test_optional_section_is_added_without_disabling_required_sections(self) -> None:
        registry = PersonaSectionRegistry(DEFAULT_V3_2_REGISTRY.enabled())
        registry.register(
            PersonaSectionSpec(
                name="pet_context",
                targets=("extensions.pet_context",),
                prompt_version="lifestyle-hobbies/v3_2.md",
                required=False,
            )
        )
        resolved = registry.resolve_generation_sections(["pet_context"])
        names = {section.name for section in resolved}
        self.assertIn("biography", names)
        self.assertIn("lifestyle_and_hobbies", names)
        self.assertIn("pet_context", names)

    def test_output_schema_is_derived_from_registry(self) -> None:
        sections = DEFAULT_V3_2_REGISTRY.enabled(["biography", "lifestyle_and_hobbies"])
        schema = build_v3_2_output_schema(sections)
        required = schema["properties"]["sections"]["required"]
        self.assertEqual(required, ["biography", "lifestyle_and_hobbies"])
        hobby_targets = schema["properties"]["sections"]["properties"]["lifestyle_and_hobbies"]["required"]
        self.assertIn("interests_and_hobbies", hobby_targets)

    def test_normalize_sections_payload_accepts_direct_single_section_shape(self) -> None:
        section = PersonaSectionSpec(
            name="childhood_environment",
            targets=("childhood_environment",),
            prompt_version="childhood-environment/v3_2.md",
        )
        payload = {
            "childhood_environment": {
                "family_structure_and_stability": "stable",
                "ordinary_childhood_scenes": [{"age": 7, "setting": "home", "scene": "sorted notes"}],
            }
        }
        normalized = _normalize_sections_payload(payload, [section])
        self.assertEqual(
            normalized,
            {
                "childhood_environment": {
                    "childhood_environment": payload["childhood_environment"],
                }
            },
        )

    def test_direct_generation_writes_v3_2_with_provenance_and_hobbies(self) -> None:
        adapter = FixtureSynthesisAdapter()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = generate_v3_2_personas(
                persona_ids=["su_0031"],
                output_dir=root,
                adapter=adapter,
                random_seed_offset=31,
            )
            self.assertEqual(paths, [root / "su_0031" / "v3_2"])
            folder = paths[0]
            report = validate_v3_2_persona_folder(folder)
            self.assertTrue(report["valid"], report)
            profile = read_json(folder / "profile.json")
            notes = read_json(folder / "generation_notes.json")
            manifest = read_json(folder / "section_manifest.json")
            constraint_report = read_json(folder / "constraint_report.json")
            self.assertTrue(profile["interests_and_hobbies"]["primary_interests"])
            self.assertEqual(notes["generation_mode"], "direct_constraint_bounded_llm_synthesis")
            self.assertEqual(notes["provider"], "fixture")
            self.assertEqual(len(notes["input_context_sha256"]), 64)
            self.assertIn("lifestyle_and_hobbies", {item["name"] for item in manifest["sections"]})
            self.assertEqual(constraint_report["status"], "pass")
            self.assertTrue(all(constraint_report["checks"].values()))
            audit = read_json(folder / "audit.json")
            self.assertEqual(
                profile["economic_profile"]["purchase_authority_type"],
                audit["seed"]["purchase_authority_type"],
            )
            self.assertFalse((root / "su_0031" / "v3_1_2").exists())
            biography = (folder / "biography.md").read_text(encoding="utf-8")
            skill = (folder / "persona.skill.md").read_text(encoding="utf-8")
            kernel = (folder / "research_kernel.md").read_text(encoding="utf-8")
            self.assertIn("## Childhood Environment & Foundations", biography)
            self.assertIn("## Childhood Foundations", skill)
            self.assertIn("## Childhood Foundations", kernel)
            self.assertGreaterEqual(len(profile["childhood_environment"]["ordinary_childhood_scenes"]), 3)

    def test_approved_generation_brief_overrides_seed_and_identity_anchors(self) -> None:
        adapter = FixtureSynthesisAdapter()
        brief = {
            "synthetic_user_id": "su_0035",
            "seed_overrides": {
                "age_band": "25-34",
                "location_type": "urban_core",
                "household_structure": "living alone",
                "occupation_band": "health_admin",
                "occupation_title": "clinic operations coordinator",
            },
            "identity_overrides": {
                "name": "Test Person",
                "age": 29,
                "gender": "woman",
                "location": "Hong Kong",
                "occupation": "clinic operations coordinator",
                "family_structure": "living alone",
            },
            "research_context": {"label": "spontaneous gap explorer"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            paths = generate_v3_2_personas(
                persona_ids=["su_0035"],
                output_dir=Path(tmp),
                adapter=adapter,
                random_seed_offset=35,
                generation_briefs={"su_0035": brief},
            )

            profile = read_json(paths[0] / "profile.json")
            notes = read_json(paths[0] / "generation_notes.json")
            stored_brief = read_json(paths[0] / "generation_brief.json")
            self.assertEqual(profile["basic_identity"]["name"], "Test Person")
            self.assertEqual(profile["basic_identity"]["age"], 29)
            self.assertEqual(profile["basic_identity"]["location"], "Hong Kong")
            self.assertEqual(stored_brief["research_context"]["label"], "spontaneous gap explorer")
            self.assertEqual(len(notes["input_context_sha256"]), 64)
            self.assertEqual(adapter.calls[0].creative_brief["approved_generation_brief"], brief)

    def test_section_batched_adapter_merges_complete_result(self) -> None:
        fixture = FixtureSynthesisAdapter()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = SectionBatchedV32SynthesisAdapter(
                fixture,
                batch_size=2,
                cache_dir=root / "cache",
            )
            paths = generate_v3_2_personas(
                persona_ids=["su_0036"],
                output_dir=root,
                adapter=adapter,
                random_seed_offset=36,
            )

            self.assertEqual(len(fixture.calls), 5)
            self.assertTrue(all(len(call.sections) <= 2 for call in fixture.calls))
            self.assertTrue(validate_v3_2_persona_folder(paths[0])["valid"])
            notes = read_json(paths[0] / "generation_notes.json")
            self.assertTrue(notes["adapter_metadata"]["section_batched"])
            self.assertEqual(notes["adapter_metadata"]["batch_count"], 5)
            generate_v3_2_personas(
                persona_ids=["su_0036"],
                output_dir=root,
                adapter=adapter,
                random_seed_offset=36,
            )
            self.assertEqual(len(fixture.calls), 5)

    def test_section_cache_is_isolated_by_transport(self) -> None:
        fixture = FixtureSynthesisAdapter()
        fixture.config = SimpleNamespace(
            provider="codex",
            model="gpt-5.4",
            profile="chatgpt-5.4-high",
            transport="codex_cli",
            model_reasoning_effort="high",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = SectionBatchedV32SynthesisAdapter(fixture, batch_size=2, cache_dir=root / "cache")
            generate_v3_2_personas(
                persona_ids=["su_0037"], output_dir=root, adapter=adapter, random_seed_offset=37
            )
            self.assertEqual(len(fixture.calls), 5)

            fixture.config.transport = "codex_sdk_node"
            generate_v3_2_personas(
                persona_ids=["su_0037"], output_dir=root, adapter=adapter, random_seed_offset=37
            )
            self.assertEqual(len(fixture.calls), 10)

    def test_section_cache_rejects_empty_cached_result(self) -> None:
        fixture = FixtureSynthesisAdapter()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = SectionBatchedV32SynthesisAdapter(fixture, batch_size=1, cache_dir=root / "cache")
            sections = DEFAULT_V3_2_REGISTRY.resolve_generation_sections()
            seed = build_seed(index=37, rng=random.Random(37))
            baseline = enrich_seed(seed=seed, index=37, rng=random.Random(37))

            request = PersonaSynthesisRequest(
                synthetic_user_id="su_0038",
                seed=seed.to_dict(),
                identity_anchors=copy.deepcopy(baseline.profile.basic_identity),
                creative_brief={},
                sections=sections[:1],
                prompt_texts=load_v3_2_prompt_texts(sections[:1]),
                random_seed=37,
            )
            cache_path, request_hash, _ = adapter._cached_result(request, [sections[0].name])
            self.assertIsNotNone(cache_path)
            empty = PersonaSynthesisResult({}, {}, {}, "", "", "codex", "gpt-5.4", [])
            adapter._write_cached_result(cache_path, request_hash, empty)
            _, _, cached = adapter._cached_result(request, [sections[0].name])
            self.assertIsNone(cached)

    def test_section_batched_adapter_retries_incomplete_batch_result(self) -> None:
        fixture = FlakyBatchFixtureAdapter()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = SectionBatchedV32SynthesisAdapter(
                fixture,
                batch_size=1,
                cache_dir=root / "cache",
                max_batch_attempts=2,
            )
            paths = generate_v3_2_personas(
                persona_ids=["su_0043"],
                output_dir=root,
                adapter=adapter,
                random_seed_offset=43,
            )
            self.assertTrue(validate_v3_2_persona_folder(paths[0])["valid"])
            self.assertGreater(len(fixture.calls), 9)

    def test_section_batched_adapter_emits_progress_messages(self) -> None:
        fixture = FixtureSynthesisAdapter()
        progress: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = SectionBatchedV32SynthesisAdapter(
                fixture,
                batch_size=2,
                cache_dir=root / "cache",
                progress_writer=progress.append,
            )
            generate_v3_2_personas(
                persona_ids=["su_0039"],
                output_dir=root,
                adapter=adapter,
                random_seed_offset=39,
                progress_writer=progress.append,
            )

        self.assertTrue(any("start su_0039" in message for message in progress))
        self.assertTrue(any("batch 1/" in message for message in progress))
        self.assertTrue(any("wrote su_0039" in message for message in progress))

    def test_validation_findings_are_sent_back_for_targeted_retry(self) -> None:
        adapter = FixtureSynthesisAdapter(omit_first_hobby_depth=True)
        with tempfile.TemporaryDirectory() as tmp:
            paths = generate_v3_2_personas(
                persona_ids=["su_0032"],
                output_dir=Path(tmp),
                adapter=adapter,
                random_seed_offset=32,
                max_attempts=2,
            )
            self.assertEqual(len(paths), 1)
            self.assertEqual(len(adapter.calls), 2)
            self.assertIn("hobby_depth_missing:interest_depth", adapter.calls[1].revision_findings)
            notes = read_json(paths[0] / "generation_notes.json")
            self.assertEqual(notes["attempts"], 2)

    def test_nested_biography_contract_triggers_targeted_retry(self) -> None:
        adapter = FixtureSynthesisAdapter(malformed_first_biography=True)
        with tempfile.TemporaryDirectory() as tmp:
            paths = generate_v3_2_personas(
                persona_ids=["su_0033"],
                output_dir=Path(tmp),
                adapter=adapter,
                random_seed_offset=33,
                max_attempts=2,
            )
            self.assertEqual(len(paths), 1)
            findings = adapter.calls[1].revision_findings
            self.assertIn("formative_event_0_missing_render_fields", findings)
            self.assertIn("non_work_purchase_scene_0_missing_render_fields", findings)

    def test_llm_cannot_override_rule_owned_economic_constraints(self) -> None:
        adapter = FixtureSynthesisAdapter(override_protected_economics=True)
        with tempfile.TemporaryDirectory() as tmp:
            paths = generate_v3_2_personas(
                persona_ids=["su_0034"],
                output_dir=Path(tmp),
                adapter=adapter,
                random_seed_offset=34,
            )
            profile = read_json(paths[0] / "profile.json")
            audit = read_json(paths[0] / "audit.json")
            constraint_report = read_json(paths[0] / "constraint_report.json")
            seed = audit["seed"]
            self.assertEqual(profile["economic_profile"]["purchase_authority_type"], seed["purchase_authority_type"])
            self.assertEqual(profile["economic_profile"]["employment_stability"], seed["employment_stability"])
            self.assertEqual(profile["economic_profile"]["cash_flow_volatility"], seed["cash_flow_volatility"])
            self.assertEqual(profile["economic_profile"]["switching_cost"], seed["switching_cost_level"])
            self.assertEqual(constraint_report["status"], "pass")

    def test_cli_exposes_v3_2_commands(self) -> None:
        stream = io.StringIO()
        with redirect_stdout(stream):
            exit_code = main(["validate-personas-v3-2", "--data-dir", str(ROOT / "does-not-exist")])
        self.assertEqual(exit_code, 1)
        self.assertIn("No V3.2 personas found", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
