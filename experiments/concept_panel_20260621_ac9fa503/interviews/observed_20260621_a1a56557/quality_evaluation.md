# Facilitator Quality Evaluation

> This audit evaluates methodological quality of a single synthetic interview and its write-up. Any product, pricing, retention, or design implication should remain bounded to this one synthetic persona unless corroborated by additional interviews.

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

- [medium] Coverage marks `payment_conditions` and `retention_repeat_use` as covered, but the transcript only captures stated hypothetical conditions, not buyer process, budget behavior, or real repeat-use evidence. The synthesis correctly flags some of this as stated/unknown, but coverage completeness overstates what was actually learned.
- [medium] Some synthesis claims exceed the narrow evidence. `workflow_effect: replaces_workflow` is not supported; the participant described a tool that could assist pre-research scoping, not replace their notes workflow. `research gatekeeper` and similar framing in `key_insights` is plausible but interpretive rather than directly evidenced.
- [medium] The interview tests fit around disruption sources and abstract value boundaries, but it does not probe actual changed actions in the participant's workflow after using such a tool. That leaves adoption fit inferred from intent statements rather than workflow change evidence.
- [low] The concept question bundles multiple possible jobs: interviewing synthetic users, testing assumptions, and testing messaging. The participant handled it well, but the prompt still contains more than one evaluative object.
- [low] The payment probe asks what error or workload reduction would justify paying, but never isolates pricing, trial expectations, or procurement mechanics. The report preserves this as unknown in part, yet still treats payment conditions as covered.

## Required Improvements

- Do not mark payment or retention fully covered when evidence is only hypothetical; distinguish behavioural proof from stated intent in coverage logic and reporting.
- Tighten synthesis to avoid replacement or workflow-effect claims unless the transcript explicitly shows changed actions or displaced steps.
- Add at least one action-change probe and one concrete commercial/procurement probe in concept-validation runs before closing.

## Improvement Hints

- Focus next: Ask the participant to walk through the same recent brief and say exactly what they would do differently, earlier, or not do at all if this platform were available.
- Focus next: Ask for a concrete comparable tool decision: who approved it, what budget line it came from, and what minimum pilot evidence was needed.
- Focus next: Probe required output format and evidence trace directly: what deliverable would make the synthetic output actionable versus unsafe to circulate.
- Close gap: Add a participant-facing probe for current workaround limits, not just the existence of a workaround, by asking where their notes process fails or becomes too slow.
- Close gap: Add a direct trial probe distinct from payment: what would make them try it once, with what input, and what would count as success.
- Close gap: Add a direct retention probe tied to workflow recurrence and artifacts, not only a generic 'next month' condition.
- Close gap: If reporting pricing or trust conclusions, collect explicit participant statements on setup burden, privacy boundary, and acceptable proof format.
- Prompt change: Change coverage rules so `payment_conditions` requires either a concrete purchase-process answer or is tagged `stated_only`.
- Prompt change: Change coverage rules so `retention_repeat_use` requires either prior analogous repeat behavior or an explicit hypothetical label in both coverage and synthesis.
- Prompt change: Prompt the facilitator to ask one `what changes in your workflow` question after positive concept reaction and before closure.
- Prompt change: In concept introduction, describe one primary use first and hold messaging-testing or assumption-testing as follow-up variants instead of combining them in a single sentence.
- Turn budget: The current 7-turn interview is close but slightly tight for concept validation with buyer-fit goals. Keep the soft limit flexible and allow 1-2 extra turns when payment, workflow change, or output-format evidence is still only hypothetical.
