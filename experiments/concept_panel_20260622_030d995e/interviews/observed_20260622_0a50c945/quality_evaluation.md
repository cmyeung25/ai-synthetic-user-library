# Facilitator Quality Evaluation

> This audit assesses a single synthetic interview only. Any product, pricing, needs, POV, HMW, or segment conclusions should be treated as directional and not as human-user evidence or market validation.

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

- [medium] The concept introduction is somewhat solution-loaded because it pre-bundles the feature scope and benefit: `免費嘅 Portfolio Health Check，幫你一眼睇返戶口、基金同 MPF`. That frames the tool as helpful and complete before the participant reacts, rather than neutrally testing what they would expect or need.
- [medium] `exchange_8` is effectively a double question: it asks both placement (`擺喺邊個位`) and timing (`咩時候出現`) in one turn, plus an anti-sales framing requirement (`唔似叫你買嘢`). The answer covers both, but the question has more than one natural focus.
- [medium] Several synthesis claims extend beyond what one synthetic participant actually evidenced. `retention_risk.workflow_effect = replaces_workflow` is stronger than the transcript supports; the participant said the tool must reduce cross-app checking and surface missed items, but did not clearly say it would replace the current workflow. Similarly, `switching_difficulty = low` is not directly established.
- [medium] The report marks multiple product-shaping assumptions as `supported` from one synthetic persona, including market-facing assumptions about retail customers broadly and embedding strategy. The transcript supports this persona's preference, but not wider segment-level support.
- [medium] The research goal asks where real portfolio-management frictions sit, but the strongest observed friction here is adjacent cash-availability sensemaking rather than portfolio management in a richer investment-behavior sense. The synthesis notes this, but still leans into portfolio-health/product implications without probing whether this participant would ever use deeper portfolio tools beyond liquidity clarity.
- [low] Coverage is marked complete, but `founder_assumption_check` was handled only through placement/tone in `exchange_8`. It did not directly test one important assumption named in the synthesis gap list: whether RM-assisted or hybrid service involvement would feel more appropriate than pure self-serve for more advanced analysis.

## Required Improvements

- Make concept introduction more neutral by removing promised value language from the first concept question.
- Tighten evidence discipline in synthesis: do not label unsupported mechanics such as `replaces_workflow` or `switching_difficulty` as established facts.
- Bound product and segment conclusions to a single synthetic persona; avoid `supported` labels that read as market evidence.
- Use one focus per asked question, especially for embedding/placement probes.
- Add at least one direct probe to distinguish liquidity-management needs from broader portfolio-management needs before shaping feature direction.

## Improvement Hints

- Focus next: Ask whether the participant would view the tool mainly as cash-planning support, investment monitoring, or both, and why.
- Focus next: After concept intro, ask what they would expect to see first before suggesting specific asset types or outcomes.
- Focus next: Probe one concrete advanced feature candidate at a time, such as plain-language explanations, loss vs volatility interpretation, or concentration alerts, to see what actually matters.
- Focus next: Test whether a human-assisted follow-up or RM handoff would feel useful or intrusive once the summary flags an issue.
- Close gap: Directly probe whether deeper portfolio analysis is wanted at all beyond knowing what money is safely usable.
- Close gap: Ask what current action the participant takes, if any, when MPF/fund values move, so the team can separate monitoring from decision support.
- Close gap: Probe service-boundary preferences participant-facing: self-serve only, optional advisor help, or bank contact after a flagged issue.
- Close gap: If pricing remains relevant, ask for one acceptable range or comparison anchor rather than only `low price` and `monthly` statements.
- Prompt change: Revise the concept-validation prompt to ban benefit-loaded phrasing such as `幫你一眼睇返...` in the first concept mention.
- Prompt change: Add a synthesis rule that any segment-level assumption must be tagged `single-persona directional only` unless supported by multiple interviews.
- Prompt change: Require synthesis fields like workflow change, switching difficulty, and evidence strength to map to direct transcript statements rather than analyst inference.
- Prompt change: Have the observer or runtime checker flag multi-focus questions before they are asked, especially placement-plus-timing combinations.
- Turn budget: The current soft/hard turn policy was sufficient for a compact first-pass concept screen, but a rerun should allow 1-2 extra turns to isolate tool framing, domain fit, and service-boundary questions without compressing them into compound prompts.
