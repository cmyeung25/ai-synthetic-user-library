# Facilitator Quality Evaluation

> This audit reviews a single synthetic concept-validation interview. Any product, retention, or journey-design implication should be treated as directional only until checked with multiple human interviews or behavioral tests.

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

- [medium] The concept was introduced with built-in positive framing and a binary usefulness test instead of a more neutral reaction probe. `exchange_3.facilitator` bundles '免費', '整合持倉', and '用簡單方式解釋風險', then asks '有冇用', which nudges evaluation toward the researcher-supplied benefits.
- [medium] `exchange_5.facilitator` presupposes a diagnosis ('你而家太集中') and offers the preferred comparison frame ('唔郁同分散少少個分別') before asking about next action. That tests a polished scenario, not the participant's own threshold for acting.
- [medium] The participant expressed skepticism in `exchange_3.persona` ('包裝到好似好叻，其實只係叫我自己再研究一次'), but the facilitator did not isolate a concrete case where the feature would not help or would be ignored. That leaves weak evidence on failure modes and false positives.
- [high] Several synthesis claims exceed what this single hypothetical concept interview established. `retention_risk.workflow_effect` says 'replaces_workflow', but the participant described supplementing the current habit, not replacing it (`exchange_5.persona`, `exchange_6.persona`). `assumption_validation[2]` claims the 'highest-value use case' is moment-based rather than institutional detail, which is broader than this one persona can support. `next_experiment` and multiple 'supported' assumption labels are useful planning outputs, but they should be framed as tentative and persona-specific, not validated conclusions.
- [medium] The research goal asks how analytics should be embedded into retail journeys without generic product selling, but the interview only lightly touched timing and placement. The synthesis moves toward broad embedding guidance from `exchange_7`, without testing whether the same surface would feel like selling, advice, or noise in different moments.

## Required Improvements

- Rewrite concept-introduction questions to remove built-in value cues and avoid binary 'useful or not' framing.
- Add at least one explicit disconfirmation probe asking when the concept would not help or would be ignored.
- Separate open reaction, trust boundary, action threshold, and embedding questions so each spoken question has one conversational focus.
- Tighten synthesis so every strong claim is persona-bounded and directly traceable to transcript evidence; remove unsupported claims like 'replaces_workflow'.
- Expand journey-fit probing beyond placement to test when the same feature feels supportive versus promotional.

## Improvement Hints

- Focus next: Ask for a concrete moment when a summary card would not change anything the participant does.
- Focus next: Probe the minimum action threshold: what exact change, risk, or cash conflict would make them act versus defer.
- Focus next: Test whether the same insight is preferred on the portfolio home, in a reminder, or via a human advisor, and which feels too sales-like.
- Focus next: Ask what current manual step the feature would actually remove, if any, versus merely add another screen to check.
- Close gap: Add a direct participant-facing probe on non-adoption or abandonment in a realistic recent context, not only generic repeat-use conditions.
- Close gap: Probe current workaround pain more concretely: what is slow, uncertain, or easy to miss in the screenshot-and-recheck flow.
- Close gap: Test trust boundaries on data source and explanation depth separately: internal holdings only, external holdings, plain-language summary, scenario comparison.
- Close gap: If pricing or retention are in scope for the report, ask them separately and label all answers as hypothetical concept reactions, not behavioural proof.
- Prompt change: In concept validation mode, require the first concept question to be neutral and prohibit stacking value adjectives such as 'free', 'simple', and 'integrated' in one sentence.
- Prompt change: Add an observer rule that any participant skepticism must trigger one counterexample or failure-case probe before closure.
- Prompt change: Add a synthesis guardrail that product-shaping outputs must be explicitly labeled 'single synthetic persona, directional only' and that unsupported transformation claims are disallowed.
- Prompt change: Encourage facilitator prompts that ask 'what would make you ignore this?' before 'where should this live in the app?'.
- Turn budget: The current soft/hard turn policy is roughly sufficient for a short concept screen, but one or two extra turns should be reserved for disconfirmation and journey-fit contrast probes before closure.
