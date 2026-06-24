# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: The facilitator handled sequence and conversational tone reasonably well, but traded too much depth for coverage once the concept was introduced. The main reusable weakness was accepting participant-stated value and skepticism without enough contrast, threshold, or failure-case probing, then allowing synthesis to treat hypothetical reactions as stronger evidence than the transcript supports.
- Primary failure mode: Coverage completion outran evidence depth after concept introduction, especially around non-adoption, action threshold, and what the proposed feature would actually replace versus merely add.
- Depth vs coverage: Coverage was completed efficiently in seven exchanges, but several high-signal clues should have triggered one more follow-up before closure. The interview was broad enough for a light concept screen, but not deep enough to support strong downstream claims.

## Feedback Tags

- [medium] solution_loaded_concept_intro: The first concept question packaged multiple positive attributes together and then asked whether the feature would be useful.
- [high] missed_failure_case_probe: The participant volunteered skepticism about a feature that sounds impressive but still requires extra work, and the facilitator moved to preferred presentation rather than isolating a non-helpful case.
- [medium] threshold_probe_missing: After the participant said they would first judge whether the difference was large enough and whether it conflicted with other constraints, the interview did not ask what size or type of difference would actually change behavior.
- [high] adjacent_hypothetical_treated_as_behavior: Participant statements about what they would do if shown a feature were later summarized in ways that implied stronger workflow change than was directly evidenced.
- [medium] single_focus_question_drift: A later follow-up combined a diagnosis, a comparison view, and a next-step question in one turn.

## Missed High-Value Follow-Ups

- [high] Can you think of a situation where a summary like that still would not help you or would not change anything you do?
  Trigger: participant skepticism
- [high] What would make the difference big enough for you to act rather than wait?
  Trigger: decision threshold cue
- [medium] What problem does that extra step protect you from, and what is frustrating about doing it that way?
  Trigger: workaround clue
- [medium] If you used this, what current step would it actually remove for you, if any?
  Trigger: replacement ambiguity
- [medium] In which of those moments would this feel helpful, and in which would it feel interruptive or promotional?
  Trigger: journey-fit ambiguity

## Likely Misclassified Drivers

- The participant appeared to want clearer presentation. -> The stronger driver may be actionability under constraint rather than clarity alone.
- The participant appeared to want reminders and easier access. -> The stronger driver may be low-friction fit with an existing review rhythm rather than standalone demand for alerts or surface placement.

## Evidence Handling Issues

- [high] Hypothetical concept reactions were allowed to support stronger downstream claims than the participant-facing evidence justified.
- [medium] The interview closed after requirement coverage was complete even though at least one high-signal skepticism cue had not been resolved with a counterexample probe.
- [high] Workflow replacement was inferred without a direct participant-facing question establishing whether an existing step would disappear.

## Prompt Adjustments

- decision_rule: In concept validation, the first concept-introduction question must be neutral and may not bundle multiple positive attributes before asking for evaluation.
- followup_trigger_rule: If a participant volunteers skepticism, distrust, or a risk that the concept adds work, require one failure-case or ignore-case follow-up before moving to ideal feature design or placement.
- followup_trigger_rule: If a participant says they would act only when a difference is big enough, clear enough, or worth it, require a threshold probe that asks what exact condition changes behavior.
- evidence_rule: Do not allow synthesis to convert hypothetical next-step statements into replacement, retention, or behavioral-impact claims unless the participant was asked what current step would be removed or what repeated use was observed in reality.
- stop_rule: Coverage-complete is not sufficient to close the interview if there is an unresolved high-signal clue about non-adoption, threshold, contrast, or failure mode that has not yet received a participant-facing probe.
- contrast_rule: When a participant names a preferred placement or timing, add one contrast probe asking where the same concept would feel unhelpful, interruptive, or promotional.

## Carry-Forward Rules

- cf_001: After concept introduction, treat volunteered skepticism as a mandatory follow-up trigger rather than a note to capture and move past.
- cf_002: When a participant states a conditional action threshold, ask what would make the condition sufficient to change behavior before concluding the concept is actionable.
- cf_003: Ask whether the proposed concept removes an existing step, shortens one, or simply adds another task before inferring workflow improvement.
- cf_004: Prefer one conversational focus per question; avoid combining diagnosis, comparison setup, and action prediction in the same turn.

## Blocked Feedback

- The facilitator should test whether this specific banking feature feels like selling in portfolio, reminder, or advisor moments. (This is tied to the project's product surface and service context rather than a domain-agnostic facilitation rule.)
- The facilitator should probe trust in integrated holdings and advisor involvement for this wealth-management concept. (This is shaped by the local product and market context.)
