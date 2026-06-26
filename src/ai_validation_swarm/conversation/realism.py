from __future__ import annotations

import math
import re
from typing import Any

from ai_validation_swarm.conversation.models import ConversationSession, ConversationTurn


FRICTION_MODES: tuple[str, ...] = ("off", "light", "natural", "high")
BEHAVIOR_SIGNALS: tuple[str, ...] = (
    "hesitation",
    "clarification_request",
    "contradiction_or_revision",
    "refusal_or_disinterest",
    "topic_drift",
    "low_effort",
    "misunderstanding",
    "over_articulated",
    "partial_answer",
    "memory_lapse",
    "pricing_or_setup_confusion",
    "example_detour",
)

_HESITATION_PATTERNS = (
    "maybe",
    "i guess",
    "kind of",
    "sort of",
    "not sure",
    "probably",
    "可能",
    "應該",
    "未必",
    "唔肯定",
    "有少少",
)
_CLARIFICATION_PATTERNS = (
    "what do you mean",
    "which part",
    "can you explain",
    "do you mean",
    "你意思係",
    "可唔可以講清楚",
    "即係點",
    "係咩意思",
)
_REVISION_PATTERNS = (
    "actually",
    "on second thought",
    "wait",
    "to be fair",
    "but maybe",
    "諗真啲",
    "唔係",
    "我改口",
)
_REFUSAL_PATTERNS = (
    "not interested",
    "wouldn't use",
    "won't use",
    "probably wouldn't",
    "i should not",
    "唔會特登用",
    "冇興趣",
    "未必會用",
)
_MISUNDERSTANDING_PATTERNS = (
    "you mean",
    "so i have to",
    "do i need to",
    "即係要我",
    "你係咪講",
    "係咪要",
)
_TOPIC_DRIFT_PATTERNS = (
    "that reminds me",
    "anyway",
    "speaking of that",
    "講開又",
    "突然諗起",
)
_MEMORY_LAPSE_PATTERNS = (
    "i forgot",
    "can't remember",
    "not sure if",
    "我唔記得",
    "唔太記得",
)


def validate_friction_mode(mode: str) -> str:
    normalized = mode.strip().lower() or "off"
    if normalized not in FRICTION_MODES:
        allowed = ", ".join(FRICTION_MODES)
        raise ValueError(f"Unknown friction mode '{mode}'. Use one of: {allowed}.")
    return normalized


def build_friction_mode_prompt(mode: str) -> str:
    normalized = validate_friction_mode(mode)
    if normalized == "off":
        return (
            "FRICTION MODE: off\n"
            "- Do not inject extra communication friction unless it is already strongly implied by the persona artifact.\n"
            "- Stay natural, but favor direct comprehension over confusion.\n"
            "- Use behavior_signals only when they genuinely occur."
        )
    if normalized == "light":
        return (
            "FRICTION MODE: light\n"
            "- Remain mostly cooperative, but allow occasional hesitation, clarification requests, or shorter answers.\n"
            "- Do not make every turn smooth, polished, or fully explicit.\n"
            "- Usually use at most one friction behavior in a turn, and tag it in behavior_signals."
        )
    if normalized == "natural":
        return (
            "FRICTION MODE: natural\n"
            "- Do not act like a maximally cooperative research participant.\n"
            "- Allow plausible friction such as partial misunderstanding, short answers, clarification requests, memory slips, side examples, disinterest, setup or permission confusion, or mid-answer revision.\n"
            "- Friction should appear intermittently, not every turn, and should still leave the interview usable.\n"
            "- When friction happens, tag it in behavior_signals."
        )
    return (
        "FRICTION MODE: high\n"
        "- Maintain plausibility, but allow regular communication friction and slower alignment.\n"
        "- It is acceptable to ask for explanation, answer too briefly at first, drift into a concrete anecdote, revise your stance, or signal low motivation to use the concept.\n"
        "- Do not become random or impossible to interview. Keep the persona coherent and tag friction in behavior_signals."
    )


def build_axis_behavior_prompt(axes: dict[str, Any]) -> str:
    if not axes:
        return ""
    lines = ["AXIS-DRIVEN BEHAVIOR CONTROLS:"]
    control_preference = _axis_value(axes, "control_preference")
    trust_style = _axis_value(axes, "trust_style")
    complexity_tolerance = _axis_value(axes, "complexity_tolerance")
    decision_tempo = _axis_value(axes, "decision_tempo")
    life_load = _axis_value(axes, "life_load")
    fragmentation_reality = _axis_value(axes, "fragmentation_reality")
    guidance_preference = _axis_value(axes, "guidance_preference")
    reflection_style = _axis_value(axes, "reflection_style")
    need_for_explanation = _axis_value(axes, "need_for_explanation")

    if _matches_any(life_load, "high", "heavy", "busy", "stretched", "crowded"):
        lines.append("- High life_load: keep answers tighter, show limited patience for long setup, and allow interruption pressure to surface.")
    if _matches_any(complexity_tolerance, "low", "limited", "simple", "narrow"):
        lines.append("- Low complexity_tolerance: ask for plainer explanation, misunderstand dense concepts more easily, and abandon sooner when setup sounds complex.")
    if _matches_any(control_preference, "high", "strong", "manual", "review"):
        lines.append("- High control_preference: ask about permissions, review steps, undo, manual override, and whether changes can be checked before trusting them.")
    if _matches_any(decision_tempo, "slow", "deliberate", "careful", "gradual"):
        lines.append("- Slow decision_tempo: avoid immediate adoption language; say you would need time, another look, or a smaller proof first.")
    if _matches_any(need_for_explanation, "low", "minimal") or _matches_any(guidance_preference, "low", "minimal"):
        lines.append("- Low need_for_explanation: do not indulge long conceptual framing; cut it short or show impatience.")
    if _matches_any(guidance_preference, "high", "guided", "step", "example"):
        lines.append("- High guidance_preference: respond better to one concrete example than to abstract positioning, and ask the interviewer to be more specific.")
    if _matches_any(fragmentation_reality, "high", "fragmented", "interrupted", "chaotic"):
        lines.append("- High fragmentation_reality: resist onboarding that assumes uninterrupted attention or one complete setup session.")
    if _matches_any(trust_style, "skeptic", "guarded", "verify", "proof", "cautious"):
        lines.append("- Verification-oriented trust_style: probe proof, reversibility, permissions, and whether claims can be checked before relying on them.")
    if _matches_any(reflection_style, "practical", "low", "concrete", "non-reflective"):
        lines.append("- Practical reflection_style: avoid neat self-analysis and keep causal explanations partial unless explicitly probed.")

    return "\n".join(lines) if len(lines) > 1 else ""


def build_persona_behavior_prompt(
    *,
    relational_defense_model: dict[str, Any],
    communication_behavior_model: dict[str, Any],
    behavior_generation_rules: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    if relational_defense_model:
        lines.extend([
            "RELATIONAL DEFENSE MODEL:",
            f"- self_other_position: {relational_defense_model.get('self_other_position', '')}",
            f"- default_trust_posture: {relational_defense_model.get('default_trust_posture', '')}",
            f"- defensive_style: {relational_defense_model.get('defensive_style', '')}",
            f"- conflict_pattern: {relational_defense_model.get('conflict_pattern', '')}",
            f"- withdrawal_pattern: {relational_defense_model.get('withdrawal_pattern', '')}",
        ])
    if communication_behavior_model:
        lines.extend([
            "COMMUNICATION BEHAVIOR MODEL:",
            f"- baseline_answer_length: {communication_behavior_model.get('baseline_answer_length', '')}",
            f"- clarification_tendency: {communication_behavior_model.get('clarification_tendency', '')}",
            f"- misunderstanding_risk: {communication_behavior_model.get('misunderstanding_risk', '')}",
            f"- topic_drift_tendency: {communication_behavior_model.get('topic_drift_tendency', '')}",
            f"- revision_tendency: {communication_behavior_model.get('revision_tendency', '')}",
            f"- disinterest_expression_style: {communication_behavior_model.get('disinterest_expression_style', '')}",
            f"- permission_sensitivity: {communication_behavior_model.get('permission_sensitivity', '')}",
            f"- dropoff_style: {communication_behavior_model.get('dropoff_style', '')}",
        ])
    if behavior_generation_rules:
        lines.append("BEHAVIOR GENERATION RULES:")
        for rule in behavior_generation_rules[:6]:
            if not isinstance(rule, dict):
                continue
            lines.append(
                f"- when {rule.get('when', {})} then {rule.get('then', [])} because {rule.get('because', '')}"
            )
    return "\n".join(lines).strip()


def analyze_conversation_realism(session: ConversationSession) -> dict[str, Any]:
    persona_turns = [turn for turn in session.turns if turn.role == "persona"]
    sample_size = len(persona_turns)
    enriched = [_enriched_turn(turn) for turn in persona_turns]
    signal_counts = {signal: 0 for signal in BEHAVIOR_SIGNALS}
    for item in enriched:
        for signal in item["signals"]:
            signal_counts[signal] += 1

    short_count = sum(1 for item in enriched if item["units"] <= 6 or "low_effort" in item["signals"])
    long_count = sum(1 for item in enriched if item["units"] >= 90 or "over_articulated" in item["signals"])
    lengths = [item["units"] for item in enriched]
    average_units = round(sum(lengths) / sample_size, 1) if sample_size else 0.0
    variance = round(_stddev(lengths), 1) if sample_size else 0.0

    metrics = {
        "response_length_realism": {
            "score": _response_length_score(lengths),
            "average_units": average_units,
            "length_variance": variance,
            "short_turn_rate": _rate(short_count, sample_size),
            "long_turn_rate": _rate(long_count, sample_size),
            "evidence_turn_ids": [
                item["turn_id"]
                for item in enriched
                if item["units"] <= 6 or item["units"] >= 90 or "over_articulated" in item["signals"]
            ][:5],
        },
        "hesitation_frequency": _signal_metric("hesitation", enriched, sample_size, good_low=0.05, good_high=0.35),
        "clarification_frequency": _signal_metric(
            "clarification_request", enriched, sample_size, good_low=0.05, good_high=0.25
        ),
        "contradiction_frequency": _signal_metric(
            "contradiction_or_revision", enriched, sample_size, good_low=0.0, good_high=0.18
        ),
        "refusal_frequency": _signal_metric(
            "refusal_or_disinterest", enriched, sample_size, good_low=0.0, good_high=0.25
        ),
        "topic_drift": _signal_metric("topic_drift", enriched, sample_size, good_low=0.0, good_high=0.18),
        "low_effort_answer_rate": _signal_metric("low_effort", enriched, sample_size, good_low=0.05, good_high=0.3),
        "misunderstanding_rate": _signal_metric(
            "misunderstanding", enriched, sample_size, good_low=0.0, good_high=0.18
        ),
        "over_articulation_risk": _signal_metric(
            "over_articulated", enriched, sample_size, good_low=0.0, good_high=0.18
        ),
    }
    overall_score = 0
    if metrics:
        weighted_total = (
            metrics["response_length_realism"]["score"] * 2
            + sum(metric["score"] for name, metric in metrics.items() if name != "response_length_realism")
        )
        overall_score = round(weighted_total / (len(metrics) + 1))

    risks: list[str] = []
    if sample_size < 4:
        risks.append("Low sample size: conversation realism score is provisional.")
    if metrics["response_length_realism"]["score"] < 60:
        risks.append("Response lengths look mechanically short or over-explained across too many turns.")
    if metrics["clarification_frequency"]["rate"] == 0 and session.friction_mode in {"natural", "high"}:
        risks.append("Friction mode was enabled but no clarification behavior appeared.")
    if metrics["misunderstanding_rate"]["rate"] > 0.35:
        risks.append("Misunderstanding rate is high enough to reduce interview usability.")
    if metrics["over_articulation_risk"]["rate"] > 0.3:
        risks.append("Persona sounds too polished or overly explanatory too often.")
    if metrics["low_effort_answer_rate"]["rate"] > 0.4:
        risks.append("Low-effort answers dominate too much of the exchange.")

    return {
        "synthetic_only_disclaimer": session.synthetic_only_disclaimer,
        "persona_id": session.persona_id,
        "persona_name": session.persona_name,
        "session_id": session.session_id,
        "friction_mode": session.friction_mode,
        "friction_axes": session.friction_axes,
        "sample_size": sample_size,
        "overall_score": overall_score,
        "metrics": metrics,
        "signal_counts": signal_counts,
        "risk_flags": risks,
        "flagged_turns": [
            {
                "turn_id": item["turn_id"],
                "signals": item["signals"],
                "excerpt": item["excerpt"],
            }
            for item in enriched
            if item["signals"]
        ][:12],
    }


def render_conversation_realism_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Conversation Realism Report: {report.get('persona_name', '')}",
        "",
        f"> {report.get('synthetic_only_disclaimer', '')}",
        "",
        f"Session: `{report.get('session_id', '')}`  ",
        f"Friction mode: `{report.get('friction_mode', 'off')}`  ",
        f"Overall realism score: `{report.get('overall_score', 0)}`  ",
        f"Persona-turn sample size: `{report.get('sample_size', 0)}`",
        "",
        "## Metrics",
        "",
    ]
    for name, metric in report.get("metrics", {}).items():
        score = metric.get("score", 0)
        rate = metric.get("rate")
        if rate is None:
            details = (
                f"avg_units={metric.get('average_units', 0)}, "
                f"variance={metric.get('length_variance', 0)}, "
                f"short_rate={metric.get('short_turn_rate', 0)}, "
                f"long_rate={metric.get('long_turn_rate', 0)}"
            )
        else:
            details = f"rate={rate}, evidence_turn_ids={metric.get('evidence_turn_ids', [])}"
        lines.append(f"- {name}: score `{score}`; {details}")

    risks = report.get("risk_flags", [])
    lines.extend(["", "## Risks", ""])
    if risks:
        for item in risks:
            lines.append(f"- {item}")
    else:
        lines.append("- No major realism risks were flagged in this sample.")

    flagged_turns = report.get("flagged_turns", [])
    friction_axes = report.get("friction_axes", {})
    if friction_axes:
        lines.extend(["", "## Friction Axes", ""])
        for key, value in friction_axes.items():
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## Flagged Turns", ""])
    if flagged_turns:
        for item in flagged_turns:
            lines.append(
                f"- turn_{item.get('turn_id', '')}: signals={item.get('signals', [])} | {item.get('excerpt', '')}"
            )
    else:
        lines.append("- No behavior signals were detected.")
    return "\n".join(lines).rstrip() + "\n"


def _enriched_turn(turn: ConversationTurn) -> dict[str, Any]:
    content = turn.content.strip()
    lowered = content.lower()
    signals = set(turn.behavior_signals)
    if any(pattern in lowered for pattern in _HESITATION_PATTERNS):
        signals.add("hesitation")
    if any(pattern in lowered for pattern in _CLARIFICATION_PATTERNS):
        signals.add("clarification_request")
    if any(pattern in lowered for pattern in _REVISION_PATTERNS):
        signals.add("contradiction_or_revision")
    if any(pattern in lowered for pattern in _REFUSAL_PATTERNS):
        signals.add("refusal_or_disinterest")
    if any(pattern in lowered for pattern in _MISUNDERSTANDING_PATTERNS):
        signals.add("misunderstanding")
    if any(pattern in lowered for pattern in _TOPIC_DRIFT_PATTERNS):
        signals.add("topic_drift")
    if any(pattern in lowered for pattern in _MEMORY_LAPSE_PATTERNS):
        signals.add("memory_lapse")
    if (
        any(token in lowered for token in ("price", "pricing", "setup", "permission", "access", "invite"))
        and any(token in lowered for token in ("do i need", "you mean", "即係要我", "係咪要"))
    ):
        signals.update({"misunderstanding", "pricing_or_setup_confusion"})
    if len(content) and content.endswith("?") and "clarification_request" in signals:
        signals.add("partial_answer")
    units = _text_units(content)
    if units <= 6:
        signals.add("low_effort")
    if units >= 90 or _sentence_count(content) >= 5:
        signals.add("over_articulated")
    return {
        "turn_id": turn.turn_id,
        "content": content,
        "excerpt": _excerpt(content),
        "signals": sorted(signal for signal in signals if signal in BEHAVIOR_SIGNALS),
        "units": units,
    }


def _signal_metric(
    signal: str,
    enriched_turns: list[dict[str, Any]],
    sample_size: int,
    *,
    good_low: float,
    good_high: float,
) -> dict[str, Any]:
    evidence_turn_ids = [item["turn_id"] for item in enriched_turns if signal in item["signals"]]
    rate = _rate(len(evidence_turn_ids), sample_size)
    return {
        "score": _band_score(rate, good_low=good_low, good_high=good_high),
        "rate": rate,
        "evidence_turn_ids": evidence_turn_ids[:5],
    }


def _response_length_score(lengths: list[int]) -> int:
    if not lengths:
        return 0
    short_rate = sum(1 for value in lengths if value <= 6) / len(lengths)
    long_rate = sum(1 for value in lengths if value >= 90) / len(lengths)
    average = sum(lengths) / len(lengths)
    variance = _stddev(lengths)
    average_score = _band_score(average, good_low=10, good_high=55, hard_high=120)
    short_score = _band_score(short_rate, good_low=0.05, good_high=0.3)
    long_score = _band_score(long_rate, good_low=0.0, good_high=0.18)
    variance_score = _band_score(variance, good_low=4, good_high=28, hard_high=60)
    return round((average_score + short_score + long_score + variance_score) / 4)


def _band_score(
    value: float,
    *,
    good_low: float,
    good_high: float,
    hard_low: float = 0.0,
    hard_high: float = 1.0,
) -> int:
    if good_low <= value <= good_high:
        return 100
    if value < good_low:
        span = max(good_low - hard_low, 1e-6)
        penalty = min(1.0, (good_low - value) / span)
        return round(100 - penalty * 45)
    span = max(hard_high - good_high, 1e-6)
    penalty = min(1.0, (value - good_high) / span)
    return round(100 - penalty * 65)


def _text_units(text: str) -> int:
    latin_tokens = re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", text)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    return len(latin_tokens) + math.ceil(len(cjk_chars) / 2)


def _sentence_count(text: str) -> int:
    matches = re.findall(r"[.!?。！？]+", text)
    return max(1, len(matches)) if text.strip() else 0


def _stddev(values: list[int]) -> float:
    if len(values) <= 1:
        return 0.0
    average = sum(values) / len(values)
    variance = sum((value - average) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def _rate(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total, 3)


def _excerpt(text: str, *, max_chars: int = 120) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3] + "..."


def _axis_value(axes: dict[str, Any], key: str) -> str:
    value = axes.get(key, "")
    if isinstance(value, str):
        return value.casefold()
    return str(value).casefold()


def _matches_any(value: str, *tokens: str) -> bool:
    return any(token in value for token in tokens)
