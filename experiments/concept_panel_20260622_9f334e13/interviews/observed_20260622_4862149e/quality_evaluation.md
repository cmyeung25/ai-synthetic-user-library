# Facilitator Quality Evaluation

> This audit reviews a synthetic interview and synthetic synthesis only. Any positive or negative product implication should be treated as method-quality feedback, not real market evidence, until validated with human participants.

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

- [high] The synthesis converts one synthetic, largely hypothetical concept reaction into product-shaping conclusions that read stronger than the evidence allows. Examples include `problem_evidence.strength: strong`, `retention_risk.workflow_effect: replaces_workflow`, and assumption statuses such as meaningful demand being `supported`. The transcript contains stated preferences about a proposed tool, not observed adoption, replacement, or demand behaviour.
- [medium] A few questions constrain the answer space by making the participant choose within researcher-supplied frames. `exchange_5.facilitator` asks when the analysis feels like understanding risk rather than product selling, which presumes those are the salient interpretations. `exchange_7.facilitator` offers a portfolio-vs-product contrast instead of first asking how the bank information currently feels in the participant's own words.
- [medium] The concept-introduction question asks for both the most useful and most suspicious part in one turn. That is manageable here, but it creates two response tasks and can blur which dimension drove the answer.
- [medium] Coverage was marked complete, but participant-facing evidence for privacy and external-asset sharing is absent. The research goal concerns understanding the whole portfolio, yet the transcript never directly tests willingness to connect non-bank assets or concrete privacy boundaries. The synthesis correctly marks one assumption `unknown`, but the interview still stopped without probing it.
- [medium] The research goal includes trust, understanding, action willingness, and asset retention, but the interview mostly gathered reactions to reporting and explanation quality. Claims about action quality, engagement, and retention remain hypothetical because no changed action or repeat-use behaviour with such a tool was observed.
- [medium] The synthesis produces broad assumptions, next experiments, and design implications from one synthetic interview. Although a disclaimer is present, labels like `supported` and `strong` still overstate what a single synthetic persona can authorize.

## Required Improvements

- Reduce synthesis claim strength so hypothetical concept reactions are not presented as strong demand, replacement behaviour, or validated retention effects.
- Add participant-facing probes for external asset linking and privacy/data-sharing boundaries before closing this concept-validation flow.
- Rewrite trust and founder-assumption questions to start open, then use contrast probes only if the participant has not surfaced the dimension unaided.
- Keep design implications and assumption verdicts explicitly limited to one synthetic persona unless corroborated by additional interviews or observed prototype behaviour.

## Improvement Hints

- Focus next: Ask which assets/accounts they would actually connect, including non-bank holdings, and which they would refuse to share.
- Focus next: Probe a concrete acceptable vs unacceptable data-use boundary, not just general sales suspicion.
- Focus next: Test whether they have ever paid for, ignored, or reused any financial-analysis aid to ground action and retention in analogous behaviour.
- Focus next: Show a neutral low-fidelity concept and ask what they would do next, before asking price or RM-assisted interpretation.
- Close gap: Add a direct privacy probe covering data sources, consent, storage concerns, and whether cross-bank aggregation is acceptable.
- Close gap: Add an external-assets probe to isolate whether whole-portfolio value survives if only bank-held assets are included.
- Close gap: If retention is important, ask for a recalled example of a financial tool/report they revisited and what made them return.
- Close gap: If willingness to pay is important, ask for comparable paid behaviours or thresholds rather than relying only on stated conditions.
- Prompt change: In concept-validation mode, require an explicit privacy/data-linkage probe whenever the concept depends on whole-portfolio aggregation.
- Prompt change: Instruct the facilitator to prefer open-first trust and founder-assumption questions before using binary contrasts like portfolio-led vs product-led.
- Prompt change: Constrain synthesis labels so `supported` is reserved for bounded persona-level support and forbid market-level wording from a single synthetic interview.
- Prompt change: Add a guardrail that design implications about retention, action quality, or asset retention must be tagged `hypothetical` unless backed by observed or analogous behaviour.
- Turn budget: Current turn budget was enough for core coverage, but it should be widened by 1-2 exchanges in concept-validation interviews that depend on data aggregation so privacy/linkage boundaries can be tested before closure.
