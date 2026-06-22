# Facilitator Quality Evaluation

> This audit evaluates a single synthetic interview. Any positive demand, pricing, trust, retention, or product-direction conclusion should be treated as provisional prompt-quality feedback, not human market evidence.

Overall verdict: **warn**

## Scores

- neutrality: 3/5
- probing_quality: 3/5
- conversation_naturalness: 4/5
- evidence_discipline: 2/5
- causal_rigor: 3/5
- hypothesis_validation_rigor: 3/5
- synthesis_fidelity: 2/5
- overall: 3/5

## Findings

- [high] The synthesis turns hypothetical stated intent from one synthetic concept interview into overly strong support claims. `assumption_validation` marks self-serve demand and paid demand as `supported`, and `retention_risk.workflow_effect` says `replaces_workflow`, but the transcript only shows conditional future intent after a concept description, not observed adoption or workflow replacement.
- [medium] The final question constrains the participant to the researcher's supplied dichotomy: real portfolio help versus another sales method. That invites classification into preselected frames instead of letting the participant describe how they would recognize the difference in their own terms.
- [medium] The concept introduction bundles multiple promised benefits in one turn: integration, overall risk, and scenario impact. That is more sell-shaped than neutral and makes it hard to isolate which part drives interest or resistance.
- [medium] The facilitator speaks in product and finance framing that may outpace a retail participant's natural language, including `Portfolio Health Check`, `整合持倉`, `整體風險`, and `情景影響`. The persona handles it, but the wording still imports the product frame rather than eliciting the participant's own vocabulary first.
- [medium] Several report statements blur behavioural evidence and hypothetical claims. `problem_evidence.strength` is `strong`, `pricing_signal.free_trial_need` is inferred rather than directly stated, and `problem_evidence` uses exchange 5 future-use language as support for the current problem.
- [low] The research goal targets trust, understanding, action willingness, and asset retention, but this single interview only directly evidences a stalled decision and conditional willingness to try or maybe pay. Asset-retention implications are not participant-evidenced here.

## Required Improvements

- Reduce synthesis confidence: re-label hypothetical future intent as conditional stated evidence, not support for demand, payment, or workflow replacement.
- Rewrite the concept intro to remove bundled benefits and product framing so the participant can react to a more neutral concept.
- Replace the forced-choice founder-assumption question with an open probe that elicits participant-defined signals of neutrality versus sales intent.
- Tighten evidence discipline in the report by separating recalled-event evidence from hypothetical concept reactions and by limiting claims to one synthetic persona.

## Improvement Hints

- Focus next: Ask the participant to describe, in their own words, what they would need to see on the first screen before trusting the tool.
- Focus next: Probe a concrete current example of how they judge whether a bank feature is advisory versus sales-led.
- Focus next: Test one narrower concept at a time: cross-account exposure summary first, then scenario analysis, then any recommendation layer.
- Focus next: Ask what they would do immediately after seeing a meaningful risk overlap, to distinguish curiosity from action intent.
- Close gap: Add a direct participant-facing probe on what specific next action they would take after a useful output, rather than only whether they would revisit the tool.
- Close gap: Probe comprehension explicitly: what parts of the output they expect to understand easily and what would be confusing.
- Close gap: If retention is important, ask what would make them return in week two or month two versus using it once and stopping.
- Close gap: If payment is important, isolate price sensitivity from trust and setup by asking what makes it worth paying for even if the bank is not selling anything.
- Prompt change: In concept-validation mode, instruct the facilitator to introduce the concept in one sentence without naming multiple benefits at once.
- Prompt change: Add a guardrail against binary founder-assumption questions unless preceded by an open probe in the participant's own language.
- Prompt change: Require the synthesis layer to tag every claim as `observed`, `stated_intent`, or `inference` and prevent `supported` labels when only stated intent exists.
- Prompt change: Add a check that pricing, retention, and design implications remain explicitly bounded to a single synthetic persona and do not imply market-level demand.
- Turn budget: The current turn budget was sufficient for basic coverage, but one or two extra turns would improve quality if used to unpack sales-trust cues and concrete post-output actions rather than adding more broad concept questions.
