import tempfile
import unittest
import io
import json
from contextlib import redirect_stderr
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.cli.main import _build_parser
from ai_validation_swarm.conversation.providers import ChatResult
from ai_validation_swarm.facilitator.learning import (
    disable_facilitator_learning_rules,
    promote_facilitator_learning_rules,
)
from ai_validation_swarm.facilitator.models import FacilitatorDecision
from ai_validation_swarm.facilitator.models import InterviewExchange, InterviewSession
from ai_validation_swarm.facilitator.providers import OpenAIFacilitatorProvider, validate_hypothesis_assessment
from ai_validation_swarm.facilitator.runtime import FacilitatedInterviewRuntime
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.providers.openai_client import OpenAIProviderConfig
from ai_validation_swarm.storage.files import read_json, save_persona


class RecordedLLMFacilitator:
    provider_name = "recorded-llm"
    model_name = "recorded-facilitator/v1"

    def __init__(self):
        self.calls = []
        self.decisions = [
            FacilitatorDecision(
                interview_phase="recent_event",
                probing_strategy="critical_incident",
                decision_rationale="A concrete recent event is needed before causal probing.",
                message_to_persona="Tell me about the last trip you had to reorganize after plans changed.",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What changed?"],
                should_end=False,
                end_reason="",
                provider_session_id="facilitator-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="root_cause",
                probing_strategy="adaptive_five_whys",
                decision_rationale="The workaround is clear, but its practical consequence is not.",
                message_to_persona="What made rechecking every booking costly in that particular situation?",
                evidence_updates=[{
                    "claim": "The participant manually rechecked bookings after a schedule change.",
                    "evidence_type": "behavioural_example",
                    "transcript_refs": ["exchange_1.persona"],
                    "confidence": "high",
                }],
                root_cause_hypotheses=[{
                    "hypothesis": "Fragmented booking ownership may create the rechecking burden.",
                    "supporting_evidence_refs": ["exchange_1.persona"],
                    "alternative_explanations": ["The disruption may have been unusually complex."],
                    "validation_gap": "Need a counterexample from a trip that changed smoothly.",
                    "confidence": "low",
                }],
                open_questions=["When does replanning work well?"],
                should_end=False,
                end_reason="",
                provider_session_id="facilitator-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="closure",
                probing_strategy="evidence_sufficiency",
                decision_rationale="The remaining causal claims require comparison with real participants.",
                message_to_persona="",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["Does this recur across real travellers?"],
                should_end=True,
                end_reason="Further probing would create synthetic precision.",
                provider_session_id="facilitator-thread-1",
            ),
        ]

    def next_turn(self, **kwargs):
        self.calls.append(("next_turn", kwargs))
        return self.decisions.pop(0)

    def synthesize(self, **kwargs):
        self.calls.append(("synthesize", kwargs))
        return ({
            "executive_summary": "Schedule changes create a manual verification burden.",
            "insights": [{
                "insight": "The burden is confidence restoration, not itinerary creation alone.",
                "evidence_refs": ["exchange_1.persona", "exchange_2.persona"],
                "confidence": "medium",
                "implication": "Test change recovery rather than only initial planning.",
            }],
            "needs": ["Regain confidence after a change without checking every booking."],
            "root_cause_hypotheses": [{
                "hypothesis": "Fragmented booking ownership may create the rechecking burden.",
                "supporting_evidence_refs": ["exchange_1.persona"],
                "alternative_explanations": ["The disruption may have been unusually complex."],
                "validation_gap": "Compare with real travellers and smooth-change cases.",
                "confidence": "low",
            }],
            "contradictions": ["Wants automation but still manually verifies changes."],
            "pov_statements": ["A traveller facing changes needs a way to restore confidence because bookings are checked separately."],
            "how_might_we_questions": ["How might we help travellers regain confidence after plans change?"],
            "hypothesis_assessment": {
                "hypothesis": "",
                "verdict": "not_tested",
                "supporting_evidence_refs": [],
                "contradicting_evidence_refs": [],
                "mechanism_test_basis": "not_tested",
                "condition_present_case_refs": [],
                "condition_absent_case_refs": [],
                "alternative_explanations": [],
                "alternative_tests": [],
                "evidence_gaps": ["No explicit hypothesis was supplied."],
                "confidence": "low",
            },
            "evidence_gaps": ["No real-human evidence."],
            "recommended_human_validation": ["Interview travellers after a recent disrupted trip."],
            "synthetic_only_disclaimer": "Synthetic-user interview for AI pre-validation only; not human market evidence.",
        }, "facilitator-thread-1")

    def judge_hypothesis_evidence(self, **kwargs):
        self.calls.append(("judge_hypothesis_evidence", kwargs))
        return ({
            "hypothesis": "Travellers recheck because ownership of updates is unclear.",
            "operational_condition_present": "A specific affected update has no known owner.",
            "operational_condition_absent": "Every affected update has a known owner.",
            "target_behaviour_observed": True,
            "target_behaviour_refs": ["exchange_1.persona"],
            "condition_present": {"status": "not_observed", "evidence_refs": [], "rationale": "No exact case."},
            "condition_absent": {"status": "observed", "evidence_refs": ["exchange_1.persona"], "rationale": "An owner was known."},
            "supporting_evidence_refs": [],
            "contradicting_evidence_refs": ["exchange_1.persona"],
            "recommended_verdict": "not_tested",
            "confidence": "low",
            "warnings": ["The exact condition-present case is missing."],
        }, "judge-thread-1")

    def synthesize_concept(self, **kwargs):
        self.calls.append(("synthesize_concept", kwargs))
        return ({
            "problem_evidence": {
                "strength": "medium",
                "supporting_quotes": [{"quote": "I checked every booking again.", "evidence_ref": "exchange_1.persona"}],
                "recent_behavior_evidence": ["Rechecked bookings after a change."],
            },
            "current_workaround": {
                "existing_workaround": ["Chat notes"], "pain_level": "medium",
                "switching_difficulty": "high", "what_must_not_change": ["Keep chat as source of truth"],
            },
            "trust_boundary": {
                "accepted_data_access": ["Selected chat"], "rejected_data_access": ["All messages"],
                "required_trust_explanation": ["Deletion and no training"],
            },
            "first_value_requirement": {
                "first_use_success": ["One real missed follow-up"], "time_to_value": "First week",
                "abandonment_triggers": ["Wrong private-data inference"],
            },
            "pricing_signal": {
                "free_trial_need": "Required", "monthly_comfort_range": "Unknown",
                "payment_justification": ["Avoided customer miss"], "evidence_strength": "hypothetical",
            },
            "retention_risk": {
                "continuation_reasons": ["Replaces manual review"], "drop_off_reasons": ["Duplicate list"],
                "workflow_effect": "unclear",
            },
            "assumption_validation": [{
                "assumption": "The participant has a recurring follow-up problem.", "status": "partially_supported",
                "evidence_refs": ["exchange_1.persona"], "rationale": "One event only.",
            }],
            "key_insights": [
                "Because checking is manual, this persona would test a selected-chat scan, unless access is broad. This means the product should start narrow.",
                "Because privacy is uncertain, this persona would reject broad connection, unless deletion is clear. This means the product should explain retention.",
                "Because duplicate tracking adds work, this persona would churn, unless one old step disappears. This means the product should replace review.",
            ],
            "next_experiment": "Run a selected-chat concierge test with five real participants.",
            "evidence_gaps": ["No payment behavior."],
            "synthetic_only_disclaimer": "Synthetic pre-validation only.",
        }, "facilitator-thread-1")


class RecordedLLMPersona:
    provider_name = "recorded-llm"
    model_name = "recorded-persona/v1"

    def __init__(self):
        self.responses = [
            "Last month a school stop moved, so I reopened each booking and kept notes in chat.",
            "The cost was not the clicks. I could not tell whether my partner had seen the latest version.",
        ]

    def respond(self, **kwargs):
        return ChatResult(
            reply=self.responses.pop(0),
            intent_level="unclear",
            confidence="high",
            provider_session_id="persona-thread-1",
        )

    def generate_persona_driver_trace(self, **kwargs):
        return type("TraceResult", (), {
            "payload": {
                "synthetic_only_disclaimer": "Synthetic persona post-interview reflection only; not human market evidence.",
                "surface_read": {
                    "what_the_persona_explicitly_said": [
                        "They reopened bookings and kept notes in chat.",
                    ],
                    "what_they_seemed_to_optimize_for": "Restoring confidence after a disruption.",
                    "what_stayed_implicit": [
                        "How much prior coordination friction shaped this reaction.",
                    ],
                },
                "likely_drivers": [
                    {
                        "driver": "Need to regain certainty before moving on",
                        "driver_type": "decision_style",
                        "why_it_matters_here": "The persona answered through verification behaviour rather than abstract preference.",
                        "evidence_refs": ["exchange_1.persona", "exchange_2.persona"],
                        "profile_source_refs": ["behavior_profile", "values.core_values"],
                        "confidence": "medium",
                        "observed_vs_inferred": "mixed",
                    }
                ],
                "unspoken_constraints": [
                    {
                        "constraint": "Shared planning feels fragile when responsibility is ambiguous.",
                        "why_likely": "The second answer points to uncertainty about whether the partner had seen the latest plan.",
                        "evidence_refs": ["exchange_2.persona"],
                        "profile_source_refs": ["contradiction_map"],
                        "confidence": "medium",
                    }
                ],
                "value_tensions": [
                    {
                        "tension": "Automation versus manual reassurance",
                        "side_a": "Wants less checking work",
                        "side_b": "Still manually verifies after change",
                        "evidence_refs": ["exchange_1.persona", "exchange_2.persona"],
                        "profile_source_refs": ["values.core_values"],
                        "confidence": "medium",
                    }
                ],
                "missed_follow_up_questions": [
                    {
                        "question": "What made you trust chat notes more than the shared plan in that moment?",
                        "why_this_would_clarify": "It would expose whether the deeper issue was coordination trust or tool reliability.",
                        "priority": "high",
                    }
                ],
            },
            "provider_session_id": "persona-trace-thread-1",
        })()


class ConceptGateFacilitator:
    provider_name = "concept-gate"
    model_name = "concept-gate/v1"

    def __init__(self, revised_decision: FacilitatorDecision):
        self.calls = []
        self.revised_decision = revised_decision

    def next_turn(self, **kwargs):
        self.calls.append(kwargs)
        return self.revised_decision


class FacilitatorRuntimeTest(unittest.TestCase):
    def test_facilitator_skill_and_versioned_prompts_are_complete(self):
        skill = (ROOT / "skills" / "design-research-facilitator" / "SKILL.md").read_text(encoding="utf-8")
        interview_prompt = (SRC / "ai_validation_swarm" / "prompts" / "facilitator-interview" / "v2.md")
        synthesis_prompt = (SRC / "ai_validation_swarm" / "prompts" / "facilitator-synthesis" / "v2.md")
        self.assertIn("name: design-research-facilitator", skill)
        self.assertIn("Use Five Whys adaptively", skill)
        self.assertNotIn("TODO", skill)
        self.assertTrue(interview_prompt.exists())
        self.assertTrue(synthesis_prompt.exists())
        interview_rules = interview_prompt.read_text(encoding="utf-8")
        synthesis_rules = synthesis_prompt.read_text(encoding="utf-8")
        self.assertIn("Do not offer an either-or classification", interview_rules)
        self.assertIn("explicitly describes doing it", interview_rules)
        self.assertIn("focused on one remembered action, decision, or consequence", interview_rules)
        self.assertIn("evidence inconsistent with it", interview_rules)
        self.assertIn("test the supplied mechanism before strengthening a competing cause", interview_rules)
        self.assertIn("Preserve participant heterogeneity", interview_rules)
        self.assertIn("Do not make overlap, concentration, stress testing, or any other named capability become mandatory pain points", interview_rules)
        self.assertIn("ties a named analytic output to a concrete decision or non-decision", interview_rules)
        self.assertIn("output_to_decision_probe", interview_rules)
        self.assertIn("leave `root_cause_hypotheses`, `needs`, `pov_statements`, and `how_might_we_questions` empty", synthesis_rules)
        self.assertIn("provisionally_supported", synthesis_rules)
        self.assertIn("Absence of supporting evidence is not contradicting evidence", synthesis_rules)
        self.assertIn("alternative_tests", synthesis_rules)
        self.assertIn("Never ask the participant to choose", interview_rules)
        self.assertIn("open participant-led cause question", interview_rules)
        self.assertIn("A direct alternative test must isolate or change", interview_rules)
        self.assertIn("Evaluate the exact claim", synthesis_rules)
        self.assertTrue((ROOT / "skills" / "design-research-facilitator" / "agents" / "openai.yaml").exists())

    def test_llm_decisions_drive_questions_phases_and_synthesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=71)[0]
            save_persona(persona, root / "personas")
            facilitator = RecordedLLMFacilitator()
            observed = []
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=facilitator,
                persona_provider=RecordedLLMPersona(),
                observer=lambda role, message: observed.append((role, message)),
            )
            output = runtime.run(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Understand root causes of trip replanning friction.",
                product_context="A possible trip-planning platform.",
                max_turns=5,
            )

            session = read_json(output / "interview.json")
            self.assertEqual(session["status"], "completed")
            self.assertEqual(session["interview_mode"], "explore_root_cause")
            self.assertEqual(session["facilitator_prompt_version"], "facilitator-interview/v2")
            self.assertEqual(session["stop_reason"], "Further probing would create synthetic precision.")
            self.assertEqual(session["soft_turn_limit"], 5)
            self.assertEqual(session["hard_turn_limit"], 5)
            self.assertEqual(session["facilitator_provider_session_id"], "facilitator-thread-1")
            self.assertEqual(session["persona_provider_session_id"], "persona-thread-1")
            self.assertEqual(
                [item["decision_status"] for item in session["facilitator_decisions"]],
                ["asked", "asked", "ended_interview"],
            )
            self.assertEqual([item["facilitator_phase"] for item in session["exchanges"]], ["recent_event", "root_cause"])
            self.assertEqual(session["exchanges"][1]["probing_strategy"], "adaptive_five_whys")
            self.assertEqual(observed[0][1], "Tell me about the last trip you had to reorganize after plans changed.")
            self.assertTrue((output / "facilitator_trace.json").exists())
            self.assertTrue((output / "insight_report.json").exists())
            self.assertTrue((output / "persona_driver_trace.json").exists())
            self.assertTrue((output / "persona_driver_trace.md").exists())
            self.assertIn("Root-Cause Hypotheses", (output / "insights.md").read_text(encoding="utf-8"))
            driver_trace = read_json(output / "persona_driver_trace.json")
            self.assertEqual(driver_trace["likely_drivers"][0]["driver_type"], "decision_style")
            self.assertEqual(session["persona_driver_trace_provider_session_id"], "persona-trace-thread-1")
            self.assertEqual(session["persona_driver_trace_prompt_version"], "persona-driver-trace/v1")

            all_facilitator_inputs = "\n".join(str(call[1]) for call in facilitator.calls)
            self.assertNotIn("PERSONA RESEARCH KERNEL", all_facilitator_inputs)
            self.assertNotIn(persona.profile.basic_identity["name"], all_facilitator_inputs)
            self.assertIn("exchange_1.persona", all_facilitator_inputs)
            self.assertIn("INTERVIEW MODE", all_facilitator_inputs)
            self.assertIn("COVERAGE STATUS", all_facilitator_inputs)
            self.assertIn("DEPTH-FIRST STOP RULE", all_facilitator_inputs)

    def test_hypothesis_validation_requires_and_propagates_hypothesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=72)[0]
            save_persona(persona, root / "personas")
            provider = RecordedLLMFacilitator()
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=provider,
                persona_provider=RecordedLLMPersona(),
            )
            with self.assertRaisesRegex(ValueError, "requires a non-empty hypothesis"):
                runtime.run(
                    persona_id=persona.profile.synthetic_user_id,
                    research_goal="Test a cause.",
                    interview_mode="validate_hypothesis",
                )

            hypothesis = "Travellers recheck because ownership of updates is unclear."
            output = runtime.run(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Test why travellers recheck changed plans.",
                interview_mode="validate_hypothesis",
                hypothesis=hypothesis,
                max_turns=2,
            )
            session = read_json(output / "interview.json")
            self.assertEqual(session["interview_mode"], "validate_hypothesis")
            self.assertEqual(session["hypothesis"], hypothesis)
            self.assertEqual(session["hypothesis_evidence_judgment"]["recommended_verdict"], "not_tested")
            self.assertEqual(session["hypothesis_evidence_judge_provider_session_id"], "judge-thread-1")
            self.assertTrue((output / "hypothesis_evidence_judgment.json").exists())
            combined = "\n".join(str(call[1]) for call in provider.calls)
            self.assertIn(hypothesis, combined)
            synthesis_call = next(call for call in provider.calls if call[0] == "synthesize")
            self.assertIn("INDEPENDENT HYPOTHESIS EVIDENCE JUDGMENT", synthesis_call[1]["user_prompt"])

    def test_concept_validation_uses_concept_synthesis_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=73)[0]
            save_persona(persona, root / "personas")
            protocol_path = root / "go-out-la-v1.md"
            protocol_path.write_text(
                "# Test Go Out La Protocol\n\nAsk about activity discovery before concept reactions.\n",
                encoding="utf-8",
            )
            provider = RecordedLLMFacilitator()
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas", session_dir=root / "interviews",
                facilitator_provider=provider, persona_provider=RecordedLLMPersona(),
            )
            output = runtime.run(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Validate Go Out La!",
                interview_mode="concept_validation",
                product_context="Use the Go Out La protocol.",
                concept_protocol=str(protocol_path),
                concept_label="Go Out La!",
                output_language="Natural Cantonese Traditional Chinese",
                max_turns=2,
            )
            session = read_json(output / "interview.json")
            report = read_json(output / "insight_report.json")
            self.assertEqual(session["interview_mode"], "concept_validation")
            self.assertEqual(session["synthesis_prompt_version"], "concept-synthesis/v1")
            self.assertEqual(session["concept_label"], "Go Out La!")
            self.assertEqual(session["concept_protocol_version"], str(protocol_path))
            self.assertEqual(report["problem_evidence"]["strength"], "medium")
            self.assertTrue(any(call[0] == "synthesize_concept" for call in provider.calls))
            first_turn_prompt = provider.calls[0][1]["system_prompt"]
            first_turn_user_prompt = provider.calls[0][1]["user_prompt"]
            self.assertIn("Test Go Out La Protocol", first_turn_prompt)
            self.assertIn("Depth-First Interviewing", first_turn_prompt)
            self.assertIn("ties a named analytic output to a concrete decision or non-decision", first_turn_prompt)
            self.assertIn("named-output-to-concrete-decision mapping probe", first_turn_user_prompt)
            self.assertIn("Assumption Validation", (output / "insights.md").read_text(encoding="utf-8"))
            self.assertIn("# Go Out La! Interview:", (output / "insights.md").read_text(encoding="utf-8"))

    def test_concept_coverage_status_tracks_depth_probes_separately_from_topic_coverage(self):
        session = InterviewSession.from_dict({
            "interview_id": "concept-depth",
            "persona_id": "su_fixture",
            "persona_name": "Fixture",
            "research_goal": "Validate a concept.",
            "product_context": "A free health-check concept.",
            "output_language": "Traditional Chinese",
            "facilitator_provider": "fixture",
            "facilitator_model": "fixture",
            "persona_provider": "fixture",
            "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "concept-synthesis/v1",
            "interview_mode": "concept_validation",
            "soft_turn_limit": 4,
            "hard_turn_limit": 10,
            "exchanges": [
                {
                    "exchange_id": 1,
                    "facilitator_question": "Tell me about the last time you checked your portfolio.",
                    "persona_response": "I checked after a big expense was coming up.",
                    "facilitator_phase": "recent_event",
                    "probing_strategy": "recent_event",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 2,
                    "facilitator_question": "How do you piece it together now?",
                    "persona_response": "I use the bank app and a few notes.",
                    "facilitator_phase": "current_workaround",
                    "probing_strategy": "workflow_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 3,
                    "facilitator_question": "If the bank added a portfolio health check, what is your first reaction?",
                    "persona_response": "Sounds useful if it is easy.",
                    "facilitator_phase": "concept_reaction",
                    "probing_strategy": "concept_intro",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 4,
                    "facilitator_question": "What data would you be okay sharing?",
                    "persona_response": "Only what is needed for the portfolio.",
                    "facilitator_phase": "trust_boundary",
                    "probing_strategy": "trust_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 5,
                    "facilitator_question": "What would you do after seeing a warning?",
                    "persona_response": "I would check it first before doing anything.",
                    "facilitator_phase": "action_followthrough",
                    "probing_strategy": "action_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "consequence",
                },
                {
                    "exchange_id": 6,
                    "facilitator_question": "What would make you come back to it again?",
                    "persona_response": "If it stayed relevant.",
                    "facilitator_phase": "repeat_use_condition",
                    "probing_strategy": "retention_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 7,
                    "facilitator_question": "Where should this show up in the banking journey?",
                    "persona_response": "Probably in the app when I am already reviewing things.",
                    "facilitator_phase": "service_embedding",
                    "probing_strategy": "journey_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
            ],
        })

        FacilitatedInterviewRuntime._update_coverage_status(session)

        self.assertTrue(session.coverage_status["coverage_complete"])
        self.assertFalse(session.coverage_status["depth_complete"])
        self.assertEqual(
            session.coverage_status["depth_missing"],
            ["contrast_probe", "driver_deepening_probe", "output_to_decision_probe"],
        )

        session.exchanges.extend([
            InterviewExchange(
                exchange_id=8,
                facilitator_question="What exact explanation would be enough for you to trust the warning on first use?",
                persona_response="Show me why it changed and by how much.",
                facilitator_phase="trust_threshold",
                probing_strategy="threshold_probe",
                question_evidence_basis="hypothetical",
                question_evidence_target="context",
            ),
            InterviewExchange(
                exchange_id=9,
                facilitator_question="If it only showed your in-bank holdings, when would it still be useful and when would it not be worth using?",
                persona_response="Useful for a quick check, but not for a full review.",
                facilitator_phase="non_use_contrast",
                probing_strategy="contrast_probe",
                question_evidence_basis="hypothetical",
                question_evidence_target="alternative_condition",
            ),
            InterviewExchange(
                exchange_id=10,
                facilitator_question="What does each of your current tools help you avoid missing?",
                persona_response="The notes remind me why I bought something and the app shows the balance.",
                facilitator_phase="workaround_function",
                probing_strategy="workaround_function_probe",
                question_evidence_basis="current_event",
                question_evidence_target="participant_cause",
            ),
            InterviewExchange(
                exchange_id=11,
                facilitator_question="If a concentration alert showed 42% of your portfolio was in one sector, what would you actually do at that point, or would you still leave it unchanged?",
                persona_response="I would compare it with my original plan first, and if it drifted too far I would trim it.",
                facilitator_phase="output_decision_mapping",
                probing_strategy="output_to_decision_probe",
                question_evidence_basis="hypothetical",
                question_evidence_target="consequence",
            ),
        ])

        FacilitatedInterviewRuntime._update_coverage_status(session)

        self.assertTrue(session.coverage_status["depth_complete"])
        self.assertEqual(session.coverage_status["depth_missing"], [])

    def test_concept_validation_does_not_finalize_at_soft_limit_until_depth_is_complete(self):
        session = InterviewSession.from_dict({
            "interview_id": "concept-stop-gate",
            "persona_id": "su_fixture",
            "persona_name": "Fixture",
            "research_goal": "Validate a concept.",
            "product_context": "A free health-check concept.",
            "output_language": "Traditional Chinese",
            "facilitator_provider": "fixture",
            "facilitator_model": "fixture",
            "persona_provider": "fixture",
            "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "concept-synthesis/v1",
            "interview_mode": "concept_validation",
            "soft_turn_limit": 4,
            "hard_turn_limit": 12,
            "exchanges": [
                {
                    "exchange_id": 1,
                    "facilitator_question": "Tell me about the last time you checked your portfolio.",
                    "persona_response": "I checked before some bills were due.",
                    "facilitator_phase": "recent_event",
                    "probing_strategy": "recent_event",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 2,
                    "facilitator_question": "How do you piece it together now?",
                    "persona_response": "I use the app and notes.",
                    "facilitator_phase": "current_workaround",
                    "probing_strategy": "workflow_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 3,
                    "facilitator_question": "If the bank added a portfolio health check, what is your first reaction?",
                    "persona_response": "Could be useful.",
                    "facilitator_phase": "concept_reaction",
                    "probing_strategy": "concept_intro",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 4,
                    "facilitator_question": "What data would you be okay sharing?",
                    "persona_response": "Only portfolio-related data.",
                    "facilitator_phase": "trust_boundary",
                    "probing_strategy": "trust_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 5,
                    "facilitator_question": "What would you do after seeing a warning?",
                    "persona_response": "I would verify it first.",
                    "facilitator_phase": "action_followthrough",
                    "probing_strategy": "action_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "consequence",
                },
                {
                    "exchange_id": 6,
                    "facilitator_question": "What would make you come back to it again?",
                    "persona_response": "If it stayed useful.",
                    "facilitator_phase": "repeat_use_condition",
                    "probing_strategy": "retention_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 7,
                    "facilitator_question": "Where should this show up in the banking journey?",
                    "persona_response": "Inside the app when I am already checking.",
                    "facilitator_phase": "service_embedding",
                    "probing_strategy": "journey_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
            ],
        })

        self.assertFalse(FacilitatedInterviewRuntime._should_finalize_after_exchange(session))
        self.assertTrue(session.coverage_status["coverage_complete"])
        self.assertFalse(session.coverage_status["depth_complete"])
        self.assertEqual(session.stop_reason, "")
        self.assertEqual(
            session.coverage_status["depth_missing"],
            ["contrast_probe", "driver_deepening_probe", "output_to_decision_probe"],
        )

        session.exchanges.extend([
            InterviewExchange(
                exchange_id=8,
                facilitator_question="What exact explanation would be enough for you to trust the warning on first use?",
                persona_response="A simple reason and a number.",
                facilitator_phase="trust_threshold",
                probing_strategy="threshold_probe",
                question_evidence_basis="hypothetical",
                question_evidence_target="context",
            ),
            InterviewExchange(
                exchange_id=9,
                facilitator_question="If it only showed part of your holdings, when would it still be useful and when would it not?",
                persona_response="Only for a quick check.",
                facilitator_phase="non_use_contrast",
                probing_strategy="contrast_probe",
                question_evidence_basis="hypothetical",
                question_evidence_target="alternative_condition",
            ),
            InterviewExchange(
                exchange_id=10,
                facilitator_question="What does each of your current tools help you avoid missing?",
                persona_response="Each one covers a different blind spot.",
                facilitator_phase="workaround_function",
                probing_strategy="workaround_function_probe",
                question_evidence_basis="current_event",
                question_evidence_target="participant_cause",
            ),
            InterviewExchange(
                exchange_id=11,
                facilitator_question="If a risk-profile mismatch alert said this portfolio now looks more aggressive than what you intended, what would you actually do next, or would you still keep it as it is?",
                persona_response="I would review the biggest positions first, and if it was only market noise I would leave it alone.",
                facilitator_phase="output_decision_mapping",
                probing_strategy="output_to_decision_probe",
                question_evidence_basis="hypothetical",
                question_evidence_target="consequence",
            ),
        ])

        self.assertTrue(FacilitatedInterviewRuntime._should_finalize_after_exchange(session))
        self.assertTrue(session.coverage_status["depth_complete"])
        self.assertEqual(session.stop_reason, "soft_turn_limit_with_required_coverage_met")

    def test_concept_validation_tracks_concept_intro_prerequisites(self):
        session = InterviewSession.from_dict({
            "interview_id": "concept-prereqs",
            "persona_id": "su_fixture",
            "persona_name": "Fixture",
            "research_goal": "Validate a concept.",
            "product_context": "A workflow concept.",
            "output_language": "Traditional Chinese",
            "facilitator_provider": "fixture",
            "facilitator_model": "fixture",
            "persona_provider": "fixture",
            "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "concept-synthesis/v1",
            "interview_mode": "concept_validation",
            "soft_turn_limit": 6,
            "hard_turn_limit": 10,
            "exchanges": [
                {
                    "exchange_id": 1,
                    "facilitator_question": "Tell me about the last time you had to reprioritize onboarding.",
                    "persona_response": "We changed it after a rough trial.",
                    "facilitator_phase": "recent_event",
                    "probing_strategy": "recent_event",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 2,
                    "facilitator_question": "How do you piece that decision together now?",
                    "persona_response": "I use notes and analytics.",
                    "facilitator_phase": "current_workaround",
                    "probing_strategy": "workflow_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
            ],
        })

        FacilitatedInterviewRuntime._update_coverage_status(session)

        self.assertFalse(session.coverage_status["concept_intro_allowed"])
        self.assertEqual(
            session.coverage_status["concept_intro_prerequisites"]["missing"],
            ["missing_evidence", "pressure", "defensible_vs_uncertain", "decision_change"],
        )

        session.exchanges.extend([
            InterviewExchange(
                exchange_id=3,
                facilitator_question="What evidence was still missing when you made that call?",
                persona_response="We still lacked a few direct user examples.",
                facilitator_phase="missing_evidence_probe",
                probing_strategy="missing_evidence_probe",
                question_evidence_basis="current_event",
                question_evidence_target="context",
            ),
            InterviewExchange(
                exchange_id=4,
                facilitator_question="What stakeholder or time pressure made waiting costly there?",
                persona_response="Sales wanted a decision that week.",
                facilitator_phase="pressure_probe",
                probing_strategy="pressure_probe",
                question_evidence_basis="current_event",
                question_evidence_target="context",
            ),
            InterviewExchange(
                exchange_id=5,
                facilitator_question="What could you defend publicly in that decision, and what still felt shaky privately?",
                persona_response="I could defend the change, but I was still unsure about the exact reason.",
                facilitator_phase="defensibility_probe",
                probing_strategy="defensibility_probe",
                question_evidence_basis="current_event",
                question_evidence_target="participant_cause",
            ),
            InterviewExchange(
                exchange_id=6,
                facilitator_question="What did you actually change in scope or priority at the end?",
                persona_response="We delayed profile questions and shipped the simpler path first.",
                facilitator_phase="decision_outcome_probe",
                probing_strategy="decision_outcome_probe",
                question_evidence_basis="current_event",
                question_evidence_target="consequence",
            ),
        ])

        FacilitatedInterviewRuntime._update_coverage_status(session)

        self.assertTrue(session.coverage_status["concept_intro_allowed"])
        self.assertEqual(session.coverage_status["concept_intro_prerequisites"]["missing"], [])

    def test_concept_validation_rejects_concept_intro_before_prerequisites_are_met(self):
        revised_decision = FacilitatorDecision(
            interview_phase="missing_evidence_probe",
            probing_strategy="missing_evidence_probe",
            decision_rationale="Need the missing current-state evidence before concept exposure.",
            message_to_persona="What evidence was still missing when you made that call?",
            evidence_updates=[],
            root_cause_hypotheses=[],
            open_questions=[],
            should_end=False,
            end_reason="",
        )
        provider = ConceptGateFacilitator(revised_decision)
        runtime = FacilitatedInterviewRuntime(
            data_dir=ROOT / "data" / "personas",
            session_dir=ROOT / "interviews",
            facilitator_provider=provider,
            persona_provider=RecordedLLMPersona(),
        )
        session = InterviewSession.from_dict({
            "interview_id": "concept-gate-session",
            "persona_id": "su_fixture",
            "persona_name": "Fixture",
            "research_goal": "Validate a concept.",
            "product_context": "A workflow concept.",
            "output_language": "Traditional Chinese",
            "facilitator_provider": "fixture",
            "facilitator_model": "fixture",
            "persona_provider": "fixture",
            "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "concept-synthesis/v1",
            "interview_mode": "concept_validation",
            "soft_turn_limit": 6,
            "hard_turn_limit": 10,
            "exchanges": [
                {
                    "exchange_id": 1,
                    "facilitator_question": "Tell me about the last time you reprioritized onboarding.",
                    "persona_response": "We changed it after a rough trial.",
                    "facilitator_phase": "recent_event",
                    "probing_strategy": "recent_event",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 2,
                    "facilitator_question": "How do you piece that decision together now?",
                    "persona_response": "I use notes and analytics.",
                    "facilitator_phase": "current_workaround",
                    "probing_strategy": "workflow_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
            ],
        })
        decision = FacilitatorDecision(
            interview_phase="concept_reaction",
            probing_strategy="concept_intro",
            decision_rationale="Move to concept reaction.",
            message_to_persona="If there were an AI synthetic-user platform for this, what would your first reaction be?",
            evidence_updates=[],
            root_cause_hypotheses=[],
            open_questions=[],
            should_end=False,
            end_reason="",
            question_evidence_basis="hypothetical",
            question_evidence_target="context",
        )

        revised = runtime._revise_non_episodic_validation_question(session, decision, "SYSTEM")

        self.assertIs(revised, revised_decision)
        self.assertEqual(len(provider.calls), 1)
        self.assertIn("CONCEPT TIMING GATE", provider.calls[0]["user_prompt"])
        self.assertIn("missing_evidence", provider.calls[0]["user_prompt"])
        self.assertIn("pressure", provider.calls[0]["user_prompt"])
        self.assertIn("defensible_vs_uncertain", provider.calls[0]["user_prompt"])
        self.assertIn("decision_change", provider.calls[0]["user_prompt"])
        self.assertEqual(
            session.facilitator_decisions[-1]["decision_status"],
            "rejected_by_concept_timing_gate",
        )

    def test_human_approved_learning_rules_are_recorded_and_injected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=74)[0]
            save_persona(persona, root / "personas")
            registry_path = root / "facilitator_rules.json"
            registry_path.write_text(
                json.dumps({
                    "artifact_version": "v1",
                    "approved_rules": [{
                        "rule_id": "linger_on_manual_verification",
                        "rule": "When a participant describes manual verification, ask what concrete mistake or avoided failure that behavior is protecting against.",
                        "status": "approved",
                    }],
                }),
                encoding="utf-8",
            )
            provider = RecordedLLMFacilitator()
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=provider,
                persona_provider=RecordedLLMPersona(),
                approved_learning_rules_path=registry_path,
            )
            output = runtime.run(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Understand root causes of trip replanning friction.",
                max_turns=2,
            )
            session = read_json(output / "interview.json")
            self.assertEqual(session["approved_learning_rule_ids"], ["linger_on_manual_verification"])
            self.assertEqual(session["approved_learning_rules_source"], str(registry_path))
            first_turn_prompt = provider.calls[0][1]["system_prompt"]
            self.assertIn("HUMAN-APPROVED FACILITATOR LEARNING RULES", first_turn_prompt)
            self.assertIn("Treat them as generic interviewing heuristics", first_turn_prompt)
            self.assertIn("linger_on_manual_verification", first_turn_prompt)

    def test_promote_facilitator_learning_rules_writes_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "facilitator_audit_learning_report.json"
            report_path.write_text(
                json.dumps({
                    "label": "Facilitator Audit Learning Report",
                    "human_review_candidates": [{
                        "rule_id": "linger_on_manual_verification",
                        "rule": "When a participant describes manual verification, ask what concrete mistake or avoided failure that behavior is protecting against.",
                        "source_tags": ["missed_high_signal_clue"],
                        "confidence": "medium",
                        "support_run_count": 2,
                        "support_persona_count": 6,
                        "candidate_strength": "strong",
                        "ready_for_human_review": True,
                    }],
                }),
                encoding="utf-8",
            )
            registry_path = root / "approved_facilitator_learning_rules.json"
            registry = promote_facilitator_learning_rules(
                report_path=report_path,
                registry_path=registry_path,
                rule_ids=["linger_on_manual_verification"],
                approved_by="test-reviewer",
                approval_note="Safe generic rule.",
            )
            self.assertEqual(registry["approved_rules"][0]["rule_id"], "linger_on_manual_verification")
            self.assertEqual(registry["approved_rules"][0]["approved_by"], "test-reviewer")
            self.assertTrue(registry_path.exists())
            self.assertTrue(registry_path.with_suffix(".md").exists())

    def test_disabled_learning_rules_are_not_injected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "facilitator_rules.json"
            registry_path.write_text(
                json.dumps({
                    "artifact_version": "v1",
                    "approved_rules": [{
                        "rule_id": "linger_on_manual_verification",
                        "rule": "When a participant describes manual verification, ask what concrete mistake or avoided failure that behavior is protecting against.",
                        "status": "disabled",
                    }],
                }),
                encoding="utf-8",
            )
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=RecordedLLMFacilitator(),
                persona_provider=RecordedLLMPersona(),
                approved_learning_rules_path=registry_path,
            )
            session = InterviewSession(
                interview_id="test",
                persona_id="su_0001",
                persona_name="Test Persona",
                research_goal="Test",
                product_context="",
                output_language="Traditional Chinese",
                facilitator_provider="x",
                facilitator_model="y",
                persona_provider="x",
                persona_model="y",
                facilitator_prompt_version="facilitator-interview/v2",
                synthesis_prompt_version="facilitator-synthesis/v2",
            )
            runtime._annotate_approved_learning_rules(session)
            prompt = runtime._facilitator_system_prompt(session)
            self.assertEqual(session.approved_learning_rule_ids, [])
            self.assertNotIn("HUMAN-APPROVED FACILITATOR LEARNING RULES", prompt)

    def test_disable_facilitator_learning_rules_updates_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "approved_facilitator_learning_rules.json"
            registry_path.write_text(
                json.dumps({
                    "artifact_version": "v1",
                    "approved_rules": [{
                        "rule_id": "linger_on_manual_verification",
                        "rule": "When a participant describes manual verification, ask what concrete mistake or avoided failure that behavior is protecting against.",
                        "status": "approved",
                    }],
                }),
                encoding="utf-8",
            )
            registry = disable_facilitator_learning_rules(
                registry_path=registry_path,
                rule_ids=["linger_on_manual_verification"],
                disabled_by="test-reviewer",
                disable_note="Rule overfit in latest run.",
            )
            self.assertEqual(registry["approved_rules"][0]["status"], "disabled")
            self.assertEqual(registry["approved_rules"][0]["disabled_by"], "test-reviewer")
            self.assertTrue(registry_path.with_suffix(".md").exists())

    def test_facilitator_provider_rejects_blank_non_terminal_question(self):
        class StubClient:
            config = OpenAIProviderConfig(api_key="fixture", model="fixture", transport="python_urllib")
            last_transport_metadata = {}

            def create_json_response(self, **kwargs):
                return {
                    "interview_phase": "opening",
                    "probing_strategy": "open_question",
                    "decision_rationale": "Start broadly.",
                    "message_to_persona": "",
                    "evidence_updates": [],
                    "root_cause_hypotheses": [],
                    "open_questions": [],
                    "should_end": False,
                    "end_reason": "",
                }

        with self.assertRaisesRegex(ValueError, "must ask a question"):
            OpenAIFacilitatorProvider(StubClient()).next_turn(system_prompt="skill", user_prompt="start")

    def test_hypothesis_assessment_rejects_high_confidence_and_unsupported_without_evidence(self):
        assessment = {
            "hypothesis_assessment": {
                "hypothesis": "A cause",
                "verdict": "unsupported",
                "supporting_evidence_refs": [],
                "contradicting_evidence_refs": [],
                "mechanism_test_basis": "not_tested",
                "condition_present_case_refs": [],
                "condition_absent_case_refs": [],
                "alternative_explanations": [],
                "alternative_tests": [],
                "evidence_gaps": [],
                "confidence": "medium",
            }
        }
        with self.assertRaisesRegex(ValueError, "requires contradicting evidence"):
            validate_hypothesis_assessment(assessment)
        assessment["hypothesis_assessment"]["verdict"] = "not_tested"
        assessment["hypothesis_assessment"]["confidence"] = "high"
        with self.assertRaisesRegex(ValueError, "cannot have high hypothesis confidence"):
            validate_hypothesis_assessment(assessment)

        assessment["hypothesis_assessment"]["confidence"] = "medium"
        assessment["hypothesis_assessment"]["verdict"] = "unsupported"
        assessment["hypothesis_assessment"]["contradicting_evidence_refs"] = ["exchange_1.persona"]
        assessment["hypothesis_assessment"]["mechanism_test_basis"] = "hypothetical"
        with self.assertRaisesRegex(ValueError, "requires an observed-event mechanism test"):
            validate_hypothesis_assessment(assessment)

        assessment["hypothesis_assessment"]["mechanism_test_basis"] = "observed_event"
        validate_hypothesis_assessment(assessment)

    def test_runtime_downgrades_hypothetical_evidence_and_clears_validation_product_outputs(self):
        self.assertEqual(
            FacilitatedInterviewRuntime._effective_question_basis("如果只有你自己，你還會再看嗎？", "current_event"),
            "hypothetical",
        )
        self.assertEqual(
            FacilitatedInterviewRuntime._effective_question_basis("你平常通常會再看嗎？", "current_event"),
            "general_pattern",
        )
        self.assertEqual(
            FacilitatedInterviewRuntime._effective_question_basis("那晚你會再看一次，最主要是卡在哪一點？", "hypothetical"),
            "current_event",
        )
        self.assertEqual(
            FacilitatedInterviewRuntime._effective_question_basis("你有沒有一次也是旅行安排有改，但不用通知其他人？", "current_event"),
            "recalled_contrast_event",
        )
        session = InterviewSession.from_dict({
            "interview_id": "fixture",
            "persona_id": "su_fixture",
            "persona_name": "Fixture",
            "research_goal": "Test a cause",
            "product_context": "",
            "output_language": "Traditional Chinese",
            "facilitator_provider": "fixture",
            "facilitator_model": "fixture",
            "persona_provider": "fixture",
            "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "facilitator-synthesis/v2",
            "interview_mode": "validate_hypothesis",
            "hypothesis": "A cause",
            "exchanges": [{
                "exchange_id": 1,
                "facilitator_question": "If nobody else were involved, would you still check?",
                "persona_response": "I might.",
                "facilitator_phase": "contrast",
                "probing_strategy": "counterfactual",
                "question_evidence_basis": "hypothetical",
            }],
        })
        synthesis = {
            "needs": ["A need"],
            "pov_statements": ["A POV"],
            "how_might_we_questions": ["A HMW"],
            "hypothesis_assessment": {
                "verdict": "mixed",
                "mechanism_test_basis": "observed_event",
                "supporting_evidence_refs": ["exchange_1.persona"],
                "contradicting_evidence_refs": ["exchange_1.persona"],
                "condition_present_case_refs": ["exchange_1.persona"],
                "condition_absent_case_refs": ["exchange_1.persona"],
                "alternative_tests": [{
                    "explanation": "Alternative",
                    "evidence_refs": ["exchange_1.persona"],
                    "basis": "observed_event",
                    "outcome": "mixed",
                }],
                "evidence_gaps": [],
                "confidence": "medium",
            },
        }
        FacilitatedInterviewRuntime._enforce_synthesis_evidence_scope(session, synthesis)
        assessment = synthesis["hypothesis_assessment"]
        self.assertEqual(assessment["verdict"], "not_tested")
        self.assertEqual(assessment["alternative_tests"][0]["basis"], "hypothetical")
        self.assertEqual(synthesis["needs"], [])
        self.assertEqual(synthesis["pov_statements"], [])
        self.assertEqual(synthesis["how_might_we_questions"], [])

    def test_independent_judge_overrides_synthesis_hypothesis_claims(self):
        session = InterviewSession.from_dict({
            "interview_id": "judged", "persona_id": "su_fixture", "persona_name": "Fixture",
            "research_goal": "Test", "product_context": "", "output_language": "English",
            "facilitator_provider": "fixture", "facilitator_model": "fixture",
            "persona_provider": "fixture", "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "facilitator-synthesis/v2",
            "interview_mode": "validate_hypothesis", "hypothesis": "Exact hypothesis",
            "hypothesis_evidence_judgment": {
                "recommended_verdict": "unsupported", "supporting_evidence_refs": [],
                "contradicting_evidence_refs": ["exchange_1.persona"], "confidence": "medium",
                "condition_present": {"status": "ambiguous", "evidence_refs": [], "rationale": "Adjacent only."},
                "condition_absent": {"status": "observed", "evidence_refs": ["exchange_1.persona"], "rationale": "Observed."},
                "warnings": ["Exact condition was not observed."],
            },
            "exchanges": [{
                "exchange_id": 1, "facilitator_question": "What happened in that event?",
                "persona_response": "An owner was known.", "facilitator_phase": "mechanism",
                "probing_strategy": "condition", "question_evidence_basis": "current_event",
                "question_evidence_target": "hypothesis_condition",
            }],
        })
        synthesis = {
            "needs": ["x"], "pov_statements": ["x"], "how_might_we_questions": ["x"],
            "hypothesis_assessment": {
                "hypothesis": "Rewritten claim", "verdict": "provisionally_supported",
                "supporting_evidence_refs": ["exchange_1.persona"], "contradicting_evidence_refs": [],
                "mechanism_test_basis": "observed_event", "condition_present_case_refs": ["exchange_1.persona"],
                "condition_absent_case_refs": ["exchange_1.persona"], "alternative_explanations": [],
                "alternative_tests": [], "evidence_gaps": [], "confidence": "medium",
            },
        }
        FacilitatedInterviewRuntime._enforce_synthesis_evidence_scope(session, synthesis)
        assessment = synthesis["hypothesis_assessment"]
        self.assertEqual(assessment["hypothesis"], "Exact hypothesis")
        self.assertEqual(assessment["verdict"], "unsupported")
        self.assertEqual(assessment["supporting_evidence_refs"], [])
        self.assertEqual(assessment["contradicting_evidence_refs"], ["exchange_1.persona"])
        self.assertIn("Exact condition was not observed.", assessment["evidence_gaps"])

    def test_facilitated_interview_cli_has_no_mock_backend(self):
        parser = _build_parser()
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args([
                    "run-facilitated-interview",
                    "--persona-id", "su_0001",
                    "--research-goal", "Understand a problem",
                    "--backend", "mock",
                ])

        parsed = parser.parse_args([
            "run-facilitated-interview",
            "--persona-id", "su_0001",
            "--research-goal", "Test a cause",
            "--interview-mode", "validate_hypothesis",
            "--hypothesis", "People recheck because ownership is unclear.",
            "--debug-progress",
        ])
        self.assertEqual(parsed.interview_mode, "validate_hypothesis")
        self.assertTrue(parsed.debug_progress)

        parsed = parser.parse_args([
            "observe-facilitated-interview",
            "--persona-id", "su_0001",
            "--research-goal", "Test",
            "--soft-turn-limit", "12",
            "--hard-turn-limit", "16",
            "--debug-progress",
        ])
        self.assertEqual(parsed.soft_turn_limit, 12)
        self.assertEqual(parsed.hard_turn_limit, 16)
        self.assertTrue(parsed.debug_progress)

        parsed = parser.parse_args([
            "run-concept-panel",
            "--research-goal", "Validate a concept",
            "--product-context", "Neutral concept context",
            "--topic-label", "Test Topic",
            "--backend", "codex-sdk",
            "--approved-learning-rules-path", "rules.json",
            "--debug-progress",
        ])
        self.assertIsNone(parsed.max_turns)
        self.assertIsNone(parsed.soft_turn_limit)
        self.assertIsNone(parsed.hard_turn_limit)
        self.assertEqual(parsed.reasoning_effort, "medium")
        self.assertEqual(parsed.backend, "codex-sdk")
        self.assertEqual(parsed.approved_learning_rules_path, Path("rules.json"))
        self.assertTrue(parsed.debug_progress)

        parsed = parser.parse_args([
            "aggregate-facilitator-audit-runs",
            "--run-dir", "run_a",
            "--run-dir", "run_b",
            "--output-dir", "learning",
        ])
        self.assertEqual(parsed.run_dirs, [Path("run_a"), Path("run_b")])

        parsed = parser.parse_args([
            "promote-facilitator-learning-rules",
            "--report-path", "report.json",
            "--registry-path", "registry.json",
            "--rule-id", "linger_on_manual_verification",
        ])
        self.assertEqual(parsed.rule_ids, ["linger_on_manual_verification"])

        parsed = parser.parse_args([
            "disable-facilitator-learning-rules",
            "--registry-path", "registry.json",
            "--rule-id", "linger_on_manual_verification",
        ])
        self.assertEqual(parsed.rule_ids, ["linger_on_manual_verification"])

        parsed = parser.parse_args([
            "compare-facilitator-learning-effects",
            "--baseline-run-dir", "baseline_run",
            "--candidate-run-dir", "candidate_run",
            "--output-dir", "effect_report",
        ])
        self.assertEqual(parsed.baseline_run_dirs, [Path("baseline_run")])
        self.assertEqual(parsed.candidate_run_dirs, [Path("candidate_run")])


if __name__ == "__main__":
    unittest.main()
