# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: Coverage was completed efficiently, but the facilitator accepted several high-signal statements at face value and moved on before probing thresholds, causal priorities, and trust evidence standards. The main improvement area is converting broad concept-validation coverage into deeper decision-grade learning.
- Primary failure mode: Coverage over depth after initial concept fit was established.
- Depth vs coverage: The interview covered all required areas in seven exchanges, but depth was thin in the most decision-relevant areas: what explanation earns trust, what evidence prevents false-alarm dismissal, which friction is most disqualifying, and what concrete output would change behavior.

## Feedback Tags

- [high] missed_threshold_probe: The facilitator captured concerns about clarity, permissions, and noise, but did not ask what exact explanation, permission scope, or alert frequency would cross the participant's acceptability threshold.
- [high] coverage_over_depth: After each broad answer, the facilitator advanced to the next coverage area instead of deepening the most information-rich points.
- [medium] missed_contrast_probe: The participant named multiple possible drop-off causes, but the facilitator did not ask which would matter most if only one problem remained.
- [high] surface_acceptance_of_trust_claim: The facilitator heard resistance to sharing data and requests for understandable calculation, but did not separate whether the main issue was data sensitivity, effort, or lack of transparency.
- [medium] missed_consequence_probe: The facilitator learned that the participant would cross-check alerts elsewhere, but did not ask what proof would allow them to stop cross-checking or act with confidence.

## Missed High-Value Follow-Ups

- [high] What exact explanation would be enough for you to trust the result on first use?
  Trigger: trust_boundary_statement
- [high] What would you need to see to believe the alert is valid enough that you would not need a manual cross-check?
  Trigger: verification_habit
- [high] If only one of those problems remained, which one by itself would be most likely to make you stop using it?
  Trigger: multi-friction_dropoff
- [medium] What would make a notification feel meaningfully important versus just more noise?
  Trigger: timing_preference
- [medium] Even if it were clear and low-permission, in what situation would this still not be useful to you?
  Trigger: positive_concept_reaction

## Likely Misclassified Drivers

- The participant appears privacy-sensitive about external data access. -> The stronger driver may be a mix of control preservation, setup burden, and desire for analysis-only boundaries, not privacy alone.
- The participant wants quick, simple summaries. -> The deeper need may be confidence-efficient review: fast comprehension that still feels auditable before action.
- The participant would use the feature if it saves time. -> Time saving may be secondary to reducing uncertainty without surrendering control.

## Evidence Handling Issues

- [high] Hypothetical concept reactions were sometimes treated too close to established future behavior in downstream synthesis.
- [medium] A workflow implication was inferred more strongly than the transcript supported.
- [medium] Several synthesized implications bundled direct quotes and facilitator inference without clearly separating them.

## Prompt Adjustments

- followup_trigger_rule: When a participant says a concept is useful only if it is 'clear,' 'fast,' 'not too much,' or 'not too frequent,' ask one threshold question that defines the minimum acceptable standard before moving on.
- followup_trigger_rule: When a participant says they would verify, compare, or double-check before acting, ask what evidence would be sufficient to reduce that extra verification step.
- contrast_rule: If a participant names three or more possible frictions or drop-off causes, ask them to choose the single biggest one and explain why.
- evidence_rule: In concept-validation synthesis, label each conclusion as one of: observed current behavior, stated preference, or hypothetical future reaction.
- question_priority_rule: After an initial positive concept reaction, prioritize one disconfirming non-use probe before covering additional checklist topics.
- decision_rule: Do not stop at full topical coverage if the participant has introduced an unprobed trust threshold, evidence standard, or prioritized friction that could materially change interpretation.

## Carry-Forward Rules

- CF-001: When participants describe a trust boundary, ask what specific explanation or boundary marker would make first-use trust sufficient.
- CF-002: When participants say they would cross-check before acting, probe for the minimum proof needed to avoid that cross-check.
- CF-003: Force prioritization when multiple adoption blockers are named; do not record a flat list without ranking.
- CF-004: Separate convenience claims from the underlying value being protected by convenience, such as control, confidence, or reduced cognitive load.

## Blocked Feedback

- The interview did not test which specific analytics outputs within the proposed portfolio tool would materially change real decisions. (This is anchored to the specific product scope and named capability set rather than a purely generic interviewing pattern.)
- The interview did not sufficiently probe what presentation would feel advisory versus sales-led within the retail banking journey. (This is tied to the project's service-embedding context and anti-selling requirement.)
- The synthesis included specific design and experiment implications for this portfolio feature that went beyond one participant's evidence. (The design implications are product-shaped and not safe as facilitator-core priors.)
