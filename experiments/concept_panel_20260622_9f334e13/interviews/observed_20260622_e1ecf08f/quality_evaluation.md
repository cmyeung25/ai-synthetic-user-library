# Facilitator Quality Evaluation

> This audit reviews a single synthetic concept-validation interview. Any support, risk, pricing, trust, or design implication should be treated as persona-specific simulated evidence, not market proof or a causal product conclusion.

Overall verdict: **warn**

## Scores

- neutrality: 4/5
- probing_quality: 3/5
- conversation_naturalness: 4/5
- evidence_discipline: 2/5
- causal_rigor: 4/5
- hypothesis_validation_rigor: 3/5
- synthesis_fidelity: 2/5
- overall: 3/5

## Findings

- [high] The synthesis makes product-shaping claims stronger than the evidence allows from one synthetic concept interview. In particular, `retention_risk.workflow_effect: "replaces_workflow"` is not supported by the transcript; the participant only said they might check it before a future buy, not that it would replace their existing process.
- [medium] Several assumption verdicts are too assertive for single-person stated intent evidence. `assumption_validation` marks premium willingness as `supported`, but `exchange_7.persona` is only conditional stated willingness, not behavioural proof. The report should preserve that this is hypothetical and persona-specific.
- [medium] The report partially blurs behavioural evidence and hypothetical concept reactions. Trust, retention, payment, and external aggregation claims are largely derived from hypothetical answers in `exchange_4` to `exchange_8`, but some synthesis bullets read like validated product truths rather than stated conditions.
- [medium] `retention_repeat_use` is marked covered, but the spoken probe only tests immediate reasons to reuse after first exposure. It does not cleanly distinguish curiosity, first trial, ongoing month-two retention, or repeat behaviour over time, which the concept-validation rubric explicitly asks to keep distinct.
- [low] `exchange_2.facilitator` mixes a recalled-event anchor ('嗰晚') with a generalized process question ('通常點樣'). This is not a major flaw, but it weakens the distinction between what happened in the specific incident and the participant's general heuristic.
- [medium] The research goal is about whether analytics improves trust, understanding, action willingness, and asset retention for Hong Kong retail or semi-retail bank customers. The interview captured stated trust and understanding conditions, but did not produce direct participant evidence on asset retention or actual changed action beyond possible future checking.
- [medium] The concept report does preserve some weak evidence, but it still frames broad founder assumptions as if they were all assessed adequately. Some assumptions, such as trust gains from institutional analytics delivery and willingness to share external data, remain conditional and only lightly tested with one persona.

## Required Improvements

- Bound synthesis claims to one synthetic persona and explicitly mark hypothetical concept reactions versus observed current behaviour.
- Remove or weaken unsupported product conclusions such as `replaces_workflow` and strong `supported` payment/adoption judgments.
- Add a distinct repeat-use or month-two retention probe rather than treating first-use value as sufficient retention evidence.
- Probe bank-specific asset-retention or future-buy-location effects directly if the research goal includes asset retention.
- Tighten event reconstruction questions so specific incident evidence is not blended with general routine too early.

## Improvement Hints

- Focus next: Ask what the participant did the next day or next purchase after feeling overlap risk, so action impact is grounded in observed behaviour.
- Focus next: After concept intro, ask separately: would they try it once, what would make them use it again a month later, and what would make them stop after one use.
- Focus next: Probe whether this feature would change where they keep assets or execute future investments, not just whether they like the analysis.
- Focus next: Test trust with a concrete mock output and ask what exact line or screen would make it feel analytical versus sales-led.
- Close gap: Get a participant-facing probe on actual or likely asset-retention behaviour: keeping assets in-bank, moving assets out, or consolidating elsewhere.
- Close gap: Separate first-use curiosity from sustained repeat use with a dedicated long-term use question.
- Close gap: If payment matters, force a bounded tradeoff question against the current workaround or an alternative tool, while still keeping it hypothetical-labeled.
- Close gap: For external account linking, probe setup friction and privacy boundaries as separate conditions rather than one combined acceptance question.
- Prompt change: Require the synthesis layer to tag every claim as `observed`, `stated`, or `hypothetical` and forbid upgrading stated intent into behavioural proof.
- Prompt change: In concept-validation mode, add an explicit prompt check that month-two retention must be evidenced separately from first reaction or first-use value.
- Prompt change: Add a guardrail that product-shaping outputs, pricing implications, and assumption verdicts must stay persona-bounded in a single synthetic interview.
- Prompt change: Ask the facilitator to keep event reconstruction fully episode-specific before generalizing to habitual behaviour.
- Turn budget: The current soft/hard turn policy is sufficient for a short concept screen, but one or two extra turns should be reserved specifically for long-term repeat use and bank-retention impact before declaring coverage complete.
