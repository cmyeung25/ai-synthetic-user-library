# Facilitator Quality Evaluation

> This audit evaluates a single synthetic interview and its artifacts. Findings assess method and evidence discipline within the simulation only, not real-user truth or market validity.

Overall verdict: **warn**

## Scores

- neutrality: 4/5
- probing_quality: 4/5
- conversation_naturalness: 4/5
- evidence_discipline: 3/5
- causal_rigor: 4/5
- hypothesis_validation_rigor: 4/5
- synthesis_fidelity: 3/5
- overall: 4/5

## Findings

- [medium] Several synthesis outputs turn hypothetical concept reactions into stronger product implications than the transcript supports. `service_embedding` and `retention` are explored only through imagined future use, but `key_insights` and `next_experiment` sometimes read as if behavior is established rather than conjectural.
- [medium] `retention_risk.workflow_effect` is stated as `adds_layer`, but the participant never said the feature would add a layer rather than replace manual stitching. The closer evidence is that they want quicker synthesis and fewer steps, and would still cross-check alerts before acting.
- [medium] The research goal asks which Aladdin-based analytics functions would materially help in real decisions and how they should embed into retail journeys without generic product selling. The interview validated a generic `Portfolio Health Check`, but did not isolate which specific analytics outputs matter beyond broad risk/distribution/change summaries, nor what concrete journey handoff would feel useful versus salesy.
- [low] Curiosity, trial, and repeat-use were mostly kept distinct, but payment was handled only in synthesis rather than participant-facing probing. That is acceptable because the concept was framed as free, yet the report should be careful not to imply any willingness-to-pay learning occurred.
- [low] Most references are valid, but some synthesis bullets compress multiple claims into paraphrases without preserving which part is observed versus inferred. For example, the first `key_insights` bullet blends observed timing with an inferred usage trigger threshold.

## Required Improvements

- Tighten synthesis so hypothetical concept reactions are not presented as behaviorally established product truths.
- Probe specific analytics outputs and anti-sales embedding conditions more directly; the current interview validates a broad concept, not which Aladdin functions materially help.
- Constrain report fields like `workflow_effect`, design implications, and experiment framing to what one synthetic persona actually evidenced.

## Improvement Hints

- Focus next: Ask which one specific summary would be most useful on a real month-end check: concentration, unusual drawdown, asset allocation drift, or cash-flow impact.
- Focus next: Ask for one concrete example of what would feel helpful versus what would feel like the bank trying to sell a product.
- Focus next: Ask what evidence or explanation would make an alert trustworthy enough to save them a manual cross-check.
- Focus next: Test whether incomplete coverage of outside assets still has value, or makes the summary unusable.
- Close gap: Add a participant-facing probe on which exact analytics output changes a real decision, not just whether a generic health check sounds useful.
- Close gap: Add a participant-facing probe on journey embedding: in-app dashboard, statement moment, push alert, RM follow-up, or self-serve drill-down, and why.
- Close gap: Add a participant-facing disconfirming probe: when would this feature still not help even if it were clear and low-permission?
- Close gap: If product-selling avoidance is central, ask directly what wording or CTA would make the experience feel promotional rather than advisory.
- Prompt change: In concept-validation mode, require the synthesis to tag each conclusion as `observed current behavior`, `stated preference`, or `hypothetical future reaction`.
- Prompt change: Add an observer rule that blocks broad product-shaping implications unless they cite a direct participant statement about that specific function or journey moment.
- Prompt change: Encourage one short disconfirming probe after positive concept reaction to test non-use conditions beyond permissions and noise.
- Prompt change: For domain-specific goals, require at least one question that compares candidate functional outputs rather than validating only a generic umbrella concept.
- Turn budget: The current turn budget was sufficient for baseline concept coverage, but it is too tight for function-level prioritization and anti-sales embedding detail. Widen the soft budget by 2-3 exchanges in reruns so one or two specific analytics outputs can be tested individually and one disconfirming probe can be added.
