# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: Strong turn-by-turn probing within a narrow slice, but the run over-optimized for depth inside one example and then treated template coverage as sufficient despite unresolved research-goal dimensions. The main improvement need is stronger closure discipline tied to the stated research objective, plus cleaner separation of observed behavior from hypothetical concept reaction in synthesis.
- Primary failure mode: The facilitator accepted local depth on one concrete use case as a substitute for full goal coverage, causing missed probes on decision context and later synthesis overreach.
- Depth vs coverage: Depth was good within the chosen incident, especially around thresholds, contrast, and trust conditions. Coverage against the broader research goal was incomplete even though concept-mode checklist coverage was complete.

## Feedback Tags

- [high] goal-template-mismatch: The run completed concept-mode fields but did not collect several research-goal dimensions explicitly called out in the brief and observer steering.
- [medium] premature-narrowing: After a broad opening, the interview quickly locked onto one onboarding/setup incident and stayed there through concept testing.
- [medium] missed-evidence-conflict-probe: The facilitator probed what evidence would build trust, but did not ask how the participant would respond if the tool output conflicted with analytics, prior observation, or other evidence.
- [high] hypothetical-evidence-blending: Later synthesis sections mixed real-event evidence with stated future-use conditions without consistently labeling the difference.
- [high] closure-too-permissive: The interview stopped once concept coverage and required depth fields were complete, despite unresolved goal-specific gaps.

## Missed High-Value Follow-Ups

- [high] Which of those decision types do you personally carry most often, and who else is involved when the call is not yours alone?
  Trigger: scope signal
- [high] In that decision, what could you comfortably defend to others, and what were you privately worried about even if you could not easily prove it yet?
  Trigger: observer-steered gap
- [high] What evidence was still missing at that point, and what made waiting for more evidence feel too costly?
  Trigger: evidence-quality cue
- [high] If the tool's conclusion points one way but your analytics or user conversations point another way, how would you resolve that conflict?
  Trigger: adoption-risk cue
- [medium] Is this type of decision the main recurring bottleneck for you, or just one recent example of a broader pattern?
  Trigger: representativeness cue

## Likely Misclassified Drivers

- The participant seemed focused on one specific operational problem in a setup flow. -> The stronger reusable driver may be a general need for decision support that exposes reasoning, assumptions, and alternatives before asking for action.
- The participant's fast action on a small number of observations could be read as low need for evidence volume. -> The deeper pattern may be reliance on mechanism-level signal once the participant believes the causal structure is visible.

## Evidence Handling Issues

- [high] Observed-event evidence and hypothetical concept-adoption evidence were not kept in clearly separated buckets in synthesis.
- [high] Synthesis moved from a single tested slice to broader product or workflow implications not established by the transcript.
- [medium] Coverage completion was treated as an evidence claim even though it reflected template completion more than goal completion.

## Prompt Adjustments

- decision_rule: Treat the stated research goal as binding. Do not declare coverage complete unless each named decision dimension in the goal has been directly participant-tested or explicitly ruled out as not applicable.
- followup_trigger_rule: When a participant names multiple decision areas in the opening, ask one short ownership/frequency probe before narrowing to a single example.
- followup_trigger_rule: If the study includes tacit-versus-defensible reasoning, ask a direct contrast question on what the participant could defend publicly versus what they privately worried about.
- followup_trigger_rule: After a participant states trust criteria for a new tool or method, ask one conflict probe about what happens when that output disagrees with another evidence source.
- evidence_rule: In synthesis, separate observed behavior, recalled interpretation, and hypothetical adoption conditions into distinct sections and do not use one as proof of the others.
- stop_rule: Do not stop solely because the concept-validation checklist is complete if goal-specific gaps remain unresolved.
- contrast_rule: Before generalizing from one concrete example, ask whether the case is typical, high-frequency, high-stakes, or merely recent.

## Carry-Forward Rules

- CF-001: When a participant describes multiple decision contexts at the start, capture ownership and frequency before selecting one for depth.
- CF-002: After a stated trust threshold, always test one evidence-conflict scenario to learn how the participant adjudicates disagreement.
- CF-003: Keep observed past behavior and hypothetical future adoption in separate evidence lanes throughout synthesis and evaluation.
- CF-004: Closure requires both template completion and research-goal completion; either one alone is insufficient.

## Blocked Feedback

- The facilitator should have asked specifically about how synthetic output would compare against the participant's other named evidence sources in this founder workflow. (As written, this is tied to the project's local evidence stack and role framing.)
- The run should not have generalized from the onboarding/setup-flow example to broader roadmap and feature-priority behavior for this founder. (This references the project's specific workflow categories.)
