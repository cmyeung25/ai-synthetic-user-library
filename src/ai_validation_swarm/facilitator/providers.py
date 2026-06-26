from __future__ import annotations

import json
import re
from typing import Any, Protocol

from ai_validation_swarm.facilitator.models import FacilitatorDecision
from ai_validation_swarm.providers.openai_client import OpenAIProviderError, OpenAIResponsesClient


EVIDENCE_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["claim", "evidence_type", "transcript_refs", "confidence"],
    "properties": {
        "claim": {"type": "string"},
        "evidence_type": {
            "type": "string",
            "enum": ["participant_statement", "behavioural_example", "facilitator_hypothesis"],
        },
        "transcript_refs": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
}

ROOT_CAUSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["hypothesis", "supporting_evidence_refs", "alternative_explanations", "validation_gap", "confidence"],
    "properties": {
        "hypothesis": {"type": "string"},
        "supporting_evidence_refs": {"type": "array", "items": {"type": "string"}},
        "alternative_explanations": {"type": "array", "items": {"type": "string"}},
        "validation_gap": {"type": "string"},
        "confidence": {"type": "string", "enum": ["low", "medium"]},
    },
}

ALTERNATIVE_TEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["explanation", "evidence_refs", "basis", "outcome"],
    "properties": {
        "explanation": {"type": "string"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "basis": {"type": "string", "enum": ["observed_event", "hypothetical", "general_claim"]},
        "outcome": {"type": "string", "enum": ["not_tested", "consistent", "inconsistent", "mixed"]},
    },
}

HYPOTHESIS_ASSESSMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "hypothesis", "verdict", "supporting_evidence_refs", "contradicting_evidence_refs",
        "mechanism_test_basis", "condition_present_case_refs", "condition_absent_case_refs",
        "alternative_explanations", "alternative_tests", "evidence_gaps", "confidence",
    ],
    "properties": {
        "hypothesis": {"type": "string"},
        "verdict": {"type": "string", "enum": ["not_tested", "unsupported", "mixed", "provisionally_supported"]},
        "supporting_evidence_refs": {"type": "array", "items": {"type": "string"}},
        "contradicting_evidence_refs": {"type": "array", "items": {"type": "string"}},
        "mechanism_test_basis": {"type": "string", "enum": ["not_tested", "observed_event", "hypothetical", "general_claim"]},
        "condition_present_case_refs": {"type": "array", "items": {"type": "string"}},
        "condition_absent_case_refs": {"type": "array", "items": {"type": "string"}},
        "alternative_explanations": {"type": "array", "items": {"type": "string"}},
        "alternative_tests": {"type": "array", "items": ALTERNATIVE_TEST_SCHEMA},
        "evidence_gaps": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["low", "medium"]},
    },
}

FACILITATOR_TURN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "interview_phase", "probing_strategy", "decision_rationale", "message_to_persona",
        "evidence_updates", "root_cause_hypotheses", "open_questions", "should_end", "end_reason",
        "question_evidence_basis",
        "question_evidence_target",
    ],
    "properties": {
        "interview_phase": {"type": "string"},
        "probing_strategy": {"type": "string"},
        "decision_rationale": {"type": "string"},
        "message_to_persona": {"type": "string"},
        "evidence_updates": {"type": "array", "items": EVIDENCE_ITEM_SCHEMA},
        "root_cause_hypotheses": {"type": "array", "items": ROOT_CAUSE_SCHEMA},
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "should_end": {"type": "boolean"},
        "end_reason": {"type": "string"},
        "question_evidence_basis": {
            "type": "string",
            "enum": ["current_event", "recalled_contrast_event", "hypothetical", "general_pattern", "clarification"],
        },
        "question_evidence_target": {
            "type": "string",
            "enum": ["context", "target_behaviour", "participant_cause", "consequence", "hypothesis_condition", "alternative_condition"],
        },
    },
}

INSIGHT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["insight", "evidence_refs", "confidence", "implication"],
    "properties": {
        "insight": {"type": "string"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "implication": {"type": "string"},
    },
}

FACILITATOR_SYNTHESIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "executive_summary", "insights", "needs", "root_cause_hypotheses", "contradictions",
        "pov_statements", "how_might_we_questions", "hypothesis_assessment", "evidence_gaps", "recommended_human_validation",
        "synthetic_only_disclaimer",
    ],
    "properties": {
        "executive_summary": {"type": "string"},
        "insights": {"type": "array", "items": INSIGHT_SCHEMA},
        "needs": {"type": "array", "items": {"type": "string"}},
        "root_cause_hypotheses": {"type": "array", "items": ROOT_CAUSE_SCHEMA},
        "contradictions": {"type": "array", "items": {"type": "string"}},
        "pov_statements": {"type": "array", "items": {"type": "string"}},
        "how_might_we_questions": {"type": "array", "items": {"type": "string"}},
        "hypothesis_assessment": HYPOTHESIS_ASSESSMENT_SCHEMA,
        "evidence_gaps": {"type": "array", "items": {"type": "string"}},
        "recommended_human_validation": {"type": "array", "items": {"type": "string"}},
        "synthetic_only_disclaimer": {"type": "string"},
    },
}

CONDITION_JUDGMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "evidence_refs", "rationale"],
    "properties": {
        "status": {"type": "string", "enum": ["observed", "not_observed", "ambiguous"]},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
}

HYPOTHESIS_EVIDENCE_JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "hypothesis", "operational_condition_present", "operational_condition_absent",
        "target_behaviour_observed", "target_behaviour_refs", "condition_present",
        "condition_absent", "supporting_evidence_refs", "contradicting_evidence_refs",
        "recommended_verdict", "confidence", "warnings",
    ],
    "properties": {
        "hypothesis": {"type": "string"},
        "operational_condition_present": {"type": "string"},
        "operational_condition_absent": {"type": "string"},
        "target_behaviour_observed": {"type": "boolean"},
        "target_behaviour_refs": {"type": "array", "items": {"type": "string"}},
        "condition_present": CONDITION_JUDGMENT_SCHEMA,
        "condition_absent": CONDITION_JUDGMENT_SCHEMA,
        "supporting_evidence_refs": {"type": "array", "items": {"type": "string"}},
        "contradicting_evidence_refs": {"type": "array", "items": {"type": "string"}},
        "recommended_verdict": {
            "type": "string",
            "enum": ["not_tested", "unsupported", "mixed", "provisionally_supported"],
        },
        "confidence": {"type": "string", "enum": ["low", "medium"]},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
}

QUOTE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["quote", "evidence_ref"],
    "properties": {
        "quote": {"type": "string"},
        "evidence_ref": {"type": "string"},
    },
}

ASSUMPTION_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["assumption", "status", "evidence_refs", "rationale"],
    "properties": {
        "assumption": {"type": "string"},
        "status": {
            "type": "string",
            "enum": ["supported", "partially_supported", "weakened", "invalidated", "unknown"],
        },
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
}

CONCEPT_SYNTHESIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "problem_evidence", "current_workaround", "trust_boundary", "first_value_requirement",
        "pricing_signal", "retention_risk", "assumption_validation", "key_insights",
        "next_experiment", "evidence_gaps", "synthetic_only_disclaimer",
    ],
    "properties": {
        "problem_evidence": {
            "type": "object", "additionalProperties": False,
            "required": ["strength", "supporting_quotes", "recent_behavior_evidence"],
            "properties": {
                "strength": {"type": "string", "enum": ["strong", "medium", "weak"]},
                "supporting_quotes": {"type": "array", "items": QUOTE_SCHEMA},
                "recent_behavior_evidence": {"type": "array", "items": {"type": "string"}},
            },
        },
        "current_workaround": {
            "type": "object", "additionalProperties": False,
            "required": ["existing_workaround", "pain_level", "switching_difficulty", "what_must_not_change"],
            "properties": {
                "existing_workaround": {"type": "array", "items": {"type": "string"}},
                "pain_level": {"type": "string", "enum": ["low", "medium", "high"]},
                "switching_difficulty": {"type": "string", "enum": ["low", "medium", "high"]},
                "what_must_not_change": {"type": "array", "items": {"type": "string"}},
            },
        },
        "trust_boundary": {
            "type": "object", "additionalProperties": False,
            "required": ["accepted_data_access", "rejected_data_access", "required_trust_explanation"],
            "properties": {
                "accepted_data_access": {"type": "array", "items": {"type": "string"}},
                "rejected_data_access": {"type": "array", "items": {"type": "string"}},
                "required_trust_explanation": {"type": "array", "items": {"type": "string"}},
            },
        },
        "first_value_requirement": {
            "type": "object", "additionalProperties": False,
            "required": ["first_use_success", "time_to_value", "abandonment_triggers"],
            "properties": {
                "first_use_success": {"type": "array", "items": {"type": "string"}},
                "time_to_value": {"type": "string"},
                "abandonment_triggers": {"type": "array", "items": {"type": "string"}},
            },
        },
        "pricing_signal": {
            "type": "object", "additionalProperties": False,
            "required": ["free_trial_need", "monthly_comfort_range", "payment_justification", "evidence_strength"],
            "properties": {
                "free_trial_need": {"type": "string"},
                "monthly_comfort_range": {"type": "string"},
                "payment_justification": {"type": "array", "items": {"type": "string"}},
                "evidence_strength": {"type": "string", "enum": ["behavioural", "stated", "hypothetical", "unknown"]},
            },
        },
        "retention_risk": {
            "type": "object", "additionalProperties": False,
            "required": ["continuation_reasons", "drop_off_reasons", "workflow_effect"],
            "properties": {
                "continuation_reasons": {"type": "array", "items": {"type": "string"}},
                "drop_off_reasons": {"type": "array", "items": {"type": "string"}},
                "workflow_effect": {"type": "string", "enum": ["replaces_workflow", "adds_layer", "unclear"]},
            },
        },
        "assumption_validation": {"type": "array", "items": ASSUMPTION_RESULT_SCHEMA},
        "key_insights": {"type": "array", "minItems": 3, "maxItems": 5, "items": {"type": "string"}},
        "next_experiment": {"type": "string"},
        "evidence_gaps": {"type": "array", "items": {"type": "string"}},
        "synthetic_only_disclaimer": {"type": "string"},
    },
}

QUALITY_FINDING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["category", "severity", "observation", "evidence_refs", "recommendation"],
    "properties": {
        "category": {"type": "string"},
        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
        "observation": {"type": "string"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "recommendation": {"type": "string"},
    },
}

QUALITY_IMPROVEMENT_HINTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "next_interview_focus",
        "coverage_gap_actions",
        "prompt_adjustments",
        "turn_budget_guidance",
    ],
    "properties": {
        "next_interview_focus": {"type": "array", "items": {"type": "string"}},
        "coverage_gap_actions": {"type": "array", "items": {"type": "string"}},
        "prompt_adjustments": {"type": "array", "items": {"type": "string"}},
        "turn_budget_guidance": {"type": "string"},
    },
}

FACILITATOR_QUALITY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "overall_verdict", "scores", "checks", "strengths", "findings",
        "required_improvements", "improvement_hints", "human_review_needed", "synthetic_only_disclaimer",
    ],
    "properties": {
        "overall_verdict": {"type": "string", "enum": ["pass", "warn", "fail"]},
        "scores": {
            "type": "object",
            "additionalProperties": False,
            "required": ["neutrality", "probing_quality", "conversation_naturalness", "evidence_discipline", "causal_rigor", "hypothesis_validation_rigor", "synthesis_fidelity", "overall"],
            "properties": {
                "neutrality": {"type": "integer", "minimum": 1, "maximum": 5},
                "probing_quality": {"type": "integer", "minimum": 1, "maximum": 5},
                "conversation_naturalness": {"type": "integer", "minimum": 1, "maximum": 5},
                "evidence_discipline": {"type": "integer", "minimum": 1, "maximum": 5},
                "causal_rigor": {"type": "integer", "minimum": 1, "maximum": 5},
                "hypothesis_validation_rigor": {"type": "integer", "minimum": 1, "maximum": 5},
                "synthesis_fidelity": {"type": "integer", "minimum": 1, "maximum": 5},
                "overall": {"type": "integer", "minimum": 1, "maximum": 5},
            },
        },
        "checks": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "leading_question_risk", "repetition_risk", "premature_root_cause_risk",
                "mechanical_five_whys_risk", "evidence_reference_quality", "synthesis_overreach_risk",
                "conversation_naturalness", "persona_over_structuring_risk", "interviewer_jargon_risk",
                "domain_fit_alignment", "hypothesis_confirmation_bias_risk",
                "hypothesis_judge_alignment",
            ],
            "properties": {
                "leading_question_risk": {"type": "string", "enum": ["pass", "warn", "fail"]},
                "repetition_risk": {"type": "string", "enum": ["pass", "warn", "fail"]},
                "premature_root_cause_risk": {"type": "string", "enum": ["pass", "warn", "fail"]},
                "mechanical_five_whys_risk": {"type": "string", "enum": ["pass", "warn", "fail"]},
                "evidence_reference_quality": {"type": "string", "enum": ["pass", "warn", "fail"]},
                "synthesis_overreach_risk": {"type": "string", "enum": ["pass", "warn", "fail"]},
                "conversation_naturalness": {"type": "string", "enum": ["pass", "warn", "fail"]},
                "persona_over_structuring_risk": {"type": "string", "enum": ["pass", "warn", "fail"]},
                "interviewer_jargon_risk": {"type": "string", "enum": ["pass", "warn", "fail"]},
                "domain_fit_alignment": {"type": "string", "enum": ["pass", "warn", "fail"]},
                "hypothesis_confirmation_bias_risk": {"type": "string", "enum": ["pass", "warn", "fail"]},
                "hypothesis_judge_alignment": {"type": "string", "enum": ["pass", "warn", "fail"]},
            },
        },
        "strengths": {"type": "array", "items": {"type": "string"}},
        "findings": {"type": "array", "items": QUALITY_FINDING_SCHEMA},
        "required_improvements": {"type": "array", "items": {"type": "string"}},
        "improvement_hints": QUALITY_IMPROVEMENT_HINTS_SCHEMA,
        "human_review_needed": {"type": "boolean"},
        "synthetic_only_disclaimer": {"type": "string"},
    },
}

FACILITATOR_AUDIT_TAG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["tag", "severity", "why_it_matters", "observed_pattern"],
    "properties": {
        "tag": {"type": "string"},
        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
        "why_it_matters": {"type": "string"},
        "observed_pattern": {"type": "string"},
    },
}

HIGH_VALUE_MISSED_FOLLOWUP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "trigger_type", "priority", "participant_signal", "missed_followup_question", "generic_learning",
    ],
    "properties": {
        "trigger_type": {"type": "string"},
        "priority": {"type": "string", "enum": ["low", "medium", "high"]},
        "participant_signal": {"type": "string"},
        "missed_followup_question": {"type": "string"},
        "generic_learning": {"type": "string"},
    },
}

MISCLASSIFIED_DRIVER_PATTERN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "observed_surface_frame", "possible_underlying_driver", "why_the_surface_frame_is_weak", "generic_learning",
    ],
    "properties": {
        "observed_surface_frame": {"type": "string"},
        "possible_underlying_driver": {"type": "string"},
        "why_the_surface_frame_is_weak": {"type": "string"},
        "generic_learning": {"type": "string"},
    },
}

EVIDENCE_HANDLING_ISSUE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["issue", "severity", "generic_learning"],
    "properties": {
        "issue": {"type": "string"},
        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
        "generic_learning": {"type": "string"},
    },
}

PROMPT_ADJUSTMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["adjustment_type", "text", "reuse_scope", "safe_for_global_reuse"],
    "properties": {
        "adjustment_type": {
            "type": "string",
            "enum": ["decision_rule", "stop_rule", "followup_trigger_rule", "evidence_rule", "contrast_rule", "question_priority_rule"],
        },
        "text": {"type": "string"},
        "reuse_scope": {"type": "string", "enum": ["global", "interview_mode_only", "manual_review_only"]},
        "safe_for_global_reuse": {"type": "boolean"},
    },
}

CARRY_FORWARD_RULE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["rule_id", "rule", "source_tags", "confidence", "safe_for_global_reuse"],
    "properties": {
        "rule_id": {"type": "string"},
        "rule": {"type": "string"},
        "source_tags": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "safe_for_global_reuse": {"type": "boolean"},
    },
}

BLOCKED_FEEDBACK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["blocked_item", "block_reason", "rewrite_as_generic"],
    "properties": {
        "blocked_item": {"type": "string"},
        "block_reason": {"type": "string"},
        "rewrite_as_generic": {"type": "string"},
    },
}

FACILITATOR_AUDIT_FEEDBACK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "artifact_version", "feedback_scope", "applies_to", "summary", "facilitator_feedback_tags",
        "high_value_missed_followups", "likely_misclassified_driver_patterns", "evidence_handling_issues",
        "prompt_adjustments", "carry_forward_rules", "blocked_feedback",
    ],
    "properties": {
        "artifact_version": {"type": "string"},
        "feedback_scope": {"type": "string", "enum": ["interview", "panel", "batch"]},
        "applies_to": {
            "type": "object",
            "additionalProperties": False,
            "required": ["interview_mode", "domains", "safe_for_global_reuse"],
            "properties": {
                "interview_mode": {"type": "array", "items": {"type": "string"}},
                "domains": {"type": "array", "items": {"type": "string"}},
                "safe_for_global_reuse": {"type": "boolean"},
            },
        },
        "summary": {
            "type": "object",
            "additionalProperties": False,
            "required": ["overall_assessment", "primary_failure_mode", "depth_vs_coverage_assessment"],
            "properties": {
                "overall_assessment": {"type": "string"},
                "primary_failure_mode": {"type": "string"},
                "depth_vs_coverage_assessment": {"type": "string"},
            },
        },
        "facilitator_feedback_tags": {"type": "array", "items": FACILITATOR_AUDIT_TAG_SCHEMA},
        "high_value_missed_followups": {"type": "array", "items": HIGH_VALUE_MISSED_FOLLOWUP_SCHEMA},
        "likely_misclassified_driver_patterns": {"type": "array", "items": MISCLASSIFIED_DRIVER_PATTERN_SCHEMA},
        "evidence_handling_issues": {"type": "array", "items": EVIDENCE_HANDLING_ISSUE_SCHEMA},
        "prompt_adjustments": {"type": "array", "items": PROMPT_ADJUSTMENT_SCHEMA},
        "carry_forward_rules": {"type": "array", "items": CARRY_FORWARD_RULE_SCHEMA},
        "blocked_feedback": {"type": "array", "items": BLOCKED_FEEDBACK_SCHEMA},
    },
}


class FacilitatorProvider(Protocol):
    provider_name: str
    model_name: str

    def next_turn(
        self, *, system_prompt: str, user_prompt: str, provider_session_id: str = "",
    ) -> FacilitatorDecision: ...

    def synthesize(
        self, *, system_prompt: str, user_prompt: str, provider_session_id: str = "",
    ) -> tuple[dict[str, Any], str]: ...

    def judge_hypothesis_evidence(
        self, *, system_prompt: str, user_prompt: str,
    ) -> tuple[dict[str, Any], str]: ...

    def synthesize_concept(
        self, *, system_prompt: str, user_prompt: str, provider_session_id: str = "",
    ) -> tuple[dict[str, Any], str]: ...

    def evaluate_quality(
        self, *, system_prompt: str, user_prompt: str, provider_session_id: str = "",
    ) -> tuple[dict[str, Any], str]: ...

    def generate_audit_feedback(
        self, *, system_prompt: str, user_prompt: str, provider_session_id: str = "",
    ) -> tuple[dict[str, Any], str]: ...


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Facilitator LLM output field '{key}' must be a string.")
    return value.strip()


def _coerce_required_string_field(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list) and len(value) == 1:
        return str(value[0]).strip()
    raise ValueError(f"Facilitator LLM output field '{key}' must be a string.")


def _coerce_string_field(payload: dict[str, Any], key: str, *, default: str = "") -> str:
    value = payload.get(key)
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return default
    if isinstance(value, list) and len(value) == 1:
        return str(value[0]).strip()
    return default


def _require_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Facilitator LLM output field '{key}' must be a list.")
    return value


def _coerce_list_field(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if isinstance(value, list):
        return value
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, dict):
        return [value]
    raise ValueError(f"Facilitator LLM output field '{key}' must be a list.")


def _coerce_object_list_field(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    items = _coerce_list_field(payload, key)
    return [item for item in items if isinstance(item, dict)]


_TEXT_FALLBACK_FIELD_PATTERN = re.compile(
    r"^(PHASE|STRATEGY|RATIONALE|QUESTION|SHOULD_END|END_REASON|BASIS|TARGET|OPEN_QUESTION)\s*:\s*(.*)$",
    re.IGNORECASE,
)


def _facilitator_text_fallback_instruction() -> str:
    return "\n".join(
        [
            "TEXT FALLBACK MODE:",
            "Return plain text only. Do not return JSON or markdown fences.",
            "Use these exact labels once each, in this order:",
            "PHASE:",
            "STRATEGY:",
            "RATIONALE:",
            "QUESTION:",
            "SHOULD_END:",
            "END_REASON:",
            "BASIS:",
            "TARGET:",
            "OPEN_QUESTION:",
            "Use yes or no for SHOULD_END.",
            "If continuing, QUESTION must contain one short participant-facing question.",
            "If ending, QUESTION may be blank.",
        ]
    )


def _parse_tagged_text_fields(raw_text: str) -> dict[str, str]:
    values: dict[str, list[str]] = {}
    current_key = ""
    for raw_line in raw_text.splitlines():
        line = raw_line.rstrip()
        match = _TEXT_FALLBACK_FIELD_PATTERN.match(line.strip())
        if match:
            current_key = match.group(1).upper()
            values[current_key] = [match.group(2).strip()]
            continue
        if current_key:
            values[current_key].append(line.strip())
    return {
        key: "\n".join(part for part in parts if part).strip()
        for key, parts in values.items()
    }


def _parse_text_boolean(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {"true", "yes", "y", "1", "end", "stop"}


def _split_text_list(value: str) -> list[str]:
    if not value.strip():
        return []
    parts = [
        item.strip(" -\t")
        for item in re.split(r"[,\n;|]+", value)
        if item.strip(" -\t")
    ]
    return parts


def _normalize_choice(value: str, allowed: set[str], default: str) -> str:
    normalized = value.strip()
    return normalized if normalized in allowed else default


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    return []


def _normalize_quote_items(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        quote = str(item.get("quote", "")).strip()
        evidence_ref = str(item.get("evidence_ref", "")).strip()
        if quote and evidence_ref:
            normalized.append({"quote": quote, "evidence_ref": evidence_ref})
    return normalized


def normalize_concept_synthesis(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)

    problem = normalized.get("problem_evidence")
    if not isinstance(problem, dict):
        problem = {}
    normalized["problem_evidence"] = {
        "strength": _normalize_choice(str(problem.get("strength", "")).lower(), {"strong", "medium", "weak"}, "weak"),
        "supporting_quotes": _normalize_quote_items(problem.get("supporting_quotes")),
        "recent_behavior_evidence": _as_string_list(problem.get("recent_behavior_evidence")),
    }

    workaround = normalized.get("current_workaround")
    if not isinstance(workaround, dict):
        workaround = {}
    normalized["current_workaround"] = {
        "existing_workaround": _as_string_list(workaround.get("existing_workaround")),
        "pain_level": _normalize_choice(str(workaround.get("pain_level", "")).lower(), {"low", "medium", "high"}, "medium"),
        "switching_difficulty": _normalize_choice(str(workaround.get("switching_difficulty", "")).lower(), {"low", "medium", "high"}, "medium"),
        "what_must_not_change": _as_string_list(workaround.get("what_must_not_change")),
    }

    trust = normalized.get("trust_boundary")
    if not isinstance(trust, dict):
        trust = {}
    normalized["trust_boundary"] = {
        "accepted_data_access": _as_string_list(trust.get("accepted_data_access")),
        "rejected_data_access": _as_string_list(trust.get("rejected_data_access")),
        "required_trust_explanation": _as_string_list(trust.get("required_trust_explanation")),
    }

    first_value = normalized.get("first_value_requirement")
    if not isinstance(first_value, dict):
        first_value = {}
    normalized["first_value_requirement"] = {
        "first_use_success": _as_string_list(first_value.get("first_use_success")),
        "time_to_value": str(first_value.get("time_to_value", "")).strip() or "Unknown",
        "abandonment_triggers": _as_string_list(first_value.get("abandonment_triggers")),
    }

    pricing = normalized.get("pricing_signal")
    if not isinstance(pricing, dict):
        pricing = {}
    normalized["pricing_signal"] = {
        "free_trial_need": str(pricing.get("free_trial_need", "")).strip() or "Unknown",
        "monthly_comfort_range": str(pricing.get("monthly_comfort_range", "")).strip() or "Unknown",
        "payment_justification": _as_string_list(pricing.get("payment_justification")),
        "evidence_strength": _normalize_choice(
            str(pricing.get("evidence_strength", "")).lower(),
            {"behavioural", "stated", "hypothetical", "unknown"},
            "unknown",
        ),
    }

    retention = normalized.get("retention_risk")
    if not isinstance(retention, dict):
        retention = {}
    normalized["retention_risk"] = {
        "continuation_reasons": _as_string_list(retention.get("continuation_reasons")),
        "drop_off_reasons": _as_string_list(retention.get("drop_off_reasons")),
        "workflow_effect": _normalize_choice(
            str(retention.get("workflow_effect", "")).lower(),
            {"replaces_workflow", "adds_layer", "unclear"},
            "unclear",
        ),
    }

    assumption_validation = normalized.get("assumption_validation")
    normalized["assumption_validation"] = [
        item for item in assumption_validation if isinstance(item, dict)
    ] if isinstance(assumption_validation, list) else []

    key_insights = _as_string_list(normalized.get("key_insights"))
    if len(key_insights) < 3:
        key_insights.extend(
            [
                "This synthetic run surfaced real bookkeeping friction around confirmation, record-keeping, and later reconciliation.",
                "Manual screenshots and handwritten logs appear to function as trust-preserving workarounds rather than pure habit.",
                "Adoption conditions remain partially untested and still need clearer trust and workflow-fit evidence.",
            ][: 3 - len(key_insights)]
        )
    normalized["key_insights"] = key_insights[:5]

    gaps = _as_string_list(normalized.get("evidence_gaps"))
    for missing_key in (
        "trust_boundary",
        "first_value_requirement",
        "pricing_signal",
        "retention_risk",
    ):
        if missing_key not in payload:
            gaps.append(f"{missing_key} remained under-specified in this synthetic run.")
    normalized["evidence_gaps"] = list(dict.fromkeys(gaps))
    normalized["next_experiment"] = str(normalized.get("next_experiment", "")).strip() or "Run a tighter follow-up interview on trust boundary, setup burden, and repeat-use conditions."
    normalized["synthetic_only_disclaimer"] = (
        str(normalized.get("synthetic_only_disclaimer", "")).strip()
        or "Synthetic pre-validation only; not human market evidence."
    )
    return normalized


def _concept_strength_from_text(value: str) -> str:
    normalized = value.strip().lower()
    if "high" in normalized or "strong" in normalized:
        return "strong"
    if "weak" in normalized or "low" in normalized:
        return "weak"
    return "medium"


def _quote_item_from_text(value: str) -> dict[str, str] | None:
    text = value.strip()
    if not text:
        return None
    if ":" in text:
        evidence_ref, quote = text.split(":", 1)
        evidence_ref = evidence_ref.strip()
        quote = quote.strip()
        if evidence_ref and quote:
            return {"quote": quote, "evidence_ref": evidence_ref}
    return None


def _concept_synthesis_from_text(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"key_insights": [text]}
    if not isinstance(payload, dict):
        return {"key_insights": [text]}
    if "problem_evidence" in payload or "current_workaround" in payload:
        return payload
    evidence = payload.get("evidence_synthesis")
    concept_reaction = payload.get("concept_reaction")
    recommended_experiment = payload.get("recommended_experiment")
    gaps = payload.get("gaps_and_missing_evidence")
    assumptions = payload.get("assumption_validation")
    key_insights = payload.get("key_insights")

    recent_behavior = evidence.get("recent_behavior", {}) if isinstance(evidence, dict) else {}
    current_workaround = evidence.get("current_workaround", {}) if isinstance(evidence, dict) else {}
    pain_threshold = evidence.get("pain_intensity_and_threshold", {}) if isinstance(evidence, dict) else {}

    supporting_quotes: list[dict[str, str]] = []
    for candidate in (
        recent_behavior.get("quote", ""),
        current_workaround.get("quote", ""),
        pain_threshold.get("quote", ""),
        concept_reaction.get("quote", "") if isinstance(concept_reaction, dict) else "",
    ):
        item = _quote_item_from_text(str(candidate))
        if item is not None:
            supporting_quotes.append(item)

    mapped_key_insights: list[str] = []
    if isinstance(key_insights, list):
        for item in key_insights:
            if isinstance(item, dict):
                text_value = str(item.get("text", "")).strip()
                if text_value:
                    mapped_key_insights.append(text_value)
            elif str(item).strip():
                mapped_key_insights.append(str(item).strip())

    mapped_assumptions: list[dict[str, Any]] = []
    if isinstance(assumptions, dict):
        for assumption, item in assumptions.items():
            if not isinstance(item, dict):
                continue
            mapped_assumptions.append(
                {
                    "assumption": str(assumption).strip().replace("_", " "),
                    "status": _normalize_choice(
                        str(item.get("status", "")).strip(),
                        {"supported", "partially_supported", "weakened", "invalidated", "unknown"},
                        "unknown",
                    ),
                    "evidence_refs": _as_string_list(item.get("evidence")),
                    "rationale": str(item.get("rationale", "")).strip(),
                }
            )

    evidence_gaps: list[str] = []
    if isinstance(gaps, dict):
        for key, item in gaps.items():
            if not isinstance(item, dict):
                continue
            reason = str(item.get("reason", "")).strip()
            if reason:
                evidence_gaps.append(f"{key}: {reason}")

    return {
        "problem_evidence": {
            "strength": _concept_strength_from_text(str(pain_threshold.get("severity", ""))),
            "supporting_quotes": supporting_quotes,
            "recent_behavior_evidence": [
                part for part in (
                    str(recent_behavior.get("summary", "")).strip(),
                    str(recent_behavior.get("details", "")).strip(),
                )
                if part
            ],
        },
        "current_workaround": {
            "existing_workaround": _as_string_list(current_workaround.get("summary")),
            "pain_level": _normalize_choice(
                _concept_strength_from_text(str(pain_threshold.get("severity", ""))),
                {"low", "medium", "high"},
                "medium",
            ),
            "switching_difficulty": "high",
            "what_must_not_change": [],
        },
        "trust_boundary": {
            "accepted_data_access": [],
            "rejected_data_access": [],
            "required_trust_explanation": [],
        },
        "first_value_requirement": {
            "first_use_success": _as_string_list(
                concept_reaction.get("details", "") if isinstance(concept_reaction, dict) else ""
            ),
            "time_to_value": "Unknown",
            "abandonment_triggers": [],
        },
        "pricing_signal": {
            "free_trial_need": "Unknown",
            "monthly_comfort_range": "Unknown",
            "payment_justification": [],
            "evidence_strength": "unknown",
        },
        "retention_risk": {
            "continuation_reasons": [],
            "drop_off_reasons": [],
            "workflow_effect": "unclear",
        },
        "assumption_validation": mapped_assumptions,
        "key_insights": mapped_key_insights or [text],
        "next_experiment": (
            str(recommended_experiment.get("description", "")).strip()
            if isinstance(recommended_experiment, dict) else ""
        ),
        "evidence_gaps": evidence_gaps,
        "synthetic_only_disclaimer": "Synthetic pre-validation only; not human market evidence.",
    }


def normalize_quality_evaluation(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    findings = normalized.get("findings")
    if not isinstance(findings, list):
        findings = []
    normalized["findings"] = findings

    strengths = normalized.get("strengths")
    if not isinstance(strengths, list):
        strengths = []
    normalized["strengths"] = [str(item).strip() for item in strengths if str(item).strip()]

    improvements = normalized.get("required_improvements")
    if not isinstance(improvements, list):
        improvements = []
    normalized["required_improvements"] = [str(item).strip() for item in improvements if str(item).strip()]

    hints = normalized.get("improvement_hints")
    if not isinstance(hints, dict):
        hints = {}
    normalized_hints = {
        "next_interview_focus": _as_string_list(hints.get("next_interview_focus")),
        "coverage_gap_actions": _as_string_list(hints.get("coverage_gap_actions")),
        "prompt_adjustments": _as_string_list(hints.get("prompt_adjustments")),
        "turn_budget_guidance": str(hints.get("turn_budget_guidance", "")).strip() or "Keep the current turn budget unless repeated coverage gaps persist.",
    }
    normalized["improvement_hints"] = normalized_hints

    scores = normalized.get("scores")
    required_score_keys = list(FACILITATOR_QUALITY_SCHEMA["properties"]["scores"]["required"])
    default_overall = scores.get("overall") if isinstance(scores, dict) else None
    if not isinstance(default_overall, int) or not 1 <= default_overall <= 5:
        default_overall = 3 if findings or normalized["required_improvements"] else 4
    normalized_scores = {
        key: (
            int(scores.get(key))
            if isinstance(scores, dict) and isinstance(scores.get(key), int) and 1 <= int(scores.get(key)) <= 5
            else default_overall
        )
        for key in required_score_keys
    }
    normalized["scores"] = normalized_scores

    checks = normalized.get("checks")
    required_check_keys = list(FACILITATOR_QUALITY_SCHEMA["properties"]["checks"]["required"])
    default_check = "warn" if findings or normalized["required_improvements"] else "pass"
    normalized_checks = {
        key: (
            str(checks.get(key)).strip()
            if isinstance(checks, dict) and str(checks.get(key)).strip() in {"pass", "warn", "fail"}
            else default_check
        )
        for key in required_check_keys
    }
    normalized["checks"] = normalized_checks

    human_review_needed = normalized.get("human_review_needed")
    if not isinstance(human_review_needed, bool):
        human_review_needed = bool(findings or normalized["required_improvements"])
    normalized["human_review_needed"] = human_review_needed

    if not normalized.get("synthetic_only_disclaimer"):
        normalized["synthetic_only_disclaimer"] = "Synthetic pre-validation only; not human market evidence."

    overall = normalized_scores.get("overall")
    verdict = normalized.get("overall_verdict")
    has_findings = bool(findings)
    has_high = any(isinstance(item, dict) and item.get("severity") == "high" for item in findings)
    has_improvements = bool(normalized["required_improvements"])
    actionable_hints = any(
        isinstance(normalized_hints.get(key), list) and bool(normalized_hints.get(key))
        for key in ("next_interview_focus", "coverage_gap_actions", "prompt_adjustments")
    )

    if verdict not in {"pass", "warn", "fail"}:
        if has_high or (isinstance(overall, int) and overall <= 2):
            verdict = "fail"
        elif has_findings or has_improvements or actionable_hints:
            verdict = "warn"
        else:
            verdict = "pass"
        normalized["overall_verdict"] = verdict

    if verdict in {"warn", "fail"} and not normalized["required_improvements"]:
        normalized["required_improvements"] = [
            "Review the transcript and synthesis manually before treating this run as calibrated evidence."
        ]
        has_improvements = True
    if verdict in {"warn", "fail"} and not actionable_hints:
        normalized_hints["next_interview_focus"] = [
            "Probe unclear evidence boundaries and verify whether the reported friction reflects repeated behavior."
        ]
        actionable_hints = True

    if has_high and isinstance(overall, int) and overall > 3:
        normalized_scores["overall"] = 3
        overall = 3
        if verdict == "pass":
            normalized["overall_verdict"] = "warn"
            verdict = "warn"

    score_values = [value for value in normalized_scores.values() if isinstance(value, int)]
    if has_findings and score_values and all(value == 5 for value in score_values):
        normalized_scores["overall"] = 4
        overall = 4
        if verdict == "pass":
            normalized["overall_verdict"] = "warn"
            verdict = "warn"

    if verdict == "warn" and isinstance(overall, int) and overall > 4 and has_improvements:
        normalized_scores["overall"] = 4
        overall = 4

    if verdict == "fail" and isinstance(overall, int) and overall > 2 and has_improvements:
        normalized_scores["overall"] = 2
        overall = 2

    if verdict == "pass" and has_findings and has_improvements and actionable_hints:
        normalized["overall_verdict"] = "warn"

    return normalized


def validate_quality_evaluation(payload: dict[str, Any]) -> None:
    verdict = payload.get("overall_verdict")
    scores = payload.get("scores")
    findings = payload.get("findings")
    improvements = payload.get("required_improvements")
    if verdict not in {"pass", "warn", "fail"} or not isinstance(scores, dict):
        raise ValueError("Facilitator quality evaluation has an invalid verdict or scores object.")
    if not isinstance(findings, list) or not isinstance(improvements, list):
        raise ValueError("Facilitator quality evaluation findings and improvements must be lists.")
    hints = payload.get("improvement_hints")
    if not isinstance(hints, dict):
        raise ValueError("Facilitator quality evaluation improvement_hints must be an object.")
    required_scores = set(FACILITATOR_QUALITY_SCHEMA["properties"]["scores"]["required"])
    missing_scores = required_scores - set(scores)
    checks = payload.get("checks")
    if missing_scores:
        raise ValueError(f"Facilitator quality evaluation is missing scores: {sorted(missing_scores)}")
    if not isinstance(checks, dict):
        raise ValueError("Facilitator quality evaluation checks must be an object.")
    required_checks = set(FACILITATOR_QUALITY_SCHEMA["properties"]["checks"]["required"])
    missing_checks = required_checks - set(checks)
    if missing_checks:
        raise ValueError(f"Facilitator quality evaluation is missing checks: {sorted(missing_checks)}")
    overall = scores.get("overall")
    if not isinstance(overall, int) or not 1 <= overall <= 5:
        raise ValueError("Facilitator quality evaluation overall score must be an integer from 1 to 5.")
    if verdict == "warn" and (overall > 4 or not improvements):
        raise ValueError("A warn quality verdict requires overall <= 4 and at least one improvement.")
    if verdict == "fail" and (overall > 2 or not improvements):
        raise ValueError("A fail quality verdict requires overall <= 2 and at least one improvement.")
    has_high = any(isinstance(item, dict) and item.get("severity") == "high" for item in findings)
    if has_high and overall > 3:
        raise ValueError("A high-severity quality finding requires overall <= 3.")
    score_values = [value for value in scores.values() if isinstance(value, int)]
    if findings and score_values and all(value == 5 for value in score_values):
        raise ValueError("Quality evaluation cannot assign all perfect scores when findings exist.")
    hint_lists = [
        hints.get("next_interview_focus", []),
        hints.get("coverage_gap_actions", []),
        hints.get("prompt_adjustments", []),
    ]
    if verdict != "pass" and not any(isinstance(item, list) and item for item in hint_lists):
        raise ValueError("Warn or fail quality evaluations require at least one actionable improvement hint.")


_PROJECT_SPECIFIC_MARKERS = (
    "aladdin",
    "mpf",
    "portfolio health check",
    "hong kong",
    "rm ",
    "rm-",
    "retail bank",
    "wealth dashboard",
)


def _contains_project_specific_marker(text: str) -> bool:
    lowered = text.casefold()
    return any(marker in lowered for marker in _PROJECT_SPECIFIC_MARKERS)


def normalize_facilitator_audit_feedback(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized.setdefault("artifact_version", "v1")
    normalized.setdefault("feedback_scope", "interview")
    applies_to = normalized.get("applies_to")
    if not isinstance(applies_to, dict):
        applies_to = {}
    applies_to.setdefault("interview_mode", [])
    applies_to.setdefault("domains", ["generic"])
    applies_to.setdefault("safe_for_global_reuse", True)
    normalized["applies_to"] = applies_to
    summary = normalized.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    summary.setdefault("overall_assessment", "")
    summary.setdefault("primary_failure_mode", "")
    summary.setdefault("depth_vs_coverage_assessment", "")
    normalized["summary"] = summary

    for key in (
        "facilitator_feedback_tags",
        "high_value_missed_followups",
        "likely_misclassified_driver_patterns",
        "evidence_handling_issues",
        "prompt_adjustments",
        "carry_forward_rules",
        "blocked_feedback",
    ):
        value = normalized.get(key)
        normalized[key] = value if isinstance(value, list) else []

    blocked: list[dict[str, Any]] = list(normalized["blocked_feedback"])
    safe_prompt_adjustments: list[dict[str, Any]] = []
    for item in normalized["prompt_adjustments"]:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", ""))
        safe_flag = bool(item.get("safe_for_global_reuse", False))
        if safe_flag and _contains_project_specific_marker(text):
            blocked.append({
                "blocked_item": text,
                "block_reason": "project_specific_content",
                "rewrite_as_generic": "",
            })
            continue
        safe_prompt_adjustments.append(item)
    normalized["prompt_adjustments"] = safe_prompt_adjustments

    safe_rules: list[dict[str, Any]] = []
    for item in normalized["carry_forward_rules"]:
        if not isinstance(item, dict):
            continue
        rule_text = str(item.get("rule", ""))
        safe_flag = bool(item.get("safe_for_global_reuse", False))
        if safe_flag and _contains_project_specific_marker(rule_text):
            blocked.append({
                "blocked_item": rule_text,
                "block_reason": "project_specific_content",
                "rewrite_as_generic": "",
            })
            continue
        safe_rules.append(item)
    normalized["carry_forward_rules"] = safe_rules
    normalized["blocked_feedback"] = blocked

    if blocked:
        normalized["applies_to"]["safe_for_global_reuse"] = False
    return normalized


def validate_facilitator_audit_feedback(payload: dict[str, Any]) -> None:
    for key in FACILITATOR_AUDIT_FEEDBACK_SCHEMA["required"]:
        if key not in payload:
            raise ValueError(f"Facilitator audit feedback is missing '{key}'.")
    if payload.get("feedback_scope") not in {"interview", "panel", "batch"}:
        raise ValueError("Facilitator audit feedback has an invalid feedback_scope.")
    applies_to = payload.get("applies_to")
    if not isinstance(applies_to, dict):
        raise ValueError("Facilitator audit feedback applies_to must be an object.")
    if not isinstance(applies_to.get("interview_mode"), list):
        raise ValueError("Facilitator audit feedback interview_mode must be a list.")
    if not isinstance(applies_to.get("domains"), list):
        raise ValueError("Facilitator audit feedback domains must be a list.")
    if not isinstance(applies_to.get("safe_for_global_reuse"), bool):
        raise ValueError("Facilitator audit feedback safe_for_global_reuse must be a boolean.")
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("Facilitator audit feedback summary must be an object.")
    for key in ("overall_assessment", "primary_failure_mode", "depth_vs_coverage_assessment"):
        if not isinstance(summary.get(key), str):
            raise ValueError(f"Facilitator audit feedback summary field '{key}' must be a string.")
    for key in (
        "facilitator_feedback_tags",
        "high_value_missed_followups",
        "likely_misclassified_driver_patterns",
        "evidence_handling_issues",
        "prompt_adjustments",
        "carry_forward_rules",
        "blocked_feedback",
    ):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Facilitator audit feedback field '{key}' must be a list.")
    for item in payload.get("carry_forward_rules", []):
        if not isinstance(item, dict):
            raise ValueError("Facilitator audit feedback carry_forward_rules must contain objects.")
        if bool(item.get("safe_for_global_reuse", False)) and _contains_project_specific_marker(str(item.get("rule", ""))):
            raise ValueError("Global-safe carry_forward_rules cannot contain project-specific content.")
    for item in payload.get("prompt_adjustments", []):
        if not isinstance(item, dict):
            raise ValueError("Facilitator audit feedback prompt_adjustments must contain objects.")
        if bool(item.get("safe_for_global_reuse", False)) and _contains_project_specific_marker(str(item.get("text", ""))):
            raise ValueError("Global-safe prompt_adjustments cannot contain project-specific content.")


def validate_hypothesis_assessment(payload: dict[str, Any]) -> None:
    assessment = payload.get("hypothesis_assessment")
    if not isinstance(assessment, dict):
        raise ValueError("Facilitator synthesis requires a hypothesis_assessment object.")
    verdict = assessment.get("verdict")
    supporting = assessment.get("supporting_evidence_refs")
    contradicting = assessment.get("contradicting_evidence_refs")
    alternative_tests = assessment.get("alternative_tests")
    mechanism_basis = assessment.get("mechanism_test_basis")
    condition_present = assessment.get("condition_present_case_refs")
    condition_absent = assessment.get("condition_absent_case_refs")
    if verdict not in {"not_tested", "unsupported", "mixed", "provisionally_supported"}:
        raise ValueError("Hypothesis assessment has an invalid verdict.")
    if assessment.get("confidence") not in {"low", "medium"}:
        raise ValueError("A single synthetic interview cannot have high hypothesis confidence.")
    if not isinstance(supporting, list) or not isinstance(contradicting, list) or not isinstance(alternative_tests, list):
        raise ValueError("Hypothesis assessment evidence and alternative tests must be lists.")
    if not isinstance(condition_present, list) or not isinstance(condition_absent, list):
        raise ValueError("Hypothesis assessment condition-case references must be lists.")
    if verdict == "unsupported" and not contradicting:
        raise ValueError("An unsupported hypothesis verdict requires contradicting evidence.")
    if verdict == "mixed" and (not supporting or not contradicting):
        raise ValueError("A mixed hypothesis verdict requires supporting and contradicting evidence.")
    if verdict == "provisionally_supported" and not supporting:
        raise ValueError("A provisionally supported hypothesis requires supporting evidence.")
    if verdict != "not_tested" and mechanism_basis != "observed_event":
        raise ValueError("A tested hypothesis verdict requires an observed-event mechanism test.")


class OpenAIFacilitatorProvider:
    def __init__(self, client: OpenAIResponsesClient) -> None:
        self.client = client
        config = client.config
        self.provider_name = "codex" if config.transport.startswith("codex") else "openai"
        self.model_name = config.model

    def next_turn(
        self, *, system_prompt: str, user_prompt: str, provider_session_id: str = "",
    ) -> FacilitatorDecision:
        is_codex = self.client.config.transport == "codex_cli"
        active_system_prompt = (
            "Continue the existing design research interview as the same independent facilitator."
            if is_codex and provider_session_id else system_prompt
        )
        try:
            payload = self.client.create_json_response(
                system_prompt=active_system_prompt,
                user_prompt=user_prompt,
                output_schema=FACILITATOR_TURN_SCHEMA,
                codex_session_id=provider_session_id or None,
                persist_codex_session=is_codex,
            )
            return self._decision_from_payload(payload, provider_session_id)
        except (OpenAIProviderError, ValueError):
            if not self._supports_text_fallback():
                raise
            raw_text = self.client.create_text_response(
                system_prompt=active_system_prompt + "\n\n" + _facilitator_text_fallback_instruction(),
                user_prompt=user_prompt,
                codex_session_id=provider_session_id or None,
                persist_codex_session=is_codex,
            )
            return self._decision_from_text(raw_text, provider_session_id)

    def _supports_text_fallback(self) -> bool:
        return (
            self.client.config.provider_name == "agnes"
            and self.client.config.transport not in {"codex_cli", "codex_sdk_node"}
            and hasattr(self.client, "create_text_response")
        )

    def _decision_from_payload(self, payload: dict[str, Any], provider_session_id: str) -> FacilitatorDecision:
        should_end = payload.get("should_end")
        if not isinstance(should_end, bool):
            raise ValueError("Facilitator LLM output field 'should_end' must be a boolean.")
        message = _coerce_required_string_field(payload, "message_to_persona")
        if not should_end and not message:
            raise ValueError("Facilitator LLM must ask a question unless it ends the interview.")
        metadata = getattr(self.client, "last_transport_metadata", {})
        return FacilitatorDecision(
            interview_phase=_coerce_required_string_field(payload, "interview_phase"),
            probing_strategy=_coerce_required_string_field(payload, "probing_strategy"),
            decision_rationale=_coerce_required_string_field(payload, "decision_rationale"),
            message_to_persona=message,
            evidence_updates=_coerce_object_list_field(payload, "evidence_updates"),
            root_cause_hypotheses=_coerce_object_list_field(payload, "root_cause_hypotheses"),
            open_questions=[str(item).strip() for item in _coerce_list_field(payload, "open_questions") if str(item).strip()],
            should_end=should_end,
            end_reason=_coerce_string_field(payload, "end_reason"),
            question_evidence_basis=_normalize_choice(
                _coerce_required_string_field(payload, "question_evidence_basis"),
                {"current_event", "recalled_contrast_event", "hypothetical", "general_pattern", "clarification"},
                "clarification",
            ),
            question_evidence_target=_normalize_choice(
                _coerce_required_string_field(payload, "question_evidence_target"),
                {"context", "target_behaviour", "participant_cause", "consequence", "hypothesis_condition", "alternative_condition"},
                "context",
            ),
            provider_session_id=str(metadata.get("codex_session_id", "")) or provider_session_id,
        )

    def _decision_from_text(self, raw_text: str, provider_session_id: str) -> FacilitatorDecision:
        parsed = _parse_tagged_text_fields(raw_text)
        message = parsed.get("QUESTION", "").strip()
        should_end = _parse_text_boolean(parsed.get("SHOULD_END", ""))
        end_reason = parsed.get("END_REASON", "").strip()
        if not should_end and not message:
            message = raw_text.strip()
        if should_end and not end_reason and not message:
            end_reason = "facilitator_text_fallback_end"
        if not should_end and not message:
            raise ValueError("Facilitator text fallback did not contain a usable question.")
        metadata = getattr(self.client, "last_transport_metadata", {})
        return FacilitatorDecision(
            interview_phase=parsed.get("PHASE", "").strip() or "follow_up",
            probing_strategy=parsed.get("STRATEGY", "").strip() or "open_ended_probe",
            decision_rationale=parsed.get("RATIONALE", "").strip() or "Recovered from Agnes plain-text fallback after structured output failure.",
            message_to_persona=message,
            evidence_updates=[],
            root_cause_hypotheses=[],
            open_questions=_split_text_list(parsed.get("OPEN_QUESTION", "")),
            should_end=should_end,
            end_reason=end_reason,
            question_evidence_basis=_normalize_choice(
                parsed.get("BASIS", ""),
                {"current_event", "recalled_contrast_event", "hypothetical", "general_pattern", "clarification"},
                "clarification",
            ),
            question_evidence_target=_normalize_choice(
                parsed.get("TARGET", ""),
                {"context", "target_behaviour", "participant_cause", "consequence", "hypothesis_condition", "alternative_condition"},
                "context",
            ),
            provider_session_id=str(metadata.get("codex_session_id", "")) or provider_session_id,
        )

    def synthesize(
        self, *, system_prompt: str, user_prompt: str, provider_session_id: str = "",
    ) -> tuple[dict[str, Any], str]:
        is_codex = self.client.config.transport == "codex_cli"
        payload = self.client.create_json_response(
            system_prompt=(
                "Continue as the same independent facilitator and produce the final evidence-led synthesis."
                if is_codex and provider_session_id else system_prompt
            ),
            user_prompt=user_prompt,
            output_schema=FACILITATOR_SYNTHESIS_SCHEMA,
            codex_session_id=provider_session_id or None,
            persist_codex_session=is_codex,
        )
        for key in FACILITATOR_SYNTHESIS_SCHEMA["required"]:
            if key not in payload:
                raise ValueError(f"Facilitator synthesis is missing '{key}'.")
        validate_hypothesis_assessment(payload)
        metadata = getattr(self.client, "last_transport_metadata", {})
        session_id = str(metadata.get("codex_session_id", "")) or provider_session_id
        return payload, session_id

    def judge_hypothesis_evidence(
        self, *, system_prompt: str, user_prompt: str,
    ) -> tuple[dict[str, Any], str]:
        is_codex = self.client.config.transport == "codex_cli"
        payload = self.client.create_json_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=HYPOTHESIS_EVIDENCE_JUDGE_SCHEMA,
            persist_codex_session=is_codex,
        )
        for key in HYPOTHESIS_EVIDENCE_JUDGE_SCHEMA["required"]:
            if key not in payload:
                raise ValueError(f"Hypothesis evidence judgment is missing '{key}'.")
        metadata = getattr(self.client, "last_transport_metadata", {})
        return payload, str(metadata.get("codex_session_id", ""))

    def synthesize_concept(
        self, *, system_prompt: str, user_prompt: str, provider_session_id: str = "",
    ) -> tuple[dict[str, Any], str]:
        is_codex = self.client.config.transport == "codex_cli"
        active_system_prompt = (
            "Continue as the same independent research facilitator and produce the concept-validation report."
            if is_codex and provider_session_id else system_prompt
        )
        try:
            payload = self.client.create_json_response(
                system_prompt=active_system_prompt,
                user_prompt=user_prompt,
                output_schema=CONCEPT_SYNTHESIS_SCHEMA,
                codex_session_id=provider_session_id or None,
                persist_codex_session=is_codex,
            )
        except OpenAIProviderError:
            if not self._supports_text_fallback():
                raise
            raw_text = self.client.create_text_response(
                system_prompt=active_system_prompt,
                user_prompt=user_prompt,
                codex_session_id=provider_session_id or None,
                persist_codex_session=is_codex,
            )
            payload = _concept_synthesis_from_text(raw_text)
        payload = normalize_concept_synthesis(payload)
        metadata = getattr(self.client, "last_transport_metadata", {})
        return payload, str(metadata.get("codex_session_id", "")) or provider_session_id

    def evaluate_quality(
        self, *, system_prompt: str, user_prompt: str, provider_session_id: str = "",
    ) -> tuple[dict[str, Any], str]:
        is_codex = self.client.config.transport == "codex_cli"
        payload = self.client.create_json_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=FACILITATOR_QUALITY_SCHEMA,
            codex_session_id=provider_session_id or None,
            persist_codex_session=is_codex,
        )
        payload = normalize_quality_evaluation(payload)
        for key in FACILITATOR_QUALITY_SCHEMA["required"]:
            if key not in payload:
                raise ValueError(f"Facilitator quality evaluation is missing '{key}'.")
        validate_quality_evaluation(payload)
        metadata = getattr(self.client, "last_transport_metadata", {})
        session_id = str(metadata.get("codex_session_id", "")) or provider_session_id
        return payload, session_id

    def generate_audit_feedback(
        self, *, system_prompt: str, user_prompt: str, provider_session_id: str = "",
    ) -> tuple[dict[str, Any], str]:
        is_codex = self.client.config.transport == "codex_cli"
        payload = self.client.create_json_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=FACILITATOR_AUDIT_FEEDBACK_SCHEMA,
            codex_session_id=provider_session_id or None,
            persist_codex_session=is_codex,
        )
        payload = normalize_facilitator_audit_feedback(payload)
        validate_facilitator_audit_feedback(payload)
        metadata = getattr(self.client, "last_transport_metadata", {})
        session_id = str(metadata.get("codex_session_id", "")) or provider_session_id
        return payload, session_id
