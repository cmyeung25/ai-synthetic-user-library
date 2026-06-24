# Facilitator Quality Evaluation

> This audit evaluates a single synthetic concept-validation interview. Any needs, POVs, HMWs, product implications, or confidence about Hong Kong retail-banking users should remain provisional until validated with multiple real participant interviews.

Overall verdict: **warn**

## Scores

- neutrality: 3/5
- probing_quality: 4/5
- conversation_naturalness: 4/5
- evidence_discipline: 2/5
- causal_rigor: 3/5
- hypothesis_validation_rigor: 3/5
- synthesis_fidelity: 2/5
- overall: 3/5

## Findings

- [medium] The concept introduction is somewhat solution-loaded and compound. It bundles `免費`, a named solution, and three promised outputs in one turn, which can steer value selection toward researcher-supplied components rather than participant-led unmet needs.
- [medium] Several key product implications are derived from hypothetical reactions rather than observed behavior. Action follow-through, trust threshold, timing, and repeat use are all based on imagined use of the proposed feature, not on an actual prior use of a similar tool.
- [high] The synthesis makes product-shaping claims that exceed the evidence from one synthetic interview. `workflow_effect: replaces_workflow`, `highest value use case`, and multiple `supported` assumption statuses read stronger than the transcript warrants.
- [medium] Some synthesis sections rest on valid refs but still blur the line between what was said and what was inferred. For example, `first_use_success` and `abandonment_triggers` synthesize design rules from scattered hypothetical statements without clearly marking them as inference.
- [medium] Although required coverage is marked complete, the interview did not distinctly separate curiosity, trial, payment, and month-two retention. Retention was asked, pricing was not tested, and first-try willingness was not isolated from general usefulness.
- [medium] The interview captured the disruption source well, but evidence about changed actions inside the banking journey is thinner. The synthesis moves toward service embedding and customer-journey design without directly probing what the participant would do inside the bank app versus outside it beyond timing preferences.

## Required Improvements

- Reduce concept selling in the intro by removing bundled benefits and testing narrower prompts.
- Mark hypothetical concept reactions as hypothetical throughout synthesis instead of treating them as behavioral validation.
- Downgrade or remove overstrong synthesis claims such as workflow replacement and broad assumption support from a single synthetic interview.
- Add participant-facing probes that separate first-use curiosity, trust-to-act, repeat use, and willingness to pay.
- Probe concrete bank-journey actions after seeing the concept so service-embedding recommendations are based on changed actions, not just stated preferences.

## Improvement Hints

- Focus next: Ask for a concrete past case where the participant received any investment alert, summary, or advisor prompt and what they actually did next.
- Focus next: After concept exposure, ask what exact screen or action they would take inside the bank journey: rebalance, defer, note it, or contact someone.
- Focus next: Test first-use willingness separately from ongoing retention: what would make them open it once versus keep relying on it monthly.
- Focus next: Probe whether they would trust the bank to aggregate all holdings, including external assets, before inferring full-portfolio adoption.
- Close gap: Add a direct probe on trial behavior: 'What would make you tap into this the first time instead of ignoring it?'
- Close gap: Add a direct probe on payment distinct from usefulness: 'If this stopped being free, what if anything would still feel worth paying for?'
- Close gap: Add a direct probe on setup/privacy boundaries if cross-account aggregation is part of the concept.
- Close gap: Add a direct probe on assisted-service boundary: when would they want RM/help instead of self-serve guidance?
- Prompt change: In `concept_validation`, instruct the facilitator to avoid packaging multiple promised benefits in the first concept turn.
- Prompt change: Require synthesis to tag each claim as `observed_behavior`, `stated_preference`, or `analyst_inference`.
- Prompt change: Add a guardrail that broad design implications and assumption statuses must be phrased as persona-specific when based on one synthetic interview.
- Prompt change: Encourage one follow-up on concrete in-app next action before closing whenever service embedding is a research goal.
- Turn budget: The current soft/hard turn policy is broadly sufficient for one persona, but reserve 1-2 additional turns for distinct probes on trial behavior, payment, and exact in-app next action before declaring concept-validation coverage complete.
