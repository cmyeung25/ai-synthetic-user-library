import tempfile
import unittest
import io
import json
import base64
import sqlite3
from contextlib import redirect_stderr
from contextlib import closing
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
from ai_validation_swarm.providers.openai_client import OpenAIProviderConfig, OpenAIProviderError
from ai_validation_swarm.storage.files import read_json, save_persona


_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO6p8s8AAAAASUVORK5CYII="
)


def _write_png(path: Path) -> Path:
    path.write_bytes(_PNG_1X1)
    return path


def _write_flow_bundle(root: Path) -> Path:
    bundle = root / "prototype-flow"
    bundle.mkdir(parents=True, exist_ok=True)
    _write_png(bundle / "01_start.png")
    _write_png(bundle / "02_review.png")
    _write_png(bundle / "03_confirm.png")
    return bundle


def _write_observed_action_trace(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "trace_version": "observed-action-trace/v1",
                "trace_label": "prototype-review-replay",
                "task_outcome": "partial_success",
                "summary": "The participant reviewed the summary, opened supporting evidence, and stopped at the permission request.",
                "first_error": "The permission scope felt too broad before value was proven.",
                "drop_off_point": "permission request modal",
                "completion_notes": "The task ended before the final confirmation step.",
                "missing_signals": [
                    "No dwell-time telemetry was captured.",
                    "No cursor path was captured.",
                ],
                "actions": [
                    {
                        "step": 1,
                        "action": "open_summary",
                        "target": "summary panel",
                        "screen": "review workspace",
                        "result": "success",
                        "note": "Started with the top-line recommendation.",
                    },
                    {
                        "step": 2,
                        "action": "open_evidence",
                        "target": "evidence drawer",
                        "screen": "review workspace",
                        "result": "success",
                    },
                    {
                        "step": 3,
                        "action": "dismiss_flow",
                        "target": "permission request modal",
                        "screen": "permission modal",
                        "result": "stopped",
                        "note": "Broad access concern blocked completion.",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _write_clickable_prototype_manifest(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "prototype_label": "Evidence Review Clickable Prototype",
                "trace_label": "clickable-prototype-task-loop",
                "start_screen": "review_workspace",
                "screens": [
                    {
                        "id": "review_workspace",
                        "label": "Review Workspace",
                        "actions": [
                            {
                                "id": "open_summary",
                                "action": "open_summary",
                                "target": "summary panel",
                                "next_screen": "review_workspace",
                                "result": "success",
                            },
                            {
                                "id": "open_evidence",
                                "action": "open_evidence",
                                "target": "evidence drawer",
                                "next_screen": "evidence_drawer",
                                "result": "success",
                            },
                        ],
                    },
                    {
                        "id": "evidence_drawer",
                        "label": "Evidence Drawer",
                        "actions": [
                            {
                                "id": "request_permission",
                                "action": "request_permission",
                                "target": "permission request modal",
                                "next_screen": "permission_modal",
                                "result": "stopped",
                                "note": "Permission scope felt too broad before value was proven.",
                                "terminal": True,
                            }
                        ],
                    },
                    {
                        "id": "permission_modal",
                        "label": "Permission Modal",
                        "actions": [
                            {
                                "id": "close_modal",
                                "action": "close_modal",
                                "target": "permission request modal",
                                "next_screen": "review_workspace",
                                "result": "backtrack",
                            }
                        ],
                    },
                ],
                "task_script": [
                    "open_summary",
                    {"action_id": "open_evidence", "note": "Inspect supporting evidence before acting."},
                    {"action_id": "request_permission", "expect_result": "stopped"},
                ],
                "missing_signals": [
                    "No dwell-time telemetry was captured.",
                    "No cursor path was captured.",
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _write_browser_behavior_trace(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "trace_version": "browser-behavior-trace/v1",
                "prototype_label": "Hosted Evidence Workspace",
                "trace_label": "hosted-browser-review-run",
                "driver": "playwright",
                "session": {
                    "start_url": "http://127.0.0.1:4173/prototype.html",
                    "final_url": "http://127.0.0.1:4173/prototype.html#evidence",
                    "viewport": {"width": 1280, "height": 800},
                },
                "events": [
                    {
                        "type": "navigation",
                        "url": "http://127.0.0.1:4173/prototype.html",
                        "page_title": "Prototype",
                        "timestamp_ms": 0,
                    },
                    {
                        "type": "click",
                        "selector": "[data-action='open-summary']",
                        "target": "summary panel",
                        "page_title": "Review Workspace",
                        "timestamp_ms": 240,
                    },
                    {
                        "type": "click",
                        "selector": "[data-action='open-evidence']",
                        "target": "evidence drawer",
                        "page_title": "Review Workspace",
                        "timestamp_ms": 700,
                        "duration_ms": 60,
                    },
                    {
                        "type": "click",
                        "selector": "[data-action='confirm-review']",
                        "target": "confirm review button",
                        "page_title": "Evidence Drawer",
                        "timestamp_ms": 1210,
                        "result": "success",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


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

    def synthesize_prototype(self, **kwargs):
        self.calls.append(("synthesize_prototype", kwargs))
        return ({
            "stimulus_interpretation": {
                "summary": "The participant reads the screen as a guided review workspace.",
                "supporting_quotes": [{"quote": "I would look for the summary first.", "evidence_ref": "exchange_1.persona"}],
                "interpretation_breakdowns": ["The participant is unsure whether the system is analyzing or merely displaying imported material."],
                "trust_signals": ["Traceable evidence links would increase trust."],
            },
            "task_journey": {
                "first_action_expectations": ["Open the evidence summary before changing anything."],
                "expected_path": ["Read summary", "check linked evidence", "decide whether to act"],
                "setup_confusions": ["Unclear whether source material must be cleaned before upload."],
                "likely_drop_off_points": ["The participant would stop if the system asks for broad permissions too early."],
                "task_success_signals": ["A concrete, inspectable recommendation tied to evidence."],
            },
            "behavioral_evidence_boundary": {
                "evidence_level": "task_guided_self_report",
                "observed_action_available": False,
                "what_was_observed": ["Stimulus interpretation and expected task path were discussed."],
                "missing_observed_signals": ["No real clicks or task traces were recorded."],
            },
            "assumption_validation": [{
                "assumption": "The participant will understand the workspace immediately.",
                "status": "weakened",
                "evidence_refs": ["exchange_1.persona", "exchange_2.persona"],
                "rationale": "The participant could describe the page, but still held key interpretation uncertainty.",
            }],
            "key_insights": [
                "Because the participant looks for evidence traceability first, they would inspect links before acting, unless trust is already established. This means the prototype should foreground evidence lineage.",
                "Because setup expectations are still ambiguous, the participant would delay serious use, unless import and cleanup requirements become obvious. This means the prototype should make preparation cost legible.",
                "Because broad access feels risky, the participant would stop early, unless the prototype explains permission scope before asking for it. This means the prototype should narrow permissions and explain why they are needed.",
            ],
            "next_experiment": "Run the same task with a real screenshot and record the actual first click.",
            "evidence_gaps": ["No observed action trace was collected."],
            "synthetic_only_disclaimer": "Synthetic prototype-validation evidence only; not human usability proof.",
        }, "facilitator-thread-1")

    def review_image_stimulus(self, **kwargs):
        self.calls.append(("review_image_stimulus", kwargs))
        return ({
            "summary": "The screen appears to be an evidence review workspace with a summary panel and linked detail areas.",
            "visible_elements": ["summary section", "linked evidence references", "recommendation area"],
            "primary_action_candidates": ["read the summary", "open the linked evidence"],
            "interpretation_risks": ["It is not fully clear whether the page is recommending action or only organizing inputs."],
            "trust_risks": ["Source boundaries may remain unclear without explicit provenance."],
            "missing_context": ["The import or preparation requirement is not visible."],
            "task_relevance": "The screen plausibly supports reviewing one recommendation before taking action.",
            "evidence_boundary": "Static image review only. No click or navigation trace is available.",
        }, "stimulus-review-thread-1")

    def review_flow_stimulus(self, **kwargs):
        self.calls.append(("review_flow_stimulus", kwargs))
        return ({
            "summary": "The flow appears to move from summary to evidence inspection to a decision checkpoint.",
            "screen_sequence": ["start summary", "review evidence", "confirm action"],
            "primary_action_candidates": ["read the summary", "inspect evidence", "decide whether to act"],
            "transition_confusions": ["The handoff from review to final decision may feel abrupt."],
            "setup_burdens": ["The flow does not show what preparation is needed before the first screen."],
            "likely_drop_off_points": ["The participant may stop if the recommendation still feels under-explained by the final screen."],
            "trust_risks": ["Trust depends on whether evidence lineage remains visible across screens."],
            "missing_context": ["The source-import step remains off-screen."],
            "task_relevance": "The flow plausibly supports reviewing one recommendation through to a decision checkpoint.",
            "evidence_boundary": "Multi-screen flow review only. No click, navigation timing, or completion trace is available.",
        }, "facilitator-flow-thread-1")


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


class PainPointDiscoveryFacilitator:
    provider_name = "pain-point"
    model_name = "pain-point/v1"

    def __init__(self):
        self.calls = []
        self.decisions = [
            FacilitatorDecision(
                interview_phase="recent_event",
                probing_strategy="critical_incident",
                decision_rationale="Anchor discovery in one recent concrete event.",
                message_to_persona="Tell me about the last time this finance task became annoying enough to notice.",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What exactly happened in that moment?"],
                should_end=False,
                end_reason="",
                provider_session_id="pain-point-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="problem_reality",
                probing_strategy="problem_reality_probe",
                decision_rationale="Confirm whether the problem was materially real in the event.",
                message_to_persona="What made that moment a real problem instead of a small inconvenience?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What consequence made it matter?"],
                should_end=False,
                end_reason="",
                provider_session_id="pain-point-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="frequency_probe",
                probing_strategy="frequency_probe",
                decision_rationale="Establish recurrence before deeper why-analysis.",
                message_to_persona="How often does that kind of finance mess happen for you now?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["Is this occasional or recurring?"],
                should_end=False,
                end_reason="",
                provider_session_id="pain-point-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="consequence_probe",
                probing_strategy="consequence_probe",
                decision_rationale="Get the actual cost or avoided failure.",
                message_to_persona="What consequence does it create when that happens?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What does it cost in time, money, or confidence?"],
                should_end=False,
                end_reason="",
                provider_session_id="pain-point-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="current_workaround",
                probing_strategy="workaround_probe",
                decision_rationale="Capture the existing workaround before synthesis.",
                message_to_persona="What do you do today to work around it when it shows up?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What are they already doing to cope?"],
                should_end=False,
                end_reason="",
                provider_session_id="pain-point-thread-1",
            ),
        ]

    def next_turn(self, **kwargs):
        self.calls.append(("next_turn", kwargs))
        return self.decisions.pop(0)

    def synthesize(self, **kwargs):
        self.calls.append(("synthesize", kwargs))
        return ({
            "executive_summary": "The finance problem is recurring enough to create manual tracking overhead.",
            "insights": [{
                "insight": "The participant tolerates the task until it threatens monthly reconciliation confidence.",
                "evidence_refs": ["exchange_2.persona", "exchange_4.persona", "exchange_5.persona"],
                "confidence": "medium",
                "implication": "Problem discovery should focus on reconciliation confidence, not only speed.",
            }],
            "needs": ["Keep monthly money tracking accurate without rebuilding the record from scratch."],
            "root_cause_hypotheses": [],
            "contradictions": [],
            "pov_statements": [
                "A busy participant tracking household spending needs a lighter way to keep the record accurate because month-end reconstruction creates confidence drag."
            ],
            "how_might_we_questions": ["How might we reduce month-end reconstruction without weakening trust in the numbers?"],
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
            "evidence_gaps": ["Human interviews are still needed to validate prevalence."],
            "recommended_human_validation": ["Interview people right after a real monthly reconciliation cycle."],
            "synthetic_only_disclaimer": "Synthetic-user interview for AI pre-validation only; not human market evidence.",
        }, "pain-point-thread-1")


class PainPointDiscoveryPersona:
    provider_name = "pain-point"
    model_name = "pain-point-persona/v1"

    def __init__(self):
        self.responses = [
            "At month end I had to rebuild my spending notes because two transfers were missing from my rough record.",
            "It stopped being a small thing because I could not tell whether the budget number I was using was still safe.",
            "A lighter version happens most weeks, but the bad version shows up at least once most months.",
            "It usually costs me half an hour and makes me delay other decisions until I trust the number again.",
            "I keep notes in my phone and mark anything uncertain so I can double-check it later.",
        ]

    def respond(self, **kwargs):
        return ChatResult(
            reply=self.responses.pop(0),
            intent_level="unclear",
            confidence="high",
            provider_session_id="pain-point-persona-thread-1",
        )

    def generate_persona_driver_trace(self, **kwargs):
        return type("TraceResult", (), {
            "payload": {
                "synthetic_only_disclaimer": "Synthetic persona post-interview reflection only; not human market evidence.",
                "surface_read": {
                    "what_the_persona_explicitly_said": [
                        "They rebuild the spending record when uncertain transfers appear.",
                    ],
                    "what_they_seemed_to_optimize_for": "Confidence in the final monthly number.",
                    "what_stayed_implicit": [
                        "Whether the current workaround fails more often under higher life-load conditions.",
                    ],
                },
                "likely_drivers": [{
                    "driver": "Protect decision confidence before acting on the number",
                    "driver_type": "decision_style",
                    "why_it_matters_here": "The participant accepts extra effort when confidence in the total is at risk.",
                    "evidence_refs": ["exchange_2.persona", "exchange_4.persona"],
                    "profile_source_refs": ["values.core_values"],
                    "confidence": "medium",
                    "observed_vs_inferred": "mixed",
                }],
                "unspoken_constraints": [],
                "value_tensions": [],
                "missed_follow_up_questions": [],
            },
            "provider_session_id": "pain-point-trace-thread-1",
        })()


class DecisionReconstructionFacilitator:
    provider_name = "decision-reconstruction"
    model_name = "decision-reconstruction/v1"

    def __init__(self):
        self.calls = []
        self.decisions = [
            FacilitatorDecision(
                interview_phase="recent_event",
                probing_strategy="decision_event_probe",
                decision_rationale="Anchor the interview in one real recent decision.",
                message_to_persona="Tell me about the last real decision where you had to change course on this.",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["Which exact decision event should we reconstruct?"],
                should_end=False,
                end_reason="",
                provider_session_id="decision-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="missing_evidence_probe",
                probing_strategy="missing_evidence_probe",
                decision_rationale="Reconstruct what was still unknown at decision time.",
                message_to_persona="What evidence was still missing when you had to make that call?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What still felt unknown?"],
                should_end=False,
                end_reason="",
                provider_session_id="decision-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="pressure_probe",
                probing_strategy="pressure_probe",
                decision_rationale="Capture the practical pressure around the decision.",
                message_to_persona="What stakeholder or time pressure made waiting costly there?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["Why couldn't they just wait?"],
                should_end=False,
                end_reason="",
                provider_session_id="decision-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="defensibility_probe",
                probing_strategy="defensibility_probe",
                decision_rationale="Separate what felt publicly defensible from private uncertainty.",
                message_to_persona="What could you defend publicly in that decision, and what still felt shaky privately?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What was publicly defensible versus privately uncertain?"],
                should_end=False,
                end_reason="",
                provider_session_id="decision-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="decision_outcome_probe",
                probing_strategy="decision_outcome_probe",
                decision_rationale="Close the reconstruction with the actual change made.",
                message_to_persona="What did you actually change in scope, sequence, priority, or go-no-go at the end?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What really changed at the end?"],
                should_end=False,
                end_reason="",
                provider_session_id="decision-thread-1",
            ),
        ]

    def next_turn(self, **kwargs):
        self.calls.append(("next_turn", kwargs))
        return self.decisions.pop(0)

    def synthesize(self, **kwargs):
        self.calls.append(("synthesize", kwargs))
        return ({
            "executive_summary": "The decision changed under delivery pressure before the evidence picture felt complete.",
            "insights": [{
                "insight": "The participant made a narrower launch decision because time pressure beat evidential comfort.",
                "evidence_refs": ["exchange_2.persona", "exchange_3.persona", "exchange_5.persona"],
                "confidence": "medium",
                "implication": "Decision reconstruction should stay focused on the pressure-evidence tradeoff, not only the final outcome.",
            }],
            "needs": ["Make scope decisions with less hidden uncertainty when time pressure is high."],
            "root_cause_hypotheses": [],
            "contradictions": [],
            "pov_statements": [
                "A pressured decision-maker needs enough evidence to narrow scope confidently because delivery pressure often forces action before certainty arrives."
            ],
            "how_might_we_questions": ["How might we make scope-narrowing decisions easier when evidence is incomplete but waiting is costly?"],
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
            "evidence_gaps": ["Human interviews are still needed to validate how common this pressure-evidence tradeoff is."],
            "recommended_human_validation": ["Interview teams immediately after a real scope or go/no-go decision."],
            "synthetic_only_disclaimer": "Synthetic-user interview for AI pre-validation only; not human market evidence.",
        }, "decision-thread-1")


class DecisionReconstructionPersona:
    provider_name = "decision-reconstruction"
    model_name = "decision-reconstruction-persona/v1"

    def __init__(self):
        self.responses = [
            "Last week we had to decide whether to cut a reporting step from the first release because onboarding was slipping.",
            "We still lacked enough examples to know whether people were confused by the current step or just slow that day.",
            "Product wanted a decision before the Friday review because engineering had already blocked the next sprint around it.",
            "I could defend simplifying the first release, but privately I was not sure whether we were cutting the right thing.",
            "We delayed the reporting step and shipped the simpler onboarding path first.",
        ]

    def respond(self, **kwargs):
        return ChatResult(
            reply=self.responses.pop(0),
            intent_level="unclear",
            confidence="high",
            provider_session_id="decision-persona-thread-1",
        )

    def generate_persona_driver_trace(self, **kwargs):
        return type("TraceResult", (), {
            "payload": {
                "synthetic_only_disclaimer": "Synthetic persona post-interview reflection only; not human market evidence.",
                "surface_read": {
                    "what_the_persona_explicitly_said": [
                        "They narrowed the first release because evidence stayed incomplete under time pressure.",
                    ],
                    "what_they_seemed_to_optimize_for": "A defensible shipping decision under delivery pressure.",
                    "what_stayed_implicit": [
                        "How often the same evidence-pressure tradeoff appears across similar launches.",
                    ],
                },
                "likely_drivers": [{
                    "driver": "Preserve decision defensibility when certainty is unavailable",
                    "driver_type": "decision_style",
                    "why_it_matters_here": "The participant accepted narrower scope to keep the release decision publicly defensible.",
                    "evidence_refs": ["exchange_3.persona", "exchange_4.persona", "exchange_5.persona"],
                    "profile_source_refs": ["values.core_values"],
                    "confidence": "medium",
                    "observed_vs_inferred": "mixed",
                }],
                "unspoken_constraints": [],
                "value_tensions": [],
                "missed_follow_up_questions": [],
            },
            "provider_session_id": "decision-trace-thread-1",
        })()


class AdoptionBarrierValidationFacilitator:
    provider_name = "adoption-barrier"
    model_name = "adoption-barrier/v1"

    def __init__(self):
        self.calls = []
        self.decisions = [
            FacilitatorDecision(
                interview_phase="recent_event",
                probing_strategy="critical_incident",
                decision_rationale="Start from one recent real behavior before testing adoption barriers.",
                message_to_persona="Tell me about the last time you seriously considered changing how you handle this job.",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What made this a live consideration?"],
                should_end=False,
                end_reason="",
                provider_session_id="adoption-barrier-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="current_workaround",
                probing_strategy="current_workaround_probe",
                decision_rationale="Capture the status-quo path before asking why adoption still fails.",
                message_to_persona="What do you do today instead when you need to handle it?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What is the workaround already protecting?"],
                should_end=False,
                end_reason="",
                provider_session_id="adoption-barrier-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="setup_burden",
                probing_strategy="setup_burden_probe",
                decision_rationale="Test the setup threshold for real use.",
                message_to_persona="What setup or onboarding would already feel like too much before you would really use it?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["Where does activation effort become too heavy?"],
                should_end=False,
                end_reason="",
                provider_session_id="adoption-barrier-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="permission_boundary",
                probing_strategy="permission_boundary_probe",
                decision_rationale="Surface access and approval friction.",
                message_to_persona="What access, approval, or coordination would make trying it difficult?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What has to be unlocked before trial?"],
                should_end=False,
                end_reason="",
                provider_session_id="adoption-barrier-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="trust_boundary",
                probing_strategy="trust_boundary_probe",
                decision_rationale="Adoption needs a trust threshold, not just curiosity.",
                message_to_persona="What would you need to trust before letting it influence a real decision?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What proof would make reliance feel safe?"],
                should_end=False,
                end_reason="",
                provider_session_id="adoption-barrier-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="pricing_condition",
                probing_strategy="pricing_condition_probe",
                decision_rationale="Identify the budget condition for adoption.",
                message_to_persona="What would have to be true on price or budget for it to feel worth adopting?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["When does the value feel defensible enough to pay for?"],
                should_end=False,
                end_reason="",
                provider_session_id="adoption-barrier-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="reversibility_probe",
                probing_strategy="reversibility_probe",
                decision_rationale="Probe how easy it must be to back out.",
                message_to_persona="How reversible would it need to feel if it turned out not to work?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What kind of exit path would still feel safe enough?"],
                should_end=False,
                end_reason="",
                provider_session_id="adoption-barrier-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="workflow_burden",
                probing_strategy="workflow_burden_probe",
                decision_rationale="Separate usefulness from routine burden.",
                message_to_persona="What extra step or routine burden would still make you drop it even if the value sounds good?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What would stop it from becoming a habit?"],
                should_end=False,
                end_reason="",
                provider_session_id="adoption-barrier-thread-1",
            ),
        ]

    def next_turn(self, **kwargs):
        self.calls.append(("next_turn", kwargs))
        return self.decisions.pop(0)

    def synthesize(self, **kwargs):
        self.calls.append(("synthesize", kwargs))
        return ({
            "executive_summary": "The concept sounds useful, but adoption depends on low setup, clear permissions, and easy reversal.",
            "insights": [{
                "insight": "The participant will tolerate evaluation work, but not a new routine that adds coordination or lock-in risk.",
                "evidence_refs": ["exchange_3.persona", "exchange_4.persona", "exchange_7.persona", "exchange_8.persona"],
                "confidence": "medium",
                "implication": "Adoption testing should focus on activation, trust, and reversibility before pricing optimization.",
            }],
            "needs": ["A useful tool still needs low-friction setup and a safe exit before it can enter routine use."],
            "root_cause_hypotheses": [],
            "contradictions": [],
            "pov_statements": [
                "A cautious operator considering a new workflow tool needs lightweight setup and a reversible trial path because added routine burden feels riskier than missing one more insight."
            ],
            "how_might_we_questions": ["How might we make first use and exit feel light enough that a useful tool can actually become routine?"],
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
            "evidence_gaps": ["Human interviews are still needed to validate which barriers dominate across real segments."],
            "recommended_human_validation": ["Run adoption-friction interviews with people immediately after they trial a comparable workflow tool."],
            "synthetic_only_disclaimer": "Synthetic-user interview for AI pre-validation only; not human market evidence.",
        }, "adoption-barrier-thread-1")


class AdoptionBarrierValidationPersona:
    provider_name = "adoption-barrier"
    model_name = "adoption-barrier-persona/v1"

    def __init__(self):
        self.responses = [
            "Last month I looked at a new research workflow tool because our manual notes were getting messy across decisions.",
            "Right now I keep a spreadsheet and chat notes because I can inspect everything myself and back out quickly.",
            "If setup takes more than one serious session or needs too much cleanup before first value, I already know I will delay it.",
            "I would need permission to connect client material, and I would hesitate if another teammate had to keep approving every step.",
            "Before trusting it, I would need to see where its claims came from and what it still could not know.",
            "Paying only makes sense if it clearly replaces a real review step, not if it just adds another dashboard.",
            "I would want to turn it off cleanly and keep my existing notes if it started giving shaky output.",
            "If I still have to re-enter context or double-check everything every week, it will never become part of my routine.",
        ]

    def respond(self, **kwargs):
        return ChatResult(
            reply=self.responses.pop(0),
            intent_level="unclear",
            confidence="high",
            provider_session_id="adoption-barrier-persona-thread-1",
        )

    def generate_persona_driver_trace(self, **kwargs):
        return type("TraceResult", (), {
            "payload": {
                "synthetic_only_disclaimer": "Synthetic persona post-interview reflection only; not human market evidence.",
                "surface_read": {
                    "what_the_persona_explicitly_said": [
                        "They stay with spreadsheet and chat notes because the current path is inspectable and easy to reverse.",
                    ],
                    "what_they_seemed_to_optimize_for": "Low-lock-in workflow control.",
                    "what_stayed_implicit": [
                        "How much prior tool disappointment increased their demand for reversibility.",
                    ],
                },
                "likely_drivers": [{
                    "driver": "Preserve workflow control while lowering review effort",
                    "driver_type": "trust_pattern",
                    "why_it_matters_here": "The participant wants value, but only if trust and reversibility stay under their control.",
                    "evidence_refs": ["exchange_2.persona", "exchange_5.persona", "exchange_7.persona", "exchange_8.persona"],
                    "profile_source_refs": ["values.core_values"],
                    "confidence": "medium",
                    "observed_vs_inferred": "mixed",
                }],
                "unspoken_constraints": [],
                "value_tensions": [],
                "missed_follow_up_questions": [],
            },
            "provider_session_id": "adoption-barrier-trace-thread-1",
        })()


class PrototypeValidationFacilitator:
    provider_name = "prototype-validation"
    model_name = "prototype-validation/v1"

    def __init__(self):
        self.calls = []
        self.decisions = [
            FacilitatorDecision(
                interview_phase="stimulus_interpretation",
                probing_strategy="stimulus_interpretation_probe",
                decision_rationale="Start by learning what the participant thinks the screen is doing.",
                message_to_persona="Looking at this prototype, what do you think it is trying to help you do?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["How are they reading the stimulus?"],
                should_end=False,
                end_reason="",
                provider_session_id="prototype-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="first_action_expectation",
                probing_strategy="first_action_probe",
                decision_rationale="Prototype validation needs the expected first move.",
                message_to_persona="If you were doing that task now, what would you try first?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What is their first action expectation?"],
                should_end=False,
                end_reason="",
                provider_session_id="prototype-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="task_path_expectation",
                probing_strategy="task_path_probe",
                decision_rationale="Reconstruct the expected task path before judging the interface.",
                message_to_persona="After that first step, how would you expect the rest of the task to unfold?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What path do they expect through the prototype?"],
                should_end=False,
                end_reason="",
                provider_session_id="prototype-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="setup_confusion",
                probing_strategy="setup_confusion_probe",
                decision_rationale="Surface onboarding or input ambiguity early.",
                message_to_persona="Where would setup or required input start feeling unclear here?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What setup ambiguity appears before task value?"],
                should_end=False,
                end_reason="",
                provider_session_id="prototype-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="trust_boundary",
                probing_strategy="trust_boundary_probe",
                decision_rationale="Prototype use still depends on trust during the task.",
                message_to_persona="What would make you trust or distrust this enough to use it for a real decision?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What trust threshold exists inside the task?"],
                should_end=False,
                end_reason="",
                provider_session_id="prototype-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="breakdown_or_dropoff",
                probing_strategy="dropoff_probe",
                decision_rationale="Capture the first real hesitation or abandonment point.",
                message_to_persona="Where would you hesitate or stop if this were a real attempt?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What is the most likely drop-off point?"],
                should_end=False,
                end_reason="",
                provider_session_id="prototype-thread-1",
            ),
            FacilitatorDecision(
                interview_phase="task_completion_signal",
                probing_strategy="completion_signal_probe",
                decision_rationale="Need the participant's definition of task success.",
                message_to_persona="What result would tell you that the task actually worked here?",
                evidence_updates=[],
                root_cause_hypotheses=[],
                open_questions=["What success signal would they rely on?"],
                should_end=False,
                end_reason="",
                provider_session_id="prototype-thread-1",
            ),
        ]

    def next_turn(self, **kwargs):
        self.calls.append(("next_turn", kwargs))
        return self.decisions.pop(0)

    def synthesize_prototype(self, **kwargs):
        self.calls.append(("synthesize_prototype", kwargs))
        return ({
            "stimulus_interpretation": {
                "summary": "The participant sees the screen as an evidence review workspace, but not yet a fully trusted decision tool.",
                "supporting_quotes": [{"quote": "I would look for the summary first.", "evidence_ref": "exchange_1.persona"}],
                "interpretation_breakdowns": ["It is unclear whether the workspace is suggesting action or just organizing evidence."],
                "trust_signals": ["Linked evidence and visible source boundaries would increase trust."],
            },
            "task_journey": {
                "first_action_expectations": ["Read the summary before changing anything."],
                "expected_path": ["Read the summary", "check the linked evidence", "decide whether to act"],
                "setup_confusions": ["The participant is unsure how much cleanup is needed before import."],
                "likely_drop_off_points": ["They would stop if permissions become broad before value is visible."],
                "task_success_signals": ["A clear recommendation backed by inspectable evidence."],
            },
            "behavioral_evidence_boundary": {
                "evidence_level": "task_guided_self_report",
                "observed_action_available": False,
                "what_was_observed": ["Stimulus interpretation and expected task path were discussed."],
                "missing_observed_signals": ["No actual clicks or backtracking were observed."],
            },
            "assumption_validation": [{
                "assumption": "The participant will immediately understand what the workspace is doing.",
                "status": "weakened",
                "evidence_refs": ["exchange_1.persona", "exchange_3.persona"],
                "rationale": "They can read the page directionally, but still expect ambiguity in how the task unfolds.",
            }],
            "key_insights": [
                "Because the participant looks for traceable evidence first, they would inspect the summary before acting, unless trust is already earned. This means the prototype should foreground evidence lineage.",
                "Because setup expectations are still unclear, the participant would delay serious use, unless input requirements become obvious. This means the prototype should make preparation cost legible.",
                "Because broad permissions feel risky before value appears, the participant would stop early, unless access scope stays narrow and explicit. This means the prototype should explain permission scope before asking for it.",
            ],
            "next_experiment": "Replay the same task against a real screenshot and capture the actual first click and first hesitation.",
            "evidence_gaps": ["No observed action trace was collected."],
            "synthetic_only_disclaimer": "Synthetic prototype-validation evidence only; not human usability proof.",
        }, "prototype-thread-1")

    def review_image_stimulus(self, **kwargs):
        self.calls.append(("review_image_stimulus", kwargs))
        return ({
            "summary": "The static screen looks like a review workspace that pairs a recommendation with inspectable evidence.",
            "visible_elements": ["summary area", "evidence links", "recommendation output"],
            "primary_action_candidates": ["read the summary", "inspect a linked source"],
            "interpretation_risks": ["It may be unclear whether the output is advisory or final."],
            "trust_risks": ["Trust depends on whether source lineage is visible."],
            "missing_context": ["The preparation or import step is not visible."],
            "task_relevance": "The screen appears relevant to reviewing a recommendation before acting on it.",
            "evidence_boundary": "Static image review only. No click or navigation trace is available.",
        }, "prototype-stimulus-thread-1")

    def review_flow_stimulus(self, **kwargs):
        self.calls.append(("review_flow_stimulus", kwargs))
        return ({
            "summary": "The flow looks like a guided review sequence from summary to evidence to decision.",
            "screen_sequence": ["screen 1 summary", "screen 2 evidence review", "screen 3 action checkpoint"],
            "primary_action_candidates": ["scan the summary", "open the evidence", "make a decision"],
            "transition_confusions": ["The move into the final checkpoint may feel too sudden without explicit status feedback."],
            "setup_burdens": ["The flow still hides the preparation or import requirement."],
            "likely_drop_off_points": ["Confidence may break before the final decision if the evidence remains too abstract."],
            "trust_risks": ["Trust depends on visible provenance across screens."],
            "missing_context": ["No screen shows where the input data came from."],
            "task_relevance": "The flow appears relevant to reviewing one recommendation before action.",
            "evidence_boundary": "Multi-screen flow review only. No click, navigation timing, or completion trace is available.",
        }, "prototype-flow-thread-1")


class PrototypeValidationPersona:
    provider_name = "prototype-validation"
    model_name = "prototype-validation-persona/v1"

    def __init__(self):
        self.responses = [
            "It looks like a workspace that summarizes evidence and then points me toward what I should review next.",
            "I would open the summary first before I trusted any recommendation.",
            "After that I would inspect the linked evidence, then decide whether the recommendation actually changes anything.",
            "I am not sure whether I need to clean up or tag the source material before this starts being useful.",
            "I would trust it more if I could see exactly where each claim came from and what it might be missing.",
            "I would stop if it asked for broad permissions before showing me anything concrete.",
            "I would count it as working only if the recommendation is specific enough that I can act or deliberately ignore it.",
        ]

    def respond(self, **kwargs):
        return ChatResult(
            reply=self.responses.pop(0),
            intent_level="unclear",
            confidence="high",
            provider_session_id="prototype-persona-thread-1",
        )

    def generate_persona_driver_trace(self, **kwargs):
        return type("TraceResult", (), {
            "payload": {
                "synthetic_only_disclaimer": "Synthetic persona post-interview reflection only; not human market evidence.",
                "surface_read": {
                    "what_the_persona_explicitly_said": [
                        "They would inspect the summary and linked evidence before acting.",
                    ],
                    "what_they_seemed_to_optimize_for": "Inspectability before task commitment.",
                    "what_stayed_implicit": [
                        "How much prior tool disappointment raised their demand for evidence traceability.",
                    ],
                },
                "likely_drivers": [{
                    "driver": "Trust comes from inspectable evidence before action",
                    "driver_type": "trust_pattern",
                    "why_it_matters_here": "The participant wants a recommendation, but only after they can inspect where it came from.",
                    "evidence_refs": ["exchange_2.persona", "exchange_3.persona", "exchange_5.persona"],
                    "profile_source_refs": ["values.core_values"],
                    "confidence": "medium",
                    "observed_vs_inferred": "mixed",
                }],
                "unspoken_constraints": [],
                "value_tensions": [],
                "missed_follow_up_questions": [],
            },
            "provider_session_id": "prototype-trace-thread-1",
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
            run_contract = read_json(output / "run_contract.json")
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
            self.assertTrue((output / "run_contract.json").exists())
            self.assertTrue((output / "insight_report.json").exists())
            self.assertTrue((output / "persona_driver_trace.json").exists())
            self.assertTrue((output / "persona_driver_trace.md").exists())
            self.assertIn("Root-Cause Hypotheses", (output / "insights.md").read_text(encoding="utf-8"))
            driver_trace = read_json(output / "persona_driver_trace.json")
            self.assertEqual(driver_trace["likely_drivers"][0]["driver_type"], "decision_style")
            self.assertEqual(session["persona_driver_trace_provider_session_id"], "persona-trace-thread-1")
            self.assertEqual(session["persona_driver_trace_prompt_version"], "persona-driver-trace/v1")
            self.assertEqual(run_contract["request"]["run_kind"], "facilitated_interview")
            self.assertEqual(run_contract["request"]["entrypoint"], "run-facilitated-interview")
            self.assertEqual(run_contract["request"]["persona_id"], persona.profile.synthetic_user_id)
            self.assertEqual(run_contract["result"]["status"], "completed")
            self.assertIn("insight_report.json", run_contract["result"]["artifact_paths"])
            metadata_db = root / "interviews" / "metadata.sqlite3"
            self.assertTrue(metadata_db.exists())
            with closing(sqlite3.connect(metadata_db)) as connection:
                run_row = connection.execute(
                    "SELECT run_kind, interview_mode, status FROM run_records WHERE run_id = ?",
                    (session["interview_id"],),
                ).fetchone()
            self.assertEqual(run_row, ("facilitated_interview", "explore_root_cause", "completed"))

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

    def test_prototype_validation_requires_task_and_stimulus_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=78)[0]
            save_persona(persona, root / "personas")
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=RecordedLLMFacilitator(),
                persona_provider=RecordedLLMPersona(),
            )
            with self.assertRaisesRegex(ValueError, "requires a non-empty prototype_task"):
                runtime.run(
                    persona_id=persona.profile.synthetic_user_id,
                    research_goal="Validate a prototype task.",
                    interview_mode="prototype_validation",
                    stimulus_type="image",
                    stimulus_artifact="prototype-review-screen-v1.png",
                )
            with self.assertRaisesRegex(ValueError, "requires a stimulus_artifact or product_context"):
                runtime.run(
                    persona_id=persona.profile.synthetic_user_id,
                    research_goal="Validate a prototype task.",
                    interview_mode="prototype_validation",
                    prototype_task="Review one recommendation and decide whether to act on it.",
                )

    def test_pain_point_discovery_is_first_class_runtime_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=74)[0]
            save_persona(persona, root / "personas")
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=PainPointDiscoveryFacilitator(),
                persona_provider=PainPointDiscoveryPersona(),
            )
            output = runtime.run(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Discover whether monthly finance tracking is a real problem.",
                interview_mode="pain_point_discovery",
                soft_turn_limit=5,
                hard_turn_limit=6,
            )

            session = read_json(output / "interview.json")
            self.assertEqual(session["interview_mode"], "pain_point_discovery")
            self.assertTrue(session["coverage_status"]["coverage_complete"])
            self.assertEqual(session["coverage_status"]["missing"], [])
            self.assertEqual(
                session["coverage_status"]["requirements"],
                ["recent_behaviour", "problem_reality", "frequency", "consequence", "current_workaround"],
            )
            self.assertEqual(session["stop_reason"], "soft_turn_limit_with_required_coverage_met")
            self.assertEqual(
                [item["facilitator_phase"] for item in session["exchanges"]],
                ["recent_event", "problem_reality", "frequency_probe", "consequence_probe", "current_workaround"],
            )
            self.assertIn("Interview mode: pain_point_discovery", (output / "transcript.md").read_text(encoding="utf-8"))
            self.assertTrue((output / "insight_report.json").exists())

    def test_decision_reconstruction_is_first_class_runtime_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=75)[0]
            save_persona(persona, root / "personas")
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=DecisionReconstructionFacilitator(),
                persona_provider=DecisionReconstructionPersona(),
            )
            output = runtime.run(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Reconstruct the last real scope decision.",
                interview_mode="decision_reconstruction",
                soft_turn_limit=5,
                hard_turn_limit=6,
            )

            session = read_json(output / "interview.json")
            self.assertEqual(session["interview_mode"], "decision_reconstruction")
            self.assertTrue(session["coverage_status"]["coverage_complete"])
            self.assertEqual(session["coverage_status"]["missing"], [])
            self.assertEqual(
                session["coverage_status"]["requirements"],
                ["recent_real_decision", "missing_evidence", "pressure", "defensible_vs_uncertain", "decision_change"],
            )
            self.assertEqual(session["stop_reason"], "soft_turn_limit_with_required_coverage_met")
            self.assertEqual(
                [item["facilitator_phase"] for item in session["exchanges"]],
                ["recent_event", "missing_evidence_probe", "pressure_probe", "defensibility_probe", "decision_outcome_probe"],
            )
            self.assertIn("Interview mode: decision_reconstruction", (output / "transcript.md").read_text(encoding="utf-8"))
            self.assertTrue((output / "insight_report.json").exists())

    def test_adoption_barrier_validation_is_first_class_runtime_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=76)[0]
            save_persona(persona, root / "personas")
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=AdoptionBarrierValidationFacilitator(),
                persona_provider=AdoptionBarrierValidationPersona(),
            )
            output = runtime.run(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Understand why a useful workflow tool still might not be adopted.",
                interview_mode="adoption_barrier_validation",
                soft_turn_limit=8,
                hard_turn_limit=9,
            )

            session = read_json(output / "interview.json")
            self.assertEqual(session["interview_mode"], "adoption_barrier_validation")
            self.assertTrue(session["coverage_status"]["coverage_complete"])
            self.assertEqual(session["coverage_status"]["missing"], [])
            self.assertEqual(
                session["coverage_status"]["requirements"],
                [
                    "recent_behaviour",
                    "current_workaround",
                    "setup_burden",
                    "permission_boundary",
                    "trust_boundary",
                    "pricing_condition",
                    "reversibility",
                    "workflow_burden",
                ],
            )
            self.assertTrue(session["coverage_status"]["adoption_intro_allowed"])
            self.assertEqual(session["stop_reason"], "soft_turn_limit_with_required_coverage_met")
            self.assertEqual(
                [item["facilitator_phase"] for item in session["exchanges"]],
                [
                    "recent_event",
                    "current_workaround",
                    "setup_burden",
                    "permission_boundary",
                    "trust_boundary",
                    "pricing_condition",
                    "reversibility_probe",
                    "workflow_burden",
                ],
            )
            self.assertIn("Interview mode: adoption_barrier_validation", (output / "transcript.md").read_text(encoding="utf-8"))
            self.assertTrue((output / "insight_report.json").exists())

    def test_prototype_validation_uses_prototype_synthesis_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=77)[0]
            save_persona(persona, root / "personas")
            provider = PrototypeValidationFacilitator()
            artifact = _write_png(root / "prototype-review-screen-v1.png")
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=provider,
                persona_provider=PrototypeValidationPersona(),
            )
            output = runtime.run(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Validate whether the evidence-review prototype supports a concrete review task.",
                interview_mode="prototype_validation",
                product_context="A workspace that summarizes evidence and links back to the source material.",
                stimulus_type="image",
                stimulus_artifact=str(artifact),
                prototype_task="Review one recommendation and decide whether to act on it.",
                soft_turn_limit=7,
                hard_turn_limit=8,
            )

            session = read_json(output / "interview.json")
            report = read_json(output / "insight_report.json")
            self.assertEqual(session["interview_mode"], "prototype_validation")
            self.assertEqual(session["synthesis_prompt_version"], "prototype-synthesis/v1")
            self.assertEqual(session["stimulus_type"], "image")
            self.assertEqual(session["stimulus_artifact"], str(artifact))
            self.assertEqual(session["prototype_task"], "Review one recommendation and decide whether to act on it.")
            self.assertTrue(session["coverage_status"]["coverage_complete"])
            self.assertFalse(report["behavioral_evidence_boundary"]["observed_action_available"])
            self.assertEqual(report["behavioral_evidence_boundary"]["evidence_level"], "task_guided_self_report")
            self.assertTrue(any(call[0] == "synthesize_prototype" for call in provider.calls))
            self.assertTrue(any(call[0] == "review_image_stimulus" for call in provider.calls))
            next_turn_call = next(call for call in provider.calls if call[0] == "next_turn")
            self.assertIn("STIMULUS TYPE:\nimage", next_turn_call[1]["user_prompt"])
            self.assertIn("PROTOTYPE TASK:\nReview one recommendation and decide whether to act on it.", next_turn_call[1]["user_prompt"])
            self.assertTrue(session["stimulus_artifact_snapshot"].endswith(".png"))
            self.assertIn("summary", session["stimulus_analysis"])
            self.assertTrue((output / "stimulus_analysis.json").exists())
            self.assertIn("Evidence Boundary", (output / "insights.md").read_text(encoding="utf-8"))

    def test_prototype_validation_flow_stimulus_review_is_first_class_runtime_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=79)[0]
            save_persona(persona, root / "personas")
            provider = PrototypeValidationFacilitator()
            flow_bundle = _write_flow_bundle(root)
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=provider,
                persona_provider=PrototypeValidationPersona(),
            )
            output = runtime.run(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Validate whether the multi-screen prototype flow supports a concrete review task.",
                interview_mode="prototype_validation",
                product_context="A workflow that summarizes evidence, lets the user inspect it, and then decide whether to act.",
                stimulus_type="flow",
                stimulus_artifact=str(flow_bundle),
                prototype_task="Review one recommendation and decide whether to act on it.",
                soft_turn_limit=7,
                hard_turn_limit=8,
            )

            session = read_json(output / "interview.json")
            self.assertEqual(session["stimulus_type"], "flow")
            self.assertTrue(any(call[0] == "review_flow_stimulus" for call in provider.calls))
            self.assertTrue(session["stimulus_artifact_snapshot"].endswith("flow_bundle"))
            self.assertEqual(session["stimulus_analysis"]["analysis_type"], "flow")
            self.assertEqual(session["stimulus_analysis"]["screen_count"], 3)
            self.assertTrue((output / "stimulus_analysis.json").exists())
            insights_text = (output / "insights.md").read_text(encoding="utf-8")
            self.assertIn("Stimulus Review", insights_text)
            self.assertIn("Transition confusion", insights_text)

    def test_prototype_validation_observed_action_trace_is_promoted_to_first_class_evidence(self):
        class ObservedTracePrototypeFacilitator(PrototypeValidationFacilitator):
            pass

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=81)[0]
            save_persona(persona, root / "personas")
            provider = ObservedTracePrototypeFacilitator()
            trace_artifact = _write_observed_action_trace(root / "prototype-observed-trace.json")
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=provider,
                persona_provider=PrototypeValidationPersona(),
            )
            output = runtime.run(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Validate whether the clickable prototype supports a concrete review task.",
                interview_mode="prototype_validation",
                product_context="A clickable workspace that summarizes evidence, reveals source detail, and asks for permission before final action.",
                stimulus_type="clickable",
                stimulus_artifact=str(trace_artifact),
                prototype_task="Review one recommendation and decide whether to act on it.",
                soft_turn_limit=7,
                hard_turn_limit=8,
            )

            session = read_json(output / "interview.json")
            report = read_json(output / "insight_report.json")
            next_turn_call = next(call for call in provider.calls if call[0] == "next_turn")
            synthesis_call = next(call for call in provider.calls if call[0] == "synthesize_prototype")
            transcript_text = (output / "transcript.md").read_text(encoding="utf-8")
            insights_text = (output / "insights.md").read_text(encoding="utf-8")

            self.assertEqual(session["stimulus_type"], "clickable")
            self.assertTrue(session["stimulus_artifact_snapshot"].endswith(".json"))
            self.assertIn("actions", session["observed_action_trace"])
            self.assertTrue((output / "observed_action_trace.json").exists())
            self.assertIn("OBSERVED ACTION TRACE", next_turn_call[1]["user_prompt"])
            self.assertIn("permission request modal", synthesis_call[1]["user_prompt"])
            self.assertEqual(report["behavioral_evidence_boundary"]["evidence_level"], "observed_action_trace")
            self.assertTrue(report["behavioral_evidence_boundary"]["observed_action_available"])
            self.assertTrue(
                any("Observed action trace captured 3 action(s)" in item for item in report["behavioral_evidence_boundary"]["what_was_observed"])
            )
            self.assertTrue(
                any("No dwell-time telemetry was captured." in item for item in report["behavioral_evidence_boundary"]["missing_observed_signals"])
            )
            self.assertIn("Observed Action Trace", transcript_text)
            self.assertIn("Observed Action Trace", insights_text)
            self.assertTrue(
                any(
                    "application-supplied artifacts, not live human usability proof" in item
                    for item in report["evidence_gaps"]
                )
            )
            self.assertFalse(any(call[0] == "review_image_stimulus" for call in provider.calls))
            self.assertFalse(any(call[0] == "review_flow_stimulus" for call in provider.calls))

    def test_prototype_validation_clickable_manifest_executes_task_loop_and_captures_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=83)[0]
            save_persona(persona, root / "personas")
            provider = PrototypeValidationFacilitator()
            manifest = _write_clickable_prototype_manifest(root / "prototype-clickable-manifest.json")
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=provider,
                persona_provider=PrototypeValidationPersona(),
            )
            output = runtime.run(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Validate whether the clickable prototype supports a concrete review task.",
                interview_mode="prototype_validation",
                product_context="A clickable workspace that summarizes evidence, reveals source detail, and asks for permission before final action.",
                stimulus_type="clickable",
                stimulus_artifact=str(manifest),
                prototype_task="Review one recommendation and decide whether to act on it.",
                soft_turn_limit=7,
                hard_turn_limit=8,
            )

            session = read_json(output / "interview.json")
            report = read_json(output / "insight_report.json")
            analysis = read_json(output / "stimulus_analysis.json")
            transcript_text = (output / "transcript.md").read_text(encoding="utf-8")
            insights_text = (output / "insights.md").read_text(encoding="utf-8")

            self.assertEqual(session["stimulus_type"], "clickable")
            self.assertEqual(session["stimulus_analysis"]["analysis_type"], "clickable_manifest")
            self.assertEqual(session["stimulus_analysis"]["task_step_count"], 3)
            self.assertEqual(session["observed_action_trace"]["task_outcome"], "partial_success")
            self.assertEqual(len(session["observed_action_trace"]["actions"]), 3)
            self.assertTrue((output / "observed_action_trace.json").exists())
            self.assertTrue((output / "stimulus_analysis.json").exists())
            self.assertEqual(analysis["analysis_type"], "clickable_manifest")
            self.assertEqual(report["behavioral_evidence_boundary"]["evidence_level"], "observed_action_trace")
            self.assertTrue(report["behavioral_evidence_boundary"]["observed_action_available"])
            self.assertTrue(
                any("Executed 3 scripted action(s)" in item for item in report["behavioral_evidence_boundary"]["what_was_observed"])
            )
            self.assertIn("CLICKABLE PROTOTYPE EXECUTION CONTEXT", next(call[1]["user_prompt"] for call in provider.calls if call[0] == "next_turn"))
            self.assertIn("Observed Action Trace", transcript_text)
            self.assertIn("Visited screen: Evidence Drawer", insights_text)
            self.assertFalse(any(call[0] == "review_image_stimulus" for call in provider.calls))
            self.assertFalse(any(call[0] == "review_flow_stimulus" for call in provider.calls))

    def test_prototype_validation_browser_behavior_trace_is_normalized_and_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=84)[0]
            save_persona(persona, root / "personas")
            provider = PrototypeValidationFacilitator()
            trace = _write_browser_behavior_trace(root / "prototype-browser-trace.json")
            runtime = FacilitatedInterviewRuntime(
                data_dir=root / "personas",
                session_dir=root / "interviews",
                facilitator_provider=provider,
                persona_provider=PrototypeValidationPersona(),
            )
            output = runtime.run(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Validate whether the hosted prototype supports a concrete review task.",
                interview_mode="prototype_validation",
                product_context="A hosted workspace that summarizes evidence, reveals source detail, and asks for permission before final action.",
                stimulus_type="clickable",
                stimulus_artifact=str(trace),
                prototype_task="Review one recommendation and decide whether to act on it.",
                soft_turn_limit=7,
                hard_turn_limit=8,
            )

            session = read_json(output / "interview.json")
            report = read_json(output / "insight_report.json")
            analysis = read_json(output / "stimulus_analysis.json")
            observed = read_json(output / "observed_action_trace.json")
            next_turn_prompt = next(call[1]["user_prompt"] for call in provider.calls if call[0] == "next_turn")
            transcript_text = (output / "transcript.md").read_text(encoding="utf-8")
            insights_text = (output / "insights.md").read_text(encoding="utf-8")

            self.assertEqual(session["stimulus_type"], "clickable")
            self.assertEqual(analysis["analysis_type"], "browser_clickable_trace")
            self.assertEqual(analysis["driver"], "playwright")
            self.assertEqual(analysis["safety_gate"]["status"], "allowed")
            self.assertEqual(observed["trace_version"], "observed-action-trace/v1")
            self.assertEqual(len(observed["actions"]), 4)
            self.assertEqual(observed["actions"][0]["action"], "navigate")
            self.assertEqual(observed["actions"][2]["raw_metadata"]["selector"], "[data-action='open-evidence']")
            self.assertEqual(report["behavioral_evidence_boundary"]["evidence_level"], "observed_action_trace")
            self.assertTrue(report["behavioral_evidence_boundary"]["observed_action_available"])
            self.assertIn("BROWSER-OBSERVED EXECUTION CONTEXT", next_turn_prompt)
            self.assertIn("Browser-observed synthetic task execution only", transcript_text)
            self.assertIn("Safety gate: allowed", insights_text)
            self.assertFalse(any(call[0] == "review_image_stimulus" for call in provider.calls))
            self.assertFalse(any(call[0] == "review_flow_stimulus" for call in provider.calls))

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

    def test_pain_point_discovery_coverage_tracks_problem_reality_and_frequency(self):
        session = InterviewSession.from_dict({
            "interview_id": "pain-coverage",
            "persona_id": "su_fixture",
            "persona_name": "Fixture",
            "research_goal": "Discover the problem.",
            "product_context": "",
            "output_language": "Traditional Chinese",
            "facilitator_provider": "fixture",
            "facilitator_model": "fixture",
            "persona_provider": "fixture",
            "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "facilitator-synthesis/v2",
            "interview_mode": "pain_point_discovery",
            "soft_turn_limit": 5,
            "hard_turn_limit": 7,
            "exchanges": [
                {
                    "exchange_id": 1,
                    "facilitator_question": "Tell me about the last time this became annoying enough to notice.",
                    "persona_response": "Month end was messy again.",
                    "facilitator_phase": "recent_event",
                    "probing_strategy": "critical_incident",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 2,
                    "facilitator_question": "What made it a real problem instead of a small inconvenience?",
                    "persona_response": "I no longer trusted the number.",
                    "facilitator_phase": "problem_reality",
                    "probing_strategy": "problem_reality_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "consequence",
                },
                {
                    "exchange_id": 3,
                    "facilitator_question": "How often does that kind of mess happen now?",
                    "persona_response": "A small version most weeks, a bad one most months.",
                    "facilitator_phase": "frequency_probe",
                    "probing_strategy": "frequency_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 4,
                    "facilitator_question": "What consequence does it create when that happens?",
                    "persona_response": "I delay decisions until I trust the number.",
                    "facilitator_phase": "consequence_probe",
                    "probing_strategy": "consequence_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "consequence",
                },
                {
                    "exchange_id": 5,
                    "facilitator_question": "What do you do today to work around it?",
                    "persona_response": "I keep notes and mark anything uncertain.",
                    "facilitator_phase": "current_workaround",
                    "probing_strategy": "workaround_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
            ],
        })

        FacilitatedInterviewRuntime._update_coverage_status(session)

        self.assertTrue(session.coverage_status["coverage_complete"])
        self.assertEqual(session.coverage_status["missing"], [])
        self.assertEqual(session.coverage_status["depth_requirements"], [])
        self.assertTrue(FacilitatedInterviewRuntime._should_finalize_after_exchange(session))
        self.assertEqual(session.stop_reason, "soft_turn_limit_with_required_coverage_met")

    def test_decision_reconstruction_coverage_tracks_decision_specific_fields(self):
        session = InterviewSession.from_dict({
            "interview_id": "decision-coverage",
            "persona_id": "su_fixture",
            "persona_name": "Fixture",
            "research_goal": "Reconstruct the decision.",
            "product_context": "",
            "output_language": "Traditional Chinese",
            "facilitator_provider": "fixture",
            "facilitator_model": "fixture",
            "persona_provider": "fixture",
            "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "facilitator-synthesis/v2",
            "interview_mode": "decision_reconstruction",
            "soft_turn_limit": 5,
            "hard_turn_limit": 7,
            "exchanges": [
                {
                    "exchange_id": 1,
                    "facilitator_question": "Tell me about the last real decision where you changed course.",
                    "persona_response": "We delayed a release step.",
                    "facilitator_phase": "recent_event",
                    "probing_strategy": "decision_event_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 2,
                    "facilitator_question": "What evidence was still missing when you had to make that call?",
                    "persona_response": "We still lacked direct user examples.",
                    "facilitator_phase": "missing_evidence_probe",
                    "probing_strategy": "missing_evidence_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 3,
                    "facilitator_question": "What stakeholder or time pressure made waiting costly there?",
                    "persona_response": "Engineering needed the answer before sprint planning.",
                    "facilitator_phase": "pressure_probe",
                    "probing_strategy": "pressure_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 4,
                    "facilitator_question": "What could you defend publicly in that decision, and what still felt shaky privately?",
                    "persona_response": "I could defend simplifying the release, but I still doubted whether we cut the right thing.",
                    "facilitator_phase": "defensibility_probe",
                    "probing_strategy": "defensibility_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "participant_cause",
                },
                {
                    "exchange_id": 5,
                    "facilitator_question": "What did you actually change in scope or priority at the end?",
                    "persona_response": "We delayed the reporting step and launched the simpler path first.",
                    "facilitator_phase": "decision_outcome_probe",
                    "probing_strategy": "decision_outcome_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "consequence",
                },
            ],
        })

        FacilitatedInterviewRuntime._update_coverage_status(session)

        self.assertTrue(session.coverage_status["coverage_complete"])
        self.assertEqual(session.coverage_status["missing"], [])
        self.assertTrue(FacilitatedInterviewRuntime._should_finalize_after_exchange(session))
        self.assertEqual(session.stop_reason, "soft_turn_limit_with_required_coverage_met")

    def test_adoption_barrier_validation_coverage_tracks_barrier_specific_fields(self):
        session = InterviewSession.from_dict({
            "interview_id": "adoption-coverage",
            "persona_id": "su_fixture",
            "persona_name": "Fixture",
            "research_goal": "Understand adoption friction.",
            "product_context": "",
            "output_language": "Traditional Chinese",
            "facilitator_provider": "fixture",
            "facilitator_model": "fixture",
            "persona_provider": "fixture",
            "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "facilitator-synthesis/v2",
            "interview_mode": "adoption_barrier_validation",
            "soft_turn_limit": 8,
            "hard_turn_limit": 10,
            "exchanges": [
                {
                    "exchange_id": 1,
                    "facilitator_question": "Tell me about the last time you seriously considered changing how you handle this job.",
                    "persona_response": "Our manual notes were getting messy.",
                    "facilitator_phase": "recent_event",
                    "probing_strategy": "critical_incident",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 2,
                    "facilitator_question": "What do you do today instead when you need to handle it?",
                    "persona_response": "I keep a spreadsheet and chat notes.",
                    "facilitator_phase": "current_workaround",
                    "probing_strategy": "current_workaround_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 3,
                    "facilitator_question": "What setup or onboarding would already feel like too much before you would really use it?",
                    "persona_response": "Anything beyond one serious session is already too much.",
                    "facilitator_phase": "setup_burden",
                    "probing_strategy": "setup_burden_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 4,
                    "facilitator_question": "What access, approval, or coordination would make trying it difficult?",
                    "persona_response": "Connecting client material would need permission.",
                    "facilitator_phase": "permission_boundary",
                    "probing_strategy": "permission_boundary_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 5,
                    "facilitator_question": "What would you need to trust before letting it influence a real decision?",
                    "persona_response": "I would need to see where its claims came from.",
                    "facilitator_phase": "trust_boundary",
                    "probing_strategy": "trust_boundary_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 6,
                    "facilitator_question": "What would have to be true on price or budget for it to feel worth adopting?",
                    "persona_response": "It has to replace a real review step.",
                    "facilitator_phase": "pricing_condition",
                    "probing_strategy": "pricing_condition_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 7,
                    "facilitator_question": "How reversible would it need to feel if it turned out not to work?",
                    "persona_response": "I want to turn it off cleanly and keep my notes.",
                    "facilitator_phase": "reversibility_probe",
                    "probing_strategy": "reversibility_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 8,
                    "facilitator_question": "What extra step or routine burden would still make you drop it even if the value sounds good?",
                    "persona_response": "If I still have to re-enter context every week, it will never stick.",
                    "facilitator_phase": "workflow_burden",
                    "probing_strategy": "workflow_burden_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
            ],
        })

        FacilitatedInterviewRuntime._update_coverage_status(session)

        self.assertTrue(session.coverage_status["coverage_complete"])
        self.assertEqual(session.coverage_status["missing"], [])
        self.assertEqual(
            session.coverage_status["adoption_intro_prerequisites"]["required"],
            ["recent_behaviour", "current_workaround"],
        )
        self.assertTrue(session.coverage_status["adoption_intro_allowed"])
        self.assertEqual(session.coverage_status["depth_requirements"], [])
        self.assertTrue(FacilitatedInterviewRuntime._should_finalize_after_exchange(session))
        self.assertEqual(session.stop_reason, "soft_turn_limit_with_required_coverage_met")

    def test_prototype_validation_coverage_tracks_stimulus_and_task_fields(self):
        session = InterviewSession.from_dict({
            "interview_id": "prototype-coverage",
            "persona_id": "su_fixture",
            "persona_name": "Fixture",
            "research_goal": "Validate a prototype task.",
            "product_context": "A research workspace prototype.",
            "stimulus_type": "image",
            "stimulus_artifact": "prototype-review-screen-v1.png",
            "prototype_task": "Review one recommendation and decide whether to act on it.",
            "output_language": "Traditional Chinese",
            "facilitator_provider": "fixture",
            "facilitator_model": "fixture",
            "persona_provider": "fixture",
            "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "prototype-synthesis/v1",
            "interview_mode": "prototype_validation",
            "soft_turn_limit": 7,
            "hard_turn_limit": 9,
            "exchanges": [
                {
                    "exchange_id": 1,
                    "facilitator_question": "Looking at this prototype, what do you think it is trying to help you do?",
                    "persona_response": "It looks like an evidence review workspace.",
                    "facilitator_phase": "stimulus_interpretation",
                    "probing_strategy": "stimulus_interpretation_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 2,
                    "facilitator_question": "If you were doing that task now, what would you try first?",
                    "persona_response": "I would open the summary first.",
                    "facilitator_phase": "first_action_expectation",
                    "probing_strategy": "first_action_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 3,
                    "facilitator_question": "After that first step, how would you expect the rest of the task to unfold?",
                    "persona_response": "I would read the linked evidence before acting.",
                    "facilitator_phase": "task_path_expectation",
                    "probing_strategy": "task_path_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 4,
                    "facilitator_question": "Where would setup or required input start feeling unclear here?",
                    "persona_response": "I am not sure how much cleanup is needed before import.",
                    "facilitator_phase": "setup_confusion",
                    "probing_strategy": "setup_confusion_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 5,
                    "facilitator_question": "What would make you trust or distrust this enough to use it for a real decision?",
                    "persona_response": "I need to see where each claim came from.",
                    "facilitator_phase": "trust_boundary",
                    "probing_strategy": "trust_boundary_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 6,
                    "facilitator_question": "Where would you hesitate or stop if this were a real attempt?",
                    "persona_response": "I would stop if permissions became broad too early.",
                    "facilitator_phase": "breakdown_or_dropoff",
                    "probing_strategy": "dropoff_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 7,
                    "facilitator_question": "What result would tell you that the task actually worked here?",
                    "persona_response": "A specific recommendation tied to evidence.",
                    "facilitator_phase": "task_completion_signal",
                    "probing_strategy": "completion_signal_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
            ],
        })

        FacilitatedInterviewRuntime._update_coverage_status(session)

        self.assertTrue(session.coverage_status["coverage_complete"])
        self.assertEqual(session.coverage_status["missing"], [])
        self.assertEqual(
            session.coverage_status["requirements"],
            [
                "stimulus_interpretation",
                "first_action_expectation",
                "task_path_expectation",
                "setup_confusion",
                "trust_boundary",
                "breakdown_or_dropoff",
                "task_completion_signal",
            ],
        )
        self.assertTrue(FacilitatedInterviewRuntime._should_finalize_after_exchange(session))
        self.assertEqual(session.stop_reason, "soft_turn_limit_with_required_coverage_met")

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

    def test_decision_reconstruction_rejects_premature_closure_before_required_fields_are_met(self):
        revised_decision = FacilitatorDecision(
            interview_phase="missing_evidence_probe",
            probing_strategy="missing_evidence_probe",
            decision_rationale="Need the missing decision-state evidence before closing.",
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
            "interview_id": "decision-gate-session",
            "persona_id": "su_fixture",
            "persona_name": "Fixture",
            "research_goal": "Reconstruct the last real decision.",
            "product_context": "",
            "output_language": "Traditional Chinese",
            "facilitator_provider": "fixture",
            "facilitator_model": "fixture",
            "persona_provider": "fixture",
            "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "facilitator-synthesis/v2",
            "interview_mode": "decision_reconstruction",
            "soft_turn_limit": 6,
            "hard_turn_limit": 10,
            "exchanges": [{
                "exchange_id": 1,
                "facilitator_question": "Tell me about the last real decision where you changed course.",
                "persona_response": "We delayed one release step.",
                "facilitator_phase": "recent_event",
                "probing_strategy": "decision_event_probe",
                "question_evidence_basis": "current_event",
                "question_evidence_target": "context",
            }],
        })
        decision = FacilitatorDecision(
            interview_phase="closure",
            probing_strategy="evidence_sufficiency",
            decision_rationale="End after one recalled decision.",
            message_to_persona="",
            evidence_updates=[],
            root_cause_hypotheses=[],
            open_questions=[],
            should_end=True,
            end_reason="Enough detail collected.",
            question_evidence_basis="current_event",
            question_evidence_target="context",
        )

        revised = runtime._revise_non_episodic_validation_question(session, decision, "SYSTEM")

        self.assertIs(revised, revised_decision)
        self.assertEqual(len(provider.calls), 1)
        self.assertIn("DECISION RECONSTRUCTION GATE", provider.calls[0]["user_prompt"])
        self.assertIn("missing_evidence", provider.calls[0]["user_prompt"])
        self.assertIn("pressure", provider.calls[0]["user_prompt"])
        self.assertIn("defensible_vs_uncertain", provider.calls[0]["user_prompt"])
        self.assertIn("decision_change", provider.calls[0]["user_prompt"])
        self.assertEqual(
            session.facilitator_decisions[-1]["decision_status"],
            "rejected_by_decision_reconstruction_gate",
        )

    def test_adoption_barrier_validation_rejects_barrier_questions_before_current_state_gate(self):
        revised_decision = FacilitatorDecision(
            interview_phase="current_workaround",
            probing_strategy="current_workaround_probe",
            decision_rationale="Need the current workaround before adoption-friction testing.",
            message_to_persona="What do you do today instead when you need to handle it?",
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
            "interview_id": "adoption-timing-gate-session",
            "persona_id": "su_fixture",
            "persona_name": "Fixture",
            "research_goal": "Understand adoption friction.",
            "product_context": "A workflow concept.",
            "output_language": "Traditional Chinese",
            "facilitator_provider": "fixture",
            "facilitator_model": "fixture",
            "persona_provider": "fixture",
            "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "facilitator-synthesis/v2",
            "interview_mode": "adoption_barrier_validation",
            "soft_turn_limit": 8,
            "hard_turn_limit": 10,
            "exchanges": [{
                "exchange_id": 1,
                "facilitator_question": "Tell me about the last time you seriously considered changing how you handle this job.",
                "persona_response": "Our manual notes were getting messy.",
                "facilitator_phase": "recent_event",
                "probing_strategy": "critical_incident",
                "question_evidence_basis": "current_event",
                "question_evidence_target": "context",
            }],
        })
        decision = FacilitatorDecision(
            interview_phase="setup_burden",
            probing_strategy="setup_burden_probe",
            decision_rationale="Move directly to adoption friction.",
            message_to_persona="What setup would already feel like too much before you would really use it?",
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
        self.assertIn("ADOPTION BARRIER TIMING GATE", provider.calls[0]["user_prompt"])
        self.assertIn("current_workaround", provider.calls[0]["user_prompt"])
        self.assertEqual(
            session.facilitator_decisions[-1]["decision_status"],
            "rejected_by_adoption_timing_gate",
        )

    def test_adoption_barrier_validation_rejects_premature_closure_before_required_fields_are_met(self):
        revised_decision = FacilitatorDecision(
            interview_phase="trust_boundary",
            probing_strategy="trust_boundary_probe",
            decision_rationale="Need trust evidence before closing.",
            message_to_persona="What would you need to trust before letting it influence a real decision?",
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
            "interview_id": "adoption-gate-session",
            "persona_id": "su_fixture",
            "persona_name": "Fixture",
            "research_goal": "Understand adoption friction.",
            "product_context": "A workflow concept.",
            "output_language": "Traditional Chinese",
            "facilitator_provider": "fixture",
            "facilitator_model": "fixture",
            "persona_provider": "fixture",
            "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "facilitator-synthesis/v2",
            "interview_mode": "adoption_barrier_validation",
            "soft_turn_limit": 8,
            "hard_turn_limit": 10,
            "exchanges": [
                {
                    "exchange_id": 1,
                    "facilitator_question": "Tell me about the last time you seriously considered changing how you handle this job.",
                    "persona_response": "Our manual notes were getting messy.",
                    "facilitator_phase": "recent_event",
                    "probing_strategy": "critical_incident",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 2,
                    "facilitator_question": "What do you do today instead when you need to handle it?",
                    "persona_response": "I keep a spreadsheet and chat notes.",
                    "facilitator_phase": "current_workaround",
                    "probing_strategy": "current_workaround_probe",
                    "question_evidence_basis": "current_event",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 3,
                    "facilitator_question": "What setup or onboarding would already feel like too much before you would really use it?",
                    "persona_response": "Anything beyond one serious session is already too much.",
                    "facilitator_phase": "setup_burden",
                    "probing_strategy": "setup_burden_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 4,
                    "facilitator_question": "What access, approval, or coordination would make trying it difficult?",
                    "persona_response": "Connecting client material would need permission.",
                    "facilitator_phase": "permission_boundary",
                    "probing_strategy": "permission_boundary_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
            ],
        })
        decision = FacilitatorDecision(
            interview_phase="closure",
            probing_strategy="evidence_sufficiency",
            decision_rationale="End after the main adoption blockers.",
            message_to_persona="",
            evidence_updates=[],
            root_cause_hypotheses=[],
            open_questions=[],
            should_end=True,
            end_reason="Enough detail collected.",
            question_evidence_basis="clarification",
            question_evidence_target="context",
        )

        revised = runtime._revise_non_episodic_validation_question(session, decision, "SYSTEM")

        self.assertIs(revised, revised_decision)
        self.assertEqual(len(provider.calls), 1)
        self.assertIn("ADOPTION BARRIER GATE", provider.calls[0]["user_prompt"])
        self.assertIn("trust_boundary", provider.calls[0]["user_prompt"])
        self.assertIn("pricing_condition", provider.calls[0]["user_prompt"])
        self.assertIn("reversibility", provider.calls[0]["user_prompt"])
        self.assertIn("workflow_burden", provider.calls[0]["user_prompt"])
        self.assertEqual(
            session.facilitator_decisions[-1]["decision_status"],
            "rejected_by_adoption_barrier_gate",
        )

    def test_prototype_validation_rejects_premature_closure_before_required_fields_are_met(self):
        revised_decision = FacilitatorDecision(
            interview_phase="trust_boundary",
            probing_strategy="trust_boundary_probe",
            decision_rationale="Need trust evidence before closing the prototype run.",
            message_to_persona="What would make you trust or distrust this enough to use it for a real decision?",
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
            "interview_id": "prototype-gate-session",
            "persona_id": "su_fixture",
            "persona_name": "Fixture",
            "research_goal": "Validate a prototype task.",
            "product_context": "A research workspace prototype.",
            "stimulus_type": "image",
            "stimulus_artifact": "prototype-review-screen-v1.png",
            "prototype_task": "Review one recommendation and decide whether to act on it.",
            "output_language": "Traditional Chinese",
            "facilitator_provider": "fixture",
            "facilitator_model": "fixture",
            "persona_provider": "fixture",
            "persona_model": "fixture",
            "facilitator_prompt_version": "facilitator-interview/v2",
            "synthesis_prompt_version": "prototype-synthesis/v1",
            "interview_mode": "prototype_validation",
            "soft_turn_limit": 7,
            "hard_turn_limit": 9,
            "exchanges": [
                {
                    "exchange_id": 1,
                    "facilitator_question": "Looking at this prototype, what do you think it is trying to help you do?",
                    "persona_response": "It looks like an evidence review workspace.",
                    "facilitator_phase": "stimulus_interpretation",
                    "probing_strategy": "stimulus_interpretation_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
                {
                    "exchange_id": 2,
                    "facilitator_question": "If you were doing that task now, what would you try first?",
                    "persona_response": "I would open the summary first.",
                    "facilitator_phase": "first_action_expectation",
                    "probing_strategy": "first_action_probe",
                    "question_evidence_basis": "hypothetical",
                    "question_evidence_target": "context",
                },
            ],
        })
        decision = FacilitatorDecision(
            interview_phase="closure",
            probing_strategy="evidence_sufficiency",
            decision_rationale="End after the main prototype interpretation.",
            message_to_persona="",
            evidence_updates=[],
            root_cause_hypotheses=[],
            open_questions=[],
            should_end=True,
            end_reason="Enough detail collected.",
            question_evidence_basis="clarification",
            question_evidence_target="context",
        )

        revised = runtime._revise_non_episodic_validation_question(session, decision, "SYSTEM")

        self.assertIs(revised, revised_decision)
        self.assertEqual(len(provider.calls), 1)
        self.assertIn("PROTOTYPE VALIDATION GATE", provider.calls[0]["user_prompt"])
        self.assertIn("task_path_expectation", provider.calls[0]["user_prompt"])
        self.assertIn("setup_confusion", provider.calls[0]["user_prompt"])
        self.assertIn("breakdown_or_dropoff", provider.calls[0]["user_prompt"])
        self.assertEqual(
            session.facilitator_decisions[-1]["decision_status"],
            "rejected_by_prototype_validation_gate",
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

    def test_facilitator_provider_coerces_singleton_list_fields_for_agnes_style_payloads(self):
        class StubClient:
            config = OpenAIProviderConfig(
                api_key="fixture",
                model="agnes-2.0-flash",
                provider_name="agnes",
                transport="powershell_webrequest",
            )
            last_transport_metadata = {}

            def create_json_response(self, **kwargs):
                return {
                    "interview_phase": ["opening"],
                    "probing_strategy": ["recent_event_probe"],
                    "decision_rationale": ["Start from one concrete finance event."],
                    "message_to_persona": ["你最近一次因為錢而要特登處理一件事，係咩情況？"],
                    "evidence_updates": {
                        "claim": "Participant has not yet described a concrete finance event.",
                        "evidence_type": "facilitator_hypothesis",
                        "transcript_refs": [],
                        "confidence": "low",
                    },
                    "root_cause_hypotheses": {
                        "hypothesis": "Pain may involve coordination or timing rather than pure budgeting.",
                        "supporting_evidence_refs": [],
                        "alternative_explanations": [],
                        "validation_gap": "Need one recent real incident.",
                        "confidence": "low",
                    },
                    "open_questions": "What recent event best exposes the participant's real finance friction?",
                    "should_end": False,
                    "end_reason": [""],
                    "question_evidence_basis": ["clarification"],
                    "question_evidence_target": ["context"],
                }

        decision = OpenAIFacilitatorProvider(StubClient()).next_turn(system_prompt="skill", user_prompt="start")

        self.assertEqual(decision.interview_phase, "opening")
        self.assertEqual(decision.probing_strategy, "recent_event_probe")
        self.assertEqual(decision.decision_rationale, "Start from one concrete finance event.")
        self.assertEqual(decision.message_to_persona, "你最近一次因為錢而要特登處理一件事，係咩情況？")
        self.assertEqual(len(decision.evidence_updates), 1)
        self.assertEqual(len(decision.root_cause_hypotheses), 1)
        self.assertEqual(
            decision.open_questions,
            ["What recent event best exposes the participant's real finance friction?"],
        )
        self.assertEqual(decision.end_reason, "")
        self.assertEqual(decision.question_evidence_basis, "clarification")
        self.assertEqual(decision.question_evidence_target, "context")

    def test_facilitator_provider_falls_back_to_tagged_text_for_agnes(self):
        class StubClient:
            config = OpenAIProviderConfig(
                api_key="fixture",
                model="agnes-2.0-flash",
                provider_name="agnes",
                transport="node_https",
            )
            last_transport_metadata = {}

            def create_json_response(self, **kwargs):
                raise OpenAIProviderError("Model did not return a valid JSON object.")

            def create_text_response(self, **kwargs):
                return "\n".join(
                    [
                        "PHASE: current_workaround",
                        "STRATEGY: concrete_follow_up",
                        "RATIONALE: Stay anchored in the participant's current bookkeeping behavior.",
                        "QUESTION: 你而家通常幾時先會發現有啲數未記低？發現咗之後你會點補救？",
                        "SHOULD_END: no",
                        "END_REASON:",
                        "BASIS: clarification",
                        "TARGET: context",
                        "OPEN_QUESTION: 佢幾時先浮面",
                    ]
                )

        decision = OpenAIFacilitatorProvider(StubClient()).next_turn(system_prompt="skill", user_prompt="start")

        self.assertEqual(decision.interview_phase, "current_workaround")
        self.assertEqual(decision.probing_strategy, "concrete_follow_up")
        self.assertIn("補救", decision.message_to_persona)
        self.assertFalse(decision.should_end)
        self.assertEqual(decision.question_evidence_basis, "clarification")
        self.assertEqual(decision.question_evidence_target, "context")
        self.assertEqual(decision.open_questions, ["佢幾時先浮面"])

    def test_concept_synthesis_normalizes_partial_agnes_payload(self):
        class StubClient:
            config = OpenAIProviderConfig(
                api_key="fixture",
                model="agnes-2.0-flash",
                provider_name="agnes",
                transport="node_https",
            )
            last_transport_metadata = {}

            def create_json_response(self, **kwargs):
                return {
                    "key_insights": ["Manual screenshots are acting as a trust-preserving workaround."],
                    "next_experiment": "Probe trust and repeat-use conditions with one more synthetic follow-up.",
                }

        payload, _ = OpenAIFacilitatorProvider(StubClient()).synthesize_concept(
            system_prompt="skill",
            user_prompt="report",
        )

        self.assertIn("problem_evidence", payload)
        self.assertIn("trust_boundary", payload)
        self.assertEqual(payload["retention_risk"]["workflow_effect"], "unclear")
        self.assertGreaterEqual(len(payload["key_insights"]), 3)
        self.assertTrue(payload["synthetic_only_disclaimer"])

    def test_concept_synthesis_maps_agnes_text_report_shape(self):
        class StubClient:
            config = OpenAIProviderConfig(
                api_key="fixture",
                model="agnes-2.0-flash",
                provider_name="agnes",
                transport="node_https",
            )
            last_transport_metadata = {}

            def create_json_response(self, **kwargs):
                raise OpenAIProviderError("Model did not return a valid JSON object.")

            def create_text_response(self, **kwargs):
                return json.dumps(
                    {
                        "evidence_synthesis": {
                            "recent_behavior": {
                                "summary": "Participant uses screenshots and a handwritten book.",
                                "details": "They log dates and amounts manually.",
                                "quote": "exchange_1.persona: I take a screenshot and write it down.",
                            },
                            "current_workaround": {
                                "summary": "Screenshots + handwritten ledger",
                                "quote": "exchange_2.persona: Messages get buried.",
                            },
                            "pain_intensity_and_threshold": {
                                "severity": "Moderate to High",
                                "quote": "exchange_5.persona: If it costs me more than half an hour, it is too much.",
                            },
                        },
                        "assumption_validation": {
                            "assumption_1": {
                                "status": "weakened",
                                "rationale": "Manual tracking is treated as a temporary fix.",
                                "evidence": "exchange_7.persona",
                            }
                        },
                        "key_insights": [
                            {"text": "The workaround preserves trust more than convenience."},
                            {"text": "Setup friction is a major adoption barrier."},
                        ],
                        "recommended_experiment": {
                            "description": "Run a concierge trial."
                        },
                    },
                    ensure_ascii=False,
                )

        payload, _ = OpenAIFacilitatorProvider(StubClient()).synthesize_concept(
            system_prompt="skill",
            user_prompt="report",
        )

        self.assertEqual(payload["problem_evidence"]["strength"], "strong")
        self.assertEqual(payload["current_workaround"]["existing_workaround"], ["Screenshots + handwritten ledger"])
        self.assertEqual(payload["next_experiment"], "Run a concierge trial.")
        self.assertGreaterEqual(len(payload["key_insights"]), 3)

    def test_prototype_synthesis_normalizes_partial_payload_and_downgrades_observed_action(self):
        class StubClient:
            config = OpenAIProviderConfig(
                api_key="fixture",
                model="agnes-2.0-flash",
                provider_name="agnes",
                transport="node_https",
            )
            last_transport_metadata = {}

            def create_json_response(self, **kwargs):
                return {
                    "behavioral_evidence_boundary": {
                        "evidence_level": "observed_action_trace",
                        "observed_action_available": False,
                    },
                    "key_insights": ["The participant wants evidence traceability before action."],
                }

        payload, _ = OpenAIFacilitatorProvider(StubClient()).synthesize_prototype(
            system_prompt="skill",
            user_prompt="report",
        )

        self.assertIn("stimulus_interpretation", payload)
        self.assertIn("task_journey", payload)
        self.assertEqual(payload["behavioral_evidence_boundary"]["evidence_level"], "task_guided_self_report")
        self.assertFalse(payload["behavioral_evidence_boundary"]["observed_action_available"])
        self.assertGreaterEqual(len(payload["key_insights"]), 3)
        self.assertTrue(payload["synthetic_only_disclaimer"])

    def test_prototype_synthesis_preserves_observed_action_boundary_when_available(self):
        class StubClient:
            config = OpenAIProviderConfig(
                api_key="fixture",
                model="agnes-2.0-flash",
                provider_name="agnes",
                transport="node_https",
            )
            last_transport_metadata = {}

            def create_json_response(self, **kwargs):
                return {
                    "behavioral_evidence_boundary": {
                        "evidence_level": "observed_action_trace",
                        "observed_action_available": True,
                        "what_was_observed": ["Recorded backtracking before the permission boundary."],
                        "missing_observed_signals": ["No dwell-time telemetry was captured."],
                    },
                    "key_insights": ["The participant backed out once the permission scope widened."],
                }

        payload, _ = OpenAIFacilitatorProvider(StubClient()).synthesize_prototype(
            system_prompt="skill",
            user_prompt="report",
        )

        self.assertEqual(payload["behavioral_evidence_boundary"]["evidence_level"], "observed_action_trace")
        self.assertTrue(payload["behavioral_evidence_boundary"]["observed_action_available"])
        self.assertNotIn("No observed action trace was collected.", payload["evidence_gaps"])
        self.assertIn("No dwell-time telemetry was captured.", payload["behavioral_evidence_boundary"]["missing_observed_signals"])
        self.assertTrue(
            any(
                "application-supplied trace" in item
                for item in payload["key_insights"]
            )
        )

    def test_quality_evaluation_normalizes_partial_agnes_payload(self):
        class StubClient:
            config = OpenAIProviderConfig(
                api_key="fixture",
                model="agnes-2.0-flash",
                provider_name="agnes",
                transport="node_https",
            )
            last_transport_metadata = {}

            def create_json_response(self, **kwargs):
                return {
                    "findings": [
                        {
                            "category": "coverage_gap",
                            "severity": "medium",
                            "observation": "Trust boundary evidence stayed thin.",
                            "evidence_refs": ["exchange_6.persona"],
                            "recommendation": "Probe what data or automation the participant would reject.",
                        }
                    ],
                    "required_improvements": [
                        "Add one explicit trust-boundary follow-up before closing."
                    ],
                }

        payload, _ = OpenAIFacilitatorProvider(StubClient()).evaluate_quality(
            system_prompt="skill",
            user_prompt="report",
        )

        self.assertEqual(payload["overall_verdict"], "warn")
        self.assertEqual(payload["scores"]["overall"], 3)
        self.assertEqual(payload["checks"]["evidence_reference_quality"], "warn")
        self.assertTrue(payload["improvement_hints"]["next_interview_focus"])
        self.assertTrue(payload["synthetic_only_disclaimer"])

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
            "run-facilitated-interview",
            "--persona-id", "su_0001",
            "--research-goal", "Discover a problem",
            "--interview-mode", "pain_point_discovery",
        ])
        self.assertEqual(parsed.interview_mode, "pain_point_discovery")

        parsed = parser.parse_args([
            "run-facilitated-interview",
            "--persona-id", "su_0001",
            "--research-goal", "Understand adoption friction",
            "--interview-mode", "adoption_barrier_validation",
        ])
        self.assertEqual(parsed.interview_mode, "adoption_barrier_validation")

        parsed = parser.parse_args([
            "run-facilitated-interview",
            "--persona-id", "su_0001",
            "--research-goal", "Validate a prototype",
            "--interview-mode", "prototype_validation",
            "--stimulus-type", "image",
            "--stimulus-artifact", "prototype-review-screen-v1.png",
            "--prototype-task", "Review one recommendation and decide whether to act on it.",
        ])
        self.assertEqual(parsed.interview_mode, "prototype_validation")
        self.assertEqual(parsed.stimulus_type, "image")
        self.assertEqual(parsed.prototype_task, "Review one recommendation and decide whether to act on it.")

        parsed = parser.parse_args([
            "run-facilitated-interview",
            "--persona-id", "su_0001",
            "--research-goal", "Reconstruct a decision",
            "--interview-mode", "decision_reconstruction",
        ])
        self.assertEqual(parsed.interview_mode, "decision_reconstruction")

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
