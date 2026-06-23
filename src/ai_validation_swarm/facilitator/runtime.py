from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Callable

from ai_validation_swarm.conversation.providers import ConversationProvider
from ai_validation_swarm.conversation.runtime import (
    DRIVER_TRACE_PROMPT_VERSION,
    ConversationRuntime,
    resolve_persona_folder,
)
from ai_validation_swarm.domain.models import utc_now_iso
from ai_validation_swarm.facilitator.concept_protocols import load_concept_protocol
from ai_validation_swarm.facilitator.models import FacilitatorDecision, InterviewExchange, InterviewSession
from ai_validation_swarm.facilitator.providers import FacilitatorProvider
from ai_validation_swarm.storage.files import ensure_dir, load_persona, write_json


FACILITATOR_PROMPT_VERSION = "facilitator-interview/v2"
SYNTHESIS_PROMPT_VERSION = "facilitator-synthesis/v2"
HYPOTHESIS_EVIDENCE_JUDGE_PROMPT_VERSION = "hypothesis-evidence-judge/v1"
CONCEPT_SYNTHESIS_PROMPT_VERSION = "concept-synthesis/v1"

CONCEPT_VALIDATION_COVERAGE_REQUIREMENTS: tuple[str, ...] = (
    "recent_behaviour",
    "current_workaround",
    "concept_reaction",
    "trust_boundary",
    "payment_conditions",
    "retention_repeat_use",
    "founder_assumption_check",
)
ROOT_CAUSE_COVERAGE_REQUIREMENTS: tuple[str, ...] = (
    "recent_behaviour",
    "participant_cause",
    "consequence",
)
HYPOTHESIS_VALIDATION_COVERAGE_REQUIREMENTS: tuple[str, ...] = (
    "target_behaviour",
    "participant_cause",
    "consequence",
    "hypothesis_condition",
    "alternative_condition",
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
    ) -> None:
        self.data_dir = data_dir
        self.session_dir = session_dir
        self.facilitator_provider = facilitator_provider
        self.persona_provider = persona_provider
        self.observer = observer or (lambda role, message: None)
        self.progress_writer = progress_writer

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
        output_language: str = "Traditional Chinese",
        max_turns: int = 10,
        soft_turn_limit: int | None = None,
        hard_turn_limit: int | None = None,
    ) -> Path:
        if not research_goal.strip():
            raise ValueError("Research goal cannot be empty.")
        soft_limit, hard_limit = self._resolve_turn_limits(
            max_turns=max_turns,
            soft_turn_limit=soft_turn_limit,
            hard_turn_limit=hard_turn_limit,
        )
        mode = self._validate_interview_brief(interview_mode, hypothesis)
        concept = load_concept_protocol(concept_protocol, label=concept_label) if mode == "concept_validation" else None

        persona_folder = resolve_persona_folder(self.data_dir, persona_id)
        persona = load_persona(persona_folder)
        persona_name = str(persona.profile.basic_identity.get("name", persona_id))
        interview_id = f"interview_{utc_now_iso()[:10].replace('-', '')}_{uuid.uuid4().hex[:8]}"
        interview_folder = self.session_dir / interview_id
        ensure_dir(interview_folder)

        persona_runtime = ConversationRuntime(
            data_dir=self.data_dir,
            session_dir=interview_folder / "persona_runtime",
            provider=self.persona_provider,
        )
        persona_session, _, _ = persona_runtime.start(persona_id)
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
                CONCEPT_SYNTHESIS_PROMPT_VERSION if mode == "concept_validation" else SYNTHESIS_PROMPT_VERSION
            ),
            concept_protocol_version=concept.identifier if concept else "",
            concept_label=concept.label if concept else "",
            hypothesis_evidence_judge_prompt_version=HYPOTHESIS_EVIDENCE_JUDGE_PROMPT_VERSION,
            interview_mode=mode,
            hypothesis=hypothesis.strip(),
            persona_conversation_session_id=persona_session.session_id,
            persona_driver_trace_prompt_version=DRIVER_TRACE_PROMPT_VERSION,
            max_turns=hard_limit,
            soft_turn_limit=soft_limit,
            hard_turn_limit=hard_limit,
        )
        self._update_coverage_status(session)
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
        else:
            synthesis, facilitator_session_id = self.facilitator_provider.synthesize(
                system_prompt=self._synthesis_system_prompt(session.interview_mode),
                user_prompt=self._synthesis_user_prompt(session),
                provider_session_id=session.facilitator_provider_session_id,
            )
        self._enforce_synthesis_evidence_scope(session, synthesis)
        session.facilitator_provider_session_id = facilitator_session_id
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
        persona_runtime.close(persona_session)
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
        if interview_mode == "validate_hypothesis":
            return HYPOTHESIS_VALIDATION_COVERAGE_REQUIREMENTS
        return ROOT_CAUSE_COVERAGE_REQUIREMENTS

    @staticmethod
    def _update_coverage_status(session: InterviewSession) -> None:
        requirements = FacilitatedInterviewRuntime._coverage_requirements(session.interview_mode)
        covered = {item: False for item in requirements}
        for exchange in session.exchanges:
            basis = FacilitatedInterviewRuntime._effective_question_basis(
                exchange.facilitator_question,
                exchange.question_evidence_basis,
            )
            phase = exchange.facilitator_phase.casefold()
            target = (exchange.question_evidence_target or "context").casefold()
            if "recent_behaviour" in covered and ("recent" in phase or "event" in phase or "warm" in phase):
                covered["recent_behaviour"] = True
            if "current_workaround" in covered and ("workflow" in phase or "workaround" in phase or "current" in phase):
                covered["current_workaround"] = True
            if "concept_reaction" in covered and ("concept" in phase or "scenario" in phase or "reaction" in phase or "fit" in phase):
                covered["concept_reaction"] = True
            if "trust_boundary" in covered and ("trust" in phase or "privacy" in phase or "data" in phase):
                covered["trust_boundary"] = True
            if "payment_conditions" in covered and ("pricing" in phase or "payment" in phase or "booking" in phase):
                covered["payment_conditions"] = True
            if "retention_repeat_use" in covered and ("retention" in phase or "repeat" in phase or "month" in phase):
                covered["retention_repeat_use"] = True
            if "founder_assumption_check" in covered and ("founder" in phase or "assumption" in phase or "closure" in phase):
                covered["founder_assumption_check"] = True
            if "target_behaviour" in covered and (target == "target_behaviour" or basis == "current_event"):
                covered["target_behaviour"] = True
            if "participant_cause" in covered and (target == "participant_cause" or "cause" in phase or "root_cause" in phase):
                covered["participant_cause"] = True
            if "consequence" in covered and (target == "consequence" or "consequence" in phase):
                covered["consequence"] = True
            if "hypothesis_condition" in covered and target == "hypothesis_condition":
                covered["hypothesis_condition"] = True
            if "alternative_condition" in covered and (target == "alternative_condition" or "counterexample" in phase or "contrast" in phase):
                covered["alternative_condition"] = True
        session.coverage_status = {
            "requirements": list(requirements),
            "covered": {key: bool(covered.get(key, False)) for key in requirements},
            "missing": [key for key in requirements if not covered.get(key, False)],
            "coverage_complete": all(covered.get(key, False) for key in requirements),
            "soft_limit_reached": len(session.exchanges) >= session.soft_turn_limit,
            "hard_limit_reached": len(session.exchanges) >= session.hard_turn_limit,
            "exchange_count": len(session.exchanges),
        }

    @staticmethod
    def _should_finalize_after_exchange(session: InterviewSession) -> bool:
        FacilitatedInterviewRuntime._update_coverage_status(session)
        if len(session.exchanges) >= session.hard_turn_limit:
            session.stop_reason = "hard_turn_limit_reached"
            return True
        if len(session.exchanges) < session.soft_turn_limit:
            return False
        if session.coverage_status.get("coverage_complete"):
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

    @staticmethod
    def _facilitator_system_prompt(session: InterviewSession) -> str:
        root = _repo_root()
        skill = _read(root / "skills" / "design-research-facilitator" / "SKILL.md")
        prompt = _read(root / "src" / "ai_validation_swarm" / "prompts" / "facilitator-interview" / "v2.md")
        concept_protocol = ""
        if session.interview_mode == "concept_validation":
            concept = load_concept_protocol(session.concept_protocol_version, label=session.concept_label)
            concept_protocol = concept.prompt_text
        return f"{prompt}\n\nFACILITATOR SKILL:\n{skill}\n\nCONCEPT VALIDATION PROTOCOL:\n{concept_protocol}"

    @staticmethod
    def _synthesis_system_prompt(interview_mode: str = "explore_root_cause") -> str:
        root = _repo_root()
        skill = _read(root / "skills" / "design-research-facilitator" / "SKILL.md")
        prompt_path = (
            root / "src" / "ai_validation_swarm" / "prompts" / "concept-synthesis" / "v1.md"
            if interview_mode == "concept_validation"
            else root / "src" / "ai_validation_swarm" / "prompts" / "facilitator-synthesis" / "v2.md"
        )
        prompt = _read(prompt_path)
        return f"{prompt}\n\nFACILITATOR SKILL:\n{skill}"

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
            f"OUTPUT LANGUAGE:\n{session.output_language}\n\n"
            f"CONCEPT LABEL:\n{session.concept_label or '(none)'}\n\n"
            f"TURN POLICY:\nsoft={session.soft_turn_limit}, hard={session.hard_turn_limit}\n\n"
            "REQUIRED COVERAGE:\n"
            f"{json.dumps(session.coverage_status.get('requirements', []), ensure_ascii=False, separators=(',', ':'))}\n\n"
            "No interview transcript exists yet. Choose and return the first interview question."
        )

    @staticmethod
    def _continuation_prompt(session: InterviewSession) -> str:
        return (
            f"INTERVIEW MODE: {session.interview_mode}\n"
            f"HYPOTHESIS TO TEST: {session.hypothesis or '(none)'}\n"
            f"OUTPUT LANGUAGE: {session.output_language}\n\n"
            f"CONCEPT LABEL: {session.concept_label or '(none)'}\n\n"
            "COVERAGE STATUS:\n"
            f"{json.dumps(session.coverage_status, ensure_ascii=False, separators=(',', ':'))}\n\n"
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

    def _save(self, session: InterviewSession, folder: Path) -> None:
        write_json(folder / "interview.json", session.to_dict())
        write_json(folder / "facilitator_trace.json", session.facilitator_decisions)
        if session.persona_driver_trace:
            write_json(folder / "persona_driver_trace.json", session.persona_driver_trace)
            (folder / "persona_driver_trace.md").write_text(
                self._render_persona_driver_trace(session),
                encoding="utf-8",
            )
        (folder / "transcript.md").write_text(self._render_transcript(session), encoding="utf-8")

    @staticmethod
    def _validate_interview_brief(interview_mode: str, hypothesis: str) -> str:
        mode = interview_mode.strip() or "explore_root_cause"
        if mode not in {"explore_root_cause", "validate_hypothesis", "concept_validation"}:
            raise ValueError("interview_mode must be explore_root_cause, validate_hypothesis, or concept_validation.")
        if mode == "validate_hypothesis" and not hypothesis.strip():
            raise ValueError("validate_hypothesis mode requires a non-empty hypothesis.")
        return mode

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
    def _render_transcript(session: InterviewSession) -> str:
        lines = [
            f"# Facilitated Interview: {session.persona_name}", "",
            f"> {session.synthetic_only_disclaimer}", "",
            f"Interview mode: {session.interview_mode}",
            *( [f"Hypothesis: {session.hypothesis}"] if session.hypothesis else [] ),
            *( [f"Concept: {session.concept_label}"] if session.concept_label else [] ),
            "",
            f"Research goal: {session.research_goal}", "",
            f"Turn policy: soft {session.soft_turn_limit}, hard {session.hard_turn_limit}",
            *( [f"Coverage complete: {session.coverage_status.get('coverage_complete', False)}"] if session.coverage_status else [] ),
            "",
        ]
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
        lines.extend(["", "## Next Experiment", "", str(report.get("next_experiment", ""))])
        return "\n".join(lines).rstrip() + "\n"
