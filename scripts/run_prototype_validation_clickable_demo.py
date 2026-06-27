from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.conversation.providers import ChatResult
from ai_validation_swarm.facilitator.models import FacilitatorDecision
from ai_validation_swarm.facilitator.runtime import FacilitatedInterviewRuntime
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.storage.files import save_persona


DEMO_ROOT = ROOT / "demo" / "prototype_validation_clickable"
MANIFEST_PATH = DEMO_ROOT / "prototype-clickable-manifest.json"
OUTPUT_ROOT = ROOT / "demo_runs"


def write_clickable_manifest(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
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


class PrototypeValidationFacilitator:
    provider_name = "prototype-validation"
    model_name = "prototype-validation/v1"

    def __init__(self) -> None:
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
        return self.decisions.pop(0)

    def synthesize_prototype(self, **kwargs):
        return (
            {
                "stimulus_interpretation": {
                    "summary": "The participant sees the screen as an evidence review workspace, but not yet a fully trusted decision tool.",
                    "supporting_quotes": [
                        {
                            "quote": "I would look for the summary first.",
                            "evidence_ref": "exchange_1.persona",
                        }
                    ],
                    "interpretation_breakdowns": [
                        "It is unclear whether the workspace is suggesting action or just organizing evidence."
                    ],
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
                    "evidence_level": "observed_action_trace",
                    "observed_action_available": True,
                    "what_was_observed": [
                        "Executed 3 scripted action(s) from the clickable prototype manifest.",
                        "The task stopped at the permission request modal after the evidence drawer was opened.",
                    ],
                    "missing_observed_signals": [
                        "No dwell-time telemetry was captured.",
                        "No cursor path was captured.",
                    ],
                },
                "assumption_validation": [
                    {
                        "assumption": "The participant will immediately understand what the workspace is doing.",
                        "status": "weakened",
                        "evidence_refs": ["exchange_1.persona", "exchange_3.persona"],
                        "rationale": "They can read the page directionally, but still expect ambiguity in how the task unfolds.",
                    }
                ],
                "key_insights": [
                    "Because the participant looks for traceable evidence first, they would inspect the summary before acting. This means the prototype should foreground evidence lineage.",
                    "Because setup expectations are still unclear, the participant would delay serious use until preparation cost becomes legible.",
                    "Because broad permissions feel risky before value appears, the participant would stop at the permission modal unless access scope stays narrow and explicit.",
                ],
                "next_experiment": "Replay the same task against a browser-driven prototype and capture the real first click, hesitation, and backtracking.",
                "evidence_gaps": [
                    "The current trace is scripted from a manifest rather than captured from a live browser session."
                ],
                "synthetic_only_disclaimer": "Synthetic prototype-validation evidence only; not human usability proof.",
            },
            "prototype-thread-1",
        )


class PrototypeValidationPersona:
    provider_name = "prototype-validation"
    model_name = "prototype-validation-persona/v1"

    def __init__(self) -> None:
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
        return type(
            "TraceResult",
            (),
            {
                "payload": {
                    "synthetic_only_disclaimer": "Synthetic persona post-interview reflection only; not human market evidence.",
                    "surface_read": {
                        "what_the_persona_explicitly_said": [
                            "They would inspect the summary and linked evidence before acting."
                        ],
                        "what_they_seemed_to_optimize_for": "Inspectability before task commitment.",
                        "what_stayed_implicit": [
                            "How much prior tool disappointment raised their demand for evidence traceability."
                        ],
                    },
                    "likely_drivers": [
                        {
                            "driver": "Trust comes from inspectable evidence before action",
                            "driver_type": "trust_pattern",
                            "why_it_matters_here": "The participant wants a recommendation, but only after they can inspect where it came from.",
                            "evidence_refs": ["exchange_2.persona", "exchange_3.persona", "exchange_5.persona"],
                            "profile_source_refs": ["values.core_values"],
                            "confidence": "medium",
                            "observed_vs_inferred": "mixed",
                        }
                    ],
                    "unspoken_constraints": [],
                    "value_tensions": [],
                    "missed_follow_up_questions": [],
                },
                "provider_session_id": "prototype-trace-thread-1",
            },
        )()


def run_demo() -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = write_clickable_manifest(MANIFEST_PATH)
    persona = generate_personas(count=1, random_seed=83)[0]
    save_persona(persona, OUTPUT_ROOT / "personas")

    runtime = FacilitatedInterviewRuntime(
        data_dir=OUTPUT_ROOT / "personas",
        session_dir=OUTPUT_ROOT / "interviews",
        facilitator_provider=PrototypeValidationFacilitator(),
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
    return output


if __name__ == "__main__":
    output_dir = run_demo()
    print(f"Demo output: {output_dir}")
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"Transcript: {output_dir / 'transcript.md'}")
    print(f"Insights: {output_dir / 'insights.md'}")
    print(f"Stimulus analysis: {output_dir / 'stimulus_analysis.json'}")
    print(f"Observed trace: {output_dir / 'observed_action_trace.json'}")
