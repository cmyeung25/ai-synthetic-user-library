# Facilitator Quality Evaluation

> This audit reviews a single synthetic interview and its artifacts for methodological quality. It does not convert the interview into human market evidence, and any product implications should remain bounded to simulated evidence until calibrated against real participant data.

Overall verdict: **warn**

## Scores

- neutrality: 4/5
- probing_quality: 3/5
- conversation_naturalness: 4/5
- evidence_discipline: 2/5
- causal_rigor: 3/5
- hypothesis_validation_rigor: 3/5
- synthesis_fidelity: 2/5
- overall: 3/5

## Findings

- [high] The interview never cleanly established the actual changed action in scope, sequence, priority, or go/no-go for the recent onboarding decision. In `exchange_3.persona`, the participant says she was 'initially inclined' toward a small change and fast validation, but there is no direct follow-up confirming what was actually decided or changed. This weakens domain-fit claims that rely on real changed actions rather than only the disruption source or decision framing.
- [medium] The facilitator asked two very similar defensible-vs-uncertain questions. `exchange_5.facilitator` and `exchange_7.facilitator` both ask what she could state confidently versus what she still held in reserve. The second question produced some clarification, but the duplication suggests the prompt or coverage tracker is allowing redundant probes.
- [high] The synthesis makes several claims that outrun the transcript. Examples: `pricing_signal.free_trial_need` and payment logic are inferred without any pricing or budget question in the transcript; `trust_boundary.accepted_data_access` reframes evidence alignment as accepted product data access, which the participant did not actually endorse; and `retention_risk.continuation_reasons` includes stable replacement-like value claims not directly asked in participant-facing form.
- [medium] `service_embedding` is marked covered, but the participant was not directly asked where this tool would sit in her team workflow, who would trigger it, or what artifact it would replace or augment. Current evidence shows trust and validation behavior, not a concrete embedding pattern.
- [medium] The concept report preserves weak evidence in some places, but it still drifts into product-shaping outputs from a single synthetic interview, especially in `next_experiment`, pricing implications, and broad adoption framing. The transcript supports an early-framing use case for this persona, not broader product direction confidence.

## Required Improvements

- Add an explicit pre-concept question that confirms the actual scope, sequence, priority, or go/no-go change made in the recalled case.
- Tighten synthesis rules so unsupported pricing, buyer, data-access, and retention claims are labeled as open hypotheses or removed.
- Require a direct workflow-embedding probe before marking `service_embedding` covered.
- Reduce redundant defensible-vs-uncertain questioning by improving coverage-state memory and follow-up selection.

## Improvement Hints

- Focus next: Ask what she actually changed in that onboarding case: what got approved, deferred, cut, or sequenced differently.
- Focus next: Ask where this tool would slot into her real workflow: before analytics review, before stakeholder alignment, before research scheduling, or somewhere else.
- Focus next: Ask what concrete artifact or meeting output would become easier: PRD framing, research brief, stakeholder rationale, experiment plan, or none.
- Focus next: Ask for a contrast case where she could make a fast priority call without needing synthetic framing, to test domain fit against adjacent-only pain.
- Close gap: Probe `recent_behaviour` to completion by isolating the final decision outcome, not just the initial lean.
- Close gap: Probe `service_embedding` with participant-facing questions about trigger moment, owner, inputs, and replacement vs added layer.
- Close gap: If pricing or buyer matters, ask directly; do not infer willingness to pay from general usefulness or trust comments.
- Close gap: If the report wants retention claims, ask what would make month-two reuse habitual versus occasional curiosity.
- Prompt change: Update the facilitation prompt so `recent_real_decision` is not considered complete until the actual changed action is explicitly stated.
- Prompt change: Add a synthesis guardrail: no pricing, buyer, accepted data access, or workflow replacement claims without direct participant-facing evidence refs.
- Prompt change: Add a dedupe rule so once public-vs-private certainty is clearly answered, the next probe must target a different missing variable.
- Prompt change: Require coverage logic to distinguish trust boundary evidence from workflow embedding evidence.
- Turn budget: The current soft/hard turn policy is sufficient for this mode. The issue is not budget shortage but probe ordering and synthesis discipline; keep the turn budget roughly the same and spend one of the early turns on the actual decision change and one later turn on workflow embedding.
