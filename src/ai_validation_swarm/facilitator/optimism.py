from __future__ import annotations

from typing import Any


def attach_over_optimism_risks(
    synthesis: dict[str, Any],
    *,
    conversation_realism: dict[str, Any] | None,
    interview_mode: str,
) -> dict[str, Any]:
    enriched = dict(synthesis)
    enriched["potential_over_optimism_risks"] = derive_over_optimism_risks(
        synthesis=synthesis,
        conversation_realism=conversation_realism or {},
        interview_mode=interview_mode,
    )
    return enriched


def derive_over_optimism_risks(
    *,
    synthesis: dict[str, Any],
    conversation_realism: dict[str, Any],
    interview_mode: str,
) -> list[str]:
    risks: list[str] = []
    metrics = conversation_realism.get("metrics", {}) if isinstance(conversation_realism, dict) else {}
    axes = conversation_realism.get("friction_axes", {}) if isinstance(conversation_realism, dict) else {}

    clarification_rate = _metric_rate(metrics, "clarification_frequency")
    misunderstanding_rate = _metric_rate(metrics, "misunderstanding_rate")
    refusal_rate = _metric_rate(metrics, "refusal_frequency")
    low_effort_rate = _metric_rate(metrics, "low_effort_answer_rate")
    over_articulation_rate = _metric_rate(metrics, "over_articulation_risk")

    if clarification_rate == 0 and misunderstanding_rate == 0:
        risks.append("Synthetic users may have understood the concept too quickly; no meaningful clarification or misunderstanding behaviour appeared.")
    if refusal_rate == 0 and low_effort_rate < 0.15:
        risks.append("Low-motivation or dismissive reactions were under-simulated, so apparent interest may be inflated.")
    if over_articulation_rate > 0.2:
        risks.append("Persona responses were unusually complete or polished, which can make the concept look clearer than it would in real interviews.")
    if misunderstanding_rate == 0:
        risks.append("Wording misunderstanding and first-use confusion were not meaningfully simulated in this run.")

    if _axis_matches(axes, "life_load", "high", "heavy", "busy", "stretched") and low_effort_rate < 0.1:
        risks.append("This persona's high life_load did not translate into enough short-answer or interruption pressure, so activation friction may be understated.")
    if _axis_matches(axes, "complexity_tolerance", "low", "limited") and clarification_rate == 0 and misunderstanding_rate == 0:
        risks.append("Low complexity_tolerance did not generate the expected explanation requests or concept confusion.")
    if _axis_matches(axes, "decision_tempo", "slow", "deliberate", "careful"):
        if interview_mode == "concept_validation":
            pricing = synthesis.get("pricing_signal", {})
            if str(pricing.get("evidence_strength", "unknown")) in {"stated", "hypothetical", "unknown"}:
                risks.append("Adoption and payment remain stated intention for a slow-decision persona, so real conversion risk is still untested.")
        else:
            risks.append("A slow-decision persona still answered inside one synthetic sitting, so downstream adoption confidence remains optimistic.")

    if interview_mode == "concept_validation":
        pricing = synthesis.get("pricing_signal", {})
        evidence_strength = str(pricing.get("evidence_strength", "unknown"))
        if evidence_strength in {"stated", "hypothetical", "unknown"}:
            risks.append("All payment and adoption signals here are still stated intention rather than observed behavior.")
        risks.append("No real prototype behavior was tested, so setup confusion, wording breakdown, and actual drop-off remain unobserved.")
    else:
        risks.append("This synthesis still relies on simulated self-report rather than observed prototype behavior.")

    return _dedupe(risks)


def derive_panel_over_optimism_risks(interviews: list[dict[str, Any]]) -> list[str]:
    risks: list[str] = []
    if not interviews:
        return ["No panel interviews were available, so simulation optimism could not be stress-tested."]
    if all(not item.get("conversation_realism", {}).get("metrics", {}).get("misunderstanding_rate", {}).get("rate") for item in interviews):
        risks.append("Across the panel, none of the synthetic users meaningfully misunderstood the wording, which is likely too optimistic.")
    if all(not item.get("conversation_realism", {}).get("metrics", {}).get("refusal_frequency", {}).get("rate") for item in interviews):
        risks.append("Across the panel, low-motivation or rejection reactions were too sparse, so concept attractiveness may be overstated.")
    if all(item.get("report", {}).get("pricing_signal", {}).get("evidence_strength") in {"stated", "hypothetical", "unknown"} for item in interviews if item.get("report")):
        risks.append("Across the panel, adoption and payment remain stated-intention evidence rather than observed behavior.")
    risks.append("Panel convergence still comes from simulated participants, not human market proof.")
    return _dedupe(risks)


def _metric_rate(metrics: dict[str, Any], key: str) -> float:
    metric = metrics.get(key, {})
    value = metric.get("rate", 0.0) if isinstance(metric, dict) else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _axis_matches(axes: dict[str, Any], key: str, *tokens: str) -> bool:
    raw = axes.get(key, "")
    value = raw.casefold() if isinstance(raw, str) else str(raw).casefold()
    return any(token in value for token in tokens)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
