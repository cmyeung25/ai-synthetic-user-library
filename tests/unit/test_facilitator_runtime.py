import tempfile
import unittest
import io
from contextlib import redirect_stderr
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.cli.main import _build_parser
from ai_validation_swarm.conversation.providers import ChatResult
from ai_validation_swarm.facilitator.models import FacilitatorDecision
from ai_validation_swarm.facilitator.models import InterviewSession
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
            self.assertIn("Root-Cause Hypotheses", (output / "insights.md").read_text(encoding="utf-8"))

            all_facilitator_inputs = "\n".join(str(call[1]) for call in facilitator.calls)
            self.assertNotIn("PERSONA RESEARCH KERNEL", all_facilitator_inputs)
            self.assertNotIn(persona.profile.basic_identity["name"], all_facilitator_inputs)
            self.assertIn("exchange_1.persona", all_facilitator_inputs)
            self.assertIn("INTERVIEW MODE", all_facilitator_inputs)

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
            self.assertIn("Test Go Out La Protocol", first_turn_prompt)
            self.assertIn("Assumption Validation", (output / "insights.md").read_text(encoding="utf-8"))
            self.assertIn("# Go Out La! Interview:", (output / "insights.md").read_text(encoding="utf-8"))

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
        ])
        self.assertEqual(parsed.interview_mode, "validate_hypothesis")


if __name__ == "__main__":
    unittest.main()
