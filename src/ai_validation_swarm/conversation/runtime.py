from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ai_validation_swarm.conversation.models import ConversationSession, ConversationTurn
from ai_validation_swarm.conversation.providers import ConversationProvider
from ai_validation_swarm.conversation.realism import (
    analyze_conversation_realism,
    build_axis_behavior_prompt,
    build_friction_mode_prompt,
    render_conversation_realism_markdown,
    validate_friction_mode,
)
from ai_validation_swarm.domain.models import PersonaSkill, utc_now_iso
from ai_validation_swarm.storage.files import (
    ensure_dir,
    load_persona,
    read_json,
    resolve_current_persona_version_folder,
    write_json,
)


PROMPT_VERSION = "persona-conversation/v1"
DRIVER_TRACE_PROMPT_VERSION = "persona-driver-trace/v1"
MAX_HISTORY_TURNS = 12
MAX_SYSTEM_CONTEXT_CHARS = 12_000
MAX_STRUCTURED_CONTEXT_CHARS = 10_000


def resolve_persona_folder(data_dir: Path, persona_id: str) -> Path:
    base = data_dir / persona_id
    try:
        return resolve_current_persona_version_folder(base)
    except ValueError as exc:
        raise ValueError(
            f"Persona '{persona_id}' could not be resolved from {data_dir}. {exc}"
        ) from None


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def _identity_name(persona: PersonaSkill) -> str:
    return str(persona.profile.basic_identity.get("name", persona.profile.synthetic_user_id))


def _relevant_profile_context(persona: PersonaSkill, message: str) -> dict[str, Any]:
    profile = persona.profile
    sections: dict[str, Any] = {
        "basic_identity": profile.basic_identity,
        "values": profile.values,
        "behavior_profile": profile.behavior_profile,
        "product_reaction_rules": profile.product_reaction_rules,
        "pricing_logic": profile.pricing_logic,
        "persona_voiceprint": profile.persona_voiceprint,
        "contradiction_map": profile.contradiction_map,
        "deep_research_notes": profile.deep_research_notes,
        "human_difference_axes": getattr(profile, "human_difference_axes", {}),
    }
    lowered = message.lower()
    if any(term in lowered for term in ("privacy", "identity", "gender", "family", "health", "politic", "data", "私隱", "身份", "家庭", "健康")):
        sections["sensitive_scenario_reactions"] = profile.sensitive_scenario_reactions
        sections["sensitive_reality_layer"] = profile.sensitive_reality_layer
    if any(term in lowered for term in ("local", "city", "payment", "currency", "language", "market", "地區", "付款", "語言")):
        sections["local_grounding_layer"] = profile.local_grounding_layer
        sections["cultural_texture"] = profile.cultural_texture
    if any(term in lowered for term in ("routine", "daily", "onboarding", "setup", "workflow", "日常", "設定", "流程")):
        sections["daily_micro_behaviours"] = profile.daily_micro_behaviours
        sections["workflow_adoption_model"] = profile.workflow_adoption_model
        sections["hidden_habits"] = profile.hidden_habits
    return sections


def _friction_axes(persona: PersonaSkill) -> dict[str, Any]:
    axes = getattr(persona.profile, "human_difference_axes", {})
    if not isinstance(axes, dict):
        return {}
    selected: dict[str, Any] = {}
    for key in (
        "control_preference",
        "trust_style",
        "complexity_tolerance",
        "decision_tempo",
        "life_load",
        "fragmentation_reality",
        "guidance_preference",
        "reflection_style",
        "need_for_explanation",
    ):
        if key in axes and axes.get(key) not in (None, ""):
            selected[key] = axes[key]
    return selected


def _driver_trace_profile_context(persona: PersonaSkill) -> dict[str, Any]:
    profile = persona.profile
    sections: dict[str, Any] = {
        "basic_identity": profile.basic_identity,
        "personality_belief": getattr(profile, "personality_belief", {}),
        "values": profile.values,
        "life_story": getattr(profile, "life_story", {}),
        "behavior_profile": profile.behavior_profile,
        "problem_context": getattr(profile, "problem_context", {}),
        "product_reaction_rules": profile.product_reaction_rules,
        "contradiction_map": profile.contradiction_map,
        "deep_research_notes": profile.deep_research_notes,
    }
    for optional_key in (
        "childhood_environment",
        "canonical_biography",
        "workflow_adoption_model",
        "daily_micro_behaviours",
        "human_difference_axes",
        "banking_context",
    ):
        value = getattr(profile, optional_key, None)
        if value:
            sections[optional_key] = value
    return sections


class ConversationRuntime:
    def __init__(self, *, data_dir: Path, session_dir: Path, provider: ConversationProvider) -> None:
        self.data_dir = data_dir
        self.session_dir = session_dir
        self.provider = provider

    def start(self, persona_id: str, *, friction_mode: str = "off") -> tuple[ConversationSession, PersonaSkill, Path]:
        folder = resolve_persona_folder(self.data_dir, persona_id)
        persona = load_persona(folder)
        normalized_friction_mode = validate_friction_mode(friction_mode)
        session = ConversationSession(
            session_id=f"chat_{utc_now_iso()[:10].replace('-', '')}_{uuid.uuid4().hex[:8]}",
            persona_id=persona_id,
            persona_name=_identity_name(persona),
            persona_version=persona.skill_version,
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            prompt_version=PROMPT_VERSION,
            friction_mode=normalized_friction_mode,
            friction_axes=_friction_axes(persona),
        )
        self.save(session)
        return session, persona, folder

    def resume(self, session_id: str) -> tuple[ConversationSession, PersonaSkill, Path]:
        path = self.session_dir / session_id / "session.json"
        if not path.exists():
            raise ValueError(f"Conversation session '{session_id}' was not found.")
        session = ConversationSession.from_dict(read_json(path))
        folder = resolve_persona_folder(self.data_dir, session.persona_id)
        return session, load_persona(folder), folder

    def send(
        self,
        session: ConversationSession,
        persona: PersonaSkill,
        persona_folder: Path,
        message: str,
        *,
        runtime_instruction: str = "",
    ) -> str:
        cleaned = message.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty.")
        user_turn = ConversationTurn(turn_id=len(session.turns) + 1, role="user", content=cleaned)
        session.turns.append(user_turn)
        system_prompt = self._system_prompt(session, persona, persona_folder, runtime_instruction=runtime_instruction)
        user_prompt = self._user_prompt(
            session,
            persona,
            cleaned,
            include_history=not bool(session.provider_session_id),
        )
        try:
            result = self.provider.respond(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                persona=persona,
                provider_session_id=session.provider_session_id,
            )
        except Exception:
            session.turns.pop()
            raise
        session.turns.append(ConversationTurn(
            turn_id=len(session.turns) + 1,
            role="persona",
            content=result.reply,
            intent_level=result.intent_level,
            confidence=result.confidence,
            behavior_signals=result.behavior_signals,
        ))
        if result.provider_session_id:
            session.provider_session_id = result.provider_session_id
        session.updated_at = utc_now_iso()
        self.save(session)
        return result.reply

    def reset(self, session: ConversationSession) -> None:
        session.turns.clear()
        session.updated_at = utc_now_iso()
        self.save(session)

    def close(self, session: ConversationSession) -> None:
        session.status = "closed"
        session.updated_at = utc_now_iso()
        self.save(session)

    def generate_persona_driver_trace(
        self,
        session: ConversationSession,
        persona: PersonaSkill,
        persona_folder: Path,
        *,
        interview_transcript: str,
        research_goal: str,
        product_context: str = "",
        output_language: str = "Traditional Chinese",
    ) -> tuple[dict[str, Any], str]:
        prompt_path = Path(__file__).parents[1] / "prompts" / "persona-driver-trace" / "v1.md"
        reflection_rules = prompt_path.read_text(encoding="utf-8").strip()
        system_prompt = self._system_prompt(
            session,
            persona,
            persona_folder,
            runtime_instruction=reflection_rules,
        )
        structured_context = json.dumps(
            _driver_trace_profile_context(persona),
            ensure_ascii=False,
            separators=(",", ":"),
        )[:MAX_STRUCTURED_CONTEXT_CHARS]
        user_prompt = (
            f"OUTPUT LANGUAGE:\n{output_language}\n\n"
            f"RESEARCH GOAL:\n{research_goal}\n\n"
            f"PRODUCT CONTEXT:\n{product_context or '(none)'}\n\n"
            "INTERVIEW TRANSCRIPT:\n"
            f"{interview_transcript}\n\n"
            "STRUCTURED PERSONA CONTEXT:\n"
            f"{structured_context}\n\n"
            "Generate a structured persona driver trace. Use transcript refs like "
            "`exchange_2.persona` and profile refs like `values.core_values` or "
            "`human_difference_axes.trust_style` whenever possible."
        )
        result = self.provider.generate_persona_driver_trace(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            persona=persona,
        )
        return result.payload, result.provider_session_id

    def save(self, session: ConversationSession) -> Path:
        folder = self.session_dir / session.session_id
        ensure_dir(folder)
        realism_report = analyze_conversation_realism(session)
        session.conversation_realism_score = int(realism_report.get("overall_score", 0))
        session.conversation_realism_summary = {
            "overall_score": realism_report.get("overall_score", 0),
            "sample_size": realism_report.get("sample_size", 0),
            "friction_mode": realism_report.get("friction_mode", "off"),
            "risk_flags": realism_report.get("risk_flags", [])[:5],
            "metric_scores": {
                name: metric.get("score", 0)
                for name, metric in realism_report.get("metrics", {}).items()
            },
        }
        write_json(folder / "session.json", session.to_dict())
        (folder / "transcript.md").write_text(self.render_transcript(session), encoding="utf-8")
        write_json(folder / "conversation_realism_report.json", realism_report)
        (folder / "conversation_realism_report.md").write_text(
            render_conversation_realism_markdown(realism_report),
            encoding="utf-8",
        )
        return folder

    @staticmethod
    def render_transcript(session: ConversationSession) -> str:
        lines = [
            f"# Conversation with {session.persona_name}", "",
            f"> {session.synthetic_only_disclaimer}", "",
            f"Session: `{session.session_id}`  ",
            f"Persona: `{session.persona_id}` ({session.persona_version})  ",
            f"Provider: `{session.provider}` / `{session.model}`  ",
            f"Prompt: `{session.prompt_version}`  ",
            f"Friction mode: `{session.friction_mode}`  ",
            f"Conversation realism score: `{session.conversation_realism_score}`", "",
        ]
        for turn in session.turns:
            speaker = "User" if turn.role == "user" else session.persona_name
            lines.extend([f"## {speaker}", "", turn.content, ""])
            if turn.role == "persona":
                metadata = f"Intent: `{turn.intent_level}` | Confidence: `{turn.confidence}`"
                if turn.behavior_signals:
                    metadata += f" | Signals: `{', '.join(turn.behavior_signals)}`"
                lines.extend([metadata, ""])
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def render_persona_driver_trace_markdown(
        payload: dict[str, Any],
        *,
        persona_name: str,
        research_goal: str,
    ) -> str:
        lines = [
            f"# Persona Driver Trace: {persona_name}",
            "",
            f"> {payload.get('synthetic_only_disclaimer', '')}",
            "",
            f"Research goal: {research_goal}",
            "",
            "## Surface Read",
            "",
        ]
        surface = payload.get("surface_read", {})
        for item in surface.get("what_the_persona_explicitly_said", []):
            lines.append(f"- Said: {item}")
        optimize_for = surface.get("what_they_seemed_to_optimize_for", "")
        if optimize_for:
            lines.append(f"- Seemed to optimize for: {optimize_for}")
        for item in surface.get("what_stayed_implicit", []):
            lines.append(f"- Implicit: {item}")

        lines.extend(["", "## Likely Drivers", ""])
        for item in payload.get("likely_drivers", []):
            lines.append(
                f"- [{item.get('confidence', 'unknown')}] {item.get('driver', '')} "
                f"({item.get('driver_type', '')}, {item.get('observed_vs_inferred', '')})"
            )
            lines.append(f"  Why: {item.get('why_it_matters_here', '')}")
            refs = ", ".join(item.get("evidence_refs", []))
            if refs:
                lines.append(f"  Transcript refs: {refs}")
            sources = ", ".join(item.get("profile_source_refs", []))
            if sources:
                lines.append(f"  Profile refs: {sources}")

        lines.extend(["", "## Unspoken Constraints", ""])
        for item in payload.get("unspoken_constraints", []):
            lines.append(f"- [{item.get('confidence', 'unknown')}] {item.get('constraint', '')}")
            lines.append(f"  Why likely: {item.get('why_likely', '')}")

        lines.extend(["", "## Value Tensions", ""])
        for item in payload.get("value_tensions", []):
            lines.append(
                f"- [{item.get('confidence', 'unknown')}] {item.get('tension', '')}: "
                f"{item.get('side_a', '')} vs {item.get('side_b', '')}"
            )

        lines.extend(["", "## Missed Follow-Up Questions", ""])
        for item in payload.get("missed_follow_up_questions", []):
            lines.append(f"- [{item.get('priority', 'unknown')}] {item.get('question', '')}")
            lines.append(f"  Why: {item.get('why_this_would_clarify', '')}")

        return "\n".join(lines).rstrip() + "\n"

    def _system_prompt(
        self,
        session: ConversationSession,
        persona: PersonaSkill,
        folder: Path,
        *,
        runtime_instruction: str = "",
    ) -> str:
        prompt_path = Path(__file__).parents[1] / "prompts" / "persona-conversation" / "v1.md"
        runtime_rules = prompt_path.read_text(encoding="utf-8").strip()
        kernel = _read_optional(folder / "research_kernel.md")
        # The kernel is the runtime artifact; persona.skill.md largely duplicates it and
        # is only a fallback for older persona folders without a kernel.
        skill = _read_optional(folder / "persona.skill.md")
        runtime_artifact = kernel or skill or persona.narrative
        artifact_label = "PERSONA RESEARCH KERNEL" if kernel else "PERSONA RUNTIME ARTIFACT"
        friction_instruction = build_friction_mode_prompt(session.friction_mode)
        axis_instruction = build_axis_behavior_prompt(session.friction_axes)
        mode_instruction = f"\n\nRUNTIME MODE:\n{runtime_instruction.strip()}" if runtime_instruction.strip() else ""
        axis_block = f"\n\n{axis_instruction}" if axis_instruction else ""
        context = (
            f"{runtime_rules}\n\n{friction_instruction}{axis_block}{mode_instruction}\n\n"
            f"{artifact_label}:\n{runtime_artifact}"
        )
        return context[:MAX_SYSTEM_CONTEXT_CHARS]

    @staticmethod
    def _user_prompt(
        session: ConversationSession,
        persona: PersonaSkill,
        latest_message: str,
        *,
        include_history: bool = True,
    ) -> str:
        history_turns = session.turns[-MAX_HISTORY_TURNS:-1] if include_history else []
        history = "\n".join(f"{turn.role.upper()}: {turn.content}" for turn in history_turns) or "(none)"
        relevant = json.dumps(
            _relevant_profile_context(persona, latest_message),
            ensure_ascii=False,
            separators=(",", ":"),
        )[:MAX_STRUCTURED_CONTEXT_CHARS]
        return (
            f"RELEVANT STRUCTURED PERSONA CONTEXT:\n{relevant}\n\n"
            f"CONVERSATION HISTORY:\n{history}\n\n"
            f"LATEST USER MESSAGE:\n{latest_message}"
        )
