from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ai_validation_swarm.conversation.providers import ConversationProvider
from ai_validation_swarm.conversation.realism import validate_friction_mode
from ai_validation_swarm.conversation.runtime import (
    DRIVER_TRACE_PROMPT_VERSION,
    ConversationRuntime,
    resolve_persona_folder,
)
from ai_validation_swarm.domain.models import utc_now_iso
from ai_validation_swarm.facilitator.concept_protocols import load_concept_protocol
from ai_validation_swarm.facilitator.models import FacilitatorDecision, InterviewExchange, InterviewSession
from ai_validation_swarm.facilitator.optimism import attach_over_optimism_risks
from ai_validation_swarm.facilitator.providers import FacilitatorProvider
from ai_validation_swarm.facilitator.runtime import (
    FACILITATOR_PROMPT_VERSION,
    CONCEPT_SYNTHESIS_PROMPT_VERSION,
    HYPOTHESIS_EVIDENCE_JUDGE_PROMPT_VERSION,
    PROTOTYPE_SYNTHESIS_PROMPT_VERSION,
    SYNTHESIS_PROMPT_VERSION,
    FacilitatedInterviewRuntime,
    _read,
    _repo_root,
)
from ai_validation_swarm.storage.files import ensure_dir, load_persona, read_json, write_json, write_markdown


QUALITY_PROMPT_VERSION = "facilitator-quality-evaluator/v2"
FACILITATOR_AUDIT_FEEDBACK_PROMPT_VERSION = "facilitator-audit-feedback/v1"


class ObserverControlledInterviewRuntime(FacilitatedInterviewRuntime):
    def __init__(
        self,
        *,
        data_dir: Path,
        session_dir: Path,
        facilitator_provider: FacilitatorProvider,
        persona_provider: ConversationProvider,
        quality_provider: FacilitatorProvider,
        progress_writer=None,
        approved_learning_rules_path: Path | None = None,
    ) -> None:
        super().__init__(
            data_dir=data_dir,
            session_dir=session_dir,
            facilitator_provider=facilitator_provider,
            persona_provider=persona_provider,
            progress_writer=progress_writer,
            approved_learning_rules_path=approved_learning_rules_path,
        )
        self.quality_provider = quality_provider

    def start(
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
    ) -> tuple[Path, InterviewSession]:
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
        interview_id = f"observed_{utc_now_iso()[:10].replace('-', '')}_{uuid.uuid4().hex[:8]}"
        folder = self.session_dir / interview_id
        ensure_dir(folder)
        prepared_stimulus = self._prepare_stimulus_context(
            interview_folder=folder,
            interview_mode=mode,
            product_context=product_context.strip(),
            stimulus_type=resolved_stimulus_type,
            stimulus_artifact=stimulus_artifact.strip(),
            prototype_task=prototype_task.strip(),
        )
        persona_runtime = ConversationRuntime(
            data_dir=self.data_dir,
            session_dir=folder / "persona_runtime",
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
            quality_provider=self.quality_provider.provider_name,
            quality_model=self.quality_provider.model_name,
            quality_prompt_version=QUALITY_PROMPT_VERSION,
            facilitator_audit_feedback_prompt_version=FACILITATOR_AUDIT_FEEDBACK_PROMPT_VERSION,
            persona_driver_trace_prompt_version=DRIVER_TRACE_PROMPT_VERSION,
            max_turns=hard_limit,
            soft_turn_limit=soft_limit,
            hard_turn_limit=hard_limit,
            status="requesting_facilitator",
        )
        self._update_coverage_status(session)
        self._annotate_approved_learning_rules(session)
        self._save_controlled(session, folder)
        self._progress(
            f"start_observed interview_id={interview_id} persona={persona_id} mode={mode} "
            f"soft={soft_limit} hard={hard_limit}"
        )
        self._request_facilitator(
            session,
            folder,
            self._opening_prompt(session),
            failed_operation="request_initial_question",
        )
        return folder, session

    def load(self, interview_id: str) -> tuple[Path, InterviewSession]:
        folder = self.session_dir / interview_id
        path = folder / "interview.json"
        if not path.exists():
            raise ValueError(f"Observed interview '{interview_id}' was not found.")
        return folder, InterviewSession.from_dict(read_json(path))

    def continue_interview(self, interview_id: str) -> InterviewSession:
        folder, session = self.load(interview_id)
        if session.status == "completed":
            return session
        if session.status == "failed":
            raise ValueError("Interview is in a failed state. Use retry before continuing.")
        if session.status == "paused":
            session.status = "awaiting_observer"
            self._save_controlled(session, folder)
        if not session.pending_facilitator_decision:
            self._request_facilitator(
                session,
                folder,
                self._continuation_prompt(session),
                failed_operation="request_next_question",
            )
            return session

        decision = FacilitatorDecision(**session.pending_facilitator_decision)
        if decision.should_end:
            return self.finalize(interview_id, stop_reason=decision.end_reason or "facilitator_decided_to_end")
        return self._ask_persona(
            folder,
            session,
            question=decision.message_to_persona,
            phase=decision.interview_phase,
            strategy=decision.probing_strategy,
            question_evidence_basis=decision.question_evidence_basis,
            failed_operation="ask_pending_question",
        )

    def steer(self, interview_id: str, instruction: str) -> InterviewSession:
        cleaned = instruction.strip()
        if not cleaned:
            raise ValueError("Observer steering instruction cannot be empty.")
        folder, session = self.load(interview_id)
        if session.status == "completed":
            raise ValueError("Completed interview cannot be steered.")
        intervention = self._intervention(session, "steer", cleaned)
        previous = session.pending_facilitator_decision.get("message_to_persona", "")
        intervention["superseded_question"] = previous
        self._mark_latest_decision_status(session, "superseded_by_observer")
        session.pending_facilitator_decision = {}
        prompt = (
            f"OBSERVER DIRECTION:\n{cleaned}\n\n"
            f"PREVIOUSLY PROPOSED QUESTION:\n{previous or '(none)'}\n\n"
            f"TRANSCRIPT:\n{self._plain_transcript(session)}\n\n"
            "Use the observer's research direction as input, but independently preserve neutrality and evidence discipline. "
            "Return a revised next decision or explain through should_end why the interview should stop."
        )
        self._request_facilitator(
            session,
            folder,
            prompt,
            failed_operation="revise_after_observer_direction",
            failed_payload={"instruction": cleaned, "prompt": prompt},
        )
        return session

    def ask_direct(self, interview_id: str, question: str) -> InterviewSession:
        cleaned = question.strip()
        if not cleaned:
            raise ValueError("Observer question cannot be empty.")
        folder, session = self.load(interview_id)
        if session.status == "completed":
            raise ValueError("Completed interview cannot accept another question.")
        intervention = self._intervention(session, "direct_question", cleaned)
        intervention["superseded_question"] = session.pending_facilitator_decision.get("message_to_persona", "")
        self._mark_latest_decision_status(session, "superseded_by_observer")
        session.pending_facilitator_decision = {}
        self._save_controlled(session, folder)
        return self._ask_persona(
            folder,
            session,
            question=cleaned,
            phase="observer_intervention",
            strategy="direct_observer_question",
            question_evidence_basis="observer_question",
            failed_operation="ask_observer_question",
            failed_payload={"question": cleaned},
        )

    def suggest_question(self, interview_id: str, question: str) -> InterviewSession:
        cleaned = question.strip()
        if not cleaned:
            raise ValueError("Observer suggested question cannot be empty.")
        folder, session = self.load(interview_id)
        if session.status == "completed":
            raise ValueError("Completed interview cannot accept another question.")
        intervention = self._intervention(session, "suggested_question", cleaned)
        previous = session.pending_facilitator_decision.get("message_to_persona", "")
        intervention["superseded_question"] = previous
        self._mark_latest_decision_status(session, "superseded_by_observer")
        session.pending_facilitator_decision = {}
        prompt = (
            f"OBSERVER SUGGESTED QUESTION:\n{cleaned}\n\n"
            f"CURRENTLY PROPOSED QUESTION:\n{previous or '(none)'}\n\n"
            f"TRANSCRIPT:\n{self._plain_transcript(session)}\n\n"
            "Evaluate the observer's research intent independently. If the wording is leading, compound, repetitive, "
            "premature, or skips an unresolved evidence gap, rewrite it as a short neutral question or defer it. "
            "Do not use the wording verbatim unless it is methodologically sound."
        )
        self._request_facilitator(
            session,
            folder,
            prompt,
            failed_operation="review_observer_question",
            failed_payload={"question": cleaned, "prompt": prompt},
        )
        return session

    def pause(self, interview_id: str) -> InterviewSession:
        folder, session = self.load(interview_id)
        if session.status != "completed":
            self._intervention(session, "pause", "Observer paused the interview.")
            session.status = "paused"
            self._save_controlled(session, folder)
        return session

    def retry(self, interview_id: str) -> InterviewSession:
        folder, session = self.load(interview_id)
        if session.status != "failed":
            raise ValueError("Retry is only available when the interview is in a failed state.")
        operation = session.failed_operation
        payload = dict(session.failed_payload)
        session.last_error = ""
        session.failed_operation = ""
        session.failed_payload = {}

        if operation in {
            "request_initial_question", "request_next_question", "revise_after_observer_direction",
            "review_observer_question",
        }:
            prompt = str(payload.get("prompt") or (
                self._opening_prompt(session) if not session.exchanges else self._continuation_prompt(session)
            ))
            self._request_facilitator(session, folder, prompt, failed_operation=operation, failed_payload=payload)
            return session
        if operation == "ask_pending_question":
            session.status = "awaiting_observer"
            self._save_controlled(session, folder)
            return self.continue_interview(interview_id)
        if operation == "ask_observer_question":
            return self._ask_persona(
                folder,
                session,
                question=str(payload.get("question", "")),
                phase="observer_intervention",
                strategy="direct_observer_question",
                question_evidence_basis="observer_question",
                failed_operation=operation,
                failed_payload=payload,
            )
        if operation in {
            "judge_hypothesis_evidence",
            "synthesize",
            "generate_persona_driver_trace",
            "evaluate_quality",
            "generate_facilitator_audit_feedback",
        }:
            self._progress(f"retry_failed_stage operation={operation} interview_id={interview_id}")
            return self.finalize(interview_id, stop_reason=session.stop_reason or "observer_stop")
        raise ValueError(f"Unsupported failed operation '{operation}'.")

    def finalize(self, interview_id: str, *, stop_reason: str = "observer_stop") -> InterviewSession:
        folder, session = self.load(interview_id)
        if session.status == "completed":
            return session
        session.stop_reason = stop_reason
        self._mark_latest_decision_status(session, "not_asked_at_close")
        session.pending_facilitator_decision = {}

        if session.interview_mode == "validate_hypothesis" and not session.hypothesis_evidence_judgment:
            session.status = "judging_hypothesis_evidence"
            self._save_controlled(session, folder)
            self._progress(f"judging_hypothesis_evidence interview_id={interview_id}")
            try:
                judgment, judge_session_id = self._judge_hypothesis_evidence(session)
            except Exception as exc:
                return self._fail(session, folder, "judge_hypothesis_evidence", exc)
            session.hypothesis_evidence_judgment = judgment
            session.hypothesis_evidence_judge_provider_session_id = judge_session_id
            write_json(folder / "hypothesis_evidence_judgment.json", judgment)

        if not session.insight_report:
            session.status = "synthesizing"
            self._save_controlled(session, folder)
            self._progress(f"synthesizing_insights interview_id={interview_id}")
            try:
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
            except Exception as exc:
                return self._fail(session, folder, "synthesize", exc)
            session.facilitator_provider_session_id = facilitator_session_id
            self._enforce_synthesis_evidence_scope(session, synthesis)
            self._enforce_prototype_evidence_boundary(session, synthesis)
            synthesis = attach_over_optimism_risks(
                synthesis,
                conversation_realism=self._persona_conversation_realism(folder, session),
                interview_mode=session.interview_mode,
            )
            session.insight_report = synthesis
            write_json(folder / "insight_report.json", synthesis)
            write_markdown(folder / "insights.md", self._render_insights(session))

        if not session.persona_driver_trace:
            session.status = "analyzing_persona_driver_trace"
            self._save_controlled(session, folder)
            self._progress(f"generating_persona_driver_trace interview_id={interview_id}")
            try:
                self._generate_persona_driver_trace(folder, session)
            except Exception as exc:
                warning = (
                    "Persona driver trace generation failed; continuing without persona_driver_trace. "
                    f"{exc}"
                )
                (folder / "persona_driver_trace.error.txt").write_text(str(exc), encoding="utf-8")
                self._progress(f"persona_driver_trace_skipped interview_id={interview_id} error={exc}")
                session.last_error = warning
                session.updated_at = utc_now_iso()
                self._save_controlled(session, folder)

        session.status = "evaluating_quality"
        self._save_controlled(session, folder)
        self._progress(f"evaluating_quality interview_id={interview_id}")
        try:
            quality, quality_session_id = self.quality_provider.evaluate_quality(
                system_prompt=self._quality_system_prompt(),
                user_prompt=self._quality_user_prompt(session),
            )
        except Exception as exc:
            return self._fail(session, folder, "evaluate_quality", exc)
        session.quality_provider_session_id = quality_session_id
        session.quality_evaluation = quality
        session.status = "auditing_facilitator"
        self._save_controlled(session, folder)
        self._progress(f"auditing_facilitator interview_id={interview_id}")
        try:
            audit_feedback, audit_session_id = self.quality_provider.generate_audit_feedback(
                system_prompt=self._audit_feedback_system_prompt(),
                user_prompt=self._audit_feedback_user_prompt(session),
                provider_session_id=session.quality_provider_session_id,
            )
        except Exception as exc:
            return self._fail(session, folder, "generate_facilitator_audit_feedback", exc)
        session.facilitator_audit_feedback_provider_session_id = audit_session_id
        session.facilitator_audit_feedback = audit_feedback
        session.status = "completed"
        session.last_error = ""
        session.failed_operation = ""
        session.failed_payload = {}
        session.updated_at = utc_now_iso()
        self._save_controlled(session, folder)
        write_json(folder / "quality_evaluation.json", quality)
        write_markdown(folder / "quality_evaluation.md", self._render_quality(quality))
        write_json(folder / "facilitator_audit_feedback.json", audit_feedback)
        write_markdown(
            folder / "facilitator_audit_feedback.md",
            self._render_audit_feedback(audit_feedback),
        )
        self._progress(f"completed_observed interview_id={interview_id}")
        return session

    def reevaluate_quality(self, interview_id: str) -> InterviewSession:
        folder, session = self.load(interview_id)
        if not session.insight_report:
            raise ValueError("Quality evaluation requires a completed synthesis.")
        previous_path = folder / "quality_evaluation.json"
        if previous_path.exists():
            write_json(folder / "quality_evaluation.previous.json", read_json(previous_path))
        audit_previous_path = folder / "facilitator_audit_feedback.json"
        if audit_previous_path.exists():
            write_json(folder / "facilitator_audit_feedback.previous.json", read_json(audit_previous_path))
        session.status = "evaluating_quality"
        session.quality_evaluation = {}
        session.quality_provider_session_id = ""
        session.facilitator_audit_feedback = {}
        session.facilitator_audit_feedback_provider_session_id = ""
        self._save_controlled(session, folder)
        self._progress(f"reevaluating_quality interview_id={interview_id}")
        try:
            quality, quality_session_id = self.quality_provider.evaluate_quality(
                system_prompt=self._quality_system_prompt(),
                user_prompt=self._quality_user_prompt(session),
            )
        except Exception as exc:
            return self._fail(session, folder, "evaluate_quality", exc)
        session.quality_provider_session_id = quality_session_id
        session.quality_evaluation = quality
        session.status = "auditing_facilitator"
        self._save_controlled(session, folder)
        self._progress(f"auditing_facilitator interview_id={interview_id}")
        try:
            audit_feedback, audit_session_id = self.quality_provider.generate_audit_feedback(
                system_prompt=self._audit_feedback_system_prompt(),
                user_prompt=self._audit_feedback_user_prompt(session),
                provider_session_id=session.quality_provider_session_id,
            )
        except Exception as exc:
            return self._fail(session, folder, "generate_facilitator_audit_feedback", exc)
        session.facilitator_audit_feedback_provider_session_id = audit_session_id
        session.facilitator_audit_feedback = audit_feedback
        session.status = "completed"
        session.last_error = ""
        session.failed_operation = ""
        session.failed_payload = {}
        session.updated_at = utc_now_iso()
        self._save_controlled(session, folder)
        write_json(folder / "quality_evaluation.json", quality)
        write_markdown(folder / "quality_evaluation.md", self._render_quality(quality))
        write_json(folder / "facilitator_audit_feedback.json", audit_feedback)
        write_markdown(
            folder / "facilitator_audit_feedback.md",
            self._render_audit_feedback(audit_feedback),
        )
        self._progress(f"completed_quality_reevaluation interview_id={interview_id}")
        return session

    def resynthesize(self, interview_id: str) -> InterviewSession:
        folder, session = self.load(interview_id)
        if not session.exchanges:
            raise ValueError("Resynthesis requires at least one completed exchange.")
        if session.insight_report:
            write_json(folder / "insight_report.previous.json", session.insight_report)
        if session.quality_evaluation:
            write_json(folder / "quality_evaluation.previous.json", session.quality_evaluation)
        if session.facilitator_audit_feedback:
            write_json(folder / "facilitator_audit_feedback.previous.json", session.facilitator_audit_feedback)
        if session.persona_driver_trace:
            write_json(folder / "persona_driver_trace.previous.json", session.persona_driver_trace)
        session.insight_report = {}
        session.quality_evaluation = {}
        session.facilitator_audit_feedback = {}
        session.persona_driver_trace = {}
        session.persona_driver_trace_provider_session_id = ""
        if session.hypothesis_evidence_judgment:
            write_json(folder / "hypothesis_evidence_judgment.previous.json", session.hypothesis_evidence_judgment)
        session.hypothesis_evidence_judgment = {}
        session.hypothesis_evidence_judge_provider_session_id = ""
        session.quality_provider_session_id = ""
        session.facilitator_audit_feedback_provider_session_id = ""
        session.status = "synthesizing"
        session.last_error = ""
        session.failed_operation = ""
        session.failed_payload = {}
        self._save_controlled(session, folder)
        self._progress(f"resynthesizing interview_id={interview_id}")
        if session.interview_mode == "validate_hypothesis":
            try:
                judgment, judge_session_id = self._judge_hypothesis_evidence(session)
            except Exception as exc:
                return self._fail(session, folder, "judge_hypothesis_evidence", exc)
            session.hypothesis_evidence_judgment = judgment
            session.hypothesis_evidence_judge_provider_session_id = judge_session_id
            write_json(folder / "hypothesis_evidence_judgment.json", judgment)
        try:
            if session.interview_mode == "concept_validation":
                synthesis, facilitator_session_id = self.facilitator_provider.synthesize_concept(
                    system_prompt=self._synthesis_system_prompt("concept_validation"),
                    user_prompt=self._synthesis_user_prompt(session),
                    provider_session_id=session.facilitator_provider_session_id,
                )
            else:
                synthesis, facilitator_session_id = self.facilitator_provider.synthesize(
                    system_prompt=self._synthesis_system_prompt(session.interview_mode),
                    user_prompt=self._synthesis_user_prompt(session),
                    provider_session_id=session.facilitator_provider_session_id,
                )
        except Exception as exc:
            return self._fail(session, folder, "synthesize", exc)
        session.facilitator_provider_session_id = facilitator_session_id
        self._enforce_synthesis_evidence_scope(session, synthesis)
        synthesis = attach_over_optimism_risks(
            synthesis,
            conversation_realism=self._persona_conversation_realism(folder, session),
            interview_mode=session.interview_mode,
        )
        session.insight_report = synthesis
        write_json(folder / "insight_report.json", synthesis)
        write_markdown(folder / "insights.md", self._render_insights(session))

        session.status = "analyzing_persona_driver_trace"
        self._save_controlled(session, folder)
        self._progress(f"generating_persona_driver_trace interview_id={interview_id}")
        try:
            self._generate_persona_driver_trace(folder, session)
        except Exception as exc:
            return self._fail(session, folder, "generate_persona_driver_trace", exc)

        session.status = "evaluating_quality"
        self._save_controlled(session, folder)
        self._progress(f"evaluating_quality interview_id={interview_id}")
        try:
            quality, quality_session_id = self.quality_provider.evaluate_quality(
                system_prompt=self._quality_system_prompt(),
                user_prompt=self._quality_user_prompt(session),
            )
        except Exception as exc:
            return self._fail(session, folder, "evaluate_quality", exc)
        session.quality_provider_session_id = quality_session_id
        session.quality_evaluation = quality
        session.status = "auditing_facilitator"
        self._save_controlled(session, folder)
        self._progress(f"auditing_facilitator interview_id={interview_id}")
        try:
            audit_feedback, audit_session_id = self.quality_provider.generate_audit_feedback(
                system_prompt=self._audit_feedback_system_prompt(),
                user_prompt=self._audit_feedback_user_prompt(session),
                provider_session_id=session.quality_provider_session_id,
            )
        except Exception as exc:
            return self._fail(session, folder, "generate_facilitator_audit_feedback", exc)
        session.facilitator_audit_feedback_provider_session_id = audit_session_id
        session.facilitator_audit_feedback = audit_feedback
        session.status = "completed"
        session.updated_at = utc_now_iso()
        self._save_controlled(session, folder)
        write_json(folder / "quality_evaluation.json", quality)
        write_markdown(folder / "quality_evaluation.md", self._render_quality(quality))
        write_json(folder / "facilitator_audit_feedback.json", audit_feedback)
        write_markdown(
            folder / "facilitator_audit_feedback.md",
            self._render_audit_feedback(audit_feedback),
        )
        self._progress(f"completed_resynthesis interview_id={interview_id}")
        return session

    def _generate_persona_driver_trace(self, folder: Path, session: InterviewSession) -> None:
        persona_folder = resolve_persona_folder(self.data_dir, session.persona_id)
        persona = load_persona(persona_folder)
        persona_runtime = ConversationRuntime(
            data_dir=self.data_dir,
            session_dir=folder / "persona_runtime",
            provider=self.persona_provider,
        )
        persona_session, _, _ = persona_runtime.resume(session.persona_conversation_session_id)
        payload, provider_session_id = persona_runtime.generate_persona_driver_trace(
            persona_session,
            persona,
            persona_folder,
            interview_transcript=self._plain_transcript(session),
            research_goal=session.research_goal,
            product_context=session.product_context,
            output_language=session.output_language,
        )
        session.persona_driver_trace = payload
        session.persona_driver_trace_provider_session_id = provider_session_id
        session.updated_at = utc_now_iso()
        self._save_controlled(session, folder)
        write_json(folder / "persona_driver_trace.json", payload)
        write_markdown(
            folder / "persona_driver_trace.md",
            self._render_persona_driver_trace(session),
        )

    @staticmethod
    def _audit_feedback_system_prompt() -> str:
        root = _repo_root()
        return _read(root / "src" / "ai_validation_swarm" / "prompts" / "facilitator-audit-feedback" / "v1.md")

    @staticmethod
    def _audit_feedback_user_prompt(session: InterviewSession) -> str:
        return "\n\n".join([
            f"INTERVIEW MODE:\n{session.interview_mode}",
            f"RESEARCH GOAL:\n{session.research_goal}",
            f"PRODUCT CONTEXT:\n{session.product_context or '(none)'}",
            f"CONCEPT LABEL:\n{session.concept_label or '(none)'}",
            FacilitatedInterviewRuntime._stimulus_prompt_block(session).rstrip(),
            f"STOP REASON:\n{session.stop_reason or '(none)'}",
            "COVERAGE STATUS:\n" + json.dumps(session.coverage_status, ensure_ascii=False, separators=(",", ":")),
            f"TRANSCRIPT:\n{FacilitatedInterviewRuntime._plain_transcript(session)}",
            "FACILITATOR TRACE:\n"
            + json.dumps(FacilitatedInterviewRuntime._audit_trace(session), ensure_ascii=False, separators=(",", ":")),
            "OBSERVER INTERVENTIONS:\n"
            + json.dumps(session.observer_interventions, ensure_ascii=False, separators=(",", ":")),
            "SYNTHESIS:\n" + json.dumps(session.insight_report, ensure_ascii=False, separators=(",", ":")),
            "QUALITY EVALUATION:\n"
            + json.dumps(session.quality_evaluation, ensure_ascii=False, separators=(",", ":")),
            "PERSONA DRIVER TRACE:\n"
            + json.dumps(session.persona_driver_trace, ensure_ascii=False, separators=(",", ":")),
        ])

    def _ask_persona(
        self,
        folder: Path,
        session: InterviewSession,
        *,
        question: str,
        phase: str,
        strategy: str,
        question_evidence_basis: str = "current_event",
        failed_operation: str,
        failed_payload: dict[str, Any] | None = None,
    ) -> InterviewSession:
        persona_folder = resolve_persona_folder(self.data_dir, session.persona_id)
        persona = load_persona(persona_folder)
        persona_runtime = ConversationRuntime(
            data_dir=self.data_dir,
            session_dir=folder / "persona_runtime",
            provider=self.persona_provider,
        )
        persona_session, _, _ = persona_runtime.resume(session.persona_conversation_session_id)
        session.status = "asking_persona"
        self._save_controlled(session, folder)
        self._progress(
            f"asking_persona interview_id={session.interview_id} exchange={len(session.exchanges) + 1} "
            f"phase={phase} strategy={strategy}"
        )
        try:
            response = persona_runtime.send(
                persona_session,
                persona,
                persona_folder,
                question,
                runtime_instruction=self._persona_interview_instruction(),
            )
        except Exception as exc:
            return self._fail(session, folder, failed_operation, exc, failed_payload)

        session.exchanges.append(InterviewExchange(
            exchange_id=len(session.exchanges) + 1,
            facilitator_question=question,
            persona_response=response,
            facilitator_phase=phase,
            probing_strategy=strategy,
            question_evidence_basis=self._effective_question_basis(question, question_evidence_basis),
            question_evidence_target=(
                session.pending_facilitator_decision.get("question_evidence_target", "context")
                if phase != "observer_intervention" else "context"
            ),
        ))
        if phase != "observer_intervention":
            self._mark_latest_decision_status(session, "asked")
        session.persona_provider_session_id = persona_session.provider_session_id
        session.pending_facilitator_decision = {}
        self._update_coverage_status(session)
        session.updated_at = utc_now_iso()
        self._save_controlled(session, folder)
        self._progress(
            f"received_persona_response interview_id={session.interview_id} "
            f"exchange={len(session.exchanges)} chars={len(response)}"
        )

        if self._should_finalize_after_exchange(session):
            self._progress(f"coverage_complete stop_reason={session.stop_reason}")
            return self.finalize(session.interview_id, stop_reason=session.stop_reason)
        self._request_facilitator(
            session,
            folder,
            self._continuation_prompt(session),
            failed_operation="request_next_question",
        )
        return session

    def _request_facilitator(
        self,
        session: InterviewSession,
        folder: Path,
        prompt: str,
        *,
        failed_operation: str,
        failed_payload: dict[str, Any] | None = None,
    ) -> None:
        session.status = "requesting_facilitator"
        self._save_controlled(session, folder)
        self._progress(
            f"requesting_facilitator interview_id={session.interview_id} "
            f"turn={len(session.exchanges) + 1}"
        )
        try:
            decision = self.facilitator_provider.next_turn(
                system_prompt=self._facilitator_system_prompt(session),
                user_prompt=prompt,
                provider_session_id=session.facilitator_provider_session_id,
            )
        except Exception as exc:
            payload = dict(failed_payload or {})
            payload.setdefault("prompt", prompt)
            self._fail(session, folder, failed_operation, exc, payload)
            return
        try:
            decision = self._revise_non_episodic_validation_question(
                session, decision, self._facilitator_system_prompt(session)
            )
        except Exception as exc:
            payload = dict(failed_payload or {})
            payload.setdefault("prompt", prompt)
            return self._fail(session, folder, failed_operation, exc, payload)
        self._record_decision(session, decision)
        session.pending_facilitator_decision = decision.to_dict()
        session.status = "awaiting_observer"
        session.last_error = ""
        session.failed_operation = ""
        session.failed_payload = {}
        session.updated_at = utc_now_iso()
        self._save_controlled(session, folder)
        self._progress(
            f"facilitator_decision_ready interview_id={session.interview_id} "
            f"phase={decision.interview_phase} should_end={decision.should_end}"
        )

    @staticmethod
    def _intervention(session: InterviewSession, action: str, content: str) -> dict[str, Any]:
        event = {
            "intervention_id": len(session.observer_interventions) + 1,
            "action": action,
            "content": content,
            "created_at": utc_now_iso(),
        }
        session.observer_interventions.append(event)
        return event

    def _fail(
        self,
        session: InterviewSession,
        folder: Path,
        operation: str,
        exc: Exception,
        payload: dict[str, Any] | None = None,
    ) -> InterviewSession:
        session.status = "failed"
        session.last_error = str(exc)
        session.failed_operation = operation
        session.failed_payload = dict(payload or {})
        session.updated_at = utc_now_iso()
        self._save_controlled(session, folder)
        self._progress(
            f"failed interview_id={session.interview_id} operation={operation} error={session.last_error}"
        )
        return session

    def _save_controlled(self, session: InterviewSession, folder: Path) -> None:
        self._save(session, folder)
        write_json(folder / "observer_events.json", session.observer_interventions)

    @staticmethod
    def _quality_system_prompt() -> str:
        root = _repo_root()
        return _read(root / "src" / "ai_validation_swarm" / "prompts" / "facilitator-quality-evaluator" / "v2.md")

    @staticmethod
    def _quality_user_prompt(session: InterviewSession) -> str:
        return "\n\n".join([
            f"INTERVIEW MODE:\n{session.interview_mode}",
            f"HYPOTHESIS TO TEST:\n{session.hypothesis or '(none)'}",
            f"RESEARCH GOAL:\n{session.research_goal}",
            f"PRODUCT CONTEXT:\n{session.product_context or '(none)'}",
            f"CONCEPT LABEL:\n{session.concept_label or '(none)'}",
            FacilitatedInterviewRuntime._stimulus_prompt_block(session).rstrip(),
            "COVERAGE STATUS:\n" + json.dumps(session.coverage_status, ensure_ascii=False, separators=(",", ":")),
            f"TRANSCRIPT:\n{FacilitatedInterviewRuntime._plain_transcript(session)}",
            "FACILITATOR TRACE:\n" + json.dumps(
                FacilitatedInterviewRuntime._audit_trace(session), ensure_ascii=False, separators=(",", ":")
            ),
            "OBSERVER INTERVENTIONS:\n" + json.dumps(session.observer_interventions, ensure_ascii=False, separators=(",", ":")),
            "SYNTHESIS:\n" + json.dumps(session.insight_report, ensure_ascii=False, separators=(",", ":")),
            "INDEPENDENT HYPOTHESIS EVIDENCE JUDGMENT:\n" + json.dumps(
                session.hypothesis_evidence_judgment, ensure_ascii=False, separators=(",", ":")
            ),
        ])

    @staticmethod
    def _render_quality(quality: dict[str, Any]) -> str:
        lines = [
            "# Facilitator Quality Evaluation", "",
            f"> {quality.get('synthetic_only_disclaimer', '')}", "",
            f"Overall verdict: **{quality.get('overall_verdict', 'unknown')}**", "",
            "## Scores", "",
        ]
        for key, value in quality.get("scores", {}).items():
            lines.append(f"- {key}: {value}/5")
        lines.extend(["", "## Findings", ""])
        for finding in quality.get("findings", []):
            lines.append(f"- [{finding.get('severity', 'unknown')}] {finding.get('observation', '')}")
        lines.extend(["", "## Required Improvements", ""])
        for item in quality.get("required_improvements", []):
            lines.append(f"- {item}")
        hints = quality.get("improvement_hints", {})
        if isinstance(hints, dict):
            lines.extend(["", "## Improvement Hints", ""])
            for item in hints.get("next_interview_focus", []):
                lines.append(f"- Focus next: {item}")
            for item in hints.get("coverage_gap_actions", []):
                lines.append(f"- Close gap: {item}")
            for item in hints.get("prompt_adjustments", []):
                lines.append(f"- Prompt change: {item}")
            if hints.get("turn_budget_guidance"):
                lines.append(f"- Turn budget: {hints.get('turn_budget_guidance')}")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _render_audit_feedback(audit_feedback: dict[str, Any]) -> str:
        summary = audit_feedback.get("summary", {})
        applies_to = audit_feedback.get("applies_to", {})

        def _append_item(lines: list[str], item: Any, formatter) -> None:
            if isinstance(item, dict):
                lines.append(formatter(item))
                return
            text = str(item).strip()
            if text:
                lines.append(f"- {text}")

        lines = [
            "# Facilitator Audit Feedback", "",
            f"- Scope: {audit_feedback.get('feedback_scope', 'unknown')}",
            f"- Safe for global reuse: {applies_to.get('safe_for_global_reuse', False)}",
            "",
            "## Summary", "",
            f"- Overall: {summary.get('overall_assessment', '')}",
            f"- Primary failure mode: {summary.get('primary_failure_mode', '')}",
            f"- Depth vs coverage: {summary.get('depth_vs_coverage_assessment', '')}",
            "",
            "## Feedback Tags", "",
        ]
        for item in audit_feedback.get("facilitator_feedback_tags", []):
            _append_item(
                lines,
                item,
                lambda row: f"- [{row.get('severity', 'unknown')}] {row.get('tag', '')}: {row.get('observed_pattern', '')}",
            )
        lines.extend(["", "## Missed High-Value Follow-Ups", ""])
        for item in audit_feedback.get("high_value_missed_followups", []):
            if isinstance(item, dict):
                lines.append(f"- [{item.get('priority', 'unknown')}] {item.get('missed_followup_question', '')}")
                if item.get("trigger_type"):
                    lines.append(f"  Trigger: {item.get('trigger_type')}")
            else:
                text = str(item).strip()
                if text:
                    lines.append(f"- {text}")
        lines.extend(["", "## Likely Misclassified Drivers", ""])
        for item in audit_feedback.get("likely_misclassified_driver_patterns", []):
            _append_item(
                lines,
                item,
                lambda row: f"- {row.get('observed_surface_frame', '')} -> {row.get('possible_underlying_driver', '')}",
            )
        lines.extend(["", "## Evidence Handling Issues", ""])
        for item in audit_feedback.get("evidence_handling_issues", []):
            _append_item(
                lines,
                item,
                lambda row: f"- [{row.get('severity', 'unknown')}] {row.get('issue', '')}",
            )
        lines.extend(["", "## Prompt Adjustments", ""])
        for item in audit_feedback.get("prompt_adjustments", []):
            _append_item(
                lines,
                item,
                lambda row: f"- {row.get('adjustment_type', '')}: {row.get('text', '')}",
            )
        lines.extend(["", "## Carry-Forward Rules", ""])
        for item in audit_feedback.get("carry_forward_rules", []):
            _append_item(
                lines,
                item,
                lambda row: f"- {row.get('rule_id', '')}: {row.get('rule', '')}",
            )
        lines.extend(["", "## Blocked Feedback", ""])
        for item in audit_feedback.get("blocked_feedback", []):
            _append_item(
                lines,
                item,
                lambda row: f"- {row.get('blocked_item', '')} ({row.get('block_reason', '')})",
            )
        return "\n".join(lines).rstrip() + "\n"
