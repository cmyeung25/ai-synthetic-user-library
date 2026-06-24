# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: The facilitator achieved broad required coverage with natural flow, but accepted several high-signal participant clues without enough causal or contrast probing. The main improvement is to trade one or two later coverage questions for deeper follow-up on trust criteria, benchmark meaning, non-action paths, and channel boundaries.
- Primary failure mode: Coverage was completed before the facilitator extracted the decision rules underneath the participant's stated preferences.
- Depth vs coverage: Coverage was strong and efficient, but depth was uneven. Several participant signals that could have clarified mechanism, thresholds, and alternatives were acknowledged and then left underexplored.

## Feedback Tags

- [medium] benefit_led_concept_intro: The concept was introduced with built-in benefit framing rather than a neutral description of what the participant would see.
- [high] missed_mechanism_probe: The participant asked for judgment transparency, but the interview stopped short of probing what exact explanation format or benchmark would cross the trust threshold.
- [high] coverage_over_depth: After collecting acceptable top-line answers for each required area, the facilitator moved on instead of deepening a few high-signal moments.
- [medium] binary_followup_framing: A later embedding question constrained the response to self-serve versus human follow-up instead of first asking what should happen next.
- [high] missing_nonuse_contrast: The interview established when the concept might fit, but not when the participant would ignore, dismiss, or defer it.

## Missed High-Value Follow-Ups

- [high] What exact evidence or comparison would make the judgment feel credible enough to act on, and what would still feel too vague?
  Trigger: trust_threshold_signal
- [high] When you say you want a comparison, do you mean versus your own past pattern, a target plan, a peer group, or some general rule of thumb?
  Trigger: benchmark_ambiguity
- [high] If the alert looked real but you decided not to act, what would make you leave it alone, and what would you want the product to do next?
  Trigger: non_action_path
- [high] If follow-up were offered, what format would feel helpful rather than pressuring?
  Trigger: anti_sales_boundary
- [medium] Can you describe the smallest change that would still be worth opening, versus a change you would dismiss as noise?
  Trigger: retention_claim
- [high] Tell me about a recent time you did not check this area even though you could have. What made it not worth your attention then?
  Trigger: contrast_case_missing

## Likely Misclassified Drivers

- The participant wants explanation before trusting the output. -> Need for personally legible evidence and decision control, not just a generic desire for more detail.
- The participant prefers to understand things in-app before any human follow-up. -> Protection against unwanted escalation or persuasion, not merely channel preference.
- The participant wants monthly reminders only when something changed. -> Low attention tolerance for repeated low-signal interruptions, with an implicit materiality threshold.

## Evidence Handling Issues

- [medium] Hypothetical post-concept statements were at risk of being treated as stronger behavioral proof than the transcript supports.
- [medium] A design implication was inferred from a single successful-use context without a contrasting non-use case.
- [medium] A constrained either-or question risked narrowing the evidence about preferred next steps.

## Prompt Adjustments

- decision_rule: In concept-validation interviews, introduce the concept with a neutral description of what appears or happens, without embedding value claims unless the value claim itself is under test.
- followup_trigger_rule: If a participant questions how a judgment is made, ask at least one follow-up to define the minimum credible evidence, comparison, or threshold they would need.
- contrast_rule: After one concrete use case is established, ask for a contrasting non-use or dismissal case before concluding workflow fit or repeat-use conditions.
- followup_trigger_rule: When a participant says they would not act immediately, probe the no-action branch: what would make them monitor, postpone, ignore, or escalate.
- question_priority_rule: Prefer deepening one or two high-signal participant cues over completing lower-value later coverage questions when the missing depth affects trust, thresholds, or action logic.
- evidence_rule: Require synthesis labels to distinguish observed behavior, stated preference, and hypothetical reaction, and prevent stronger conclusion labels when evidence is mostly hypothetical.
- followup_trigger_rule: Use an open question before any self-serve-versus-human or channel-choice framing when exploring what should happen after a complex result.
- stop_rule: Do not stop at coverage complete if at least one unresolved high-signal clue remains about trust threshold, acceptable benchmark, materiality threshold, or anti-escalation boundary.

## Carry-Forward Rules

- CF-001: When a participant asks how a system reached its conclusion, follow up until the acceptable proof standard is concrete.
- CF-002: After a participant describes a likely use moment, collect one contrasting non-use moment before inferring fit or retention.
- CF-003: Probe the no-action path after alerts or recommendations to distinguish monitoring behavior from action intent.
- CF-004: Use open-ended next-step questions before offering channel or follow-up options.
- CF-005: Separate behavioral evidence from hypothetical concept reactions in both questioning and synthesis confidence labels.

## Blocked Feedback

- The facilitator should specifically probe which benchmark for diversification this participant would trust in this financial context. (The underlying interviewing lesson is reusable, but the original phrasing is too tied to a domain-specific analytic construct.)
- The facilitator should ask earlier whether overview-page embedding is better than other retail-banking journey placements. (This is a product-design conclusion about a specific journey, not a generic interviewing rule.)
- The facilitator should probe what kind of follow-up would avoid feeling like sales outreach in this banking setting. (The anti-sales concern is expressed in a specific service context, though the interviewing pattern is reusable.)
