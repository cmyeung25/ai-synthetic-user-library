# Facilitator Quality Evaluation

> This audit evaluates a single synthetic concept-validation interview. Any apparent support is limited to participant-facing quality and evidence handling within this simulated case, not real-market truth or cross-persona product direction.

Overall verdict: **warn**

## Scores

- neutrality: 3/5
- probing_quality: 4/5
- conversation_naturalness: 4/5
- evidence_discipline: 2/5
- causal_rigor: 3/5
- hypothesis_validation_rigor: 4/5
- synthesis_fidelity: 2/5
- overall: 3/5

## Findings

- [high] The synthesis promotes product-shaping conclusions beyond what one synthetic concept interview can support. Claims such as a likely default journey pattern and prioritized retail blind spots are treated as supported, even though they come from a single persona reacting to a hypothetical concept.
- [medium] Several synthesis claims are not tightly grounded in the cited transcript. `replaces_workflow` in `retention_risk.workflow_effect` is stronger than the evidence, which only shows a faster aid layered into an existing review habit. The quote `自己以為分散咗，但原來風險都係堆埋一邊` is a hypothetical first-use desire, not direct problem evidence from observed current behavior.
- [medium] The final channel-placement question is partially forced choice. `exchange_8.facilitator` asks the participant to choose between app self-serve and RM follow-up, which can suppress other embedding options or mixed workflows.
- [medium] The concept is introduced fairly neutrally, but the framing still presupposes usefulness by naming a `Portfolio Health Check` that `會用簡單方法幫你睇返成個組合`. That subtly packages the concept as helpful rather than letting value emerge entirely from the participant.
- [medium] The report includes pricing implications even though pricing was not behaviorally explored. It correctly notes `unknown`, but the presence of a pricing section risks overstating what this interview can say about willingness to pay.
- [medium] The research goal asks which Aladdin-based analytics functions would materially help real decisions and how each should be embedded. This interview mostly validates one narrow use case: concentration and cash-coordination checks. It does not yet test other candidate functions, so the synthesis should not imply broader domain-fit for `Aladdin-type analytics` generally.

## Required Improvements

- Tighten synthesis discipline: distinguish observed current behavior from hypothetical concept reaction, and remove or downgrade claims that imply broader product direction from one synthetic interview.
- Replace forced-choice embedding probes with open-first questions before narrowing to channels or support models.
- Limit assumption verdicts to persona-specific signals; do not mark cross-persona journey or feature-priority assumptions as `supported` without comparative evidence.
- Keep non-assessed areas such as pricing and wider analytics scope clearly labeled as untested rather than partially validated.

## Improvement Hints

- Focus next: Ask the participant to compare this concept against their current screenshot-and-revisit method in a specific recent case.
- Focus next: Probe one concrete moment when a concentration signal would have changed what they actually did, not just what they think they would do.
- Focus next: Test at least one alternative analytic output beyond concentration/cash coordination to learn relative value, not just absolute concept appeal.
- Focus next: Ask what would make them ignore the feature even if it appeared at the right moment.
- Close gap: Get a participant-facing probe on whether they would trust analysis that includes external assets or only bank-held assets.
- Close gap: Probe what exact output format they can act on fastest: alert, summary card, or dashboard.
- Close gap: Ask what specific follow-up they would expect after seeing a warning and what would feel too sales-led.
- Close gap: If pricing is needed, ask separately about payment behavior and tradeoffs rather than inferring from the word `free` in the concept intro.
- Prompt change: In concept-validation mode, instruct the facilitator to keep concept descriptions benefit-neutral and avoid labels that imply health, optimization, or smartness.
- Prompt change: Add a synthesis guardrail: hypothetical reactions cannot be used as current problem evidence or workflow-replacement evidence.
- Prompt change: Require open-first service-embedding questions before any either-or channel prompt.
- Prompt change: Add a report rule that broad design outputs, feature priority, POV, or HMW statements must be explicitly bounded to `single synthetic persona` and not marked validated.
- Turn budget: The current turn budget was sufficient for this interview. Keep the soft/hard limits as-is, but spend one extra turn only if needed for open-format/channel probing or comparative concept testing; the bigger issue is prompt discipline, not interview length.
