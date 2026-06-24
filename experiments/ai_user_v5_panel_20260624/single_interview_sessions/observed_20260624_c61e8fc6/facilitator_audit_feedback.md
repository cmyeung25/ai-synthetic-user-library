# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: Strong coverage and generally natural probing, with the main improvement need being stricter evidence discipline before concept introduction and tighter separation between hypothetical reactions and behavioral proof.
- Primary failure mode: The facilitator moved into concept validation before fully exhausting the highest-signal current-state uncertainty and occasionally embedded value claims into participant-facing concept framing.
- Depth vs coverage: Coverage was high and depth was often good, but one important pre-concept depth thread was skipped: what the participant could defend publicly versus what still felt uncertain in the real recalled decision.

## Feedback Tags

- [medium] premature_concept_transition: The interview established a real recent event, but did not directly probe what the participant felt able to defend versus what still felt uncertain before moving into the concept.
- [medium] solution_loaded_concept_intro: The concept was introduced with promised upside such as finding assumption gaps and objections early, rather than with a thinner workflow description.
- [medium] coverage_over_depth_on_decision_context: The interview covered many required areas, but skipped a direct question on what evidence the participant could publicly stand behind versus what remained privately unresolved in the recalled event.
- [medium] hypothetical_adoption_overinterpreted: Later answers about where the tool would fit and when it would still be rechecked were useful, but they remained hypothetical and should not be treated as behavioral retention evidence.
- [low] analyst_interpretation_not_labeled: Some synthesized labels compressed the participant's workflow stance into stronger shorthand than the transcript itself used.

## Missed High-Value Follow-Ups

- [high] In that actual decision, what part of your recommendation could you defend confidently in the room, and what part still felt uncertain to you even after the synthesis?
  Trigger: public_vs_private_uncertainty cue
- [high] What concrete decision changed because of that evidence: scope, sequence, priority, or whether to proceed at all?
  Trigger: roadmap_or_priority relevance gap
- [medium] Can you recall a time when an objection or minority signal looked important at first but later turned out not to matter, and how you distinguished that?
  Trigger: minority_signal_threshold cue
- [medium] If a tool showed a clear evidence trail but its conclusion still conflicted with your own first read, what would you check first?
  Trigger: trust_conflict calibration cue

## Likely Misclassified Drivers

- The participant appears primarily concerned with whether outputs are smooth or messy. -> The deeper driver may be reputational and evidentiary defensibility rather than a simple stylistic preference for nuance.
- The participant seems to want a tool that saves synthesis time. -> The stronger driver may be reducing avoidable rework without sacrificing auditability.

## Evidence Handling Issues

- [high] Hypothetical future-use statements were close to being treated as evidence of retention or stable workflow insertion.
- [medium] A synthesized workflow label compressed the participant's stance into stronger analyst wording than the transcript directly supported.
- [medium] Product implications in synthesis extended beyond what one synthetic concept-validation interview can support.

## Prompt Adjustments

- decision_rule: In concept-validation mode, do not introduce the concept until the facilitator has extracted one concrete unresolved uncertainty from the recalled real decision, not just the participant's process description.
- followup_trigger_rule: If the research goal references prioritization, roadmap, scope, or sequencing, require at least one participant-facing probe that asks what concrete decision changed because of the evidence.
- followup_trigger_rule: When a participant describes making evidence 'defensible' or avoiding being misled by tidy summaries, trigger a probe that separates what they could defend publicly from what still felt privately uncertain.
- evidence_rule: Do not let hypothetical willingness-to-use, repeat-use, or trust-threshold answers become retention or adoption evidence unless the interview also captures analogous past behavior.
- contrast_rule: When a participant values preserved disagreement or exceptions, ask for one case where an apparent objection did not deserve action, to reveal their threshold for distinguishing signal from noise.
- question_priority_rule: Prefer exhausting the highest-signal current-state decision probe before switching into concept reaction, even when coverage is progressing well.
- decision_rule: Use a lean concept introduction that describes the workflow change without embedding benefits or promised outcomes.

## Carry-Forward Rules

- cf_public_private_split: Before concept introduction, when a recalled decision is established, ask what evidence the participant could defend confidently and what still remained uncertain.
- cf_changed_decision_probe: If the interview goal includes decision impact, require one probe that names the changed action: scope, sequence, priority, launch, or no-go.
- cf_hypothetical_boundary: Separate 'would try once,' 'would use in a bounded step,' and 'would continue relying on' as distinct evidence classes.
- cf_neutral_concept_intro: Describe the candidate tool or workflow neutrally first; ask usefulness and risk before mentioning potential benefits.
- cf_signal_vs_noise_probe: When a participant emphasizes contradiction, minority views, or edge cases, ask how they decide which objections matter and which do not.

## Blocked Feedback

- The facilitator missed a chance to ask about who specifically would challenge the participant in review and what organizational pressures shaped the need for defensible evidence. (Specific stakeholder types and review dynamics could turn into project- or organization-shaped priors if carried forward too literally.)
- The interview did not fully realize the study's stated interest in roadmap and feature-priority decisions because the recalled example stayed closer to prototype-review preparation. (The exact mismatch depends partly on this study's project framing and should not become a hardcoded domain assumption.)
