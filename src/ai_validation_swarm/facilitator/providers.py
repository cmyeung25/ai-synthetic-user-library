from __future__ import annotations

from typing import Any, Protocol

from ai_validation_swarm.facilitator.models import FacilitatorDecision
from ai_validation_swarm.providers.openai_client import OpenAIResponsesClient


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


def _require_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Facilitator LLM output field '{key}' must be a list.")
    return value


def normalize_quality_evaluation(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    scores = normalized.get("scores")
    findings = normalized.get("findings")
    improvements = normalized.get("required_improvements")
    hints = normalized.get("improvement_hints")
    if not isinstance(scores, dict) or not isinstance(findings, list):
        return normalized

    normalized_scores = dict(scores)
    normalized["scores"] = normalized_scores
    overall = normalized_scores.get("overall")
    verdict = normalized.get("overall_verdict")
    has_findings = bool(findings)
    has_high = any(isinstance(item, dict) and item.get("severity") == "high" for item in findings)
    has_improvements = isinstance(improvements, list) and bool(improvements)
    actionable_hints = False
    if isinstance(hints, dict):
        actionable_hints = any(
            isinstance(hints.get(key), list) and bool(hints.get(key))
            for key in ("next_interview_focus", "coverage_gap_actions", "prompt_adjustments")
        )

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
        payload = self.client.create_json_response(
            system_prompt=(
                "Continue the existing design research interview as the same independent facilitator."
                if is_codex and provider_session_id else system_prompt
            ),
            user_prompt=user_prompt,
            output_schema=FACILITATOR_TURN_SCHEMA,
            codex_session_id=provider_session_id or None,
            persist_codex_session=is_codex,
        )
        should_end = payload.get("should_end")
        if not isinstance(should_end, bool):
            raise ValueError("Facilitator LLM output field 'should_end' must be a boolean.")
        message = _require_string(payload, "message_to_persona")
        if not should_end and not message:
            raise ValueError("Facilitator LLM must ask a question unless it ends the interview.")
        metadata = getattr(self.client, "last_transport_metadata", {})
        return FacilitatorDecision(
            interview_phase=_require_string(payload, "interview_phase"),
            probing_strategy=_require_string(payload, "probing_strategy"),
            decision_rationale=_require_string(payload, "decision_rationale"),
            message_to_persona=message,
            evidence_updates=_require_list(payload, "evidence_updates"),
            root_cause_hypotheses=_require_list(payload, "root_cause_hypotheses"),
            open_questions=[str(item) for item in _require_list(payload, "open_questions")],
            should_end=should_end,
            end_reason=_require_string(payload, "end_reason"),
            question_evidence_basis=_require_string(payload, "question_evidence_basis"),
            question_evidence_target=_require_string(payload, "question_evidence_target"),
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
        payload = self.client.create_json_response(
            system_prompt=(
                "Continue as the same independent research facilitator and produce the concept-validation report."
                if is_codex and provider_session_id else system_prompt
            ),
            user_prompt=user_prompt,
            output_schema=CONCEPT_SYNTHESIS_SCHEMA,
            codex_session_id=provider_session_id or None,
            persist_codex_session=is_codex,
        )
        for key in CONCEPT_SYNTHESIS_SCHEMA["required"]:
            if key not in payload:
                raise ValueError(f"Concept synthesis is missing '{key}'.")
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
