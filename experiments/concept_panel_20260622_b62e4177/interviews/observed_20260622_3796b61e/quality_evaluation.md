# Facilitator Quality Evaluation

> This audit reviews a single synthetic concept-validation interview. Findings about interview quality are usable, but any product, market, need, POV, or HMW implication should remain strictly persona-bounded and non-generalized.

Overall verdict: **warn**

## Scores

- neutrality: 3/5
- probing_quality: 4/5
- conversation_naturalness: 4/5
- evidence_discipline: 3/5
- causal_rigor: 3/5
- hypothesis_validation_rigor: 3/5
- synthesis_fidelity: 3/5
- overall: 4/5

## Findings

- [medium] The concept was introduced in a solution-loaded way. `exchange_3.facilitator` names a branded-sounding feature (`Portfolio Health Check`) and prepackages the benefits (`整體風險、重疊同集中度`), which steers the participant toward the intended value instead of first testing whether the concept is compelling in their own terms.
- [medium] Several synthesis claims generalize from one synthetic persona to a broader customer segment. Examples include assumptions labeled `supported` such as `很多零售客戶目前是靠碎片化...` and `零售客戶可以理解簡化版 institutional analytics`, which exceed the actual evidence from this single interview.
- [medium] `workflow_effect: replaces_workflow` is not supported by the transcript. The participant described using the proposed tool for checking concentration after market moves or adjustments (`exchange_5.persona`), which suggests augmentation of the current workflow, not replacement.
- [low] `exchange_7.facilitator` is somewhat compound. It asks the participant to sort multiple analysis types across two service modes in one turn (`邊啲分析適合自己喺app直接睇，邊啲一定要有人解釋先有用`). The answer is still usable, but the prompt bundles classification and explanation threshold together.
- [low] The report mostly handles pricing as stated evidence, but other concept-stage outputs such as `first_value_requirement`, `abandonment_triggers`, and parts of `retention_risk` are also hypothetical reactions and should be labeled as such more explicitly to avoid sounding behaviorally proven.
- [low] The interview collected positive value reactions but did not directly probe what would make the concept unhelpful aside from data misuse and weak reminders. That leaves limited disconfirming evidence about concept irrelevance, confusion, or substitution with existing tools.

## Required Improvements

- Make concept introduction more neutral and less benefit-preloaded.
- Constrain synthesis language to one synthetic persona and remove segment-wide claims.
- Remove or soften unsupported product-behavior inferences such as `replaces_workflow`.
- Label hypothetical concept reactions consistently across retention, value, and design implications.
- Add one explicit disconfirmation probe in future concept-validation runs.

## Improvement Hints

- Focus next: Ask what, if anything, would make the participant ignore or distrust the concept even if it is free.
- Focus next: Probe the current workaround's consequence more concretely: what mistakes, delays, or missed decisions come from stitching together banks and MPF manually.
- Focus next: Test one embedding choice at a time: existing portfolio page, alert card, or assisted review flow, instead of inferring the best embedding from a single general question.
- Focus next: Separate willingness to try from willingness to rely on it for an actual allocation change.
- Close gap: Get a participant-facing probe on what the participant would do instead if this feature did not exist.
- Close gap: Ask which external-asset connection method they would actually use first: manual entry, read-only link, or periodic import.
- Close gap: Probe whether educational/retirement goal linkage is genuinely useful or just sounds good in the abstract.
- Close gap: Capture one clearer non-adoption threshold for paid services beyond `more charts is not enough`.
- Prompt change: In concept_validation mode, require a neutral concept script that states the capability without naming the hoped-for insights first.
- Prompt change: Add a rule that at least one disconfirming or non-use question must be asked after initial concept reaction.
- Prompt change: Instruct synthesis to mark every claim as `behavioral`, `stated`, or `hypothetical` and to prohibit segment-level wording from a single interview.
- Prompt change: Add a guardrail that product embedding recommendations must be framed as tentative unless the interview explicitly compares alternatives.
- Turn budget: The current turn budget was sufficient for basic coverage. Keep the same soft limit, but reserve 1 additional turn for a mandatory disconfirmation probe and 1 additional turn when testing embedding alternatives or connection-method variants.
