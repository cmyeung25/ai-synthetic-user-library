# Facilitator Quality Evaluation

> This audit evaluates a single synthetic interview and its associated artifacts. Judgments about rigor, evidence strength, and design implications are limited to this simulated case and should not be treated as market-level validation.

Overall verdict: **warn**

## Scores

- neutrality: 3/5
- probing_quality: 4/5
- conversation_naturalness: 4/5
- evidence_discipline: 4/5
- causal_rigor: 4/5
- hypothesis_validation_rigor: 4/5
- synthesis_fidelity: 3/5
- overall: 4/5

## Findings

- [medium] The concept introduction is mildly solution-loaded and benefit-framed. It names a `免費` feature and says it would `幫你整體睇風險同集中情況`, which preloads usefulness instead of introducing the concept more neutrally.
- [medium] The repeat-use question presumes the feature will become a regular habit: `如果呢個功能要變成你會定期用嘅一部分`. That frames continued use as the default instead of first testing whether it deserves any reuse at all.
- [medium] Several product implications and the `workflow_effect` field go beyond what one synthetic, mostly hypothetical concept interview can support. For example, `adds_layer` and repeated `This means the product should...` claims treat stated preferences as stronger design proof than the transcript warrants.
- [medium] The research goal asked which Aladdin-based analytics functions would materially help in real decisions, but the participant-facing probes stayed at a generic `Portfolio Health Check` level. The interview surfaced broad needs around concentration, risk drift, explanation, and alert timing, but not which specific analytic outputs would change a real retail-banking decision.
- [low] `action_followthrough` and retention conclusions rely on hypothetical responses rather than observed concept use. The synthesis usually notes this, but some downstream insights read more definitive than the evidence type supports.

## Required Improvements

- Rewrite concept introduction prompts to remove embedded benefit framing and sales-adjacent assumptions.
- Separate `would you use it again?` from `when should it appear?` so repeat-use evidence is not forced by the question.
- Narrow synthesis claims to persona-level, hypothetical evidence and avoid treating one synthetic interview as design proof.
- Add participant-facing probes on specific analytics outputs tied to actual decision moments, not only generic health-check reactions.

## Improvement Hints

- Focus next: Probe one recent portfolio review where the participant considered but did not make a change, then test which specific analytics output would have changed that decision.
- Focus next: Ask the participant to react to 2-3 concrete output types separately, such as concentration drift, risk-profile mismatch, drawdown attribution, or cash-flow impact.
- Focus next: Test reuse neutrally: whether they would reopen the feature at all, what would trigger that, and what would make them ignore it.
- Close gap: Add direct probes for which exact analytic explanation is missing today when they inspect holdings after market volatility.
- Close gap: Test whether explanation of `why this alert appeared` is enough on its own, or whether they also need benchmark, trend, or action-threshold context.
- Close gap: Probe service embedding with a non-sales RM or advisory touchpoint only if relevant, since the current interview leaves cross-channel embedding untested.
- Prompt change: In concept-validation mode, forbid concept intros that include built-in value claims like `help you see` unless quoted from the participant.
- Prompt change: Require a neutral reuse sequence: `would use again?` before `when/how should it appear?`.
- Prompt change: Constrain synthesis templates so design implications are tagged `tentative`, `stated preference`, or `observed behaviour` explicitly.
- Prompt change: For this research goal, require at least one probe that maps a named analytic function to a concrete decision or non-decision.
- Turn budget: The current turn budget was sufficient for baseline concept coverage, but the goal is broader than the achieved evidence. Keep the same soft limit only if a follow-up run is dedicated to specific analytics-function testing; otherwise widen the budget slightly to allow concrete output-by-output probing without rushing closure.
