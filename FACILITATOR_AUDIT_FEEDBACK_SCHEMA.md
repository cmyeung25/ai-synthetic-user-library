# Facilitator Audit Feedback Schema

## Purpose

This document defines a generic, reusable feedback schema for improving the platform's facilitator over time.

The goal is not to teach the facilitator the "right answer" for one project.
The goal is to teach the facilitator better interviewing behavior across projects, domains, concepts, and persona sets.

This schema exists to support:

- post-run offline audit
- safe feedback accumulation across many panels
- generic facilitator evolution
- protection against project-specific prompt contamination

## Core Principle

The facilitator may learn from:

- interviewing mistakes
- missed follow-up patterns
- weak evidence handling
- shallow causal extraction
- poor contrast testing
- premature concept steering

The facilitator must not learn:

- a domain's preferred answer
- a concept's expected pain point
- a project's preferred objection framing
- a specific persona's hidden biography
- a panel's consensus as if it were a universal truth

In short:

- learn the interviewing method
- do not learn the project conclusion

## Design Requirements

Any audit feedback artifact must satisfy all of the following:

1. It must be generic enough to apply to unrelated domains.
2. It must describe facilitator behavior, not participant truth.
3. It must separate observed issue from recommended improvement.
4. It must clearly mark whether the feedback is safe to reuse globally.
5. It must explicitly reject project-specific answer leakage.

## Artifact Scope

This schema is intended for offline auditor output after:

- a single interview
- a concept panel
- a batch of interviews in one study

It is not the facilitator prompt itself.
It is an intermediate feedback artifact that may later be filtered and distilled into safe facilitator improvements.

## Schema Overview

The audit artifact should contain the following top-level sections.

```json
{
  "artifact_version": "v1",
  "feedback_scope": "interview|panel|batch",
  "applies_to": {
    "interview_mode": ["explore_root_cause", "validate_hypothesis", "concept_validation"],
    "domains": ["generic"],
    "safe_for_global_reuse": true
  },
  "summary": {
    "overall_assessment": "string",
    "primary_failure_mode": "string",
    "depth_vs_coverage_assessment": "string"
  },
  "facilitator_feedback_tags": [],
  "high_value_missed_followups": [],
  "likely_misclassified_driver_patterns": [],
  "evidence_handling_issues": [],
  "prompt_adjustments": [],
  "carry_forward_rules": [],
  "blocked_feedback": []
}
```

## Top-Level Fields

### `artifact_version`

Schema version for forward compatibility.

### `feedback_scope`

Allowed values:

- `interview`
- `panel`
- `batch`

### `applies_to`

Defines where the feedback is safe to reuse.

```json
{
  "interview_mode": ["concept_validation"],
  "domains": ["generic"],
  "safe_for_global_reuse": true
}
```

Rules:

- `domains` should normally remain `["generic"]`.
- If any feedback is domain-shaped, it must not be marked safe for global reuse.
- If uncertain, set `safe_for_global_reuse` to `false`.

### `summary`

Short human-readable framing of the facilitator weakness.

Example:

```json
{
  "overall_assessment": "The facilitator covered the required topics but repeatedly moved on before extracting causal depth.",
  "primary_failure_mode": "coverage_over_depth",
  "depth_vs_coverage_assessment": "Coverage was adequate; precision was weak because high-signal behavioural clues were not pursued."
}
```

## `facilitator_feedback_tags`

This is the main generic error taxonomy.

Each item should use a stable tag plus a short explanation.

```json
{
  "tag": "missed_high_signal_clue",
  "severity": "high",
  "why_it_matters": "High-information participant details were not converted into deeper causal follow-up.",
  "observed_pattern": "Participant mentioned a concrete workaround artifact, but the facilitator moved to the next protocol bucket."
}
```

### Approved Generic Tags

The following tags are safe platform-level learning signals.

- `missed_high_signal_clue`
- `coverage_over_depth`
- `accepted_surface_answer_without_cause`
- `did_not_probe_consequence`
- `did_not_probe_near_miss`
- `did_not_probe_contrast_case`
- `did_not_probe_threshold_for_action`
- `jumped_to_concept_too_early`
- `jumped_to_solution_too_early`
- `merged_multiple_topics_in_one_turn`
- `underused_participant_language`
- `did_not_test_alternative_explanation`
- `converted_statement_into_assumption_too_fast`
- `over-indexed_on_protocol_slots`
- `failed_to_preserve_participant_frame`
- `did_not_linger_on_workaround_artifact`
- `did_not_follow_up_on_delay_or_deferral_behavior`
- `did_not_clarify_trust_sequence`

### Disallowed Tags

The following are too project-specific and must not be carried forward as generic facilitator learning:

- `should_have_asked_about_mpf_overlap`
- `should_have_probed_aladdin_brand_trust`
- `hong_kong_users_fear_sales_trigger`
- `retail_bank_users_want_whole_portfolio_view`

These encode a study conclusion, not a facilitation skill.

## `high_value_missed_followups`

These capture follow-ups the facilitator should likely have asked in the moment.

They are useful for diagnosis and later training, but must remain phrased generically.

```json
{
  "trigger_type": "workaround_artifact",
  "priority": "high",
  "participant_signal": "The participant said they keep notes about why they bought something.",
  "missed_followup_question": "When those notes matter most, what mistake are they helping you avoid?",
  "generic_learning": "When a participant mentions a self-made artifact, probe what failure it protects against before moving on."
}
```

### Approved Trigger Types

- `workaround_artifact`
- `delayed_decision_behavior`
- `manual_reconciliation`
- `trust_boundary_statement`
- `threshold_for_action`
- `emotional_pause_or_hesitation`
- `false_positive_or_data_freshness_concern`
- `proof_before_permission_boundary`
- `memory_aid_usage`
- `contrast_between_routine_and_exception`

### Rules

- The `participant_signal` may be study-specific.
- The `generic_learning` must be generic.
- The missed question should be reusable in many domains with light rewriting.

## `likely_misclassified_driver_patterns`

These identify places where the facilitator may have labeled the participant too quickly.

This section is especially important for improving precision.

```json
{
  "observed_surface_frame": "wants better risk analytics",
  "possible_underlying_driver": "wants fewer silent errors during fragmented review sessions",
  "why_the_surface_frame_is_weak": "The participant's examples focused on reconciliation and confidence, not on richer analysis.",
  "generic_learning": "Do not treat a requested feature as the root driver until the underlying failure or avoided mistake is explicit."
}
```

### Good Uses

- feature request mistaken for root cause
- stated preference mistaken for decision mechanism
- trust concern mistaken for total refusal
- desire for simplicity mistaken for low sophistication

### Bad Uses

- asserting what the participant "really" wanted without transcript support
- importing hidden persona profile facts into the generic rule
- converting one panel finding into a universal market claim

## `evidence_handling_issues`

These capture where the facilitator used weak evidence carelessly.

```json
{
  "issue": "The facilitator treated a stated month-two intent as if it were strong behavioral evidence.",
  "severity": "medium",
  "generic_learning": "Distinguish hypothetical retention claims from actual repeated behavior or analogous past behavior."
}
```

### Typical Issue Types

- hypothetical treated as observed
- concern treated as consequence
- preference treated as action
- one case treated as repeated pattern
- no contrast before conclusion
- no participant-led cause before facilitator interpretation

## `prompt_adjustments`

These are generic prompt-level changes that may be safely injected into future facilitator prompts or policies.

Each adjustment must be domain-agnostic.

```json
{
  "adjustment_type": "decision_rule",
  "text": "If the participant gives a concrete workaround detail, ask one follow-up about what failure, confusion, or avoided mistake that workaround is protecting against before returning to protocol coverage.",
  "reuse_scope": "global",
  "safe_for_global_reuse": true
}
```

### Allowed Adjustment Types

- `decision_rule`
- `stop_rule`
- `followup_trigger_rule`
- `evidence_rule`
- `contrast_rule`
- `question_priority_rule`

### Disallowed Adjustment Types

- domain tactics
- concept-specific prompts
- market conclusions
- participant segment assumptions

## `carry_forward_rules`

This section is the safe distillation layer.

Only generic, reusable feedback may enter here.

```json
{
  "rule_id": "linger_on_high_signal_clue",
  "rule": "When a participant gives a specific self-created workaround, ask one depth question before moving to the next research bucket.",
  "source_tags": ["missed_high_signal_clue", "coverage_over_depth"],
  "confidence": "medium"
}
```

Rules in this section are candidates for future facilitator evolution.

They should be:

- short
- generic
- observable
- testable in later runs

## `blocked_feedback`

This section is mandatory whenever the auditor detects project-specific contamination.

```json
{
  "blocked_item": "The facilitator should ask about MPF overlap earlier next time.",
  "block_reason": "project_specific_content",
  "rewrite_as_generic": "If a participant points to one asset bucket as uncertain or opaque, probe what that opacity prevents them from knowing about the whole portfolio."
}
```

This section is critical because it prevents the system from "learning the last project."

## Safety Filter

Before any audit artifact is allowed to influence facilitator evolution, run this filter:

1. Does it describe facilitator behavior rather than project truth?
2. Can it apply to multiple unrelated domains?
3. Does it avoid named products, brands, asset classes, or local market assumptions?
4. Does it avoid turning one panel's answer into a prior for future panels?
5. Can it be rewritten as a generic interviewing rule?

If the answer to any of these is no, the item must be blocked or rewritten.

## What The Facilitator May Learn

Safe examples:

- When a participant mentions a manual workaround, ask what it protects against.
- When a participant delays a decision, ask what mistake they were trying to avoid.
- When a participant states a trust boundary, ask what minimum proof would lower that boundary.
- When a participant mentions a recurring check, ask what would trigger immediate action versus later review.
- Before moving to pricing or retention, confirm at least one concrete consequence or avoided failure.

## What The Facilitator Must Not Learn

Unsafe examples:

- Retail banking users mainly care about overlap.
- Hong Kong customers dislike RM upsell.
- Free analytics should always focus on concentration risk.
- Aladdin should be embedded in the portfolio overview page.
- MPF opacity is a common primary pain point.

These are research outputs, not facilitation rules.

## Learning Loop

The intended platform loop is:

1. Run interviews
2. Audit facilitator behavior offline
3. Generate generic feedback artifact
4. Filter out project-specific contamination
5. Distill safe carry-forward rules
6. Update facilitator prompt or decision policy
7. Re-test on unrelated studies

This preserves platform evolution without poisoning the facilitator with local conclusions.

## Evaluation Criteria For Good Feedback

A good facilitator audit artifact should improve:

- follow-up precision
- causal depth
- evidence discipline
- contrast testing
- participant-frame preservation
- resistance to concept steering

It should not improve:

- agreement with one project thesis
- reproduction of one panel's dominant pattern
- speed of filling protocol buckets at the cost of depth

## Minimum Viable v1 Output

If a first implementation needs to stay small, require only:

- `summary`
- `facilitator_feedback_tags`
- `high_value_missed_followups`
- `prompt_adjustments`
- `blocked_feedback`

That is enough to begin safe iterative improvement.

## Recommended Next Step

Once this schema is accepted, the next platform step should be:

1. add an auditor output artifact such as `facilitator_audit_feedback.json`
2. add a safe filter that rewrites or blocks project-specific comments
3. inject only `carry_forward_rules` into later facilitator runs

Do not inject raw audit text directly into the facilitator prompt.
