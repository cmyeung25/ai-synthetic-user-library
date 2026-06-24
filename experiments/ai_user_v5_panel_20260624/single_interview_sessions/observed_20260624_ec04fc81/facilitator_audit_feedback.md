# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: The interview was generally natural and well-sequenced, but it accepted key event framing as sufficient without confirming the actual decision outcome, allowed one redundant confidence-boundary probe, and the downstream synthesis converted hypothetical concept reactions into stronger workflow and pricing claims than the transcript supports.
- Primary failure mode: Coverage was marked complete before the recalled real decision was closed with a concrete changed action, which weakened later domain-fit and workflow-fit interpretation.
- Depth vs coverage: Coverage discipline was strong at the checklist level, but depth was uneven: the facilitator probed thresholds and trust boundaries well, yet skipped the highest-value follow-up on what was actually changed and how the tool would fit into a real workflow.

## Feedback Tags

- [high] missing_actual_decision_outcome: The participant described an initial lean toward a small change and fast validation, but no follow-up confirmed what was actually approved, deferred, cut, or sequenced differently.
- [medium] redundant_confidence_boundary_probe: Two separate questions asked what the participant could defend publicly versus what remained privately uncertain, with substantial overlap.
- [medium] workflow_embedding_marked_without_direct_probe: The interview covered trust and validation behavior, but did not directly ask when the participant would open the tool, who would use it, or what existing step it would replace or augment.
- [high] hypothetical_to_behavioral_slippage: Participant statements about what would make the concept useful, reusable, or worth paying for were hypothetical, but later synthesis promoted some of them into stronger workflow and pricing implications.

## Missed High-Value Follow-Ups

- [high] What did you actually change in the end: what was approved, deferred, cut, or sequenced differently?
  Trigger: recent-event incompleteness
- [medium] What did that uncertainty change in what you recommended or held back from committing to?
  Trigger: confidence boundary answer
- [medium] Which part of that workaround is protecting you from the biggest mistake, and which part is just extra effort you tolerate?
  Trigger: workaround description
- [high] At what exact step in your existing process would you open something like this, and what would it replace, speed up, or leave unchanged?
  Trigger: concept interest with caveats
- [medium] Can you recall a recent case where you could already reach a workable decision quickly without needing an extra framing tool?
  Trigger: non-use condition

## Likely Misclassified Drivers

- The participant appears to want better early framing before research. -> The stronger underlying driver may be avoidance of added verification burden rather than desire for more ideation input.
- Trust was interpreted mainly as a transparency requirement. -> The underlying driver may be decision defensibility under uncertainty, with transparency being one mechanism rather than the root need.

## Evidence Handling Issues

- [high] Recent-behavior coverage was treated as complete without a confirmed final action in the recalled case.
- [medium] Workflow embedding was inferred from hypothetical usefulness and trust statements rather than directly probed.
- [high] Hypothetical concept reactions were later used to support stronger pricing and operational conclusions.
- [medium] A repeated certainty-boundary probe consumed a turn that could have been used to close a higher-value evidence gap.

## Prompt Adjustments

- decision_rule: Do not mark `recent_real_decision` complete until the participant states the actual change made in scope, sequence, priority, go/no-go, or deferment.
- followup_trigger_rule: If a participant gives an initial lean or recommendation in a recalled event, immediately ask what was actually decided and who accepted it before moving to concept exposure.
- followup_trigger_rule: After a confidence-boundary answer, prefer a consequence probe about what that uncertainty changed in the recommendation; do not repeat the public-versus-private certainty split unless a specific ambiguity remains.
- evidence_rule: Do not mark workflow or service embedding covered from trust, usefulness, or validation answers alone; require a direct participant-facing probe on where the concept fits in the existing process.
- evidence_rule: Do not convert hypothetical usefulness, reuse, or willingness-to-pay statements into stronger synthesis claims without direct transcript evidence tied to behavior, budget action, or a real usage decision.
- question_priority_rule: When turns are limited, prioritize unresolved concrete event closure and workflow placement over additional attitude refinement once threshold and trust boundaries are already clear.
- stop_rule: Do not stop on checklist completeness alone if the core recalled event still lacks the final action taken or if workflow placement has not been directly probed.

## Carry-Forward Rules

- cf-001: Close every recalled recent event with the concrete action taken before treating it as usable behavioral evidence.
- cf-002: When a participant states what they can and cannot defend, ask how that uncertainty changed the decision rather than re-asking the same certainty contrast.
- cf-003: Require a direct workflow-placement probe before concluding that a new tool fits the participant's process.
- cf-004: Keep hypothetical concept reactions labeled as hypothetical unless anchored to a real observed behavior or decision.

## Blocked Feedback

- The interview should have asked specifically whether this concept belongs before real user interviews in this product manager's onboarding prioritization workflow. (This is too tied to the local concept positioning and project context.)
- The synthesis should not have inferred pricing readiness for this synthetic-user platform from this participant's answers. (The named concept is project-specific even though the methodological issue is generic.)
