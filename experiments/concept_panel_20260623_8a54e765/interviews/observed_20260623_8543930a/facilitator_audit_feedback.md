# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: Coverage was completed cleanly and the conversation stayed natural, but the facilitator often traded depth for checklist completion and the synthesis converted hypothetical concept reactions into stronger evidence than the interview earned.
- Primary failure mode: The main failure mode was accepting first-pass hypothetical reactions without enough contrast, threshold, or current-workflow comparison probing, then treating those reactions as stronger proof than the transcript supports.
- Depth vs coverage: Coverage was prioritized over depth. Required areas were touched, but several high-signal participant clues were not unpacked before moving to the next coverage item.

## Feedback Tags

- [medium] coverage_over_depth: After the participant mentioned screenshotting, delayed comparison, and avoiding emotional moves in `exchange_1.persona` and `exchange_2.persona`, the facilitator moved into concept introduction instead of deepening what the workaround protects against and where it breaks.
- [medium] open_signal_not_exploited: The participant volunteered signals about emotional self-control, delayed review, and explanation thresholds in `exchange_2.persona`, `exchange_4.persona`, and `exchange_5.persona`, but those were not followed with consequence, near-miss, or threshold probes.
- [medium] forced_choice_narrowing: `exchange_8.facilitator` narrowed service embedding to self-serve versus follow-up support instead of first asking open-endedly where the feature should live and what, if any, human involvement should exist.
- [high] hypothetical_as_behavioral_evidence: The synthesis uses hypothetical statements from `exchange_3.persona` and `exchange_4.persona` as support for broader behavioral and workflow claims, including stronger interpretations such as replacement effects and validated design direction.
- [low] benefit_presupposition_in_concept_intro: `exchange_3.facilitator` introduced the concept with a label and a helpfulness frame, describing it as a free check that would simply help review the portfolio.

## Missed High-Value Follow-Ups

- [high] What does that delayed comparison protect you from, and can you recall a time when that pause changed what you would have done?
  Trigger: volunteered_workaround_protection
- [high] What would count as far enough off that you would move from waiting to acting, and can you anchor that to a recent real case?
  Trigger: threshold_signal
- [high] Can you think of a time a tool or report failed that explanation standard, and what did you do instead?
  Trigger: trust_condition_signal
- [medium] What happens if the same signal arrives outside that moment, and how would you handle it differently?
  Trigger: timing_preference_signal
- [medium] What would make you stop opening it after the first few uses even if it seemed useful at first?
  Trigger: repeat_use_claim

## Likely Misclassified Drivers

- The participant's current behavior was treated mainly as a lightweight review habit. -> The stronger driver may be self-protection against impulsive action under uncertainty, not just preference for convenience.
- The participant's request for explanations was treated mainly as a feature trust requirement. -> The deeper driver may be preserving decision autonomy and resisting opaque external steering.

## Evidence Handling Issues

- [high] Hypothetical concept reactions were used as if they were direct evidence of current problem structure and downstream behavior.
- [medium] The report inferred stronger workflow impact than the transcript warranted.
- [medium] Broad assumption statuses were marked supported from one participant-facing reaction set without enough comparative or disconfirming evidence.

## Prompt Adjustments

- followup_trigger_rule: When a participant volunteers a workaround that appears to manage risk, emotion, or uncertainty, require one follow-up on what that workaround protects against before introducing the concept.
- contrast_rule: When a participant states a preferred moment, format, or channel, require one contrast probe about the non-preferred alternative before closing that topic.
- decision_rule: In concept-validation mode, concept reactions may satisfy coverage but do not count as behavioral proof unless anchored to a recalled past event or explicit comparison to an actual recent workflow.
- question_priority_rule: Before moving from current behavior into concept introduction, prioritize one depth probe on consequence, threshold, or failure mode if the participant has already revealed a concrete self-protective behavior.
- evidence_rule: Keep synthesis fields for observed behavior and hypothetical concept response separate, and block stronger labels such as replacement, validation, or support when the transcript only contains stated intent.
- followup_trigger_rule: Use open-first channel or embedding questions. Only offer either-or options after the participant has described their own preferred setup.

## Carry-Forward Rules

- cf_open_signal_depth_01: If a participant volunteers a concrete ritual or safeguard in their current workflow, ask one follow-up about the failure it prevents before advancing to the next coverage area.
- cf_threshold_probe_01: When a participant uses vague threshold language such as 'too much,' 'obvious,' or 'enough,' ask what that threshold looks like in a specific remembered case.
- cf_hypothetical_discipline_01: Do not treat stated future use, stated trust, or stated willingness as equivalent to observed behavior; label and synthesize them separately.
- cf_open_first_embedding_01: For placement or service-model questions, ask open-endedly first and narrow with options only after the participant has offered their own frame.

## Blocked Feedback

- The interview should have tested whether this specific analytics feature should remain self-serve first and only escalate to relationship-manager involvement later. (This is a project-specific product-routing conclusion rather than a generic facilitation lesson.)
- The facilitator should probe whether concentration analysis matters more than other analytics functions in this banking context. (This is tied to the project's particular feature set and domain scope.)
- The synthesis should not generalize this retail-banking participant's dislike of proactive outreach into a broader channel strategy. (This is too tied to the study context and participant segment.)
