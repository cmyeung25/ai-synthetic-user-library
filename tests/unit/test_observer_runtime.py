import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.conversation.providers import ChatResult
from ai_validation_swarm.facilitator.models import FacilitatorDecision
from ai_validation_swarm.facilitator.providers import (
    normalize_facilitator_audit_feedback,
    normalize_quality_evaluation,
    validate_facilitator_audit_feedback,
    validate_quality_evaluation,
)
from ai_validation_swarm.observer.runtime import ObserverControlledInterviewRuntime
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.storage.files import read_json, save_persona


def decision(question, phase, strategy, session_id="fac-thread", *, should_end=False):
    return FacilitatorDecision(
        interview_phase=phase,
        probing_strategy=strategy,
        decision_rationale=f"LLM selected {strategy} from the available transcript.",
        message_to_persona=question,
        evidence_updates=[],
        root_cause_hypotheses=[],
        open_questions=[],
        should_end=should_end,
        end_reason="Evidence is sufficient." if should_end else "",
        provider_session_id=session_id,
    )


def synthesis_payload():
    return {
        "executive_summary": "Responsibility ambiguity may be more important than route generation.",
        "insights": [{
            "insight": "Changes create coordination work.",
            "evidence_refs": ["exchange_1.persona"],
            "confidence": "medium",
            "implication": "Validate responsibility handoffs.",
        }],
        "needs": ["Know who owns the next action after a change."],
        "root_cause_hypotheses": [{
            "hypothesis": "Unclear ownership may cause repeated checking.",
            "supporting_evidence_refs": ["exchange_1.persona"],
            "alternative_explanations": ["The trip may have been unusually complex."],
            "validation_gap": "Interview real travellers.",
            "confidence": "low",
        }],
        "contradictions": [],
        "pov_statements": ["A traveller facing change needs clear ownership because coordination becomes uncertain."],
        "how_might_we_questions": ["How might we clarify responsibility after plans change?"],
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
        "evidence_gaps": ["No human evidence."],
        "recommended_human_validation": ["Interview people after a disrupted trip."],
        "synthetic_only_disclaimer": "Synthetic-user interview for AI pre-validation only; not human market evidence.",
    }


def quality_payload():
    return {
        "overall_verdict": "warn",
        "scores": {
            "neutrality": 4,
            "probing_quality": 3,
            "conversation_naturalness": 3,
            "evidence_discipline": 4,
            "causal_rigor": 3,
            "hypothesis_validation_rigor": 3,
            "synthesis_fidelity": 4,
            "overall": 3,
        },
        "checks": {
            "leading_question_risk": "pass",
            "repetition_risk": "warn",
            "premature_root_cause_risk": "warn",
            "mechanical_five_whys_risk": "pass",
            "evidence_reference_quality": "pass",
            "synthesis_overreach_risk": "pass",
            "conversation_naturalness": "warn",
            "persona_over_structuring_risk": "warn",
            "interviewer_jargon_risk": "pass",
            "domain_fit_alignment": "pass",
            "hypothesis_confirmation_bias_risk": "pass",
            "hypothesis_judge_alignment": "pass",
        },
        "strengths": ["Questions requested concrete examples."],
        "findings": [{
            "category": "repetition",
            "severity": "medium",
            "observation": "One probe partially repeated sequence detail.",
            "evidence_refs": ["exchange_1.facilitator"],
            "recommendation": "Move to a counterexample sooner.",
        }],
        "required_improvements": ["Ask for a counterexample before strengthening the root-cause hypothesis."],
        "improvement_hints": {
            "next_interview_focus": ["Ask for a concrete counterexample before closing."],
            "coverage_gap_actions": ["Collect one explicit contrast event with a different outcome."],
            "prompt_adjustments": ["Tell the facilitator to prefer counterexamples after one causal claim appears."],
            "turn_budget_guidance": "Keep the current hard limit, but allow one extra turn after the soft limit when contrast evidence is missing.",
        },
        "human_review_needed": True,
        "synthetic_only_disclaimer": "Synthetic interview quality review only.",
    }


def facilitator_audit_feedback_payload():
    return {
        "artifact_version": "v1",
        "feedback_scope": "interview",
        "applies_to": {
            "interview_mode": ["explore_root_cause"],
            "domains": ["generic"],
            "safe_for_global_reuse": True,
        },
        "summary": {
            "overall_assessment": "The facilitator covered the interview adequately but left depth on the table.",
            "primary_failure_mode": "coverage_over_depth",
            "depth_vs_coverage_assessment": "Coverage was acceptable, but one high-signal clue was not pursued.",
        },
        "facilitator_feedback_tags": [{
            "tag": "missed_high_signal_clue",
            "severity": "medium",
            "why_it_matters": "A concrete workaround clue was not converted into a deeper causal probe.",
            "observed_pattern": "The participant described rechecking behavior and the facilitator moved on.",
        }],
        "high_value_missed_followups": [{
            "trigger_type": "manual_reconciliation",
            "priority": "high",
            "participant_signal": "The participant said they checked every booking again.",
            "missed_followup_question": "What mistake were you trying to avoid by checking everything again?",
            "generic_learning": "When a participant manually reconciles information, ask what failure that behavior is protecting against.",
        }],
        "likely_misclassified_driver_patterns": [{
            "observed_surface_frame": "needs better trip planning tools",
            "possible_underlying_driver": "needs confidence restoration after a coordination change",
            "why_the_surface_frame_is_weak": "The transcript centered on verification, not on planning breadth.",
            "generic_learning": "Do not treat a requested tool improvement as the root driver until the avoided error is explicit.",
        }],
        "evidence_handling_issues": [{
            "issue": "The facilitator accepted an intention statement without probing its consequence threshold.",
            "severity": "medium",
            "generic_learning": "When a participant states what they would do next time, ask what would trigger that action in a real event.",
        }],
        "prompt_adjustments": [{
            "adjustment_type": "followup_trigger_rule",
            "text": "If a participant mentions a manual verification step, ask one follow-up about what failure it protects against before moving on.",
            "reuse_scope": "global",
            "safe_for_global_reuse": True,
        }],
        "carry_forward_rules": [{
            "rule_id": "linger_on_manual_verification",
            "rule": "When a participant describes manual verification, ask what concrete mistake, confusion, or avoided failure that behavior is protecting against.",
            "source_tags": ["missed_high_signal_clue"],
            "confidence": "medium",
            "safe_for_global_reuse": True,
        }],
        "blocked_feedback": [],
    }


class ObserverFacilitatorFixture:
    provider_name = "recorded-llm"
    model_name = "recorded-facilitator/v1"

    def __init__(self):
        self.calls = []
        self.decisions = [
            decision("Describe the last disrupted trip.", "recent_event", "critical_incident"),
            decision("Which handoff was uncertain in that event?", "workflow", "observer_steered_probe"),
            decision("What consequence did that uncertainty create?", "consequence", "consequence_probe"),
            decision("When has a similar change gone smoothly?", "counterexample", "counterexample_probe"),
            decision("What would you do differently next time?", "closure", "counterfactual_probe"),
        ]

    def next_turn(self, **kwargs):
        self.calls.append(kwargs)
        return self.decisions.pop(0)

    def synthesize(self, **kwargs):
        self.calls.append(kwargs)
        return synthesis_payload(), "fac-thread"

    def judge_hypothesis_evidence(self, **kwargs):
        self.calls.append(kwargs)
        return ({
            "hypothesis": "A fixture hypothesis.",
            "operational_condition_present": "Condition is present.",
            "operational_condition_absent": "Condition is absent.",
            "target_behaviour_observed": True,
            "target_behaviour_refs": ["exchange_1.persona"],
            "condition_present": {"status": "not_observed", "evidence_refs": [], "rationale": "Missing."},
            "condition_absent": {"status": "observed", "evidence_refs": ["exchange_1.persona"], "rationale": "Observed."},
            "supporting_evidence_refs": [],
            "contradicting_evidence_refs": ["exchange_1.persona"],
            "recommended_verdict": "not_tested",
            "confidence": "low",
            "warnings": ["Condition-present case missing."],
        }, "judge-thread")

    def synthesize_concept(self, **kwargs):
        self.calls.append(kwargs)
        return synthesis_payload(), "fac-thread"


class ObserverPersonaFixture:
    provider_name = "recorded-llm"
    model_name = "recorded-persona/v1"

    def __init__(self):
        self.calls = []
        self.responses = [
            "My partner and I each thought the other person had confirmed the new time.",
            "I then checked every booking again because I did not trust the shared plan.",
            "Next time I would assign one owner before changing the rest of the plan.",
        ]

    def respond(self, **kwargs):
        self.calls.append(kwargs)
        return ChatResult(self.responses.pop(0), "unclear", "high", "persona-thread")

    def generate_persona_driver_trace(self, **kwargs):
        return type("TraceResult", (), {
            "payload": {
                "synthetic_only_disclaimer": "Synthetic persona post-interview reflection only; not human market evidence.",
                "surface_read": {
                    "what_the_persona_explicitly_said": [
                        "They thought the other person had confirmed the new time.",
                        "They rechecked every booking because they did not trust the shared plan.",
                    ],
                    "what_they_seemed_to_optimize_for": "Avoiding another coordination miss.",
                    "what_stayed_implicit": [
                        "Whether this caution comes from a broader household role or one bad recent incident.",
                    ],
                },
                "likely_drivers": [
                    {
                        "driver": "Responsibility ambiguity triggers manual checking",
                        "driver_type": "trust_pattern",
                        "why_it_matters_here": "The persona defaults to verification when shared ownership feels unclear.",
                        "evidence_refs": ["exchange_1.persona", "exchange_2.persona"],
                        "profile_source_refs": ["human_difference_axes.control_preference", "behavior_profile"],
                        "confidence": "medium",
                        "observed_vs_inferred": "mixed",
                    }
                ],
                "unspoken_constraints": [
                    {
                        "constraint": "The persona may feel accountable for making sure the plan does not fail publicly.",
                        "why_likely": "Their answer moves quickly from ambiguity to self-checking.",
                        "evidence_refs": ["exchange_2.persona"],
                        "profile_source_refs": ["life_story", "human_difference_axes.life_load"],
                        "confidence": "low",
                    }
                ],
                "value_tensions": [
                    {
                        "tension": "Shared planning versus single ownership",
                        "side_a": "Wants collaboration",
                        "side_b": "Falls back to one owner to feel safe",
                        "evidence_refs": ["exchange_1.persona", "exchange_3.persona"],
                        "profile_source_refs": ["values.core_values", "human_difference_axes.control_preference"],
                        "confidence": "medium",
                    }
                ],
                "missed_follow_up_questions": [
                    {
                        "question": "When you say you did not trust the shared plan, what exactly were you afraid would happen next?",
                        "why_this_would_clarify": "It would separate social embarrassment, practical loss, and control anxiety.",
                        "priority": "high",
                    }
                ],
            },
            "provider_session_id": "persona-trace-thread",
        })()


class ObserverQualityFixture:
    provider_name = "recorded-llm"
    model_name = "recorded-quality/v1"

    def __init__(self):
        self.calls = []

    def evaluate_quality(self, **kwargs):
        self.calls.append(kwargs)
        return quality_payload(), "quality-thread"

    def generate_audit_feedback(self, **kwargs):
        self.calls.append(kwargs)
        return facilitator_audit_feedback_payload(), "audit-thread"


class FailingTracePersonaFixture(ObserverPersonaFixture):
    def __init__(self):
        super().__init__()
        self.responses = [
            "The disruption started when the booking time changed and we both assumed the other person had handled it.",
            "I thought the cause was that nobody wanted to take clear ownership of the updates.",
            "The consequence was that I checked every booking again and still felt unsure.",
        ]

    def generate_persona_driver_trace(self, **kwargs):
        raise RuntimeError("persona trace timeout")


class FailOnceFacilitator(ObserverFacilitatorFixture):
    def __init__(self):
        super().__init__()
        self.failed = False

    def next_turn(self, **kwargs):
        if not self.failed:
            self.failed = True
            raise RuntimeError("temporary LLM transport failure")
        return super().next_turn(**kwargs)


class HypotheticalThenEpisodicFacilitator(ObserverFacilitatorFixture):
    def __init__(self):
        self.calls = []
        self.decisions = [
            FacilitatorDecision(
                interview_phase="contrast",
                probing_strategy="counterfactual",
                decision_rationale="Test an imagined condition.",
                message_to_persona="如果只有你自己，你還會再看嗎？",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=[],
                should_end=False,
                end_reason="",
                question_evidence_basis="current_event",
                provider_session_id="fac-thread",
            ),
            FacilitatorDecision(
                interview_phase="contrast",
                probing_strategy="recalled_contrast_event",
                decision_rationale="Use a real past contrast.",
                message_to_persona="你記得另一次只有自己出發、安排又有改動的情況嗎？",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=[],
                should_end=False,
                end_reason="",
                question_evidence_basis="recalled_contrast_event",
                provider_session_id="fac-thread",
            ),
        ]


class EndThenContrastFacilitator(HypotheticalThenEpisodicFacilitator):
    def __init__(self):
        self.calls = []
        self.decisions = [
            FacilitatorDecision(
                interview_phase="closure",
                probing_strategy="evidence_sufficiency",
                decision_rationale="Enough evidence.",
                message_to_persona="",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=[],
                should_end=True,
                end_reason="Enough evidence.",
                question_evidence_basis="clarification",
                provider_session_id="fac-thread",
            ),
            FacilitatorDecision(
                interview_phase="contrast",
                probing_strategy="recalled_contrast_event",
                decision_rationale="Collect the missing real contrast.",
                message_to_persona="你記得另一次不知道由誰更新安排的情況嗎？",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=[],
                should_end=False,
                end_reason="",
                question_evidence_basis="recalled_contrast_event",
                provider_session_id="fac-thread",
            ),
        ]


class LoadedThenNeutralFacilitator(HypotheticalThenEpisodicFacilitator):
    def __init__(self):
        self.calls = []
        self.decisions = [
            FacilitatorDecision(
                interview_phase="mechanism",
                probing_strategy="hypothesis_condition",
                decision_rationale="Test ownership.",
                message_to_persona="嗰次其實冇人講清楚邊個負責更新嗎？",
                evidence_updates=[], root_cause_hypotheses=[], open_questions=[],
                should_end=False, end_reason="", question_evidence_basis="current_event",
                question_evidence_target="hypothesis_condition", provider_session_id="fac-thread",
            ),
            FacilitatorDecision(
                interview_phase="mechanism",
                probing_strategy="role_reconstruction",
                decision_rationale="Reconstruct roles neutrally.",
                message_to_persona="嗰次住宿、車票同接送最後分別係邊個處理？",
                evidence_updates=[], root_cause_hypotheses=[], open_questions=[],
                should_end=False, end_reason="", question_evidence_basis="current_event",
                question_evidence_target="hypothesis_condition", provider_session_id="fac-thread",
            ),
        ]


class CoverageAwareFacilitator:
    provider_name = "recorded-llm"
    model_name = "coverage-aware/v1"

    def __init__(self):
        self.calls = []
        self.decisions = [
            decision("Tell me about the last disrupted trip.", "recent_event", "critical_incident"),
            decision("What did you think was causing the repeated checking in that moment?", "root_cause", "participant_cause_probe"),
            decision("What consequence did that create for you or the other person?", "consequence", "consequence_probe"),
            decision("What would you change next time?", "closure", "counterfactual_probe", should_end=True),
        ]

    def next_turn(self, **kwargs):
        self.calls.append(kwargs)
        return self.decisions.pop(0)

    def synthesize(self, **kwargs):
        self.calls.append(kwargs)
        return synthesis_payload(), "coverage-thread"

    def judge_hypothesis_evidence(self, **kwargs):
        self.calls.append(kwargs)
        return ObserverFacilitatorFixture().judge_hypothesis_evidence(**kwargs)

    def synthesize_concept(self, **kwargs):
        self.calls.append(kwargs)
        return synthesis_payload(), "coverage-thread"


class CoverageAwarePersonaFixture(ObserverPersonaFixture):
    def __init__(self):
        super().__init__()
        self.responses = [
            "The disruption started when the booking time changed and we both assumed the other person had handled it.",
            "I thought the cause was that nobody wanted to take clear ownership of the updates.",
            "The consequence was that I checked every booking again and still felt unsure.",
        ]


class ObserverRuntimeTest(unittest.TestCase):
    def _library(self, root):
        persona = generate_personas(count=1, random_seed=83)[0]
        save_persona(persona, root / "personas")
        return persona

    def test_observer_can_steer_ask_pause_resume_stop_and_receive_quality_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = self._library(root)
            facilitator = ObserverFacilitatorFixture()
            quality = ObserverQualityFixture()
            persona_provider = ObserverPersonaFixture()
            progress = []
            runtime = ObserverControlledInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=facilitator,
                persona_provider=persona_provider,
                quality_provider=quality,
                progress_writer=progress.append,
            )
            folder, session = runtime.start(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Understand trip replanning friction.",
                max_turns=6,
            )
            self.assertEqual(session.status, "awaiting_observer")
            self.assertEqual(session.pending_facilitator_decision["message_to_persona"], "Describe the last disrupted trip.")

            session = runtime.steer(session.interview_id, "Focus on responsibility without suggesting a cause.")
            self.assertEqual(session.pending_facilitator_decision["message_to_persona"], "Which handoff was uncertain in that event?")
            self.assertEqual(session.observer_interventions[0]["action"], "steer")
            self.assertEqual(session.observer_interventions[0]["superseded_question"], "Describe the last disrupted trip.")

            session = runtime.continue_interview(session.interview_id)
            self.assertEqual(len(session.exchanges), 1)
            self.assertEqual(session.exchanges[0].facilitator_phase, "workflow")
            self.assertEqual(session.pending_facilitator_decision["message_to_persona"], "What consequence did that uncertainty create?")

            session = runtime.pause(session.interview_id)
            self.assertEqual(session.status, "paused")
            _, reloaded = runtime.load(session.interview_id)
            self.assertEqual(reloaded.status, "paused")
            session = runtime.continue_interview(session.interview_id)
            self.assertEqual(session.status, "awaiting_observer")
            self.assertEqual(len(session.exchanges), 2)
            self.assertEqual(session.pending_facilitator_decision["message_to_persona"], "When has a similar change gone smoothly?")

            session = runtime.ask_direct(session.interview_id, "What did you do next because of that uncertainty?")
            self.assertEqual(len(session.exchanges), 3)
            self.assertEqual(session.exchanges[2].facilitator_phase, "observer_intervention")
            self.assertEqual(session.observer_interventions[-1]["action"], "direct_question")
            self.assertEqual(session.pending_facilitator_decision["message_to_persona"], "What would you do differently next time?")

            session = runtime.finalize(session.interview_id, stop_reason="observer_stop")
            self.assertEqual(session.status, "completed")
            self.assertEqual(session.quality_provider_session_id, "quality-thread")
            self.assertEqual(session.facilitator_audit_feedback_provider_session_id, "audit-thread")
            self.assertEqual(session.quality_evaluation["overall_verdict"], "warn")
            self.assertEqual(
                session.facilitator_audit_feedback["summary"]["primary_failure_mode"],
                "coverage_over_depth",
            )
            self.assertNotEqual(session.facilitator_provider_session_id, session.persona_provider_session_id)
            decision_statuses = [item["decision_status"] for item in session.facilitator_decisions]
            self.assertIn("superseded_by_observer", decision_statuses)
            self.assertIn("asked", decision_statuses)
            self.assertIn("not_asked_at_close", decision_statuses)
            for name in (
                "observer_events.json", "insight_report.json", "insights.md",
                "persona_driver_trace.json", "persona_driver_trace.md",
                "quality_evaluation.json", "quality_evaluation.md",
                "facilitator_audit_feedback.json", "facilitator_audit_feedback.md",
            ):
                self.assertTrue((folder / name).exists(), name)
            trace = read_json(folder / "persona_driver_trace.json")
            self.assertEqual(trace["likely_drivers"][0]["driver_type"], "trust_pattern")
            self.assertEqual(session.persona_driver_trace_provider_session_id, "persona-trace-thread")

            facilitator_input = "\n".join(str(call) for call in facilitator.calls)
            self.assertNotIn("PERSONA RESEARCH KERNEL", facilitator_input)
            self.assertNotIn(persona.profile.basic_identity["name"], facilitator_input)
            self.assertIn("OBSERVER DIRECTION", facilitator_input)
            self.assertIn("OBSERVER INTERVENTIONS", quality.calls[0]["user_prompt"])
            self.assertIn("COVERAGE STATUS", quality.calls[0]["user_prompt"])
            self.assertNotIn('"evidence_updates"', quality.calls[0]["user_prompt"])
            self.assertIn('"question_evidence_basis"', quality.calls[0]["user_prompt"])
            self.assertIn("QUALITY EVALUATION", quality.calls[1]["user_prompt"])
            self.assertIn("PERSONA DRIVER TRACE", quality.calls[1]["user_prompt"])
            self.assertIn("Natural Synthetic Participant Interview Mode", persona_provider.calls[0]["system_prompt"])
            self.assertIn("Do not exhaustively account for the decision", persona_provider.calls[0]["system_prompt"])
            quality_md = (folder / "quality_evaluation.md").read_text(encoding="utf-8")
            audit_md = (folder / "facilitator_audit_feedback.md").read_text(encoding="utf-8")
            self.assertIn("Improvement Hints", quality_md)
            self.assertIn("Turn budget:", quality_md)
            self.assertIn("Missed High-Value Follow-Ups", audit_md)
            self.assertTrue(any("start_observed" in item for item in progress))
            self.assertTrue(any("requesting_facilitator" in item for item in progress))
            self.assertTrue(any("asking_persona" in item for item in progress))
            self.assertTrue(any("evaluating_quality" in item for item in progress))
            self.assertTrue(any("auditing_facilitator" in item for item in progress))
            self.assertTrue(any("completed_observed" in item for item in progress))

            session = runtime.reevaluate_quality(session.interview_id)
            self.assertEqual(session.status, "completed")
            self.assertEqual(len(quality.calls), 4)
            self.assertTrue((folder / "quality_evaluation.previous.json").exists())
            self.assertTrue((folder / "facilitator_audit_feedback.previous.json").exists())

            session = runtime.resynthesize(session.interview_id)
            self.assertEqual(session.status, "completed")
            self.assertTrue((folder / "insight_report.previous.json").exists())
            self.assertTrue((folder / "persona_driver_trace.previous.json").exists())
            self.assertEqual(session.last_error, "")
            self.assertEqual(session.failed_operation, "")

    def test_observer_suggested_question_is_reviewed_by_facilitator_before_asking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = self._library(root)
            facilitator = CoverageAwareFacilitator()
            persona_provider = ObserverPersonaFixture()
            runtime = ObserverControlledInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=facilitator,
                persona_provider=persona_provider,
                quality_provider=ObserverQualityFixture(),
            )
            _, session = runtime.start(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Understand trip replanning friction.",
            )
            suggested = "Which confirmation failure would have the most serious consequence?"
            session = runtime.suggest_question(session.interview_id, suggested)
            self.assertEqual(session.observer_interventions[-1]["action"], "suggested_question")
            self.assertEqual(session.facilitator_decisions[0]["decision_status"], "superseded_by_observer")
            self.assertNotEqual(session.pending_facilitator_decision["message_to_persona"], suggested)
            self.assertIn("OBSERVER SUGGESTED QUESTION", facilitator.calls[-1]["user_prompt"])
            self.assertEqual(len(persona_provider.calls), 0)

    def test_observer_continues_when_persona_driver_trace_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = self._library(root)
            facilitator = CoverageAwareFacilitator()
            quality = ObserverQualityFixture()
            persona_provider = FailingTracePersonaFixture()
            progress = []
            runtime = ObserverControlledInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=facilitator,
                persona_provider=persona_provider,
                quality_provider=quality,
                progress_writer=progress.append,
            )
            _, session = runtime.start(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Understand trip replanning friction.",
                max_turns=6,
            )

            while session.status not in {"completed", "failed"}:
                session = runtime.continue_interview(session.interview_id)

            folder, session = runtime.load(session.interview_id)
            self.assertEqual(session.status, "completed")
            self.assertEqual(session.persona_driver_trace, {})
            self.assertTrue((folder / "persona_driver_trace.error.txt").exists())
            self.assertFalse((folder / "persona_driver_trace.json").exists())
            self.assertFalse((folder / "persona_driver_trace.md").exists())
            self.assertTrue((folder / "quality_evaluation.json").exists())
            self.assertTrue((folder / "facilitator_audit_feedback.json").exists())
            self.assertEqual(session.last_error, "")
            self.assertTrue(any("persona_driver_trace_skipped" in item for item in progress))

    def test_observed_hypothesis_mode_reaches_facilitator_and_quality_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = self._library(root)
            facilitator = ObserverFacilitatorFixture()
            runtime = ObserverControlledInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=facilitator,
                persona_provider=ObserverPersonaFixture(),
                quality_provider=ObserverQualityFixture(),
            )
            hypothesis = "People recheck because responsibility for updates is unclear."
            _, session = runtime.start(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Test why changed trips trigger repeated checks.",
                interview_mode="validate_hypothesis",
                hypothesis=hypothesis,
            )
            self.assertEqual(session.interview_mode, "validate_hypothesis")
            self.assertEqual(session.hypothesis, hypothesis)
            self.assertIn("INTERVIEW MODE:\nvalidate_hypothesis", facilitator.calls[0]["user_prompt"])
            self.assertIn(hypothesis, facilitator.calls[0]["user_prompt"])
            quality_context = runtime._quality_user_prompt(session)
            self.assertIn("INTERVIEW MODE:\nvalidate_hypothesis", quality_context)
            self.assertIn(hypothesis, quality_context)

    def test_observed_concept_validation_uses_custom_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = self._library(root)
            protocol_path = root / "go-out-la-v1.md"
            protocol_path.write_text("## Go Out La test protocol", encoding="utf-8")
            facilitator = ObserverFacilitatorFixture()
            runtime = ObserverControlledInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=facilitator,
                persona_provider=ObserverPersonaFixture(),
                quality_provider=ObserverQualityFixture(),
            )
            _, session = runtime.start(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Validate Go Out La.",
                interview_mode="concept_validation",
                product_context="Go Out La concept test.",
                concept_protocol=str(protocol_path),
                concept_label="Go Out La!",
            )
            self.assertEqual(session.concept_label, "Go Out La!")
            self.assertEqual(session.concept_protocol_version, str(protocol_path))
            self.assertIn("Go Out La test protocol", facilitator.calls[0]["system_prompt"])

    def test_hypothetical_validation_question_is_revised_before_persona_sees_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = self._library(root)
            facilitator = HypotheticalThenEpisodicFacilitator()
            runtime = ObserverControlledInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=facilitator,
                persona_provider=ObserverPersonaFixture(),
                quality_provider=ObserverQualityFixture(),
            )
            _, session = runtime.start(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Test a cause.",
                interview_mode="validate_hypothesis",
                hypothesis="Unclear ownership causes repeated checking.",
            )
            self.assertEqual(
                session.pending_facilitator_decision["message_to_persona"],
                "你記得另一次只有自己出發、安排又有改動的情況嗎？",
            )
            self.assertEqual(session.facilitator_decisions[0]["decision_status"], "rejected_by_evidence_gate")
            self.assertEqual(session.facilitator_decisions[0]["question_evidence_basis"], "hypothetical")
            self.assertIn("EVIDENCE GATE", facilitator.calls[1]["user_prompt"])

    def test_validation_closure_is_rejected_until_real_contrasts_are_attempted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = self._library(root)
            facilitator = EndThenContrastFacilitator()
            runtime = ObserverControlledInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=facilitator,
                persona_provider=ObserverPersonaFixture(),
                quality_provider=ObserverQualityFixture(),
            )
            _, session = runtime.start(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Test a cause.",
                interview_mode="validate_hypothesis",
                hypothesis="Unclear ownership causes repeated checking.",
            )
            self.assertFalse(session.pending_facilitator_decision["should_end"])
            self.assertEqual(session.facilitator_decisions[0]["decision_status"], "rejected_by_evidence_gate")
            self.assertIn("evidence checklist was complete", facilitator.calls[1]["user_prompt"])

    def test_loaded_hypothesis_condition_is_rewritten_as_neutral_reconstruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = self._library(root)
            facilitator = LoadedThenNeutralFacilitator()
            runtime = ObserverControlledInterviewRuntime(
                data_dir=root / "personas", session_dir=root / "interviews",
                facilitator_provider=facilitator, persona_provider=ObserverPersonaFixture(),
                quality_provider=ObserverQualityFixture(),
            )
            _, session = runtime.start(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Test a cause.", interview_mode="validate_hypothesis",
                hypothesis="Unclear ownership causes repeated checking.",
            )
            self.assertEqual(
                session.pending_facilitator_decision["message_to_persona"],
                "嗰次住宿、車票同接送最後分別係邊個處理？",
            )
            self.assertEqual(session.facilitator_decisions[0]["decision_status"], "rejected_by_evidence_gate")
            self.assertIn("Reconstruct actions first", facilitator.calls[1]["user_prompt"])

    def test_failed_llm_operation_is_persisted_and_retryable_without_rules_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = self._library(root)
            facilitator = FailOnceFacilitator()
            runtime = ObserverControlledInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=facilitator,
                persona_provider=ObserverPersonaFixture(),
                quality_provider=ObserverQualityFixture(),
            )
            _, session = runtime.start(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Understand trip replanning friction.",
            )
            self.assertEqual(session.status, "failed")
            self.assertEqual(session.failed_operation, "request_initial_question")
            self.assertFalse(session.pending_facilitator_decision)

            session = runtime.retry(session.interview_id)
            self.assertEqual(session.status, "awaiting_observer")
            self.assertEqual(session.pending_facilitator_decision["message_to_persona"], "Describe the last disrupted trip.")
            persisted = read_json(root / "interviews" / session.interview_id / "interview.json")
            self.assertEqual(persisted["failed_operation"], "")

    def test_observer_extends_past_soft_limit_until_coverage_is_met(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = self._library(root)
            runtime = ObserverControlledInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=CoverageAwareFacilitator(),
                persona_provider=CoverageAwarePersonaFixture(),
                quality_provider=ObserverQualityFixture(),
            )
            _, session = runtime.start(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Understand trip replanning friction.",
                soft_turn_limit=1,
                hard_turn_limit=4,
            )
            self.assertFalse(session.coverage_status["coverage_complete"])
            session = runtime.continue_interview(session.interview_id)
            self.assertEqual(len(session.exchanges), 1)
            self.assertEqual(session.status, "awaiting_observer")
            self.assertEqual(session.stop_reason, "")
            self.assertIn("participant_cause", session.coverage_status["missing"])

            session = runtime.continue_interview(session.interview_id)
            self.assertEqual(len(session.exchanges), 2)
            self.assertEqual(session.status, "awaiting_observer")
            self.assertIn("consequence", session.coverage_status["missing"])

            session = runtime.continue_interview(session.interview_id)
            self.assertEqual(len(session.exchanges), 3)
            self.assertEqual(session.status, "completed")
            self.assertEqual(session.stop_reason, "soft_turn_limit_with_required_coverage_met")
            self.assertTrue(session.coverage_status["coverage_complete"])

    def test_quality_contract_rejects_warn_with_perfect_overall_score(self):
        payload = quality_payload()
        payload["scores"]["overall"] = 5
        payload["findings"][0]["severity"] = "high"
        with self.assertRaisesRegex(ValueError, "overall <= 4"):
            validate_quality_evaluation(payload)

    def test_quality_contract_requires_actionable_hints_for_warn(self):
        payload = quality_payload()
        payload["improvement_hints"] = {
            "next_interview_focus": [],
            "coverage_gap_actions": [],
            "prompt_adjustments": [],
            "turn_budget_guidance": "No change.",
        }
        with self.assertRaisesRegex(ValueError, "actionable improvement hint"):
            validate_quality_evaluation(payload)

    def test_quality_normalizer_demotes_high_severity_inconsistent_overall(self):
        payload = quality_payload()
        payload["overall_verdict"] = "pass"
        payload["scores"]["overall"] = 5
        payload["findings"][0]["severity"] = "high"

        normalized = normalize_quality_evaluation(payload)

        self.assertEqual(normalized["overall_verdict"], "warn")
        self.assertEqual(normalized["scores"]["overall"], 3)
        validate_quality_evaluation(normalized)

    def test_audit_feedback_normalizer_blocks_project_specific_rules(self):
        payload = facilitator_audit_feedback_payload()
        payload["prompt_adjustments"][0]["text"] = "If a Hong Kong retail bank customer mentions MPF overlap, ask about Aladdin report confusion."
        payload["carry_forward_rules"][0]["rule"] = "When reviewing an Aladdin portfolio health check, ask what RM explanation was missing."

        normalized = normalize_facilitator_audit_feedback(payload)

        self.assertFalse(normalized["applies_to"]["safe_for_global_reuse"])
        self.assertEqual(normalized["prompt_adjustments"], [])
        self.assertEqual(normalized["carry_forward_rules"], [])
        self.assertEqual(len(normalized["blocked_feedback"]), 2)
        validate_facilitator_audit_feedback(normalized)


if __name__ == "__main__":
    unittest.main()
