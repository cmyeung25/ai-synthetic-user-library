# Facilitator Quality Evaluation

> This audit evaluates a single synthetic interview and its write-up. It can judge methodological quality and evidence discipline, but it does not convert the synthetic transcript into real user evidence or market truth.

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

- [high] The synthesis marks multiple founder assumptions as `supported` even though most concept-stage evidence is hypothetical preference talk, not behavioral proof. Claims such as understanding simplified analytics, ideal embedding, and ability to distinguish self-serve vs assisted service rely mainly on `exchange_3`, `exchange_5`, `exchange_6`, and `exchange_7`, all framed as hypothetical future use.
- [medium] Several synthesis outputs go beyond the cited evidence. `retention_risk.workflow_effect` says `replaces_workflow`, but the transcript only shows that the participant might reopen the feature under certain triggers; it does not establish replacement of the current screenshot-and-discussion workflow.
- [medium] The concept introduction bundled the concept name with pre-framed value dimensions: `集中睇返成個組合嘅風險分佈、重疊同集中度`. That is acceptable for concept validation, but it still narrows response space toward the researcher's supplied benefits rather than first eliciting what the participant would want from such a feature.
- [medium] The research goal includes how Aladdin-like functions should embed into retail banking service, but the participant-facing coverage of embedding remained partial. `exchange_6` identifies self-serve versus explained analyses, yet it does not probe channel, trigger, or handoff mechanics such as alert, RM call, branch follow-up, or in-app escalation.
- [low] Coverage bookkeeping is inconsistent. `COVERAGE STATUS` says `founder_assumption_check` is missing, while the trace after `exchange_6` says it is basically covered and the closing decision treats required coverage as complete.
- [medium] The concept report preserves too little negative or weak problem evidence. The participant does describe a workaround and a gap, but there is no strong evidence of acute pain or repeated failure; yet `problem_evidence.strength` is set to `medium` and several downstream implications treat the problem as already substantial.

## Required Improvements

- Separate observed behavior evidence from hypothetical concept reactions in the synthesis and assumption table.
- Add one participant-facing embedding question that tests channel and handoff, not just which analyses need explanation.
- Tighten evidence claims around retention, workflow replacement, and problem strength so conclusions do not outrun transcript support.
- Fix coverage-state logic so missing protocol items are not simultaneously marked complete at close.

## Improvement Hints

- Focus next: Ask how the participant would want this to appear in practice: passive dashboard, maturity alert, push notification, or banker conversation prep.
- Focus next: Probe one concrete current blind spot consequence from the recent review, such as whether the fragmented view ever changed or delayed a decision.
- Focus next: Test whether the participant would act differently if the feature only used in-bank holdings first, then later offered optional external aggregation.
- Focus next: After concept reaction, ask what would make the feature feel useless or ignorable to surface disconfirming signals.
- Close gap: Directly probe the founder assumption about service embedding with a participant-facing question on preferred channel and escalation path.
- Close gap: Probe whether current manual review is merely acceptable friction or has caused missed opportunities, confusion, or duplicated holdings in a specific event.
- Close gap: Ask what they would do after seeing a concentration warning to distinguish curiosity from actionability.
- Close gap: If pricing is important, ask for a recalled case of paying for adjacent advice or analysis rather than relying only on hypothetical willingness.
- Prompt change: Require the synthesis to label every major claim as `observed`, `stated`, or `hypothetical` and prevent `supported` status from resting only on hypothetical future-use answers.
- Prompt change: In concept mode, instruct the facilitator to ask one open reaction question before naming specific candidate outputs like overlap or concentration.
- Prompt change: Add a guardrail that `workflow replacement`, `retention`, and `payment` claims need either a direct comparative probe or must stay explicitly tentative.
- Prompt change: Have the observer or runtime validator flag coverage inconsistencies when the close rationale says complete but a required item remains missing.
- Turn budget: The current soft/hard turn policy is close to sufficient for a synthetic concept interview, but one additional turn should be reserved for a direct embedding/handoff probe when that is part of the research goal.
