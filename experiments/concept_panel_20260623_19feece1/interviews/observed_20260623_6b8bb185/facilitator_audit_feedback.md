# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: Coverage was achieved efficiently, but the facilitator moved from grounded behavior into concept-led hypothetical probing too quickly and the downstream synthesis treated stated reactions as stronger evidence than the transcript supports.
- Primary failure mode: Coverage was prioritized over depth after concept introduction, causing missed follow-ups on real past analogs, decision thresholds, and concrete next actions.
- Depth vs coverage: Good breadth and conversational flow; insufficient depth on the highest-signal clues once the participant revealed a concrete workaround and a credibility threshold.

## Feedback Tags

- [medium] concept_intro_too_compound: The first concept question packaged a named solution plus several outputs in one turn, then immediately asked which part felt most useful (`exchange_3.facilitator`).
- [high] coverage_over_depth: After the participant described noting issues without acting immediately and weighing them against cash needs, the interview moved on instead of probing one specific remembered case or threshold (`exchange_2.persona`, `exchange_4.persona`, `FACILITATOR TRACE`).
- [high] missed_behavioral_analog_probe: Trust, action, timing, and repeat-use were all gathered as hypothetical reactions to the proposed feature without asking for a past comparable experience (`exchange_4` to `exchange_7`).
- [medium] threshold_without_contrast: The participant specified what explanation would make a signal credible, but there was no contrast probe on the minimum insufficient explanation or a near-miss example beyond one vague-alert complaint (`exchange_3.persona`, `exchange_5.persona`).
- [medium] service_embedding_without_action_path: The facilitator asked when the participant would want to see the feature, but not what they would do immediately after seeing it inside the journey (`exchange_6.facilitator`, `exchange_7.facilitator`).

## Missed High-Value Follow-Ups

- [high] Can you walk me through the last time you noticed something was off but chose not to act right away? What made it a 'note for later' instead of a follow-up then?
  Trigger: workaround_contains_delay_or_deferral
- [high] What is the minimum information that would still feel too weak to act on, even if the alert looked relevant?
  Trigger: participant_names_trust_criterion
- [high] Have you ever received anything similar before, from any tool or person? What did you actually do next that time?
  Trigger: hypothetical_action_claim
- [medium] If you saw it at that moment, what would be the very next step you would take in the product or outside it?
  Trigger: workflow_timing_preference
- [medium] What would happen in the first two or three uses that would make you stop checking it, even if you liked the idea at first?
  Trigger: repeat_use_claim

## Likely Misclassified Drivers

- The participant seemed to be expressing a feature preference for one type of signal over another. -> The stronger underlying driver may have been decision efficiency: reducing the work needed to judge whether follow-up is warranted.
- The participant seemed to be describing a preferred notification moment. -> The stronger underlying driver may have been workflow protection: wanting support only when it fits an existing review routine and does not create interruption cost.

## Evidence Handling Issues

- [high] Hypothetical reactions were allowed to stand as the main evidence for trust, action, and retention without a past-behavior check.
- [medium] The interview closed once coverage slots were marked complete even though several high-signal statements had not been pressure-tested with examples, contrasts, or near misses.
- [high] The synthesis blurred direct participant statements and analyst inference, making downstream conclusions sound more certain than the transcript supports.

## Prompt Adjustments

- followup_trigger_rule: After concept introduction, if the participant gives any trust criterion, deferral rule, or repeat-use condition, ask one depth follow-up before moving to the next coverage slot.
- evidence_rule: Do not treat hypothetical concept reactions as behavioral evidence until the facilitator asks for a concrete past analog or explicitly labels the claim as stated preference only.
- contrast_rule: When a participant states what would make a concept credible or useful, ask a paired contrast probe about what would still be insufficient or ignorable.
- stop_rule: Do not end solely because required coverage is complete if the latest answer contains an unresolved threshold, consequence, or workflow clue that could materially improve evidence quality in one more turn.
- question_priority_rule: Prefer probing the participant's actual last analogous behavior over advancing to the next concept dimension whenever both are available.

## Carry-Forward Rules

- CF-01: When a participant describes noticing a problem but delaying action, ask for the last specific instance and what threshold separated noticing from acting.
- CF-02: After a participant names a trust or usefulness requirement, ask one contrast question to identify the minimum unacceptable version.
- CF-03: For concept-validation claims about ongoing use, separate initial appeal, first real use, and sustained repeat use into distinct probes.
- CF-04: For service-embedding questions, ask not only when the participant wants to see something but also what immediate action they would take next.

## Blocked Feedback

- The prior quality evaluation recommended adding willingness-to-pay probes. (That recommendation conflicts with this run's study setup and would be too project-shaped to reuse safely here.)
- Feedback about a specific analytics feature being the most valuable signal. (This is a project-specific conclusion about content preference, not reusable facilitator guidance.)
- In concept validation, introduce the concept in the narrowest testable form first; avoid bundling multiple benefits or outputs into the first exposure question. (project_specific_content)
