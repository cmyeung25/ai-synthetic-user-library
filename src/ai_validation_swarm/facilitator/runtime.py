from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Callable

from ai_validation_swarm.conversation.providers import ConversationProvider
from ai_validation_swarm.conversation.realism import validate_friction_mode
from ai_validation_swarm.conversation.runtime import (
    DRIVER_TRACE_PROMPT_VERSION,
    ConversationRuntime,
    resolve_persona_folder,
)
from ai_validation_swarm.domain.models import utc_now_iso
from ai_validation_swarm.domain.validators import InputValidationError, validate_observed_action_trace_payload
from ai_validation_swarm.facilitator.concept_protocols import load_concept_protocol
from ai_validation_swarm.facilitator.learning import build_approved_facilitator_learning_prompt_fragment
from ai_validation_swarm.facilitator.models import FacilitatorDecision, InterviewExchange, InterviewSession
from ai_validation_swarm.facilitator.optimism import attach_over_optimism_risks
from ai_validation_swarm.facilitator.providers import FacilitatorProvider
from ai_validation_swarm.facilitator.stimulus_executor import (
    SCRIPTED_CLICKABLE_EXECUTOR_VERSION,
    ScriptedClickablePrototypeExecutor,
    StimulusExecutor,
)
from ai_validation_swarm.saas.run_contract import build_interview_run_contract, write_shared_run_contract
from ai_validation_swarm.storage.files import ensure_dir, load_persona, write_json, write_markdown


FACILITATOR_PROMPT_VERSION = "facilitator-interview/v2"
SYNTHESIS_PROMPT_VERSION = "facilitator-synthesis/v2"
HYPOTHESIS_EVIDENCE_JUDGE_PROMPT_VERSION = "hypothesis-evidence-judge/v1"
CONCEPT_SYNTHESIS_PROMPT_VERSION = "concept-synthesis/v1"
PROTOTYPE_SYNTHESIS_PROMPT_VERSION = "prototype-synthesis/v1"
IMAGE_STIMULUS_REVIEW_PROMPT_VERSION = "stimulus-image-review/v1"
FLOW_STIMULUS_REVIEW_PROMPT_VERSION = "stimulus-flow-review/v1"
OBSERVED_ACTION_TRACE_VERSION = "observed-action-trace/v1"

CONCEPT_VALIDATION_COVERAGE_REQUIREMENTS: tuple[str, ...] = (
    "recent_behaviour",
    "current_workaround",
    "concept_reaction",
    "trust_boundary",
    "action_followthrough",
    "repeat_use_condition",
    "service_embedding",
)
ROOT_CAUSE_COVERAGE_REQUIREMENTS: tuple[str, ...] = (
    "recent_behaviour",
    "participant_cause",
    "consequence",
)
PAIN_POINT_DISCOVERY_COVERAGE_REQUIREMENTS: tuple[str, ...] = (
    "recent_behaviour",
    "problem_reality",
    "frequency",
    "consequence",
    "current_workaround",
)
ADOPTION_BARRIER_VALIDATION_COVERAGE_REQUIREMENTS: tuple[str, ...] = (
    "recent_behaviour",
    "current_workaround",
    "setup_burden",
    "permission_boundary",
    "trust_boundary",
    "pricing_condition",
    "reversibility",
    "workflow_burden",
)
PROTOTYPE_VALIDATION_COVERAGE_REQUIREMENTS: tuple[str, ...] = (
    "stimulus_interpretation",
    "first_action_expectation",
    "task_path_expectation",
    "setup_confusion",
    "trust_boundary",
    "breakdown_or_dropoff",
    "task_completion_signal",
)
DECISION_RECONSTRUCTION_COVERAGE_REQUIREMENTS: tuple[str, ...] = (
    "recent_real_decision",
    "missing_evidence",
    "pressure",
    "defensible_vs_uncertain",
    "decision_change",
)
HYPOTHESIS_VALIDATION_COVERAGE_REQUIREMENTS: tuple[str, ...] = (
    "target_behaviour",
    "participant_cause",
    "consequence",
    "hypothesis_condition",
    "alternative_condition",
)
CONCEPT_VALIDATION_DEPTH_REQUIREMENTS: tuple[str, ...] = (
    "threshold_probe",
    "contrast_probe",
    "driver_deepening_probe",
    "output_to_decision_probe",
)
CONCEPT_INTRO_PREREQUISITES: tuple[str, ...] = (
    "recent_real_decision",
    "missing_evidence",
    "pressure",
    "defensible_vs_uncertain",
    "decision_change",
)
PROTOTYPE_STIMULUS_TYPES: tuple[str, ...] = (
    "text_concept",
    "image",
    "flow",
    "clickable",
    "live_app",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


class FacilitatedInterviewRuntime:
    def __init__(
        self,
        *,
        data_dir: Path,
        session_dir: Path,
        facilitator_provider: FacilitatorProvider,
        persona_provider: ConversationProvider,
        observer: Callable[[str, str], None] | None = None,
        progress_writer: Callable[[str], None] | None = None,
        approved_learning_rules_path: Path | None = None,
        max_approved_learning_rules: int = 5,
        stimulus_executors: list[StimulusExecutor] | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.session_dir = session_dir
        self.facilitator_provider = facilitator_provider
        self.persona_provider = persona_provider
        self.observer = observer or (lambda role, message: None)
        self.progress_writer = progress_writer
        self.approved_learning_rules_path = approved_learning_rules_path
        self.max_approved_learning_rules = max_approved_learning_rules
        self.stimulus_executors = list(stimulus_executors or [ScriptedClickablePrototypeExecutor()])

    def _progress(self, message: str) -> None:
        if self.progress_writer is not None:
            self.progress_writer(f"[interview] {message}")

    def run(
        self,
        *,
        persona_id: str,
        research_goal: str,
        interview_mode: str = "explore_root_cause",
        hypothesis: str = "",
        product_context: str = "",
        concept_protocol: str = "",
        concept_label: str = "",
        stimulus_type: str = "",
        stimulus_artifact: str = "",
        prototype_task: str = "",
        output_language: str = "Traditional Chinese",
        max_turns: int = 10,
        soft_turn_limit: int | None = None,
        hard_turn_limit: int | None = None,
        friction_mode: str = "off",
    ) -> Path:
        if not research_goal.strip():
            raise ValueError("Research goal cannot be empty.")
        soft_limit, hard_limit = self._resolve_turn_limits(
            max_turns=max_turns,
            soft_turn_limit=soft_turn_limit,
            hard_turn_limit=hard_turn_limit,
        )
        mode, resolved_stimulus_type = self._validate_interview_brief(
            interview_mode,
            hypothesis,
            product_context=product_context,
            stimulus_type=stimulus_type,
            stimulus_artifact=stimulus_artifact,
            prototype_task=prototype_task,
        )
        concept = load_concept_protocol(concept_protocol, label=concept_label) if mode == "concept_validation" else None

        persona_folder = resolve_persona_folder(self.data_dir, persona_id)
        persona = load_persona(persona_folder)
        persona_name = str(persona.profile.basic_identity.get("name", persona_id))
        interview_id = f"interview_{utc_now_iso()[:10].replace('-', '')}_{uuid.uuid4().hex[:8]}"
        interview_folder = self.session_dir / interview_id
        ensure_dir(interview_folder)
        prepared_stimulus = self._prepare_stimulus_context(
            interview_folder=interview_folder,
            interview_mode=mode,
            product_context=product_context.strip(),
            stimulus_type=resolved_stimulus_type,
            stimulus_artifact=stimulus_artifact.strip(),
            prototype_task=prototype_task.strip(),
        )

        persona_runtime = ConversationRuntime(
            data_dir=self.data_dir,
            session_dir=interview_folder / "persona_runtime",
            provider=self.persona_provider,
        )
        persona_session, _, _ = persona_runtime.start(persona_id, friction_mode=validate_friction_mode(friction_mode))
        session = InterviewSession(
            interview_id=interview_id,
            persona_id=persona_id,
            persona_name=persona_name,
            research_goal=research_goal.strip(),
            product_context=product_context.strip(),
            output_language=output_language.strip() or "Traditional Chinese",
            facilitator_provider=self.facilitator_provider.provider_name,
            facilitator_model=self.facilitator_provider.model_name,
            persona_provider=self.persona_provider.provider_name,
            persona_model=self.persona_provider.model_name,
            facilitator_prompt_version=FACILITATOR_PROMPT_VERSION,
            synthesis_prompt_version=(
                CONCEPT_SYNTHESIS_PROMPT_VERSION if mode == "concept_validation"
                else PROTOTYPE_SYNTHESIS_PROMPT_VERSION if mode == "prototype_validation"
                else SYNTHESIS_PROMPT_VERSION
            ),
            concept_protocol_version=concept.identifier if concept else "",
            concept_label=concept.label if concept else "",
            stimulus_type=resolved_stimulus_type,
            stimulus_artifact=prepared_stimulus["stimulus_artifact"],
            stimulus_artifact_snapshot=prepared_stimulus["stimulus_artifact_snapshot"],
            stimulus_analysis_prompt_version=prepared_stimulus["stimulus_analysis_prompt_version"],
            stimulus_analysis_provider_session_id=prepared_stimulus["stimulus_analysis_provider_session_id"],
            stimulus_analysis=prepared_stimulus["stimulus_analysis"],
            observed_action_trace=prepared_stimulus["observed_action_trace"],
            prototype_task=prototype_task.strip(),
            hypothesis_evidence_judge_prompt_version=HYPOTHESIS_EVIDENCE_JUDGE_PROMPT_VERSION,
            interview_mode=mode,
            hypothesis=hypothesis.strip(),
            persona_conversation_session_id=persona_session.session_id,
            persona_friction_mode=persona_session.friction_mode,
            persona_driver_trace_prompt_version=DRIVER_TRACE_PROMPT_VERSION,
            max_turns=hard_limit,
            soft_turn_limit=soft_limit,
            hard_turn_limit=hard_limit,
        )
        self._update_coverage_status(session)
        self._annotate_approved_learning_rules(session)
        self._save(session, interview_folder)
        self._progress(
            f"start interview_id={interview_id} persona={persona_id} mode={mode} "
            f"soft={soft_limit} hard={hard_limit}"
        )

        facilitator_system = self._facilitator_system_prompt(session)
        self._progress("requesting_initial_facilitator_question")
        decision = self.facilitator_provider.next_turn(
            system_prompt=facilitator_system,
            user_prompt=self._opening_prompt(session),
        )
        decision = self._revise_non_episodic_validation_question(session, decision, facilitator_system)

        while len(session.exchanges) < session.hard_turn_limit:
            self._record_decision(session, decision)
            if decision.should_end:
                self._mark_latest_decision_status(session, "ended_interview")
                session.stop_reason = decision.end_reason or "facilitator_decided_evidence_was_sufficient"
                break

            self.observer("facilitator", decision.message_to_persona)
            self._progress(
                f"asking_persona exchange={len(session.exchanges) + 1} "
                f"phase={decision.interview_phase} strategy={decision.probing_strategy}"
            )
            persona_reply = persona_runtime.send(
                persona_session,
                persona,
                persona_folder,
                decision.message_to_persona,
                runtime_instruction=self._persona_interview_instruction(),
            )
            self.observer("persona", persona_reply)
            self._progress(
                f"received_persona_response exchange={len(session.exchanges) + 1} chars={len(persona_reply)}"
            )
            exchange = InterviewExchange(
                exchange_id=len(session.exchanges) + 1,
                facilitator_question=decision.message_to_persona,
                persona_response=persona_reply,
                facilitator_phase=decision.interview_phase,
                probing_strategy=decision.probing_strategy,
                question_evidence_basis=self._effective_question_basis(
                    decision.message_to_persona, decision.question_evidence_basis
                ),
                question_evidence_target=decision.question_evidence_target,
            )
            session.exchanges.append(exchange)
            self._mark_latest_decision_status(session, "asked")
            session.persona_provider_session_id = persona_session.provider_session_id
            self._update_coverage_status(session)
            session.updated_at = utc_now_iso()
            self._save(session, interview_folder)

            if self._should_finalize_after_exchange(session):
                self._progress(f"coverage_complete stop_reason={session.stop_reason}")
                break

            self._progress("requesting_next_facilitator_question")
            decision = self.facilitator_provider.next_turn(
                system_prompt=facilitator_system,
                user_prompt=self._continuation_prompt(session),
                provider_session_id=session.facilitator_provider_session_id,
            )
            decision = self._revise_non_episodic_validation_question(session, decision, facilitator_system)

        if session.interview_mode == "validate_hypothesis":
            self._progress("judging_hypothesis_evidence")
            judgment, judge_session_id = self._judge_hypothesis_evidence(session)
            session.hypothesis_evidence_judgment = judgment
            session.hypothesis_evidence_judge_provider_session_id = judge_session_id
            write_json(interview_folder / "hypothesis_evidence_judgment.json", judgment)

        session.status = "synthesizing"
        self._progress("synthesizing_insights")
        if session.interview_mode == "concept_validation":
            synthesis, facilitator_session_id = self.facilitator_provider.synthesize_concept(
                system_prompt=self._synthesis_system_prompt("concept_validation"),
                user_prompt=self._synthesis_user_prompt(session),
                provider_session_id=session.facilitator_provider_session_id,
            )
        elif session.interview_mode == "prototype_validation":
            synthesis, facilitator_session_id = self.facilitator_provider.synthesize_prototype(
                system_prompt=self._synthesis_system_prompt("prototype_validation"),
                user_prompt=self._synthesis_user_prompt(session),
                provider_session_id=session.facilitator_provider_session_id,
            )
        else:
            synthesis, facilitator_session_id = self.facilitator_provider.synthesize(
                system_prompt=self._synthesis_system_prompt(session.interview_mode),
                user_prompt=self._synthesis_user_prompt(session),
                provider_session_id=session.facilitator_provider_session_id,
            )
        self._enforce_synthesis_evidence_scope(session, synthesis)
        self._enforce_prototype_evidence_boundary(session, synthesis)
        session.facilitator_provider_session_id = facilitator_session_id
        persona_runtime.close(persona_session)
        conversation_realism = self._persona_conversation_realism(interview_folder, session)
        synthesis = attach_over_optimism_risks(
            synthesis,
            conversation_realism=conversation_realism,
            interview_mode=session.interview_mode,
        )
        session.insight_report = synthesis
        self._progress("generating_persona_driver_trace")
        driver_trace, trace_session_id = persona_runtime.generate_persona_driver_trace(
            persona_session,
            persona,
            persona_folder,
            interview_transcript=self._plain_transcript(session),
            research_goal=session.research_goal,
            product_context=session.product_context,
            output_language=session.output_language,
        )
        session.persona_driver_trace = driver_trace
        session.persona_driver_trace_provider_session_id = trace_session_id
        session.status = "completed"
        session.updated_at = utc_now_iso()
        self._save(session, interview_folder)
        write_json(interview_folder / "insight_report.json", synthesis)
        write_json(interview_folder / "persona_driver_trace.json", driver_trace)
        (interview_folder / "insights.md").write_text(self._render_insights(session), encoding="utf-8")
        (interview_folder / "persona_driver_trace.md").write_text(
            self._render_persona_driver_trace(session),
            encoding="utf-8",
        )
        self._progress(f"completed interview_id={interview_id}")
        return interview_folder

    @staticmethod
    def _persona_conversation_realism(interview_folder: Path, session: InterviewSession) -> dict[str, Any]:
        if not session.persona_conversation_session_id:
            return {}
        report_path = (
            interview_folder
            / "persona_runtime"
            / session.persona_conversation_session_id
            / "conversation_realism_report.json"
        )
        if not report_path.exists():
            return {}
        return json.loads(report_path.read_text(encoding="utf-8"))

    @staticmethod
    def _resolve_turn_limits(
        *,
        max_turns: int = 10,
        soft_turn_limit: int | None = None,
        hard_turn_limit: int | None = None,
    ) -> tuple[int, int]:
        soft_limit = max_turns if soft_turn_limit is None else soft_turn_limit
        hard_limit = max_turns if hard_turn_limit is None else hard_turn_limit
        if soft_limit < 1:
            raise ValueError("soft_turn_limit must be at least 1.")
        if hard_limit < 1:
            raise ValueError("hard_turn_limit must be at least 1.")
        if soft_limit > hard_limit:
            raise ValueError("soft_turn_limit cannot exceed hard_turn_limit.")
        return soft_limit, hard_limit

    @staticmethod
    def _coverage_requirements(interview_mode: str) -> tuple[str, ...]:
        if interview_mode == "concept_validation":
            return CONCEPT_VALIDATION_COVERAGE_REQUIREMENTS
        if interview_mode == "prototype_validation":
            return PROTOTYPE_VALIDATION_COVERAGE_REQUIREMENTS
        if interview_mode == "adoption_barrier_validation":
            return ADOPTION_BARRIER_VALIDATION_COVERAGE_REQUIREMENTS
        if interview_mode == "decision_reconstruction":
            return DECISION_RECONSTRUCTION_COVERAGE_REQUIREMENTS
        if interview_mode == "pain_point_discovery":
            return PAIN_POINT_DISCOVERY_COVERAGE_REQUIREMENTS
        if interview_mode == "validate_hypothesis":
            return HYPOTHESIS_VALIDATION_COVERAGE_REQUIREMENTS
        return ROOT_CAUSE_COVERAGE_REQUIREMENTS

    @staticmethod
    def _depth_requirements(interview_mode: str) -> tuple[str, ...]:
        if interview_mode == "concept_validation":
            return CONCEPT_VALIDATION_DEPTH_REQUIREMENTS
        return ()

    @staticmethod
    def _normalize_probe_text(value: str) -> str:
        return (value or "").casefold().replace("-", "_").replace(" ", "_")

    @staticmethod
    def _question_indicates_threshold(question: str) -> bool:
        lowered = question.casefold()
        markers = (
            "what exact",
            "what would make",
            "what would still",
            "what would be enough",
            "what would count as",
            "what kind of change",
            "how much",
            "minimum",
            "clear enough",
            "stop trusting",
            "too vague",
            "too pushy",
            "meaningful change",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _question_indicates_contrast(question: str) -> bool:
        lowered = question.casefold()
        markers = (
            "if only",
            "would it still",
            "would you still",
            "when would you ignore",
            "when would it not",
            "what if it only",
            "which matters more",
            "which one matters more",
            "or would it",
            "rather than",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _question_indicates_driver_deepening(question: str) -> bool:
        lowered = question.casefold()
        markers = (
            "what mistake",
            "what failure",
            "what would you need to see",
            "what would break trust",
            "why that",
            "which one by itself",
            "which one would",
            "what does each",
            "what job",
            "what gap",
            "what protects against",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _question_mentions_specific_output(question: str) -> bool:
        lowered = question.casefold()
        markers = (
            "concentration",
            "allocation",
            "risk profile",
            "risk-profile",
            "mismatch",
            "exposure",
            "sector",
            "region",
            "country",
            "currency",
            "fx",
            "stress test",
            "scenario",
            "drawdown",
            "attribution",
            "factor",
            "volatility",
            "alert",
            "cash flow",
            "income impact",
            "goal success",
            "interest rate",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _question_mentions_decision_mapping(question: str) -> bool:
        lowered = question.casefold()
        markers = (
            "what would you do",
            "would you do anything",
            "would you change",
            "would it change",
            "would that make you",
            "would that be enough to",
            "would you still hold",
            "would you keep holding",
            "would you wait",
            "would you ignore",
            "would you leave it",
            "would you reduce",
            "would you rebalance",
            "would you sell",
            "would you buy",
            "would you top up",
            "would you move",
            "would you stay with",
            "or still do nothing",
            "or would you still not",
            "or would you still wait",
            "rather than just",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _question_mentions_missing_evidence(question: str) -> bool:
        lowered = question.casefold()
        markers = (
            "what evidence was missing",
            "what was still missing",
            "what did you still not know",
            "what was still unclear",
            "what would you still need to know",
            "what was the gap",
            "missing evidence",
            "evidence gap",
            "仲差咩證據",
            "仲未有咩 evidence",
            "仲未清楚咩",
            "仲未知咩",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _question_mentions_pressure(question: str) -> bool:
        lowered = question.casefold()
        markers = (
            "what pressure",
            "who was pushing",
            "what made waiting costly",
            "what made it urgent",
            "what deadline",
            "how much time",
            "stakeholder pressure",
            "time pressure",
            "runway",
            "delivery pressure",
            "邊個催",
            "有咩壓力",
            "時間壓力",
            "點解等唔到",
            "趕住",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _question_mentions_defensibility(question: str) -> bool:
        lowered = question.casefold()
        markers = (
            "what could you defend",
            "what could you say in the room",
            "what were you less sure about",
            "what still worried you",
            "what still felt shaky",
            "publicly",
            "privately",
            "defend publicly",
            "private worry",
            "公開",
            "心入面",
            "其實仲唔穩",
            "仲擔心咩",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _question_mentions_decision_change(question: str) -> bool:
        lowered = question.casefold()
        markers = (
            "what did you change",
            "what changed in the end",
            "what did you delay",
            "what did you cut",
            "what shipped first",
            "what moved later",
            "what did you prioritize",
            "what became lower priority",
            "go or no-go",
            "scope",
            "sequence",
            "priority",
            "最後改咗咩",
            "最後實際改",
            "延後",
            "優先次序",
            "先做邊個",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _concept_intro_prerequisite_flags(
        *,
        question: str,
        phase: str,
        strategy: str,
        basis: str,
    ) -> dict[str, bool]:
        normalized_phase = FacilitatedInterviewRuntime._normalize_probe_text(phase)
        normalized_strategy = FacilitatedInterviewRuntime._normalize_probe_text(strategy)
        event_like_basis = basis in {"current_event", "recalled_contrast_event"}
        recent_real_decision = (
            basis == "current_event"
            and (
                "recent" in normalized_phase
                or "event" in normalized_phase
                or "incident" in normalized_phase
                or "recent" in normalized_strategy
                or "event" in normalized_strategy
            )
        )
        missing_evidence = event_like_basis and (
            "missing_evidence" in normalized_phase
            or "missing_evidence" in normalized_strategy
            or "evidence_gap" in normalized_phase
            or "evidence_gap" in normalized_strategy
            or FacilitatedInterviewRuntime._question_mentions_missing_evidence(question)
        )
        pressure = event_like_basis and (
            "pressure" in normalized_phase
            or "pressure" in normalized_strategy
            or "stakeholder" in normalized_phase
            or "stakeholder" in normalized_strategy
            or FacilitatedInterviewRuntime._question_mentions_pressure(question)
        )
        defensible_vs_uncertain = event_like_basis and (
            "defensibility" in normalized_phase
            or "defensibility" in normalized_strategy
            or "public_private" in normalized_phase
            or "public_private" in normalized_strategy
            or FacilitatedInterviewRuntime._question_mentions_defensibility(question)
        )
        decision_change = event_like_basis and (
            "decision_outcome" in normalized_phase
            or "decision_outcome" in normalized_strategy
            or "tradeoff" in normalized_phase
            or "tradeoff" in normalized_strategy
            or "priority" in normalized_phase
            or "priority" in normalized_strategy
            or "scope" in normalized_phase
            or "scope" in normalized_strategy
            or "sequence" in normalized_phase
            or "sequence" in normalized_strategy
            or "go_no_go" in normalized_phase
            or "go_no_go" in normalized_strategy
            or FacilitatedInterviewRuntime._question_mentions_decision_change(question)
        )
        return {
            "recent_real_decision": recent_real_decision,
            "missing_evidence": missing_evidence,
            "pressure": pressure,
            "defensible_vs_uncertain": defensible_vs_uncertain,
            "decision_change": decision_change,
        }

    @staticmethod
    def _concept_intro_prerequisite_status(session: InterviewSession) -> dict[str, Any]:
        covered = {item: False for item in CONCEPT_INTRO_PREREQUISITES}
        for exchange in session.exchanges:
            basis = FacilitatedInterviewRuntime._effective_question_basis(
                exchange.facilitator_question,
                exchange.question_evidence_basis,
            )
            flags = FacilitatedInterviewRuntime._concept_intro_prerequisite_flags(
                question=exchange.facilitator_question,
                phase=exchange.facilitator_phase,
                strategy=exchange.probing_strategy,
                basis=basis,
            )
            for item in CONCEPT_INTRO_PREREQUISITES:
                if flags.get(item):
                    covered[item] = True
        return {
            "required": list(CONCEPT_INTRO_PREREQUISITES),
            "covered": {item: bool(covered[item]) for item in CONCEPT_INTRO_PREREQUISITES},
            "missing": [item for item in CONCEPT_INTRO_PREREQUISITES if not covered[item]],
            "ready": all(covered.values()),
        }

    @staticmethod
    def _decision_reconstruction_coverage_status(session: InterviewSession) -> dict[str, Any]:
        covered = {item: False for item in DECISION_RECONSTRUCTION_COVERAGE_REQUIREMENTS}
        for exchange in session.exchanges:
            basis = FacilitatedInterviewRuntime._effective_question_basis(
                exchange.facilitator_question,
                exchange.question_evidence_basis,
            )
            flags = FacilitatedInterviewRuntime._concept_intro_prerequisite_flags(
                question=exchange.facilitator_question,
                phase=exchange.facilitator_phase,
                strategy=exchange.probing_strategy,
                basis=basis,
            )
            for item in DECISION_RECONSTRUCTION_COVERAGE_REQUIREMENTS:
                if flags.get(item):
                    covered[item] = True
        return {
            "required": list(DECISION_RECONSTRUCTION_COVERAGE_REQUIREMENTS),
            "covered": {item: bool(covered[item]) for item in DECISION_RECONSTRUCTION_COVERAGE_REQUIREMENTS},
            "missing": [item for item in DECISION_RECONSTRUCTION_COVERAGE_REQUIREMENTS if not covered[item]],
            "ready": all(covered.values()),
        }

    @staticmethod
    def _concept_already_introduced(session: InterviewSession) -> bool:
        return any(
            "concept" in FacilitatedInterviewRuntime._normalize_probe_text(exchange.facilitator_phase)
            or "scenario" in FacilitatedInterviewRuntime._normalize_probe_text(exchange.facilitator_phase)
            or "concept" in FacilitatedInterviewRuntime._normalize_probe_text(exchange.probing_strategy)
            for exchange in session.exchanges
        )

    @staticmethod
    def _decision_attempts_concept_progression(
        session: InterviewSession,
        decision: FacilitatorDecision,
    ) -> bool:
        if decision.should_end:
            return False
        if FacilitatedInterviewRuntime._concept_already_introduced(session):
            return False
        basis = FacilitatedInterviewRuntime._effective_question_basis(
            decision.message_to_persona,
            decision.question_evidence_basis,
        )
        normalized_phase = FacilitatedInterviewRuntime._normalize_probe_text(decision.interview_phase)
        normalized_strategy = FacilitatedInterviewRuntime._normalize_probe_text(decision.probing_strategy)
        if basis == "hypothetical":
            return True
        concept_markers = (
            "concept",
            "scenario",
            "reaction",
            "fit",
            "setup",
            "activation",
            "onboard",
            "permission",
            "approval",
            "access",
            "trust",
            "pricing",
            "payment",
            "budget",
            "retention",
            "repeat",
            "revers",
            "undo",
            "rollback",
            "service_embedding",
            "workflow_insertion",
            "workflow",
            "routine",
            "burden",
            "adoption",
            "output_to_decision",
            "decision_mapping",
        )
        return (
            any(marker in normalized_phase for marker in concept_markers)
            or any(marker in normalized_strategy for marker in concept_markers)
        )

    @staticmethod
    def _concept_intro_gap_instruction(gap: str) -> tuple[str, str]:
        mapping = {
            "recent_real_decision": (
                "recent_event",
                "Ask for one specific recent real decision event before any concept exposure.",
            ),
            "missing_evidence": (
                "missing_evidence_probe",
                "Ask what evidence was still missing in that real decision and what they still could not tell.",
            ),
            "pressure": (
                "pressure_probe",
                "Ask what stakeholder, timing, runway, or delivery pressure made waiting costly in that real decision.",
            ),
            "defensible_vs_uncertain": (
                "defensibility_probe",
                "Ask what they could defend publicly in that decision and what still felt privately uncertain.",
            ),
            "decision_change": (
                "decision_outcome_probe",
                "Ask what actually changed in scope, sequence, priority, or go-no-go because of that decision.",
            ),
        }
        return mapping.get(
            gap,
            (
                "recent_event",
                "Ask one short current-state question that fills the highest-value missing pre-concept evidence gap.",
            ),
        )

    @staticmethod
    def _adoption_barrier_gap_instruction(gap: str) -> tuple[str, str]:
        mapping = {
            "recent_behaviour": (
                "recent_event",
                "Ask for one recent real moment when they handled this job or problem in practice.",
            ),
            "current_workaround": (
                "current_workaround",
                "Ask what they do today instead, and what the current workaround already protects against.",
            ),
            "setup_burden": (
                "setup_burden",
                "Ask what setup, onboarding, or activation effort would already feel too heavy before routine use starts.",
            ),
            "permission_boundary": (
                "permission_boundary",
                "Ask what data access, approvals, stakeholder sign-off, or coordination permission would block trial or use.",
            ),
            "trust_boundary": (
                "trust_boundary",
                "Ask what trust proof, accuracy threshold, or risk explanation they would need before relying on it.",
            ),
            "pricing_condition": (
                "pricing_condition",
                "Ask what payment, budget, or value-for-cost condition would need to be true before adoption feels defensible.",
            ),
            "reversibility": (
                "reversibility_probe",
                "Ask how easy it must be to undo, exit, turn off, or back out if it does not work as expected.",
            ),
            "workflow_burden": (
                "workflow_burden",
                "Ask what extra routine step, habit change, or workflow burden would stop repeated use even if the value sounds real.",
            ),
        }
        return mapping.get(
            gap,
            (
                "adoption_barrier_probe",
                "Ask one short adoption-friction question that fills the highest-value missing barrier gap.",
            ),
        )

    @staticmethod
    def _prototype_validation_gap_instruction(gap: str) -> tuple[str, str]:
        mapping = {
            "stimulus_interpretation": (
                "stimulus_interpretation",
                "Ask what they think this prototype, screen, or flow is doing before testing preference or value.",
            ),
            "first_action_expectation": (
                "first_action_expectation",
                "Ask what they would try first or where they would click, tap, or look first for the task.",
            ),
            "task_path_expectation": (
                "task_path_expectation",
                "Ask how they expect the task to unfold step by step from the current stimulus.",
            ),
            "setup_confusion": (
                "setup_confusion",
                "Ask where setup, onboarding, permissions, or required input would likely confuse or slow them down.",
            ),
            "trust_boundary": (
                "trust_boundary",
                "Ask what would make the prototype feel safe or unsafe enough to rely on during the task.",
            ),
            "breakdown_or_dropoff": (
                "breakdown_or_dropoff",
                "Ask where they would hesitate, back out, or stop if this were a real task attempt.",
            ),
            "task_completion_signal": (
                "task_completion_signal",
                "Ask what result would tell them the task actually worked or was completed correctly.",
            ),
        }
        return mapping.get(
            gap,
            (
                "prototype_probe",
                "Ask one short prototype-specific task question that fills the highest-value missing coverage gap.",
            ),
        )

    @staticmethod
    def _depth_probe_flags(
        *,
        question: str,
        phase: str,
        strategy: str,
        target: str,
        basis: str,
    ) -> dict[str, bool]:
        normalized_phase = FacilitatedInterviewRuntime._normalize_probe_text(phase)
        normalized_strategy = FacilitatedInterviewRuntime._normalize_probe_text(strategy)
        normalized_target = FacilitatedInterviewRuntime._normalize_probe_text(target)
        threshold_keywords = (
            "threshold",
            "credibility",
            "materiality",
            "proof",
            "priority",
            "ranking",
            "trust_source",
            "action_threshold",
        )
        contrast_keywords = (
            "contrast",
            "counterexample",
            "disconfirm",
            "non_use",
            "tradeoff",
            "opposite",
        )
        deepening_keywords = (
            "driver",
            "deepen",
            "workaround_function",
            "trust_source",
            "action_threshold",
            "tradeoff",
            "priority",
            "ranking",
            "threshold",
        )
        output_mapping_keywords = (
            "output_to_decision",
            "decision_mapping",
            "function_to_decision",
            "analytic_mapping",
            "output_mapping",
            "decision_threshold",
        )
        threshold_probe = (
            any(keyword in normalized_strategy for keyword in threshold_keywords)
            or any(keyword in normalized_phase for keyword in threshold_keywords)
            or FacilitatedInterviewRuntime._question_indicates_threshold(question)
        )
        contrast_probe = (
            basis == "recalled_contrast_event"
            or normalized_target == "alternative_condition"
            or any(keyword in normalized_strategy for keyword in contrast_keywords)
            or any(keyword in normalized_phase for keyword in contrast_keywords)
            or FacilitatedInterviewRuntime._question_indicates_contrast(question)
        )
        driver_deepening_probe = (
            any(keyword in normalized_strategy for keyword in deepening_keywords)
            or any(keyword in normalized_phase for keyword in deepening_keywords)
            or FacilitatedInterviewRuntime._question_indicates_driver_deepening(question)
        )
        output_to_decision_probe = (
            any(keyword in normalized_strategy for keyword in output_mapping_keywords)
            or any(keyword in normalized_phase for keyword in output_mapping_keywords)
            or (
                FacilitatedInterviewRuntime._question_mentions_specific_output(question)
                and FacilitatedInterviewRuntime._question_mentions_decision_mapping(question)
            )
        )
        return {
            "threshold_probe": threshold_probe,
            "contrast_probe": contrast_probe,
            "driver_deepening_probe": driver_deepening_probe,
            "output_to_decision_probe": output_to_decision_probe,
        }

    @staticmethod
    def _update_coverage_status(session: InterviewSession) -> None:
        if session.interview_mode == "decision_reconstruction":
            decision_gate = FacilitatedInterviewRuntime._decision_reconstruction_coverage_status(session)
            session.coverage_status = {
                "requirements": decision_gate["required"],
                "covered": decision_gate["covered"],
                "missing": decision_gate["missing"],
                "coverage_complete": decision_gate["ready"],
                "depth_requirements": [],
                "depth_covered": {},
                "depth_missing": [],
                "depth_complete": True,
                "soft_limit_reached": len(session.exchanges) >= session.soft_turn_limit,
                "hard_limit_reached": len(session.exchanges) >= session.hard_turn_limit,
                "exchange_count": len(session.exchanges),
            }
            return
        requirements = FacilitatedInterviewRuntime._coverage_requirements(session.interview_mode)
        depth_requirements = FacilitatedInterviewRuntime._depth_requirements(session.interview_mode)
        covered = {item: False for item in requirements}
        depth_covered = {item: False for item in depth_requirements}
        for exchange in session.exchanges:
            basis = FacilitatedInterviewRuntime._effective_question_basis(
                exchange.facilitator_question,
                exchange.question_evidence_basis,
            )
            phase = exchange.facilitator_phase.casefold()
            strategy = exchange.probing_strategy.casefold()
            labels = f"{phase} {strategy}"
            target = (exchange.question_evidence_target or "context").casefold()
            if "recent_behaviour" in covered and ("recent" in labels or "event" in labels or "warm" in labels):
                covered["recent_behaviour"] = True
            if "current_workaround" in covered and ("workflow" in labels or "workaround" in labels or "current" in labels):
                covered["current_workaround"] = True
            if "problem_reality" in covered and (
                "problem" in labels or "pain" in labels or "severity" in labels or "reality" in labels
            ):
                covered["problem_reality"] = True
            if "frequency" in covered and (
                "frequency" in labels or "recurrence" in labels or "repeat" in labels or "pattern" in labels
            ):
                covered["frequency"] = True
            if "concept_reaction" in covered and ("concept" in labels or "scenario" in labels or "reaction" in labels or "fit" in labels):
                covered["concept_reaction"] = True
            if "stimulus_interpretation" in covered and (
                "stimulus" in labels or "interpret" in labels or "understand" in labels or "comprehension" in labels
            ):
                covered["stimulus_interpretation"] = True
            if "first_action_expectation" in covered and (
                "first_action" in labels or "first_step" in labels or "first_click" in labels
            ):
                covered["first_action_expectation"] = True
            if "task_path_expectation" in covered and (
                "task_path" in labels or "journey" in labels or "sequence" in labels or "path" in labels
            ):
                covered["task_path_expectation"] = True
            if "setup_burden" in covered and (
                "setup" in labels or "activation" in labels or "onboard" in labels or "install" in labels
            ):
                covered["setup_burden"] = True
            if "setup_confusion" in covered and (
                "setup" in labels or "activation" in labels or "onboard" in labels or "confusion" in labels
            ):
                covered["setup_confusion"] = True
            if "permission_boundary" in covered and (
                "permission" in labels or "approval" in labels or "access" in labels or "sign_off" in labels
            ):
                covered["permission_boundary"] = True
            if "trust_boundary" in covered and ("trust" in labels or "privacy" in labels or "data" in labels):
                covered["trust_boundary"] = True
            if "action_followthrough" in covered and (
                "action" in labels or "follow" in labels or "next_step" in labels or "decision" in labels
            ):
                covered["action_followthrough"] = True
            if "pricing_condition" in covered and (
                "pricing" in labels or "payment" in labels or "budget" in labels or "price" in labels or "cost" in labels
            ):
                covered["pricing_condition"] = True
            if "reversibility" in covered and (
                "revers" in labels or "undo" in labels or "rollback" in labels or "exit" in labels or "cancel" in labels
            ):
                covered["reversibility"] = True
            if "repeat_use_condition" in covered and (
                "retention" in labels or "repeat" in labels or "month" in labels or "habit" in labels
            ):
                covered["repeat_use_condition"] = True
            if "workflow_burden" in covered and (
                "workflow" in labels or "routine" in labels or "habit" in labels or "friction" in labels
                or "integration" in labels or "extra_step" in labels
            ):
                covered["workflow_burden"] = True
            if "breakdown_or_dropoff" in covered and (
                "drop" in labels or "breakdown" in labels or "hesitation" in labels or "abandon" in labels
                or "confusion" in labels or "failure" in labels
            ):
                covered["breakdown_or_dropoff"] = True
            if "task_completion_signal" in covered and (
                "completion" in labels or "success" in labels or "done" in labels or "finished" in labels
            ):
                covered["task_completion_signal"] = True
            if "service_embedding" in covered and (
                "embed" in labels or "journey" in labels or "channel" in labels or "placement" in labels
                or "workflow" in labels or "rm" in labels
            ):
                covered["service_embedding"] = True
            if "target_behaviour" in covered and (target == "target_behaviour" or basis == "current_event"):
                covered["target_behaviour"] = True
            if "participant_cause" in covered and (target == "participant_cause" or "cause" in labels or "root_cause" in labels):
                covered["participant_cause"] = True
            if "consequence" in covered and (target == "consequence" or "consequence" in labels):
                covered["consequence"] = True
            if "hypothesis_condition" in covered and target == "hypothesis_condition":
                covered["hypothesis_condition"] = True
            if "alternative_condition" in covered and (target == "alternative_condition" or "counterexample" in labels or "contrast" in labels):
                covered["alternative_condition"] = True
            depth_flags = FacilitatedInterviewRuntime._depth_probe_flags(
                question=exchange.facilitator_question,
                phase=exchange.facilitator_phase,
                strategy=exchange.probing_strategy,
                target=exchange.question_evidence_target,
                basis=basis,
            )
            for item in depth_requirements:
                if depth_flags.get(item):
                    depth_covered[item] = True
        session.coverage_status = {
            "requirements": list(requirements),
            "covered": {key: bool(covered.get(key, False)) for key in requirements},
            "missing": [key for key in requirements if not covered.get(key, False)],
            "coverage_complete": all(covered.get(key, False) for key in requirements),
            "depth_requirements": list(depth_requirements),
            "depth_covered": {key: bool(depth_covered.get(key, False)) for key in depth_requirements},
            "depth_missing": [key for key in depth_requirements if not depth_covered.get(key, False)],
            "depth_complete": all(depth_covered.get(key, False) for key in depth_requirements),
            "soft_limit_reached": len(session.exchanges) >= session.soft_turn_limit,
            "hard_limit_reached": len(session.exchanges) >= session.hard_turn_limit,
            "exchange_count": len(session.exchanges),
        }
        if session.interview_mode == "concept_validation":
            concept_gate = FacilitatedInterviewRuntime._concept_intro_prerequisite_status(session)
            session.coverage_status["concept_intro_prerequisites"] = concept_gate
            session.coverage_status["concept_intro_allowed"] = concept_gate["ready"]
        if session.interview_mode == "adoption_barrier_validation":
            adoption_gate_required = ("recent_behaviour", "current_workaround")
            adoption_gate = {
                "required": list(adoption_gate_required),
                "covered": {
                    key: bool(session.coverage_status["covered"].get(key, False))
                    for key in adoption_gate_required
                },
            }
            adoption_gate["missing"] = [
                key for key in adoption_gate_required if not adoption_gate["covered"].get(key, False)
            ]
            adoption_gate["ready"] = not adoption_gate["missing"]
            session.coverage_status["adoption_intro_prerequisites"] = adoption_gate
            session.coverage_status["adoption_intro_allowed"] = adoption_gate["ready"]

    @staticmethod
    def _should_finalize_after_exchange(session: InterviewSession) -> bool:
        FacilitatedInterviewRuntime._update_coverage_status(session)
        if len(session.exchanges) >= session.hard_turn_limit:
            session.stop_reason = "hard_turn_limit_reached"
            return True
        if len(session.exchanges) < session.soft_turn_limit:
            return False
        if (
            session.coverage_status.get("coverage_complete")
            and session.coverage_status.get("depth_complete", True)
        ):
            session.stop_reason = "soft_turn_limit_with_required_coverage_met"
            return True
        return False

    @staticmethod
    def _record_decision(session: InterviewSession, decision: FacilitatorDecision) -> None:
        payload = decision.to_dict()
        payload["question_evidence_basis"] = FacilitatedInterviewRuntime._effective_question_basis(
            decision.message_to_persona, decision.question_evidence_basis
        )
        payload["decision_status"] = "proposed"
        session.facilitator_decisions.append(payload)
        if decision.provider_session_id:
            session.facilitator_provider_session_id = decision.provider_session_id

    @staticmethod
    def _mark_latest_decision_status(session: InterviewSession, status: str) -> None:
        for decision in reversed(session.facilitator_decisions):
            if decision.get("decision_status") == "proposed":
                decision["decision_status"] = status
                return

    def _revise_non_episodic_validation_question(
        self,
        session: InterviewSession,
        decision: FacilitatorDecision,
        system_prompt: str,
    ) -> FacilitatorDecision:
        basis = self._effective_question_basis(decision.message_to_persona, decision.question_evidence_basis)
        if session.interview_mode == "concept_validation":
            self._update_coverage_status(session)
            concept_gate = session.coverage_status.get("concept_intro_prerequisites", {})
            if (
                not concept_gate.get("ready", False)
                and self._decision_attempts_concept_progression(session, decision)
            ):
                missing = concept_gate.get("missing", [])
                next_gap = missing[0] if missing else "recent_real_decision"
                phase_hint, gap_instruction = self._concept_intro_gap_instruction(next_gap)
                rejected = decision.to_dict()
                rejected["question_evidence_basis"] = basis
                rejected["decision_status"] = "rejected_by_concept_timing_gate"
                session.facilitator_decisions.append(rejected)
                correction = (
                    "CONCEPT TIMING GATE: Do not introduce or advance the AI synthetic-user concept yet. "
                    "In concept-validation mode, the current-state interview must first cover five participant-facing "
                    "items from one recent real decision: the event itself, missing evidence, stakeholder/time pressure, "
                    "what was publicly defensible versus privately uncertain, and what actually changed in scope, sequence, "
                    "priority, or go-no-go. "
                    f"Current missing prerequisites: {', '.join(missing) or '(none listed)'}. "
                    f"Ask one short, neutral current-state question next. Use a phase or strategy label like "
                    f"'{phase_hint}' so the runtime can audit the gap. {gap_instruction} "
                    "Do not mention the concept, synthetic users, AI, trust, pricing, retention, or workflow fit in this turn.\n\n"
                    f"REJECTED QUESTION:\n{decision.message_to_persona}\n\n"
                    f"TRANSCRIPT:\n{self._plain_transcript(session)}"
                )
                return self.facilitator_provider.next_turn(
                    system_prompt=system_prompt,
                    user_prompt=correction,
                    provider_session_id=decision.provider_session_id or session.facilitator_provider_session_id,
                )
        if session.interview_mode == "adoption_barrier_validation":
            self._update_coverage_status(session)
            adoption_gate = session.coverage_status.get("adoption_intro_prerequisites", {})
            if (
                not adoption_gate.get("ready", False)
                and self._decision_attempts_concept_progression(session, decision)
            ):
                missing = adoption_gate.get("missing", [])
                next_gap = missing[0] if missing else "recent_behaviour"
                phase_hint, gap_instruction = self._adoption_barrier_gap_instruction(next_gap)
                rejected = decision.to_dict()
                rejected["question_evidence_basis"] = basis
                rejected["decision_status"] = "rejected_by_adoption_timing_gate"
                session.facilitator_decisions.append(rejected)
                correction = (
                    "ADOPTION BARRIER TIMING GATE: Do not test setup, permissions, trust, pricing, reversibility, "
                    "or workflow burden yet. In adoption-barrier mode, first anchor the interview in one recent real "
                    "behavior and the current workaround. "
                    f"Current missing prerequisites: {', '.join(missing) or '(none listed)'}. "
                    f"Ask one short current-state question next. Use a phase or strategy label like '{phase_hint}' "
                    f"so the runtime can audit the gap. {gap_instruction} "
                    "Do not ask hypothetical adoption, payment, trust, or routine-use questions in this turn.\n\n"
                    f"REJECTED QUESTION:\n{decision.message_to_persona}\n\n"
                    f"TRANSCRIPT:\n{self._plain_transcript(session)}"
                )
                return self.facilitator_provider.next_turn(
                    system_prompt=system_prompt,
                    user_prompt=correction,
                    provider_session_id=decision.provider_session_id or session.facilitator_provider_session_id,
                )
            missing = list(session.coverage_status.get("missing", []))
            if not decision.should_end or not missing:
                return decision
            next_gap = missing[0]
            phase_hint, gap_instruction = self._adoption_barrier_gap_instruction(next_gap)
            rejected = decision.to_dict()
            rejected["question_evidence_basis"] = basis
            rejected["decision_status"] = "rejected_by_adoption_barrier_gate"
            session.facilitator_decisions.append(rejected)
            correction = (
                "ADOPTION BARRIER GATE: Do not end yet. This mode must cover recent real behavior, current workaround, "
                "setup burden, permission boundary, trust boundary, pricing condition, reversibility, and workflow burden. "
                f"Missing items: {', '.join(missing) or '(none listed)'}. "
                f"Ask one short barrier question next. Use a phase or strategy label like '{phase_hint}' so the runtime "
                f"can audit the gap. {gap_instruction}\n\n"
                f"TRANSCRIPT:\n{self._plain_transcript(session)}"
            )
            return self.facilitator_provider.next_turn(
                system_prompt=system_prompt,
                user_prompt=correction,
                provider_session_id=decision.provider_session_id or session.facilitator_provider_session_id,
            )
        if session.interview_mode == "prototype_validation":
            self._update_coverage_status(session)
            missing = list(session.coverage_status.get("missing", []))
            if not decision.should_end or not missing:
                return decision
            next_gap = missing[0]
            phase_hint, gap_instruction = self._prototype_validation_gap_instruction(next_gap)
            rejected = decision.to_dict()
            rejected["question_evidence_basis"] = basis
            rejected["decision_status"] = "rejected_by_prototype_validation_gate"
            session.facilitator_decisions.append(rejected)
            correction = (
                "PROTOTYPE VALIDATION GATE: Do not end yet. This mode must cover stimulus interpretation, first action, "
                "task path expectation, setup confusion, trust boundary, breakdown or drop-off risk, and the task "
                "completion signal. Do not collapse this into generic concept appeal or adoption intent. "
                f"Missing items: {', '.join(missing) or '(none listed)'}. "
                f"Ask one short prototype-task question next. Use a phase or strategy label like '{phase_hint}' so the "
                f"runtime can audit the gap. {gap_instruction}\n\n"
                f"TRANSCRIPT:\n{self._plain_transcript(session)}"
            )
            return self.facilitator_provider.next_turn(
                system_prompt=system_prompt,
                user_prompt=correction,
                provider_session_id=decision.provider_session_id or session.facilitator_provider_session_id,
            )
        if session.interview_mode == "decision_reconstruction":
            self._update_coverage_status(session)
            missing = list(session.coverage_status.get("missing", []))
            non_episodic_question = not decision.should_end and basis in {"hypothetical", "general_pattern"}
            premature_closure = bool(decision.should_end and missing)
            if not non_episodic_question and not premature_closure:
                return decision
            rejected = decision.to_dict()
            rejected["question_evidence_basis"] = basis
            rejected["decision_status"] = "rejected_by_decision_reconstruction_gate"
            session.facilitator_decisions.append(rejected)
            if premature_closure:
                correction = (
                    "DECISION RECONSTRUCTION GATE: Do not end yet. This mode must reconstruct one real recent decision "
                    "through five participant-facing items: the event itself, missing evidence, stakeholder or time pressure, "
                    "what was publicly defensible versus privately uncertain, and what actually changed in scope, sequence, "
                    f"priority, or go-no-go. Missing items: {', '.join(missing) or '(none listed)'}. "
                    "Ask one short factual question that fills the highest-value missing item next.\n\n"
                    f"TRANSCRIPT:\n{self._plain_transcript(session)}"
                )
            else:
                correction = (
                    "DECISION RECONSTRUCTION GATE: Your proposed participant question is hypothetical or generic. "
                    "Rewrite it as one short factual reconstruction question about the same real decision event. "
                    "Stay anchored in what happened, what evidence was missing, what pressure existed, what felt defensible "
                    "versus uncertain, or what actually changed.\n\n"
                    f"REJECTED QUESTION:\n{decision.message_to_persona}\n\n"
                    f"TRANSCRIPT:\n{self._plain_transcript(session)}"
                )
            return self.facilitator_provider.next_turn(
                system_prompt=system_prompt,
                user_prompt=correction,
                provider_session_id=decision.provider_session_id or session.facilitator_provider_session_id,
            )
        if session.interview_mode != "validate_hypothesis":
            return decision
        recalled_count = sum(
            self._effective_question_basis(exchange.facilitator_question, exchange.question_evidence_basis)
            == "recalled_contrast_event"
            for exchange in session.exchanges
        )
        covered_targets = {exchange.question_evidence_target for exchange in session.exchanges}
        required_targets = {"participant_cause", "consequence", "hypothesis_condition", "alternative_condition"}
        missing_targets = sorted(required_targets - covered_targets)
        closure_missing_evidence = decision.should_end and (recalled_count < 2 or bool(missing_targets))
        forced_choice_markers = ("定係", "還是", "or is it", " or ")
        loaded_condition_markers = (
            "冇人講清楚", "沒人講清楚", "沒有人講清楚", "責任不清", "無人負責",
            "不確定該由誰", "唔確定應該由邊個", "等別人確認", "等人確認",
            "no one owns", "nobody owns", "unclear responsibility", "係咪都比", "是不是更",
        )
        forced_choice_question = not decision.should_end and any(
            marker in decision.message_to_persona.casefold() for marker in forced_choice_markers
        )
        loaded_condition_question = not decision.should_end and any(
            marker in decision.message_to_persona.casefold() for marker in loaded_condition_markers
        )
        non_episodic_question = not decision.should_end and basis in {"hypothetical", "general_pattern"}
        if not closure_missing_evidence and not non_episodic_question and not forced_choice_question and not loaded_condition_question:
            return decision
        rejected = decision.to_dict()
        rejected["question_evidence_basis"] = basis
        rejected["decision_status"] = "rejected_by_evidence_gate"
        session.facilitator_decisions.append(rejected)
        if closure_missing_evidence:
            correction = (
                "EVIDENCE GATE: You proposed ending before the hypothesis-validation evidence checklist was complete. "
                f"Missing targets: {', '.join(missing_targets) or 'a second recalled contrast event'}. "
                "Ask one short, neutral question that fills the highest-value missing target using a specific recalled event. "
                "After a participant-led cause has been obtained, you may ask directly whether the hypothesis condition "
                "was present, but do not assert that it caused the behaviour. If the participant cannot recall such a "
                "case, preserve that as an evidence gap.\n\n"
                f"TRANSCRIPT:\n{self._plain_transcript(session)}"
            )
        elif forced_choice_question or loaded_condition_question:
            correction = (
                "QUESTION QUALITY GATE: Your proposed question forces a researcher classification, comparison, or "
                "hypothesis condition into the participant's answer. Rewrite it as one open, single-focus factual "
                "reconstruction grounded in the same recalled event. For an ownership hypothesis, ask who handled "
                "each affected item in a named past event; do not use uncertainty, waiting, or ownership language as "
                "the retrieval cue. Reconstruct actions first and classify the condition only afterward.\n\n"
                f"REJECTED QUESTION:\n{decision.message_to_persona}\n\n"
                f"TRANSCRIPT:\n{self._plain_transcript(session)}"
            )
        else:
            correction = (
                "EVIDENCE GATE: Your proposed participant question is hypothetical or asks for a general pattern, "
                "so it cannot test the supplied hypothesis. Replace it with one short, neutral question about a "
                "specific recalled past occasion where the relevant condition was present or absent. Do not classify "
                "the condition for the participant. If no episodic probe is justified, end with the hypothesis unresolved.\n\n"
                f"REJECTED QUESTION:\n{decision.message_to_persona}\n\n"
                f"TRANSCRIPT:\n{self._plain_transcript(session)}"
            )
        return self.facilitator_provider.next_turn(
            system_prompt=system_prompt,
            user_prompt=correction,
            provider_session_id=decision.provider_session_id or session.facilitator_provider_session_id,
        )

    def _facilitator_system_prompt(self, session: InterviewSession) -> str:
        root = _repo_root()
        skill = _read(root / "skills" / "design-research-facilitator" / "SKILL.md")
        prompt = _read(root / "src" / "ai_validation_swarm" / "prompts" / "facilitator-interview" / "v2.md")
        concept_protocol = ""
        if session.interview_mode == "concept_validation":
            concept = load_concept_protocol(session.concept_protocol_version, label=session.concept_label)
            concept_protocol = concept.prompt_text
        approved_rules_text, _ = build_approved_facilitator_learning_prompt_fragment(
            self.approved_learning_rules_path,
            max_rules=self.max_approved_learning_rules,
        )
        sections = [
            prompt,
            f"FACILITATOR SKILL:\n{skill}",
        ]
        if approved_rules_text:
            sections.append(approved_rules_text)
        sections.append(f"CONCEPT VALIDATION PROTOCOL:\n{concept_protocol}")
        return "\n\n".join(section for section in sections if section)

    def _annotate_approved_learning_rules(self, session: InterviewSession) -> None:
        _, rule_ids = build_approved_facilitator_learning_prompt_fragment(
            self.approved_learning_rules_path,
            max_rules=self.max_approved_learning_rules,
        )
        session.approved_learning_rules_source = str(self.approved_learning_rules_path or "")
        session.approved_learning_rule_ids = rule_ids

    @staticmethod
    def _synthesis_system_prompt(interview_mode: str = "explore_root_cause") -> str:
        root = _repo_root()
        skill = _read(root / "skills" / "design-research-facilitator" / "SKILL.md")
        prompt_path = (
            root / "src" / "ai_validation_swarm" / "prompts" / "concept-synthesis" / "v1.md"
            if interview_mode == "concept_validation"
            else root / "src" / "ai_validation_swarm" / "prompts" / "prototype-synthesis" / "v1.md"
            if interview_mode == "prototype_validation"
            else root / "src" / "ai_validation_swarm" / "prompts" / "facilitator-synthesis" / "v2.md"
        )
        prompt = _read(prompt_path)
        return f"{prompt}\n\nFACILITATOR SKILL:\n{skill}"

    @staticmethod
    def _stimulus_review_system_prompt() -> str:
        root = _repo_root()
        return _read(root / "src" / "ai_validation_swarm" / "prompts" / "stimulus-image-review" / "v1.md")

    @staticmethod
    def _flow_stimulus_review_system_prompt() -> str:
        root = _repo_root()
        return _read(root / "src" / "ai_validation_swarm" / "prompts" / "stimulus-flow-review" / "v1.md")

    @staticmethod
    def _hypothesis_evidence_judge_system_prompt() -> str:
        root = _repo_root()
        return _read(root / "src" / "ai_validation_swarm" / "prompts" / "hypothesis-evidence-judge" / "v1.md")

    def _judge_hypothesis_evidence(self, session: InterviewSession) -> tuple[dict[str, Any], str]:
        return self.facilitator_provider.judge_hypothesis_evidence(
            system_prompt=self._hypothesis_evidence_judge_system_prompt(),
            user_prompt=self._hypothesis_evidence_judge_user_prompt(session),
        )

    @staticmethod
    def _hypothesis_evidence_judge_user_prompt(session: InterviewSession) -> str:
        exchanges = [{
            "ref": f"exchange_{exchange.exchange_id}",
            "question": exchange.facilitator_question,
            "answer": exchange.persona_response,
            "question_evidence_basis": FacilitatedInterviewRuntime._effective_question_basis(
                exchange.facilitator_question, exchange.question_evidence_basis
            ),
            "question_evidence_target": exchange.question_evidence_target,
        } for exchange in session.exchanges]
        return (
            f"EXACT HYPOTHESIS:\n{session.hypothesis}\n\n"
            f"RESEARCH GOAL:\n{session.research_goal}\n\n"
            "ASKED EXCHANGES WITH EVIDENCE METADATA:\n"
            + json.dumps(exchanges, ensure_ascii=False, separators=(",", ":"))
        )

    @staticmethod
    def _persona_interview_instruction() -> str:
        root = _repo_root()
        return _read(root / "src" / "ai_validation_swarm" / "prompts" / "persona-interview-response" / "v1.md")

    @staticmethod
    def _opening_prompt(session: InterviewSession) -> str:
        return (
            f"INTERVIEW MODE:\n{session.interview_mode}\n\n"
            f"HYPOTHESIS TO TEST:\n{session.hypothesis or '(none; discover causes from evidence)'}\n\n"
            f"RESEARCH GOAL:\n{session.research_goal}\n\n"
            f"DISCLOSED PRODUCT CONTEXT:\n{session.product_context or '(none; remain in problem discovery)'}\n\n"
            f"{FacilitatedInterviewRuntime._stimulus_prompt_block(session)}"
            f"OUTPUT LANGUAGE:\n{session.output_language}\n\n"
            f"CONCEPT LABEL:\n{session.concept_label or '(none)'}\n\n"
            f"TURN POLICY:\nsoft={session.soft_turn_limit}, hard={session.hard_turn_limit}\n\n"
            "REQUIRED COVERAGE:\n"
            f"{json.dumps(session.coverage_status.get('requirements', []), ensure_ascii=False, separators=(',', ':'))}\n\n"
            "DEPTH-FIRST STOP RULE:\n"
            "Do not stop at topic coverage in concept_validation mode. Before ending, complete the required depth probes shown in DEPTH REQUIREMENTS, including at least one named-output-to-concrete-decision mapping probe.\n\n"
            "DEPTH REQUIREMENTS:\n"
            f"{json.dumps(session.coverage_status.get('depth_requirements', []), ensure_ascii=False, separators=(',', ':'))}\n\n"
            "No interview transcript exists yet. Choose and return the first interview question."
        )

    @staticmethod
    def _continuation_prompt(session: InterviewSession) -> str:
        return (
            f"INTERVIEW MODE: {session.interview_mode}\n"
            f"HYPOTHESIS TO TEST: {session.hypothesis or '(none)'}\n"
            f"OUTPUT LANGUAGE: {session.output_language}\n\n"
            f"CONCEPT LABEL: {session.concept_label or '(none)'}\n\n"
            f"{FacilitatedInterviewRuntime._stimulus_prompt_block(session)}"
            "COVERAGE STATUS:\n"
            f"{json.dumps(session.coverage_status, ensure_ascii=False, separators=(',', ':'))}\n\n"
            "DEPTH-FIRST RULE:\n"
            "If the participant has given a high-signal cue and depth status is incomplete, ask the highest-value threshold, contrast/non-use, driver-deepening, or named-output-to-decision follow-up before closing.\n\n"
            "INTERVIEW TRANSCRIPT TO DATE:\n"
            f"{FacilitatedInterviewRuntime._plain_transcript(session)}\n\n"
            "Use the transcript to choose the next question or end the interview."
        )

    @staticmethod
    def _synthesis_user_prompt(session: InterviewSession) -> str:
        trace = json.dumps(
            FacilitatedInterviewRuntime._audit_trace(session), ensure_ascii=False, separators=(",", ":")
        )
        return (
            f"INTERVIEW MODE:\n{session.interview_mode}\n\n"
            f"HYPOTHESIS TO TEST:\n{session.hypothesis or '(none)'}\n\n"
            f"RESEARCH GOAL:\n{session.research_goal}\n\n"
            f"DISCLOSED PRODUCT CONTEXT:\n{session.product_context or '(none)'}\n\n"
            f"{FacilitatedInterviewRuntime._stimulus_prompt_block(session)}"
            f"OUTPUT LANGUAGE:\n{session.output_language}\n\n"
            f"CONCEPT LABEL:\n{session.concept_label or '(none)'}\n\n"
            f"STOP REASON:\n{session.stop_reason or 'facilitator decision'}\n\n"
            "COVERAGE STATUS:\n"
            f"{json.dumps(session.coverage_status, ensure_ascii=False, separators=(',', ':'))}\n\n"
            f"TRANSCRIPT:\n{FacilitatedInterviewRuntime._plain_transcript(session)}\n\n"
            f"FACILITATOR EVIDENCE TRACE:\n{trace}\n\n"
            "INDEPENDENT HYPOTHESIS EVIDENCE JUDGMENT:\n"
            f"{json.dumps(session.hypothesis_evidence_judgment, ensure_ascii=False, separators=(',', ':'))}\n\n"
            "Produce the final structured insight report."
        )

    @staticmethod
    def _audit_trace(session: InterviewSession) -> list[dict[str, Any]]:
        keys = (
            "interview_phase", "probing_strategy", "decision_rationale", "message_to_persona",
            "root_cause_hypotheses", "should_end", "end_reason", "decision_status",
            "question_evidence_basis", "question_evidence_target",
        )
        return [{key: item.get(key) for key in keys if key in item} for item in session.facilitator_decisions]

    @staticmethod
    def _plain_transcript(session: InterviewSession) -> str:
        if not session.exchanges:
            return "(no exchanges)"
        lines: list[str] = []
        for exchange in session.exchanges:
            lines.append(f"exchange_{exchange.exchange_id}.facilitator: {exchange.facilitator_question}")
            lines.append(f"exchange_{exchange.exchange_id}.persona: {exchange.persona_response}")
        return "\n".join(lines)

    @staticmethod
    def _stimulus_prompt_block(session: InterviewSession) -> str:
        sections = [
            f"STIMULUS TYPE:\n{session.stimulus_type or '(none)'}\n\n"
            f"STIMULUS ARTIFACT:\n{session.stimulus_artifact or '(none)'}\n\n"
            f"STIMULUS ARTIFACT SNAPSHOT:\n{session.stimulus_artifact_snapshot or '(none)'}\n\n"
            f"PROTOTYPE TASK:\n{session.prototype_task or '(none)'}\n\n"
        ]
        if session.observed_action_trace:
            trace = session.observed_action_trace
            actions = trace.get("actions", [])
            action_lines = []
            if isinstance(actions, list):
                for action in actions[:8]:
                    if not isinstance(action, dict):
                        continue
                    action_lines.append(
                        f"- Step {action.get('step', '?')}: {action.get('action', 'unknown')} -> "
                        f"{action.get('target', '(unspecified)')} [{action.get('result', 'unknown')}]"
                    )
                if len(actions) > 8:
                    action_lines.append(f"- Additional observed actions omitted: {len(actions) - 8}")
            sections.append(
                "OBSERVED ACTION TRACE (application-supplied runtime evidence):\n"
                f"- Trace label: {trace.get('trace_label', '') or '(none)'}\n"
                f"- Trace version: {trace.get('trace_version', '') or '(none)'}\n"
                f"- Task outcome: {trace.get('task_outcome', '') or '(unknown)'}\n"
                f"- Summary: {trace.get('summary', '') or '(none)'}\n"
                f"- First error: {trace.get('first_error', '') or '(none)'}\n"
                f"- Drop-off point: {trace.get('drop_off_point', '') or '(none)'}\n"
                f"- Completion notes: {trace.get('completion_notes', '') or '(none)'}\n"
                f"- Artifact sha256: {trace.get('artifact_sha256', '') or '(none)'}\n"
                f"{chr(10).join(action_lines) or '- No normalized actions were available.'}\n\n"
            )
        if session.stimulus_analysis:
            analysis = session.stimulus_analysis
            analysis_type = str(analysis.get("analysis_type", session.stimulus_type or "stimulus")).strip()
            if analysis_type == "flow":
                sections.append(
                    "MULTI-SCREEN FLOW STIMULUS REVIEW (application-supplied context, not participant evidence):\n"
                    f"- Summary: {analysis.get('summary', '')}\n"
                    f"- Screen sequence: {', '.join(analysis.get('screen_sequence', [])) or '(none)'}\n"
                    f"- Primary action candidates: {', '.join(analysis.get('primary_action_candidates', [])) or '(none)'}\n"
                    f"- Transition confusions: {', '.join(analysis.get('transition_confusions', [])) or '(none)'}\n"
                    f"- Setup burdens: {', '.join(analysis.get('setup_burdens', [])) or '(none)'}\n"
                    f"- Likely drop-off points: {', '.join(analysis.get('likely_drop_off_points', [])) or '(none)'}\n"
                    f"- Trust risks: {', '.join(analysis.get('trust_risks', [])) or '(none)'}\n"
                    f"- Missing context: {', '.join(analysis.get('missing_context', [])) or '(none)'}\n"
                    f"- Task relevance: {analysis.get('task_relevance', '')}\n"
                    f"- Evidence boundary: {analysis.get('evidence_boundary', '')}\n\n"
                )
            elif analysis_type == "clickable_manifest":
                sections.append(
                    "CLICKABLE PROTOTYPE EXECUTION CONTEXT (application-executed manifest task loop, not human session evidence):\n"
                    f"- Summary: {analysis.get('summary', '')}\n"
                    f"- Prototype label: {analysis.get('prototype_label', '')}\n"
                    f"- Screen count: {analysis.get('screen_count', 0)}\n"
                    f"- Task step count: {analysis.get('task_step_count', 0)}\n"
                    f"- Start screen: {analysis.get('start_screen', '')}\n"
                    f"- Visited screens: {', '.join(analysis.get('visited_screens', [])) or '(none)'}\n"
                    f"- Evidence boundary: {analysis.get('evidence_boundary', '')}\n\n"
                )
            else:
                sections.append(
                    "STATIC IMAGE STIMULUS REVIEW (application-supplied context, not participant evidence):\n"
                    f"- Summary: {analysis.get('summary', '')}\n"
                    f"- Visible elements: {', '.join(analysis.get('visible_elements', [])) or '(none)'}\n"
                    f"- Primary action candidates: {', '.join(analysis.get('primary_action_candidates', [])) or '(none)'}\n"
                    f"- Interpretation risks: {', '.join(analysis.get('interpretation_risks', [])) or '(none)'}\n"
                    f"- Trust risks: {', '.join(analysis.get('trust_risks', [])) or '(none)'}\n"
                    f"- Missing context: {', '.join(analysis.get('missing_context', [])) or '(none)'}\n"
                    f"- Task relevance: {analysis.get('task_relevance', '')}\n"
                    f"- Evidence boundary: {analysis.get('evidence_boundary', '')}\n\n"
                )
        return "".join(sections)

    def _save(self, session: InterviewSession, folder: Path) -> None:
        write_json(folder / "interview.json", session.to_dict())
        write_json(folder / "facilitator_trace.json", session.facilitator_decisions)
        if session.stimulus_analysis:
            write_json(folder / "stimulus_analysis.json", session.stimulus_analysis)
        if session.observed_action_trace:
            write_json(folder / "observed_action_trace.json", session.observed_action_trace)
        if session.persona_driver_trace:
            write_json(folder / "persona_driver_trace.json", session.persona_driver_trace)
            write_markdown(
                folder / "persona_driver_trace.md",
                self._render_persona_driver_trace(session),
            )
        write_markdown(folder / "transcript.md", self._render_transcript(session))
        artifact_paths = ["interview.json", "facilitator_trace.json", "transcript.md", "run_contract.json"]
        if session.stimulus_analysis:
            artifact_paths.append("stimulus_analysis.json")
        if session.observed_action_trace:
            artifact_paths.append("observed_action_trace.json")
        if session.hypothesis_evidence_judgment:
            artifact_paths.append("hypothesis_evidence_judgment.json")
        if session.insight_report:
            artifact_paths.extend(["insight_report.json", "insights.md"])
        if session.persona_driver_trace:
            artifact_paths.extend(["persona_driver_trace.json", "persona_driver_trace.md"])
        run_kind = "observer_controlled_interview" if session.quality_provider else "facilitated_interview"
        write_shared_run_contract(
            folder / "run_contract.json",
            build_interview_run_contract(
                session,
                output_path=folder,
                artifact_paths=artifact_paths,
                run_kind=run_kind,
            ),
        )

    @staticmethod
    def _validate_interview_brief(
        interview_mode: str,
        hypothesis: str,
        *,
        product_context: str = "",
        stimulus_type: str = "",
        stimulus_artifact: str = "",
        prototype_task: str = "",
    ) -> tuple[str, str]:
        mode = interview_mode.strip() or "explore_root_cause"
        resolved_stimulus_type = ""
        if mode not in {
            "pain_point_discovery",
            "adoption_barrier_validation",
            "prototype_validation",
            "decision_reconstruction",
            "explore_root_cause",
            "validate_hypothesis",
            "concept_validation",
        }:
            raise ValueError(
                "interview_mode must be pain_point_discovery, adoption_barrier_validation, prototype_validation, "
                "decision_reconstruction, explore_root_cause, validate_hypothesis, or concept_validation."
            )
        if mode == "validate_hypothesis" and not hypothesis.strip():
            raise ValueError("validate_hypothesis mode requires a non-empty hypothesis.")
        if mode == "prototype_validation":
            resolved_stimulus_type = stimulus_type.strip() or "text_concept"
            if resolved_stimulus_type not in PROTOTYPE_STIMULUS_TYPES:
                raise ValueError(
                    "prototype_validation mode requires stimulus_type to be one of: "
                    + ", ".join(PROTOTYPE_STIMULUS_TYPES)
                    + "."
                )
            if not prototype_task.strip():
                raise ValueError("prototype_validation mode requires a non-empty prototype_task.")
            if not stimulus_artifact.strip() and not product_context.strip():
                raise ValueError(
                    "prototype_validation mode requires a stimulus_artifact or product_context describing the prototype stimulus."
                )
            if resolved_stimulus_type == "image":
                if not stimulus_artifact.strip():
                    raise ValueError("prototype_validation mode with stimulus_type=image requires a non-empty stimulus_artifact path.")
                FacilitatedInterviewRuntime._resolve_image_stimulus_artifact(stimulus_artifact.strip())
            if resolved_stimulus_type == "flow":
                if not stimulus_artifact.strip():
                    raise ValueError("prototype_validation mode with stimulus_type=flow requires a non-empty stimulus_artifact path.")
                FacilitatedInterviewRuntime._resolve_flow_stimulus_artifact_bundle(stimulus_artifact.strip())
        return mode, resolved_stimulus_type

    def _prepare_stimulus_context(
        self,
        *,
        interview_folder: Path,
        interview_mode: str,
        product_context: str,
        stimulus_type: str,
        stimulus_artifact: str,
        prototype_task: str,
    ) -> dict[str, Any]:
        prepared = {
            "stimulus_artifact": stimulus_artifact,
            "stimulus_artifact_snapshot": "",
            "stimulus_analysis_prompt_version": "",
            "stimulus_analysis_provider_session_id": "",
            "stimulus_analysis": {},
            "observed_action_trace": {},
        }
        if interview_mode != "prototype_validation":
            return prepared
        if stimulus_type == "image":
            source_path = self._resolve_image_stimulus_artifact(stimulus_artifact)
            snapshot_path = self._snapshot_stimulus_artifact(source_path, interview_folder)
            self._progress(f"analyzing_image_stimulus artifact={source_path.name}")
            analysis, provider_session_id = self.facilitator_provider.review_image_stimulus(
                system_prompt=self._stimulus_review_system_prompt(),
                user_prompt=self._stimulus_review_user_prompt(
                    product_context=product_context,
                    prototype_task=prototype_task,
                    stimulus_artifact=stimulus_artifact,
                ),
                image_path=str(snapshot_path),
            )
            analysis = dict(analysis)
            analysis["analysis_type"] = "image"
            analysis["artifact_filename"] = source_path.name
            analysis["artifact_sha256"] = self._file_sha256(snapshot_path)
            prepared["stimulus_artifact_snapshot"] = str(snapshot_path)
            prepared["stimulus_analysis_prompt_version"] = IMAGE_STIMULUS_REVIEW_PROMPT_VERSION
            prepared["stimulus_analysis_provider_session_id"] = provider_session_id
            prepared["stimulus_analysis"] = analysis
        elif stimulus_type == "flow":
            bundle = self._resolve_flow_stimulus_artifact_bundle(stimulus_artifact)
            snapshot_dir, snapshot_screens = self._snapshot_flow_stimulus_artifacts(bundle, interview_folder)
            self._progress(f"analyzing_flow_stimulus screens={len(snapshot_screens)}")
            analysis, provider_session_id = self.facilitator_provider.review_flow_stimulus(
                system_prompt=self._flow_stimulus_review_system_prompt(),
                user_prompt=self._flow_stimulus_review_user_prompt(
                    product_context=product_context,
                    prototype_task=prototype_task,
                    stimulus_artifact=stimulus_artifact,
                    screens=snapshot_screens,
                ),
                screens=snapshot_screens,
            )
            analysis = dict(analysis)
            analysis["analysis_type"] = "flow"
            analysis["screen_count"] = len(snapshot_screens)
            analysis["screens"] = [
                {
                    "sequence": screen["sequence"],
                    "label": screen["label"],
                    "snapshot_path": screen["path"],
                    "sha256": self._file_sha256(Path(screen["path"])),
                }
                for screen in snapshot_screens
            ]
            prepared["stimulus_artifact_snapshot"] = str(snapshot_dir)
            prepared["stimulus_analysis_prompt_version"] = FLOW_STIMULUS_REVIEW_PROMPT_VERSION
            prepared["stimulus_analysis_provider_session_id"] = provider_session_id
            prepared["stimulus_analysis"] = analysis
        elif stimulus_type in {"clickable", "live_app"} and stimulus_artifact.strip():
            trace_path = self._resolve_json_stimulus_artifact(stimulus_artifact)
            snapshot_path = self._snapshot_stimulus_artifact(trace_path, interview_folder)
            payload = self._load_json_stimulus_payload(snapshot_path)
            prepared["stimulus_artifact_snapshot"] = str(snapshot_path)
            execution = self._execute_stimulus_artifact(
                stimulus_type=stimulus_type,
                artifact_path=snapshot_path,
                payload=payload,
                prototype_task=prototype_task,
            )
            if execution is not None:
                prepared["stimulus_analysis_prompt_version"] = execution.get(
                    "stimulus_analysis_prompt_version",
                    SCRIPTED_CLICKABLE_EXECUTOR_VERSION,
                )
                prepared["stimulus_analysis_provider_session_id"] = execution.get(
                    "stimulus_analysis_provider_session_id", ""
                )
                prepared["stimulus_analysis"] = execution.get("stimulus_analysis", {})
                prepared["observed_action_trace"] = execution["observed_action_trace"]
            else:
                prepared["stimulus_analysis_prompt_version"] = OBSERVED_ACTION_TRACE_VERSION
                prepared["observed_action_trace"] = self._load_observed_action_trace(snapshot_path)
        return prepared

    @staticmethod
    def _stimulus_review_user_prompt(
        *,
        product_context: str,
        prototype_task: str,
        stimulus_artifact: str,
    ) -> str:
        return (
            f"PRODUCT CONTEXT:\n{product_context or '(none)'}\n\n"
            f"PROTOTYPE TASK:\n{prototype_task or '(none)'}\n\n"
            f"STIMULUS ARTIFACT LABEL:\n{stimulus_artifact or '(none)'}\n\n"
            "Inspect the supplied static prototype image and summarize the visible screen, the most likely primary actions, "
            "the main interpretation risks, trust or clarity risks, and any missing context that could block the task."
        )

    @staticmethod
    def _flow_stimulus_review_user_prompt(
        *,
        product_context: str,
        prototype_task: str,
        stimulus_artifact: str,
        screens: list[dict[str, str]],
    ) -> str:
        screen_list = "\n".join(
            f"- Screen {screen['sequence']}: {screen['label']}"
            for screen in screens
        ) or "(none)"
        return (
            f"PRODUCT CONTEXT:\n{product_context or '(none)'}\n\n"
            f"PROTOTYPE TASK:\n{prototype_task or '(none)'}\n\n"
            f"STIMULUS ARTIFACT LABEL:\n{stimulus_artifact or '(none)'}\n\n"
            f"FLOW SCREENS:\n{screen_list}\n\n"
            "Inspect the supplied multi-screen prototype flow in order. Summarize what task path the flow appears to support, "
            "where transitions become unclear, what setup burden is hidden across screens, and where trust or drop-off risk appears."
        )

    @staticmethod
    def _resolve_image_stimulus_artifact(stimulus_artifact: str) -> Path:
        raw = stimulus_artifact.strip()
        candidate = Path(raw)
        candidates = [candidate]
        if not candidate.is_absolute():
            candidates.append(_repo_root() / candidate)
        for item in candidates:
            resolved = item.expanduser()
            if resolved.exists() and resolved.is_file():
                return resolved.resolve()
        raise ValueError(f"Image stimulus artifact was not found or is not a file: {stimulus_artifact}")

    @staticmethod
    def _resolve_flow_stimulus_artifact_bundle(stimulus_artifact: str) -> list[dict[str, Any]]:
        raw = stimulus_artifact.strip()
        candidate = Path(raw)
        candidates = [candidate]
        if not candidate.is_absolute():
            candidates.append(_repo_root() / candidate)
        resolved_path: Path | None = None
        for item in candidates:
            resolved = item.expanduser()
            if resolved.exists():
                resolved_path = resolved.resolve()
                break
        if resolved_path is None:
            raise ValueError(f"Flow stimulus artifact was not found: {stimulus_artifact}")
        if resolved_path.is_dir():
            screens = sorted(
                path for path in resolved_path.iterdir()
                if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}
            )
            if not screens:
                raise ValueError(f"Flow stimulus artifact directory does not contain supported image files: {stimulus_artifact}")
            return [
                {"source_path": path, "label": path.stem, "sequence": index}
                for index, path in enumerate(screens, start=1)
            ]
        if resolved_path.is_file() and resolved_path.suffix.lower() == ".json":
            try:
                payload = json.loads(resolved_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"Flow stimulus manifest is invalid JSON: {stimulus_artifact}") from exc
            screens_payload = payload.get("screens", payload) if isinstance(payload, dict) else payload
            if not isinstance(screens_payload, list) or not screens_payload:
                raise ValueError("Flow stimulus manifest must contain a non-empty screens list.")
            bundle: list[dict[str, Any]] = []
            for index, item in enumerate(screens_payload, start=1):
                if isinstance(item, str):
                    relative_path = item.strip()
                    label = Path(relative_path).stem
                elif isinstance(item, dict):
                    relative_path = str(item.get("path", "")).strip()
                    label = str(item.get("label", "")).strip() or Path(relative_path).stem
                else:
                    raise ValueError("Flow stimulus manifest screens must be strings or objects.")
                if not relative_path:
                    raise ValueError("Flow stimulus manifest screens require a non-empty path.")
                screen_path = (resolved_path.parent / relative_path).resolve()
                if not screen_path.exists() or not screen_path.is_file():
                    raise ValueError(f"Flow stimulus screen was not found: {screen_path}")
                bundle.append({"source_path": screen_path, "label": label, "sequence": index})
            return bundle
        raise ValueError(
            "Flow stimulus artifact must be either a directory of ordered image screens or a JSON manifest."
        )

    @staticmethod
    def _resolve_json_stimulus_artifact(stimulus_artifact: str) -> Path:
        raw = stimulus_artifact.strip()
        candidate = Path(raw)
        candidates = [candidate]
        if not candidate.is_absolute():
            candidates.append(_repo_root() / candidate)
        for item in candidates:
            resolved = item.expanduser()
            if resolved.exists() and resolved.is_file() and resolved.suffix.lower() == ".json":
                return resolved.resolve()
        raise ValueError(
            "Stimulus JSON artifact was not found, is not a file, or is not a JSON file: "
            f"{stimulus_artifact}"
        )

    @staticmethod
    def _load_json_stimulus_payload(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Stimulus JSON artifact is invalid JSON: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Stimulus JSON artifact must contain a top-level JSON object.")
        return payload

    def _execute_stimulus_artifact(
        self,
        *,
        stimulus_type: str,
        artifact_path: Path,
        payload: dict[str, Any],
        prototype_task: str,
    ) -> dict[str, Any] | None:
        for executor in self.stimulus_executors:
            if executor.can_execute(stimulus_type=stimulus_type, payload=payload, artifact_path=artifact_path):
                self._progress(
                    f"executing_{stimulus_type}_stimulus executor={executor.executor_id} artifact={artifact_path.name}"
                )
                return executor.execute(
                    artifact_path=artifact_path,
                    payload=payload,
                    prototype_task=prototype_task,
                )
        return None

    @staticmethod
    def _load_observed_action_trace(path: Path) -> dict[str, Any]:
        payload = FacilitatedInterviewRuntime._load_json_stimulus_payload(path)
        try:
            trace = validate_observed_action_trace_payload(payload, default_label=path.stem)
        except InputValidationError as exc:
            raise ValueError(str(exc)) from exc
        normalized = trace.to_dict()
        normalized["artifact_sha256"] = FacilitatedInterviewRuntime._file_sha256(path)
        if not normalized.get("trace_version"):
            normalized["trace_version"] = OBSERVED_ACTION_TRACE_VERSION
        return normalized

    @staticmethod
    def _snapshot_stimulus_artifact(source_path: Path, interview_folder: Path) -> Path:
        target_dir = interview_folder / "stimulus_artifacts"
        ensure_dir(target_dir)
        target_path = target_dir / source_path.name
        if target_path.exists():
            stem = source_path.stem
            suffix = source_path.suffix
            target_path = target_dir / f"{stem}-{uuid.uuid4().hex[:6]}{suffix}"
        shutil.copyfile(source_path, target_path)
        return target_path

    @staticmethod
    def _snapshot_flow_stimulus_artifacts(
        bundle: list[dict[str, Any]],
        interview_folder: Path,
    ) -> tuple[Path, list[dict[str, str]]]:
        target_dir = interview_folder / "stimulus_artifacts" / "flow_bundle"
        ensure_dir(target_dir)
        snapshots: list[dict[str, str]] = []
        for item in bundle:
            source_path = Path(item["source_path"])
            sequence = int(item["sequence"])
            label = str(item["label"]).strip() or source_path.stem
            filename = f"{sequence:02d}_{source_path.name}"
            target_path = target_dir / filename
            shutil.copyfile(source_path, target_path)
            snapshots.append(
                {
                    "sequence": str(sequence),
                    "label": label,
                    "path": str(target_path),
                }
            )
        return target_dir, snapshots

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        digest.update(path.read_bytes())
        return digest.hexdigest()

    @staticmethod
    def _render_persona_driver_trace(session: InterviewSession) -> str:
        return ConversationRuntime.render_persona_driver_trace_markdown(
            session.persona_driver_trace,
            persona_name=session.persona_name,
            research_goal=session.research_goal,
        )

    @staticmethod
    def _effective_question_basis(question: str, declared_basis: str) -> str:
        lowered = question.casefold()
        hypothetical_markers = ("如果", "假如", "假設", "的話", "if ", "would you", "would still", "imagine")
        general_markers = ("通常", "平常", "一般", "usually", "normally", "in general")
        recalled_markers = ("有沒有一次", "有冇一次", "另一次", "另一個情況", "記得一次", "remember a time")
        current_markers = ("那次", "當時", "那晚", "那天", "後來", "嗰次", "嗰晚", "in that event")
        if lowered.startswith("要是") or any(marker in lowered for marker in hypothetical_markers):
            return "hypothetical"
        if any(marker in lowered for marker in general_markers):
            return "general_pattern"
        if any(marker in lowered for marker in recalled_markers):
            return "recalled_contrast_event"
        if any(marker in lowered for marker in current_markers):
            return "current_event"
        if declared_basis in {
            "current_event", "recalled_contrast_event", "clarification", "observer_question",
        }:
            return declared_basis
        return "clarification"

    @staticmethod
    def _enforce_synthesis_evidence_scope(session: InterviewSession, synthesis: dict[str, Any]) -> None:
        if session.interview_mode != "validate_hypothesis":
            return
        synthesis["needs"] = []
        synthesis["pov_statements"] = []
        synthesis["how_might_we_questions"] = []

        basis_by_ref = {
            f"exchange_{exchange.exchange_id}.persona": FacilitatedInterviewRuntime._effective_question_basis(
                exchange.facilitator_question, exchange.question_evidence_basis
            )
            for exchange in session.exchanges
        }
        observed_bases = {"current_event", "recalled_contrast_event"}
        assessment = synthesis.get("hypothesis_assessment", {})
        if not isinstance(assessment, dict):
            return

        judgment = session.hypothesis_evidence_judgment
        if isinstance(judgment, dict) and judgment:
            present = judgment.get("condition_present", {})
            absent = judgment.get("condition_absent", {})
            present_observed = isinstance(present, dict) and present.get("status") == "observed"
            absent_observed = isinstance(absent, dict) and absent.get("status") == "observed"
            assessment["hypothesis"] = session.hypothesis
            assessment["verdict"] = judgment.get("recommended_verdict", "not_tested")
            assessment["supporting_evidence_refs"] = list(judgment.get("supporting_evidence_refs", []))
            assessment["contradicting_evidence_refs"] = list(judgment.get("contradicting_evidence_refs", []))
            assessment["condition_present_case_refs"] = list(present.get("evidence_refs", [])) if present_observed else []
            assessment["condition_absent_case_refs"] = list(absent.get("evidence_refs", [])) if absent_observed else []
            assessment["mechanism_test_basis"] = "observed_event" if present_observed or absent_observed else "not_tested"
            assessment["confidence"] = judgment.get("confidence", "low")
            gaps = assessment.setdefault("evidence_gaps", [])
            for warning in judgment.get("warnings", []):
                if warning not in gaps:
                    gaps.append(warning)

        def refs_are_observed(refs: Any) -> bool:
            return bool(refs) and all(basis_by_ref.get(str(ref)) in observed_bases for ref in refs)

        present = assessment.get("condition_present_case_refs", [])
        absent = assessment.get("condition_absent_case_refs", [])
        if not judgment and (not refs_are_observed(present) or not refs_are_observed(absent)):
            assessment["verdict"] = "not_tested"
            assessment["mechanism_test_basis"] = "not_tested"
            assessment["supporting_evidence_refs"] = []
            assessment["contradicting_evidence_refs"] = []
            assessment["condition_present_case_refs"] = []
            assessment["condition_absent_case_refs"] = []
            assessment["confidence"] = "low"
            gaps = assessment.setdefault("evidence_gaps", [])
            note = "A real observed contrast with the proposed condition present and absent was not collected."
            if note not in gaps:
                gaps.append(note)

        for alternative in assessment.get("alternative_tests", []):
            if not isinstance(alternative, dict):
                continue
            refs = alternative.get("evidence_refs", [])
            bases = {basis_by_ref.get(str(ref), "") for ref in refs}
            if "hypothetical" in bases:
                alternative["basis"] = "hypothetical"
            elif "general_pattern" in bases:
                alternative["basis"] = "general_claim"
            elif not refs_are_observed(refs):
                alternative["basis"] = "general_claim"

    @staticmethod
    def _enforce_prototype_evidence_boundary(session: InterviewSession, synthesis: dict[str, Any]) -> None:
        if session.interview_mode != "prototype_validation":
            return
        boundary = synthesis.get("behavioral_evidence_boundary")
        if not isinstance(boundary, dict):
            boundary = {}
            synthesis["behavioral_evidence_boundary"] = boundary
        trace = session.observed_action_trace if isinstance(session.observed_action_trace, dict) else {}
        actions = trace.get("actions", [])
        observed_trace_available = isinstance(actions, list) and bool(actions)
        boundary["observed_action_available"] = observed_trace_available

        observed = boundary.get("what_was_observed")
        if not isinstance(observed, list):
            observed = []
        missing = boundary.get("missing_observed_signals")
        if not isinstance(missing, list):
            missing = []

        no_trace_note = "No observed action trace was collected from the prototype or interface."
        self_report_note = (
            f"Stimulus type was {session.stimulus_type or 'unspecified'} and this run collected task-guided "
            "self-report rather than recorded actions."
        )
        contradictory_no_trace_notes = {
            no_trace_note,
            "No observed action trace was collected.",
            "No real clicks or task traces were recorded.",
            "No actual clicks or backtracking were observed.",
        }
        if observed_trace_available:
            boundary["evidence_level"] = "observed_action_trace"
            observed_notes = [
                f"Observed action trace captured {len(actions)} action(s) for a {session.stimulus_type or 'prototype'} stimulus.",
            ]
            for note in trace.get("observed_summary", []):
                if isinstance(note, str) and note.strip():
                    observed_notes.append(note.strip())
            if trace.get("summary"):
                observed_notes.append(f"Trace summary: {trace['summary']}")
            if trace.get("task_outcome"):
                observed_notes.append(f"Task outcome: {trace['task_outcome']}")
            if trace.get("first_error"):
                observed_notes.append(f"First error: {trace['first_error']}")
            if trace.get("drop_off_point"):
                observed_notes.append(f"Drop-off point: {trace['drop_off_point']}")
            for action in actions[:5]:
                if not isinstance(action, dict):
                    continue
                observed_notes.append(
                    f"Step {action.get('step', '?')}: {action.get('action', 'unknown')} -> "
                    f"{action.get('target', '(unspecified)')} [{action.get('result', 'unknown')}]"
                )
            for note in observed_notes:
                if note not in observed:
                    observed.append(note)
            missing = [item for item in missing if item not in contradictory_no_trace_notes]
            for signal in trace.get("missing_signals", []):
                if signal not in missing:
                    missing.append(signal)
        else:
            if boundary.get("evidence_level") == "observed_action_trace":
                boundary["evidence_level"] = "task_guided_self_report"
            if not boundary.get("evidence_level"):
                boundary["evidence_level"] = "task_guided_self_report"
            if no_trace_note not in missing:
                missing.append(no_trace_note)
            if self_report_note not in observed:
                observed.append(self_report_note)
        boundary["missing_observed_signals"] = missing
        boundary["what_was_observed"] = observed
        gaps = synthesis.get("evidence_gaps")
        if not isinstance(gaps, list):
            gaps = []
            synthesis["evidence_gaps"] = gaps
        without_trace_gap = "Prototype-validation findings here are simulated expectations, not observed action traces."
        with_trace_gap = "Observed action traces here are application-supplied artifacts, not live human usability proof."
        gaps = [
            item for item in gaps
            if item not in contradictory_no_trace_notes and item != without_trace_gap and item != with_trace_gap
        ]
        gaps.append(with_trace_gap if observed_trace_available else without_trace_gap)
        synthesis["evidence_gaps"] = gaps

    @staticmethod
    def _render_transcript(session: InterviewSession) -> str:
        lines = [
            f"# Facilitated Interview: {session.persona_name}", "",
            f"> {session.synthetic_only_disclaimer}", "",
            f"Interview mode: {session.interview_mode}",
            *( [f"Hypothesis: {session.hypothesis}"] if session.hypothesis else [] ),
            *( [f"Concept: {session.concept_label}"] if session.concept_label else [] ),
            *( [f"Stimulus type: {session.stimulus_type}"] if session.stimulus_type else [] ),
            *( [f"Stimulus artifact: {session.stimulus_artifact}"] if session.stimulus_artifact else [] ),
            *( [f"Stimulus artifact snapshot: {session.stimulus_artifact_snapshot}"] if session.stimulus_artifact_snapshot else [] ),
            *( [f"Prototype task: {session.prototype_task}"] if session.prototype_task else [] ),
            "",
            f"Research goal: {session.research_goal}", "",
            f"Turn policy: soft {session.soft_turn_limit}, hard {session.hard_turn_limit}",
            *( [f"Coverage complete: {session.coverage_status.get('coverage_complete', False)}"] if session.coverage_status else [] ),
            "",
        ]
        if session.stimulus_analysis:
            analysis_type = str(session.stimulus_analysis.get("analysis_type", session.stimulus_type or "stimulus")).strip()
            lines.extend([
                "## Stimulus Review", "",
                f"- Summary: {session.stimulus_analysis.get('summary', '')}",
                f"- Primary action candidates: {', '.join(session.stimulus_analysis.get('primary_action_candidates', [])) or '(none)'}",
                f"- Trust risks: {', '.join(session.stimulus_analysis.get('trust_risks', [])) or '(none)'}",
                f"- Missing context: {', '.join(session.stimulus_analysis.get('missing_context', [])) or '(none)'}",
                f"- Task relevance: {session.stimulus_analysis.get('task_relevance', '')}",
                f"- Evidence boundary: {session.stimulus_analysis.get('evidence_boundary', '')}",
                "",
            ])
            if analysis_type == "flow":
                lines.extend([
                    f"- Screen sequence: {', '.join(session.stimulus_analysis.get('screen_sequence', [])) or '(none)'}",
                    f"- Transition confusions: {', '.join(session.stimulus_analysis.get('transition_confusions', [])) or '(none)'}",
                    f"- Setup burdens: {', '.join(session.stimulus_analysis.get('setup_burdens', [])) or '(none)'}",
                    f"- Likely drop-off points: {', '.join(session.stimulus_analysis.get('likely_drop_off_points', [])) or '(none)'}",
                    "",
                ])
            elif analysis_type == "clickable_manifest":
                lines.extend([
                    f"- Prototype label: {session.stimulus_analysis.get('prototype_label', '')}",
                    f"- Screen count: {session.stimulus_analysis.get('screen_count', 0)}",
                    f"- Task step count: {session.stimulus_analysis.get('task_step_count', 0)}",
                    f"- Start screen: {session.stimulus_analysis.get('start_screen', '')}",
                    f"- Visited screens: {', '.join(session.stimulus_analysis.get('visited_screens', [])) or '(none)'}",
                    f"- Evidence boundary: {session.stimulus_analysis.get('evidence_boundary', '')}",
                    "",
                ])
            else:
                lines.extend([
                    f"- Visible elements: {', '.join(session.stimulus_analysis.get('visible_elements', [])) or '(none)'}",
                    f"- Interpretation risks: {', '.join(session.stimulus_analysis.get('interpretation_risks', [])) or '(none)'}",
                    "",
                ])
        if session.observed_action_trace:
            trace = session.observed_action_trace
            actions = trace.get("actions", [])
            lines.extend([
                "## Observed Action Trace",
                "",
                f"- Trace label: {trace.get('trace_label', '') or '(none)'}",
                f"- Trace version: {trace.get('trace_version', '') or '(none)'}",
                f"- Task outcome: {trace.get('task_outcome', '') or '(unknown)'}",
                f"- Summary: {trace.get('summary', '') or '(none)'}",
                f"- First error: {trace.get('first_error', '') or '(none)'}",
                f"- Drop-off point: {trace.get('drop_off_point', '') or '(none)'}",
                f"- Completion notes: {trace.get('completion_notes', '') or '(none)'}",
                "",
            ])
            if isinstance(actions, list):
                for action in actions[:8]:
                    if not isinstance(action, dict):
                        continue
                    lines.append(
                        f"- Step {action.get('step', '?')}: {action.get('action', 'unknown')} -> "
                        f"{action.get('target', '(unspecified)')} [{action.get('result', 'unknown')}]"
                    )
                if len(actions) > 8:
                    lines.append(f"- Additional observed actions omitted: {len(actions) - 8}")
            for item in trace.get("missing_signals", []):
                lines.append(f"- Missing observed signal: {item}")
            lines.append("")
        for exchange in session.exchanges:
            lines.extend([
                f"## Exchange {exchange.exchange_id}", "",
                f"**Facilitator ({exchange.facilitator_phase} / {exchange.probing_strategy})**", "",
                exchange.facilitator_question, "",
                f"**{session.persona_name}**", "",
                exchange.persona_response, "",
            ])
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _render_insights(session: InterviewSession) -> str:
        report = session.insight_report
        if session.interview_mode == "concept_validation":
            return FacilitatedInterviewRuntime._render_concept_insights(session)
        if session.interview_mode == "prototype_validation":
            return FacilitatedInterviewRuntime._render_prototype_insights(session)
        lines = [
            f"# Interview Insights: {session.persona_name}", "",
            f"> {report.get('synthetic_only_disclaimer', session.synthetic_only_disclaimer)}", "",
            "## Executive Summary", "", str(report.get("executive_summary", "")), "",
            "## Insights", "",
        ]
        for item in report.get("insights", []):
            lines.append(f"- {item.get('insight', '')} ({item.get('confidence', 'unknown')}; refs: {', '.join(item.get('evidence_refs', []))})")
        lines.extend(["", "## Root-Cause Hypotheses", ""])
        for item in report.get("root_cause_hypotheses", []):
            lines.append(f"- {item.get('hypothesis', '')} ({item.get('confidence', 'unknown')})")
        assessment = report.get("hypothesis_assessment", {})
        if session.interview_mode == "validate_hypothesis":
            lines.extend(["", "## Hypothesis Assessment", ""])
            lines.append(f"- Verdict: {assessment.get('verdict', 'not_tested')}")
            lines.append(f"- Confidence: {assessment.get('confidence', 'low')}")
        lines.extend(["", "## Potential Over-Optimism Risks", ""])
        risks = report.get("potential_over_optimism_risks", [])
        for item in risks:
            lines.append(f"- {item}")
        if not risks:
            lines.append("- No explicit over-optimism risks were generated.")
        lines.extend(["", "## How Might We", ""])
        for item in report.get("how_might_we_questions", []):
            lines.append(f"- {item}")
        lines.extend(["", "## Evidence Gaps", ""])
        for item in report.get("evidence_gaps", []):
            lines.append(f"- {item}")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _render_concept_insights(session: InterviewSession) -> str:
        report = session.insight_report
        problem = report.get("problem_evidence", {})
        workaround = report.get("current_workaround", {})
        trust = report.get("trust_boundary", {})
        value = report.get("first_value_requirement", {})
        pricing = report.get("pricing_signal", {})
        retention = report.get("retention_risk", {})
        concept_label = session.concept_label or "Concept Validation"
        lines = [
            f"# {concept_label} Interview: {session.persona_name}", "",
            f"> {report.get('synthetic_only_disclaimer', session.synthetic_only_disclaimer)}", "",
            "## Problem Evidence", "", f"- Strength: {problem.get('strength', 'unknown')}",
        ]
        for quote in problem.get("supporting_quotes", []):
            lines.append(f"- \"{quote.get('quote', '')}\" ({quote.get('evidence_ref', '')})")
        lines.extend(["", "## Current Workaround", ""])
        lines.append(f"- Pain: {workaround.get('pain_level', 'unknown')}; switching: {workaround.get('switching_difficulty', 'unknown')}")
        for item in workaround.get("existing_workaround", []): lines.append(f"- {item}")
        lines.extend(["", "## Trust Boundary", ""])
        for item in trust.get("required_trust_explanation", []): lines.append(f"- {item}")
        lines.extend(["", "## First Value", ""])
        for item in value.get("first_use_success", []): lines.append(f"- {item}")
        lines.extend(["", "## Pricing Signal", ""])
        lines.append(f"- Monthly comfort: {pricing.get('monthly_comfort_range', 'unknown')} ({pricing.get('evidence_strength', 'unknown')})")
        lines.extend(["", "## Retention Risk", "", f"- Workflow effect: {retention.get('workflow_effect', 'unclear')}"])
        for item in retention.get("drop_off_reasons", []): lines.append(f"- Drop-off: {item}")
        lines.extend(["", "## Assumption Validation", ""])
        for item in report.get("assumption_validation", []):
            lines.append(f"- [{item.get('status', 'unknown')}] {item.get('assumption', '')}")
        lines.extend(["", "## Key Insights", ""])
        for item in report.get("key_insights", []): lines.append(f"- {item}")
        lines.extend(["", "## Potential Over-Optimism Risks", ""])
        risks = report.get("potential_over_optimism_risks", [])
        for item in risks:
            lines.append(f"- {item}")
        if not risks:
            lines.append("- No explicit over-optimism risks were generated.")
        lines.extend(["", "## Next Experiment", "", str(report.get("next_experiment", ""))])
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _render_prototype_insights(session: InterviewSession) -> str:
        report = session.insight_report
        interpretation = report.get("stimulus_interpretation", {})
        journey = report.get("task_journey", {})
        boundary = report.get("behavioral_evidence_boundary", {})
        stimulus_label = session.stimulus_artifact or session.concept_label or "Prototype Validation"
        lines = [
            f"# {stimulus_label} Interview: {session.persona_name}", "",
            f"> {report.get('synthetic_only_disclaimer', session.synthetic_only_disclaimer)}", "",
            "## Stimulus Context", "",
            f"- Type: {session.stimulus_type or 'unknown'}",
            f"- Artifact: {session.stimulus_artifact or 'undisclosed'}",
            f"- Snapshot: {session.stimulus_artifact_snapshot or 'undisclosed'}",
            f"- Task: {session.prototype_task or 'undisclosed'}",
        ]
        if session.stimulus_analysis:
            analysis_type = str(session.stimulus_analysis.get("analysis_type", session.stimulus_type or "stimulus")).strip()
            lines.extend([
                "",
                "## Stimulus Review",
                "",
                f"- Summary: {session.stimulus_analysis.get('summary', '')}",
            ])
            for item in session.stimulus_analysis.get("primary_action_candidates", []):
                lines.append(f"- Primary action candidate: {item}")
            for item in session.stimulus_analysis.get("trust_risks", []):
                lines.append(f"- Trust risk: {item}")
            for item in session.stimulus_analysis.get("missing_context", []):
                lines.append(f"- Missing context: {item}")
            if analysis_type == "flow":
                for item in session.stimulus_analysis.get("screen_sequence", []):
                    lines.append(f"- Screen sequence: {item}")
                for item in session.stimulus_analysis.get("transition_confusions", []):
                    lines.append(f"- Transition confusion: {item}")
                for item in session.stimulus_analysis.get("setup_burdens", []):
                    lines.append(f"- Setup burden: {item}")
                for item in session.stimulus_analysis.get("likely_drop_off_points", []):
                    lines.append(f"- Likely drop-off point: {item}")
            elif analysis_type == "clickable_manifest":
                lines.append(f"- Prototype label: {session.stimulus_analysis.get('prototype_label', '')}")
                lines.append(f"- Screen count: {session.stimulus_analysis.get('screen_count', 0)}")
                lines.append(f"- Task step count: {session.stimulus_analysis.get('task_step_count', 0)}")
                lines.append(f"- Start screen: {session.stimulus_analysis.get('start_screen', '')}")
                for item in session.stimulus_analysis.get("visited_screens", []):
                    lines.append(f"- Visited screen: {item}")
                lines.append(f"- Evidence boundary: {session.stimulus_analysis.get('evidence_boundary', '')}")
            else:
                for item in session.stimulus_analysis.get("visible_elements", []):
                    lines.append(f"- Visible element: {item}")
                for item in session.stimulus_analysis.get("interpretation_risks", []):
                    lines.append(f"- Interpretation risk: {item}")
        if session.observed_action_trace:
            trace = session.observed_action_trace
            actions = trace.get("actions", [])
            lines.extend([
                "",
                "## Observed Action Trace",
                "",
                f"- Trace label: {trace.get('trace_label', '') or '(none)'}",
                f"- Trace version: {trace.get('trace_version', '') or '(none)'}",
                f"- Task outcome: {trace.get('task_outcome', '') or '(unknown)'}",
                f"- Summary: {trace.get('summary', '') or '(none)'}",
                f"- First error: {trace.get('first_error', '') or '(none)'}",
                f"- Drop-off point: {trace.get('drop_off_point', '') or '(none)'}",
                f"- Completion notes: {trace.get('completion_notes', '') or '(none)'}",
            ])
            if isinstance(actions, list):
                for action in actions[:8]:
                    if not isinstance(action, dict):
                        continue
                    lines.append(
                        f"- Step {action.get('step', '?')}: {action.get('action', 'unknown')} -> "
                        f"{action.get('target', '(unspecified)')} [{action.get('result', 'unknown')}]"
                    )
                if len(actions) > 8:
                    lines.append(f"- Additional observed actions omitted: {len(actions) - 8}")
            for item in trace.get("missing_signals", []):
                lines.append(f"- Missing observed signal: {item}")
        lines.extend([
            "",
            "## Stimulus Interpretation", "",
            f"- Summary: {interpretation.get('summary', '')}",
        ])
        for quote in interpretation.get("supporting_quotes", []):
            lines.append(f"- \"{quote.get('quote', '')}\" ({quote.get('evidence_ref', '')})")
        for item in interpretation.get("interpretation_breakdowns", []):
            lines.append(f"- Breakdown: {item}")
        for item in interpretation.get("trust_signals", []):
            lines.append(f"- Trust signal: {item}")
        lines.extend(["", "## Task Journey", ""])
        for item in journey.get("first_action_expectations", []):
            lines.append(f"- First action: {item}")
        for item in journey.get("expected_path", []):
            lines.append(f"- Expected path: {item}")
        for item in journey.get("setup_confusions", []):
            lines.append(f"- Setup confusion: {item}")
        for item in journey.get("likely_drop_off_points", []):
            lines.append(f"- Drop-off: {item}")
        for item in journey.get("task_success_signals", []):
            lines.append(f"- Success signal: {item}")
        lines.extend(["", "## Evidence Boundary", ""])
        lines.append(f"- Evidence level: {boundary.get('evidence_level', 'unknown')}")
        lines.append(f"- Observed action available: {boundary.get('observed_action_available', False)}")
        for item in boundary.get("what_was_observed", []):
            lines.append(f"- Observed: {item}")
        for item in boundary.get("missing_observed_signals", []):
            lines.append(f"- Missing observed signal: {item}")
        lines.extend(["", "## Assumption Validation", ""])
        for item in report.get("assumption_validation", []):
            lines.append(f"- [{item.get('status', 'unknown')}] {item.get('assumption', '')}")
        lines.extend(["", "## Key Insights", ""])
        for item in report.get("key_insights", []):
            lines.append(f"- {item}")
        lines.extend(["", "## Potential Over-Optimism Risks", ""])
        risks = report.get("potential_over_optimism_risks", [])
        for item in risks:
            lines.append(f"- {item}")
        if not risks:
            lines.append("- No explicit over-optimism risks were generated.")
        lines.extend(["", "## Next Experiment", "", str(report.get("next_experiment", ""))])
        lines.extend(["", "## Evidence Gaps", ""])
        for item in report.get("evidence_gaps", []):
            lines.append(f"- {item}")
        return "\n".join(lines).rstrip() + "\n"
