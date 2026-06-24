# Facilitator Quality Evaluation

> This audit evaluates methodological quality on a single synthetic concept-validation interview. Any findings about product direction or customer behaviour should be treated as method feedback, not market evidence.

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

- [high] Several synthesis claims go beyond the evidence by converting one persona's hypothetical concept reactions into product-shaping conclusions. `workflow_effect` is stated as `replaces_workflow`, but the participant never said they would replace their current method; in `exchange_6.persona` they explicitly say they would still re-check bank information and delay action. Likewise, key-insight phrasing such as `真正缺口` and `最有潛力嘅輸出` overstates certainty from one synthetic interview.
- [medium] The concept introduction is somewhat solution-loaded. In `exchange_4.facilitator`, the feature is framed as `免費`, `簡單方式`, and explicitly names benefits and dimensions (`整體風險、集中度同持倉分布`) before the participant states what kind of help would matter most. That risks steering toward acceptance of the supplied frame.
- [medium] The session gathers strong signals about checking behaviour and trust boundaries, but not actual changed investment actions. The research goal asks which analytics functions would materially help in real decisions and how to embed them in journeys. Here, action impact remains hypothetical: in `exchange_6.persona` the participant says they would not trade immediately and would first verify or postpone. Claims about materially helping decisions should therefore stay limited to 'decision orientation' or 'triage support,' not decision change.
- [medium] Some supporting evidence mixes observed behaviour with hypothetical concept reaction without clearly separating them. For example, `problem_evidence.supporting_quotes` includes `exchange_4.persona`, which is a reaction to a proposed concept rather than evidence of the existing problem in real behaviour.
- [medium] Repeat-use conclusions are based on a single hypothetical prompt rather than behavioural evidence. `exchange_7` is useful for stated conditions, but it does not validate retention, month-two use, or continued habit formation.
- [low] The trace classifies some questions imprecisely. `exchange_5` is tagged toward `hypothesis_condition` although no hypothesis is under test, and `exchange_6`/`exchange_7` are hypothetical action and reuse questions rather than evidence of observed consequences. This did not contaminate participant evidence, but it weakens planning clarity.

## Required Improvements

- Separate observed current behaviour evidence from hypothetical concept reaction in both trace labels and synthesis claims.
- Reduce solution-loading in the concept introduction; remove built-in value cues like `免費` and `簡單` unless those attributes are the explicit test variable.
- Do not infer workflow replacement, strongest-value output format, or material decision impact from one hypothetical synthetic interview without a recalled action-comparison case.
- Add one participant-facing probe on a real prior decision or non-decision to anchor whether the concept would change action rather than just improve understanding.

## Improvement Hints

- Focus next: Ask for one recalled instance where the participant actually changed, delayed, or chose not to change holdings after noticing something concerning.
- Focus next: After the recalled case is established, ask how a health-check style summary would or would not have changed that exact step.
- Focus next: Test alternative output formats separately: summary card, alert, report, RM-assisted view, without presuming one is best.
- Focus next: Probe what the participant currently does when markets are calm, not only during volatility, to see whether the concept has any non-event-driven role.
- Close gap: Directly probe a real decision-followthrough case instead of only hypothetical next-step intent.
- Close gap: Probe whether the participant uses any non-bank sources or people before acting, so journey embedding is based on the full current path.
- Close gap: If pricing or payment matters to the concept, ask it explicitly; otherwise omit pricing sections from the report rather than implying relevance.
- Close gap: Distinguish stated reuse conditions from evidence of likely month-two retention and keep both labeled separately.
- Prompt change: In concept-validation mode, require the facilitator to mark each answer as observed behaviour, recalled event, or hypothetical reaction, and prevent synthesis from merging them.
- Prompt change: Tighten synthesis rules so product implications must be phrased as persona-bounded hypotheses unless supported by an observed action-comparison case.
- Prompt change: Revise the concept-intro prompt to avoid value-laden descriptors and to allow variant testing after an initial neutral reaction.
- Prompt change: Add a report check that blocks terms like `replace`, `highest value`, `real decision impact`, or `must` unless backed by transcript evidence type rules.
- Turn budget: The current turn budget was sufficient for baseline coverage, but one or two additional turns should be reserved in reruns for a recalled decision-followthrough case and a format-comparison probe. No major expansion is needed beyond that.
