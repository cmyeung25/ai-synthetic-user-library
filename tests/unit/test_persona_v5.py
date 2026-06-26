import copy
import io
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
from ai_validation_swarm.personas.v3_1_2 import RAW_ENUM_TOKENS, upgrade_persona_to_v3_1_2
from ai_validation_swarm.personas.schema_v5_1 import upgrade_profile_payload_to_v5_1
from ai_validation_swarm.personas.v5 import (
    GENERATOR_VERSION,
    V5SynthesisResult,
    build_v5_output_schema,
    generate_v5_persona,
    normalize_v5_result_structure,
    result_to_persona,
    validate_v5_persona_folder,
    validate_v5_result,
)
from ai_validation_swarm.storage.files import read_json


def _childhood() -> dict:
    return {
        "family_structure_and_stability": "A mostly stable household with ordinary changes in adult availability.",
        "caregiver_dynamics": "Care was practical, with explanations offered more often as the child grew older.",
        "emotional_climate": "Warm but not highly expressive; repair usually followed a cooling-off period.",
        "money_environment": "Purchases were discussed through trade-offs and durability.",
        "authority_and_rules": "Rules gained trust when adults explained their purpose.",
        "ordinary_childhood_scenes": [
            {"age": 7, "setting": "home", "scene": "Helped compare two grocery lists.", "lesson_at_the_time": "Small choices add up.", "adult_echo": "Checks recurring cost."},
            {"age": 10, "setting": "school", "scene": "Shared a computer for a group task.", "lesson_at_the_time": "Shared systems need clear turns.", "adult_echo": "Notices role clarity."},
            {"age": 14, "setting": "local shop", "scene": "Waited while an old device was repaired.", "lesson_at_the_time": "Repairability can beat novelty.", "adult_echo": "Asks about support."},
        ],
        "adult_decision_links": [
            {"childhood_pattern": "budget comparison", "adult_value_or_assumption": "cost repeats", "product_judgment_effect": "checks total cost", "limits_of_inference": "still buys occasional novelty"},
            {"childhood_pattern": "shared device", "adult_value_or_assumption": "roles matter", "product_judgment_effect": "checks permissions", "limits_of_inference": "can enjoy solo tools"},
            {"childhood_pattern": "repair visit", "adult_value_or_assumption": "support matters", "product_judgment_effect": "checks ownership", "limits_of_inference": "does not reject new products"},
            {"childhood_pattern": "explained rules", "adult_value_or_assumption": "purpose earns trust", "product_judgment_effect": "questions defaults", "limits_of_inference": "can act quickly in emergencies"},
        ],
        "uncertainty_notes": "These are plausible influences, not deterministic causes.",
    }


def _remove_enum_tokens(value):
    if isinstance(value, dict):
        return {key: _remove_enum_tokens(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_remove_enum_tokens(item) for item in value]
    if isinstance(value, str):
        for token in RAW_ENUM_TOKENS:
            value = value.replace(token, token.replace("_", " "))
    return value


class FixtureV5Adapter:
    def __init__(self) -> None:
        self.requests = []

    def synthesize(self, request):
        self.requests.append(copy.deepcopy(request))
        contract = request.contract() if hasattr(request, "contract") else {}
        seed = build_seed(index=1000, rng=random.Random(request.random_seed))
        persona = upgrade_persona_to_v3_1_2(
            enrich_seed(seed=seed, index=1000, rng=random.Random(request.random_seed + 1)),
            random_seed=request.random_seed,
        )
        profile = _remove_enum_tokens(persona.profile.to_dict())
        profile.setdefault("basic_identity", {})
        profile["basic_identity"]["synthetic_user_id"] = getattr(
            request,
            "synthetic_user_id",
            getattr(request, "persona_id", "su_1001"),
        )
        profile["childhood_environment"] = _childhood()
        profile["canonical_biography"].setdefault(
            "product_research_implications", ["Concrete proof matters more than polished claims."]
        )
        for category, block in profile["cross_domain_product_reaction_model"].items():
            block.setdefault("reaction_basis", "Ordinary buying and tool-use experience shapes this response.")
            block.setdefault("first_question", "What would this change in an ordinary week?")
            block.setdefault("positive_trigger", "A concrete and reversible proof of value.")
            block.setdefault("negative_trigger", "A claim that hides the ongoing effort.")
            block.setdefault("trust_requirement", "Clear limits and evidence.")
            block.setdefault("likely_objection", "The benefit may not survive normal use.")
            block.setdefault("persona_specific_example", f"They would test {category.replace('_', ' ')} in one bounded situation.")
        if "human_difference_axes" in contract.get("profile_sections", []):
            profile["human_difference_axes"] = {
                "control_preference": "Moderate; wants room to decide but appreciates scaffolding.",
                "trust_style": "Evidence with some benefit-of-doubt for credible institutions.",
                "complexity_tolerance": "Moderate; will engage if the detail clearly helps.",
                "decision_tempo": "Neither rushed nor highly delayed; gathers enough signal before acting.",
                "financial_attention_cadence": "Periodic with spikes around relevant events.",
                "relationship_to_money": "Money is a practical buffer and progress marker.",
                "risk_orientation": "Open to measured risk when the downside is understandable.",
                "need_for_explanation": "High enough to want plain-language framing.",
                "life_load": "Moderate; daily life leaves limited room for unnecessary friction.",
                "fragmentation_reality": "Some holdings and information live across more than one place.",
                "guidance_preference": "Hybrid self-serve plus optional expert clarification.",
                "reflection_style": "Explains decisions through recent examples and trade-offs.",
            }
        profile["relational_defense_model"] = {
            "self_other_position": "self_protective_other_guarded",
            "default_trust_posture": "guarded_until_proven_safe",
            "defensive_style": "question_then_withhold",
            "status_sensitivity": "medium_high",
            "attribution_style": "assumes_optimistic_claims_hide_cost",
            "conflict_pattern": "polite_pushback_then_detach",
            "withdrawal_pattern": "shorter_answers_when_not_convinced",
        }
        profile["communication_behavior_model"] = {
            "baseline_answer_length": "short_to_medium",
            "clarification_tendency": "high_when_abstract",
            "misunderstanding_risk": "high_when_concept_dense",
            "topic_drift_tendency": "medium_via_life_examples",
            "memory_lapse_tendency": "medium",
            "revision_tendency": "medium",
            "disinterest_expression_style": "polite_but_direct",
            "permission_sensitivity": "high",
            "pricing_confusion_risk": "medium",
            "dropoff_style": "says_probably_wont_bother_without_a_fast_first_win",
        }
        if "banking_context" in contract.get("profile_sections", []):
            profile["banking_context"] = {
                "bank_relationship": "Uses one main Hong Kong retail bank app.",
                "investment_experience": "Early-stage but active enough to compare options.",
                "investment_products_held": "ETF, fund, and a few direct stocks.",
                "investable_assets_band": "HKD 500k-1m",
                "monthly_income_band": "Mid-career salary earner.",
                "primary_financial_goal": "Grow wealth while understanding downside better.",
                "current_investment_decision_process": "Self-research first, then checks bank views.",
                "relationship_manager_usage": "Occasional RM contact.",
                "digital_banking_usage": "High mobile app usage.",
                "trust_in_bank": "Moderate and conditional.",
                "trust_in_blackrock_or_institutional_brand": "Moderately positive but still checks incentives.",
                "risk_understanding_level": "Can follow basic portfolio risk explanations.",
                "portfolio_complexity": "Moderate multi-asset portfolio.",
                "external_asset_fragmentation": "Some holdings sit outside the bank.",
                "data_sharing_comfort": "Conditional on clear limits and value.",
                "advisory_preference": "Hybrid self-serve plus optional RM explanation.",
                "fee_sensitivity": "Will pay only if the insight feels materially better.",
                "past_bad_investment_experience": "Has one past regret from following momentum too late.",
                "suitability_sensitivity": "Wants recommendations to match stated risk appetite.",
            }
        profile.pop("audit_evidence_layer", None)
        profile.pop("generation_status", None)
        profile.pop("extensions", None)
        profile.pop("consistency_exceptions", None)
        concept_outputs = {}
        if contract.get("concept_outputs", {}).get("mode") == "required_when_declared":
            concept_outputs["portfolio_health_check"] = {
                "first_reaction": "Interesting if it helps me see the whole picture, not just more sales prompts.",
                "strongest_appeal": "Whole-portfolio scenario visibility.",
                "biggest_concern": "Whether the bank will use it to push products.",
                "what_they_understand": "It looks like a risk interpretation tool, not auto-trading.",
                "what_they_misunderstand": "Unclear how much of the model is truly independent from product incentives.",
                "data_they_would_share": "Bank-held positions and selected outside holdings.",
                "data_they_would_not_share": "Anything that feels unrelated to risk analysis.",
                "preferred_explanation_format": "Plain-language summary with one or two charts.",
                "whether_rm_needed": "RM optional but useful for larger reallocations.",
                "whether_they_would_pay": "Maybe for premium review depth, not for a basic dashboard.",
                "what_would_make_them_try": "A clear sample report and optional external holding sync.",
                "what_would_make_them_abandon": "If the feature turns into product pushing or noisy warnings.",
            }
        return V5SynthesisResult(
            profile=profile,
            decision_policy=persona.decision_policy,
            response_style=persona.response_style,
            narrative=persona.narrative,
            generation_rationale="One-pass fixture generation.",
            quality_self_review={
                "strengths": ["Grounded ordinary scenes"],
                "weaknesses": ["Local detail needs human review"],
                "uncertainties": ["Some spending details are inferred"],
                "human_review_priorities": ["Review local realism"],
            },
            concept_outputs=concept_outputs,
            provider="fixture",
            model="fixture-v5",
            metadata={
                "transport": "fixture",
                "transport_metadata": {"usage": {"input_tokens": 1000, "output_tokens": 2000, "total_tokens": 3000, "source": "fixture"}},
            },
        )


class ObjectBuyingLogicV5Adapter(FixtureV5Adapter):
    def synthesize(self, request):
        result = super().synthesize(request)
        result.profile["product_reaction_rules"]["difference_between_curiosity_and_purchase"] = {
            "curiosity": "Interest starts when the problem feels real enough to bookmark.",
            "trial": "Trial starts when setup looks reversible and small.",
            "purchase": "Payment starts when the product removes enough uncertainty to act now.",
        }
        return result


class FailingV5Adapter:
    def synthesize(self, request):
        raise AssertionError("resume_response should not call synthesize")


class PersonaV5Test(unittest.TestCase):
    def test_output_schema_is_single_complete_response(self) -> None:
        schema = build_v5_output_schema()
        self.assertEqual(
            schema["required"],
            ["profile", "decision_policy", "response_style", "narrative", "generation_rationale", "quality_self_review"],
        )

    def test_missing_profile_section_is_rejected_without_repair_plan(self) -> None:
        result = FixtureV5Adapter().synthesize(type("Request", (), {"random_seed": 9})())
        result.profile.pop("persona_voiceprint")
        findings = validate_v5_result(result, "su_1001")
        self.assertIn("profile_section_type:persona_voiceprint:object", findings)

    def test_flexible_profile_sections_accept_non_object_payloads(self) -> None:
        result = FixtureV5Adapter().synthesize(type("Request", (), {"random_seed": 9, "contract": lambda self: {}})())
        result.profile["daily_micro_behaviours"] = "Checks finance apps in short bursts."
        result.profile["identity_symbols"] = ["Uses one main bank app as the default money home."]
        result.profile["sensitive_scenario_salience"] = ["privacy_and_data", "financial_vulnerability"]
        findings = validate_v5_result(result, "su_1001")
        self.assertNotIn("profile_section_type:daily_micro_behaviours:object", findings)
        self.assertNotIn("profile_section_type:identity_symbols:object", findings)
        self.assertNotIn("profile_section_type:sensitive_scenario_salience:object", findings)

    def test_normalize_wraps_domain_fit_and_sensitive_scenario_strings(self) -> None:
        result = FixtureV5Adapter().synthesize(type("Request", (), {"random_seed": 9, "contract": lambda self: {}})())
        result.profile["domain_fit"] = "Strong fit for the target panel."
        result.profile["sensitive_scenario_reactions"] = {
            "identity_disclosure": "Prefers minimal identity disclosure.",
            "privacy_and_data": "Wants read-only sharing.",
        }
        changes = normalize_v5_result_structure(result)
        self.assertIn("wrapped_string_as_object:domain_fit", changes)
        self.assertEqual(result.profile["domain_fit"]["summary"], "Strong fit for the target panel.")
        self.assertEqual(result.profile["sensitive_scenario_reactions"]["identity_disclosure"]["reaction"], "Prefers minimal identity disclosure.")

    def test_normalize_flattens_buying_behavior_object_to_text(self) -> None:
        result = FixtureV5Adapter().synthesize(type("Request", (), {"random_seed": 9, "contract": lambda self: {}})())
        result.profile["behavior_profile"]["buying_behavior"] = {
            "research_pattern": "Checks reviews first.",
            "trial_pattern": "Starts small.",
        }
        changes = normalize_v5_result_structure(result)
        self.assertIn("flattened_container_as_text:behavior_profile.buying_behavior", changes)
        self.assertIsInstance(result.profile["behavior_profile"]["buying_behavior"], str)
        self.assertIn("research pattern: Checks reviews first.", result.profile["behavior_profile"]["buying_behavior"])

    def test_generation_writes_trace_usage_and_guided_brief(self) -> None:
        adapter = FixtureV5Adapter()
        guide = {"mode": "guided", "fixed": {"location": "Kuala Lumpur"}, "preferred": {"interests": ["urban gardening"]}}
        with tempfile.TemporaryDirectory() as tmp:
            target = generate_v5_persona(
                persona_id="su_1001",
                output_dir=Path(tmp),
                adapter=adapter,
                guide=guide,
                random_seed=1001,
            )
            report = validate_v5_persona_folder(target)
            self.assertTrue(report["valid"], report)
            self.assertEqual(read_json(target / "generation_notes.json")["generator_version"], GENERATOR_VERSION)
            self.assertEqual(read_json(target / "audit.json")["skill_version"], "v5.1")
            schema_payload = read_json(target / "persona_schema_v5_1.json")
            self.assertEqual(schema_payload["schema_version"], "v5.1")
            self.assertIn("behavior_generation_rules", schema_payload["optional_profile_fields"])
            self.assertEqual(read_json(target / "generation_notes.json")["token_usage"]["total_tokens"], 3000)
            self.assertEqual(read_json(target / "generation_brief.json")["fixed"]["location"], "Kuala Lumpur")
            self.assertTrue((target / "generation.log.jsonl").read_text(encoding="utf-8").strip())
            self.assertEqual(adapter.requests[0].guide, guide)

    def test_generation_handles_object_buying_logic_when_building_duplicate_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            generate_v5_persona(
                persona_id="su_1001",
                output_dir=base,
                adapter=FixtureV5Adapter(),
                random_seed=1001,
            )
            target = generate_v5_persona(
                persona_id="su_1002",
                output_dir=base,
                adapter=ObjectBuyingLogicV5Adapter(),
                random_seed=1002,
            )
            report = validate_v5_persona_folder(target)
            self.assertTrue(report["valid"], report)
            duplicate_report = read_json(target / "duplicate_report.json")
            self.assertEqual(duplicate_report["synthetic_user_id"], "su_1002")
            self.assertTrue(duplicate_report["compared_against"])

    def test_generation_writes_concept_sidecar_and_guided_sections_when_guide_requires_them(self) -> None:
        guide = {
            "mode": "guided",
            "required_profile_sections": ["human_difference_axes", "banking_context"],
            "concept_output_contracts": {
                "portfolio_health_check": {
                    "required_fields": [
                        "first_reaction",
                        "strongest_appeal",
                        "biggest_concern",
                        "what_they_understand",
                        "what_they_misunderstand",
                        "data_they_would_share",
                        "data_they_would_not_share",
                        "preferred_explanation_format",
                        "whether_rm_needed",
                        "whether_they_would_pay",
                        "what_would_make_them_try",
                        "what_would_make_them_abandon",
                    ]
                }
            },
            "fixed": {"location": "Hong Kong"},
            "preferred": {"persona_focus": "Portfolio Health Check test"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            target = generate_v5_persona(
                persona_id="su_1003",
                output_dir=Path(tmp),
                adapter=FixtureV5Adapter(),
                guide=guide,
                random_seed=1003,
            )
            report = validate_v5_persona_folder(target)
            self.assertTrue(report["valid"], report)
            profile = read_json(target / "profile.json")
            self.assertIn("human_difference_axes", profile)
            self.assertIn("banking_context", profile)
            self.assertIn("relational_defense_model", profile)
            self.assertIn("communication_behavior_model", profile)
            self.assertIn("persona_schema_meta", profile)
            self.assertIn("behavior_generation_rules", profile)
            concept_outputs = read_json(target / "concept_outputs.json")
            self.assertIn("portfolio_health_check", concept_outputs)

    def test_result_to_persona_canonicalizes_v5_1_behavior_blocks(self) -> None:
        result = FixtureV5Adapter().synthesize(type("Request", (), {"random_seed": 9, "contract": lambda self: {}})())
        result.profile.pop("relational_defense_model", None)
        result.profile.pop("communication_behavior_model", None)
        persona = result_to_persona(result, "su_1004")
        self.assertEqual(persona.skill_version, "v5.1")
        self.assertTrue(persona.profile.relational_defense_model)
        self.assertTrue(persona.profile.communication_behavior_model)
        self.assertTrue(persona.profile.behavior_generation_rules)
        self.assertEqual(persona.profile.persona_schema_meta["schema_version"], "v5.1")

    def test_upgrade_profile_payload_to_v5_1_maps_legacy_v5_behavior_blocks(self) -> None:
        legacy_result = FixtureV5Adapter().synthesize(type("Request", (), {"random_seed": 9, "contract": lambda self: {}})())
        legacy_result.profile.pop("relational_defense_model", None)
        legacy_result.profile.pop("communication_behavior_model", None)
        legacy_result.profile.pop("behavior_generation_rules", None)
        upgraded, applied = upgrade_profile_payload_to_v5_1(legacy_result.profile, source_version="v5")
        self.assertTrue(upgraded["relational_defense_model"])
        self.assertTrue(upgraded["communication_behavior_model"])
        self.assertTrue(upgraded["behavior_generation_rules"])
        self.assertEqual(upgraded["persona_schema_meta"]["schema_version"], "v5.1")
        self.assertEqual(upgraded["persona_schema_meta"]["source_version"], "v5")
        self.assertEqual(upgraded["persona_schema_meta"]["upgrade_strategy"], "fallback_from_v5")
        self.assertTrue(any("v5_fallback_derivation" in step for step in applied))

    def test_resume_response_preserves_existing_guided_brief(self) -> None:
        guide = {"mode": "guided", "fixed": {"location": "Hong Kong urban districts"}, "preferred": {"persona_role": "spontaneous_free_time_explorer"}}
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            target = generate_v5_persona(
                persona_id="su_1001",
                output_dir=base,
                adapter=FixtureV5Adapter(),
                guide=guide,
                random_seed=1001,
            )
            resumed_target = generate_v5_persona(
                persona_id="su_1001",
                output_dir=base,
                adapter=FailingV5Adapter(),
                resume_response=True,
                random_seed=1001,
            )
            self.assertEqual(target, resumed_target)
            self.assertEqual(read_json(target / "generation_notes.json")["guide_mode"], "guided")
            self.assertEqual(read_json(target / "generation_notes.json")["random_seed"], 1001)
            self.assertEqual(read_json(target / "generation_brief.json")["fixed"]["location"], "Hong Kong urban districts")

    def test_cli_exposes_v5_validation(self) -> None:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["validate-personas-v5", "--data-dir", str(ROOT / "does-not-exist")])
        self.assertEqual(code, 1)
        self.assertIn("No V5 personas found", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
