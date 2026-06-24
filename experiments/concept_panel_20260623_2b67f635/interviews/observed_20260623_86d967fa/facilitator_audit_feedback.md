# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: The facilitator handled sequencing and conversational tone well, but accepted several high-signal statements at surface level and then let synthesis treat hypothetical concept reactions as stronger evidence than the interview earned.
- Primary failure mode: Coverage completion outran evidence depth, especially around action change, repeat use, and separation of observed behaviour from hypothetical reactions.
- Depth vs coverage: Coverage was completed efficiently, but one or two additional depth probes would likely have produced substantially better evidence for downstream synthesis.

## Feedback Tags

- [high] coverage_over_depth: After the participant exposed a meaningful current shortcut and decision threshold in `exchange_2.persona` and `exchange_3.persona`, the interview moved to concept testing instead of probing one concrete consequence or exception case.
- [high] hypothetical_as_behavioral_evidence: Questions in `exchange_4.facilitator`, `exchange_6.facilitator`, and `exchange_7.facilitator` elicited stated reactions and intentions, but later synthesis treated some of those as evidence of actual workflow change or durable reuse.
- [medium] solution_loaded_concept_intro: `exchange_4.facilitator` introduced the concept with built-in positive framing such as free, simple, and named benefits before the participant defined what help would matter most.
- [medium] missed_threshold_probe: The participant described acting only when change feels noticeable in `exchange_3.persona`, but the facilitator did not ask what qualifies as noticeable or what happens right at the boundary.
- [low] imprecise_evidence_labeling: The trace labels hypothetical probes as consequence-oriented evidence and uses hypothesis-style targets in a concept-validation interview, even though no tested hypothesis was in play.

## Missed High-Value Follow-Ups

- [high] Can you think of a recent time it was close to that line but you still decided not to dig in, and what made it stay in the 'leave it' bucket?
  Trigger: threshold_signal
- [high] What does that quick check help you avoid or protect you from in that moment?
  Trigger: workaround_protection_signal
- [medium] What would make it feel like a legitimate tool instead of something trying to push you somewhere?
  Trigger: trust_concern_signal
- [high] Tell me about the last time you saw something concerning and what you actually did step by step after that.
  Trigger: action_intent_signal
- [medium] What would make you open it a second or third time instead of forgetting it after the first try?
  Trigger: repeat_use_signal

## Likely Misclassified Drivers

- The participant appears to want more analysis depth from the concept. -> The stronger driver may be reducing effort and ambiguity during quick triage, not maximizing analytical richness.
- The participant's main issue is feature preference around concentration or risk views. -> The underlying driver may be preserving control and avoiding unwanted escalation after engaging with a tool.

## Evidence Handling Issues

- [high] Observed behaviour and hypothetical concept reactions were not kept cleanly separate in downstream interpretation.
- [medium] Stated repeat-use conditions were allowed to stand in for retention evidence.
- [medium] Participant language about what they might do next was stronger in synthesis than in the transcript.

## Prompt Adjustments

- evidence_rule: In concept-validation interviews, label every participant answer as one of: recalled behaviour, current routine, hypothetical reaction, hypothetical intent, or inference, and forbid synthesis from merging these categories.
- followup_trigger_rule: If a participant names a threshold, shortcut, near-miss, or 'usually I just...' pattern, ask one depth probe on the boundary or tradeoff before introducing the concept.
- question_priority_rule: Before asking about repeat use or embedding, prioritize one probe that anchors whether the concept would change a recalled real action or non-action case.
- contrast_rule: When a participant expresses interest plus distrust in the same answer, ask a contrast probe that distinguishes 'helpful tool' from 'thing I avoid' before moving to later coverage items.
- decision_rule: Introduce concepts with the minimum necessary description. Avoid built-in value claims unless those attributes are the explicit variable under test.
- stop_rule: Do not stop solely because coverage flags are complete if action impact or reuse evidence is still hypothetical and a single high-yield follow-up could anchor it in a recalled case.

## Carry-Forward Rules

- cf_rule_01: When a participant states an action threshold, probe one concrete threshold-present or threshold-near-miss case before moving on.
- cf_rule_02: Keep concept-reaction evidence separate from current-behaviour evidence in both trace labels and synthesis outputs.
- cf_rule_03: Ask at least one contrast or consequence probe that reveals what the current workaround is protecting against.
- cf_rule_04: Treat stated reuse conditions as provisional until they are anchored to a concrete second-use scenario or recalled repeat behaviour.

## Blocked Feedback

- The concept was framed with specific attributes and analytic dimensions that likely steered reactions toward those particular capabilities. (This is tied to the named concept and its domain-specific feature bundle rather than a reusable facilitator rule if stated directly.)
- The interview did not test whether this service should appear in a particular banking moment or channel relative to the participant's investment workflow. (The original point is too tied to this product context and journey design question.)
