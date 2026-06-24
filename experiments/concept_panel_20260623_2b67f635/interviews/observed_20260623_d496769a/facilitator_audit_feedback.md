# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: Coverage was completed cleanly and the conversation stayed natural, but the facilitator moved too quickly from broad concept reaction to coverage completion. The main reusable issues are bundled concept prompts, missed high-signal follow-ups on trial threshold and verification burden, and synthesis/evidence handling that treated hypothetical statements too strongly.
- Primary failure mode: Coverage was prioritized over isolating the most decision-relevant follow-ups after the participant surfaced concrete concerns about data access, explanation quality, and verification.
- Depth vs coverage: Good breadth for a short concept-validation interview, but depth was left on the table at the exact moments where the participant exposed adoption thresholds and proof requirements.

## Feedback Tags

- [medium] coverage_over_depth: After the participant raised clear concerns in `exchange_3.persona` and described a verification step in `exchange_5.persona`, the facilitator continued filling remaining coverage areas rather than deepening those clues.
- [medium] bundled_concept_prompt: `exchange_3.facilitator` combined free pricing, automatic aggregation, risk analysis, and simple explanation in one opening concept prompt.
- [medium] missed_threshold_probe: The interview captured first reaction in `exchange_3` and repeat use in `exchange_7`, but never asked what would make the participant actually start onboarding or connect accounts now.
- [medium] missed_contrast_probe: After `exchange_7.persona` said reuse depends on being faster than the current manual method, no follow-up tested whether the tool would replace the workaround, supplement it, or only be used occasionally.
- [high] hypothetical_evidence_drift: The synthesis promoted hypothetical answers from `exchange_3.persona`, `exchange_5.persona`, and `exchange_7.persona` into stronger claims such as workflow replacement and trust requirements without consistently labeling them as stated conditions.

## Missed High-Value Follow-Ups

- [high] Which part is actually giving you value first: seeing everything in one place, understanding risk, or getting a simpler explanation?
  Trigger: participant raised multiple value drivers in one answer
- [high] What is the minimum result you would need to see before you would continue with setup or grant more access?
  Trigger: participant stated a setup boundary
- [high] If the result looked roughly right but you still needed to verify it elsewhere, would that still save enough effort to be worth using?
  Trigger: participant described a verification behavior
- [medium] Would this replace your current method, sit alongside it, or only be something you check occasionally?
  Trigger: participant gave a repeat-use condition
- [medium] If you saw it at the right moment, what would make you tap in then instead of ignoring it?
  Trigger: participant named a timing preference

## Likely Misclassified Drivers

- The participant appeared to be giving a trust/privacy answer about external account connection. -> The deeper driver may have been proof-before-effort or proof-before-commitment rather than trust alone.
- The participant appeared to want better explanations of risk outputs. -> The deeper driver may have been the need to independently verify output quality before acting.

## Evidence Handling Issues

- [high] Hypothetical concept reactions were allowed to support stronger behavioral claims than the transcript justified.
- [high] Some synthesis claims were attached to exchanges that did not most directly support them, especially where trust-boundary conclusions borrowed from later action-validation answers.
- [medium] A convenience condition was summarized as workflow replacement without a direct participant statement of replacement.

## Prompt Adjustments

- followup_trigger_rule: After the first concept reaction, if the participant mentions more than one appealing or concerning element in a single answer, ask one isolating follow-up to identify the primary value driver or primary blocker before moving to the next coverage area.
- decision_rule: In concept validation, treat setup threshold, first-trial threshold, and repeat-use condition as distinct evidence targets. Do not infer one from another.
- question_priority_rule: When the participant describes a verification step before acting on concept output, prioritize probing whether that verification still leaves enough value to change behavior.
- evidence_rule: Label synthesis claims by evidence type: observed past behavior, recalled workaround, stated immediate intent, or hypothetical future condition. Prevent stronger behavioral wording when the underlying evidence is hypothetical.
- decision_rule: Do not stop solely because required coverage slots are filled if the participant has recently surfaced an unresolved threshold, contrast, or verification clue that could materially change interpretation.
- question_priority_rule: When introducing a concept, avoid stacking multiple benefits and pricing in the opening prompt. If bundling is unavoidable, immediately ask which element drove the reaction.

## Carry-Forward Rules

- cf_rule_01: If a participant names a permission or setup boundary, follow with the minimum value needed to cross that boundary before moving on.
- cf_rule_02: Separate mild concept interest from actual trial intent and from repeat-use conditions; capture each with its own participant-facing question.
- cf_rule_03: When a participant says they would verify results, probe whether the verification burden preserves value, reduces value, or eliminates the benefit.
- cf_rule_04: Do not infer replacement of an existing workaround from statements about speed or convenience alone; ask whether the new behavior would replace, supplement, or coexist with the old one.

## Blocked Feedback

- The facilitator should probe which specific analytics outputs matter most and where they should appear in the banking journey. (This is tied to the project's product and channel design agenda rather than a globally reusable interviewing rule.)
- The facilitator should ask whether this should be self-serve or assisted by a relationship manager. (The service-boundary framing is specific to this project context.)
