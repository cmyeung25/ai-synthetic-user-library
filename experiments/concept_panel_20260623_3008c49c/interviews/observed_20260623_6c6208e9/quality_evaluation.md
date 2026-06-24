# Facilitator Quality Evaluation

> This audit evaluates a synthetic interview and its artifacts only. Findings are about methodological quality and evidence discipline within the provided simulation, not real-user truth.

Overall verdict: **warn**

## Scores

- neutrality: 3/5
- probing_quality: 4/5
- conversation_naturalness: 4/5
- evidence_discipline: 3/5
- causal_rigor: 4/5
- hypothesis_validation_rigor: 4/5
- synthesis_fidelity: 3/5
- overall: 4/5

## Findings

- [medium] The concept was introduced with benefit-loaded framing: `免費` plus `幫你一眼睇晒整體風險同分散情況` already implies speed and usefulness before the participant reacts. That weakens neutrality in `concept_validation` mode.
- [medium] The final question narrows the response into researcher-supplied options: `喺 app 自己睇明，定係想之後有人再幫你跟進`. The participant still answered well, but the structure can suppress other embedding preferences such as saving, deferring, sharing, or ignoring.
- [medium] `workflow_effect: adds_layer` is not supported by the transcript. The participant explicitly preferred no extra interrupting layer and wanted the feature embedded in the overview or as a small reminder, which points in the opposite direction.
- [medium] The first assumption is marked `supported`, but key parts of that claim rest on hypothetical concept reactions rather than observed repeated behavior. `第一步唔會即刻買賣` and wanting to self-serve first are useful signals, but they do not fully prove how the feature would function in real decisions over time.
- [medium] The report makes product-shaping claims about embedding inside the overview journey, but the interview only covered one month-end checking context. That is a useful fit signal for this persona, not yet a stronger statement about retail-banking journey design more broadly.
- [low] The opening question is mildly compound: it asks both `幾時` and `咩事令你去睇`. It worked here, but separating time anchor from trigger can reduce answer compression.

## Required Improvements

- Rewrite concept introduction to remove benefit-selling language and present the feature more neutrally.
- Replace binary embedding/follow-up questions with an open participant-led probe before offering options.
- Tighten synthesis so every design implication is explicitly bounded to one synthetic persona and every operational claim has direct transcript support.
- Downgrade or qualify assumption verdicts that rely mainly on hypothetical post-concept statements rather than observed behavior.

## Improvement Hints

- Focus next: Ask for one contrasting recent case where the participant did not open the portfolio, to bound when this feature would be ignored.
- Focus next: Probe what exact wording or benchmark would make `一般分散做法` feel helpful rather than preachy or sales-like.
- Focus next: Ask what the participant would do if the app showed a change but they had no intention to act, to separate curiosity from action follow-through.
- Focus next: Test one concrete reminder example and ask what part is worth opening versus dismissing.
- Close gap: Add a participant-facing probe for non-use or dismissal conditions, not only the successful month-end scenario.
- Close gap: Probe current workaround limits more directly: what is hard to see today, what is easy enough already, and what would not justify a new summary card.
- Close gap: For service embedding, ask open-endedly what should happen after a complex alert before forcing channels such as self-serve versus human follow-up.
- Close gap: If benchmarking is important, ask what comparison baseline they would trust: own past allocation, peer norm, bank model, or risk-plan target.
- Prompt change: In `concept_validation`, prohibit concept intros that pre-state value claims like `省時間`, `一眼睇晒`, or `免費` unless price is the object of the test.
- Prompt change: Add a guardrail to prefer open follow-up questions before any either-or framing in participant-facing probes.
- Prompt change: Require synthesis labels to distinguish `observed current behavior`, `stated preference`, and `hypothetical concept reaction` in assumption validation.
- Prompt change: Add a check that any design implication stronger than `for this persona` must cite more than one behavioral context or be downgraded to a tentative experiment hypothesis.
- Turn budget: Current turn budget was sufficient for the required coverage. Keep the same soft/hard limits, but reserve 1-2 extra turns for a contrasting non-use case and one concrete reminder-message probe so embedding and retention claims are less one-sided.
