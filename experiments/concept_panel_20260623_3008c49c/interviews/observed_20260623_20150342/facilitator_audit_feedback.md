# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: Coverage was complete, but the facilitator accepted several high-signal cues without enough causal or contrast probing and later treated hypothetical concept reactions as stronger evidence than the interview supported.
- Primary failure mode: Coverage was prioritized over depth once required slots were filled, especially around trust calibration, workaround meaning, and what would actually change behavior.
- Depth vs coverage: Good breadth and sequencing, but multiple answers contained clear follow-up hooks that were not pursued before closing.

## Feedback Tags

- [high] stacked_concept_intro: The concept was introduced with price, convenience, breadth, and explanation style combined in a single question, so the answer mixed convenience, trust, and permission concerns.
- [high] missed_trust_calibration_probe: The participant said they would first check whether the output was accurate and alarmist, but the interview moved to permission scope instead of probing what would make a warning feel credible versus overstated.
- [medium] workaround_without_function_probe: The facilitator captured that the participant uses notes, messaging history, and calendar reminders, but did not ask what gap each workaround covers or which missed-risk matters most.
- [high] hypothetical_evidence_overweighting: Later synthesis and assumption scoring leaned on stated future reactions to infer product implications and usage patterns more strongly than the transcript supports.
- [medium] early_driver_closure: The trace formed an explanatory account of the participant's behavior before probing competing reasons such as low complexity, low relevance, time scarcity, or tool sufficiency.
- [medium] stop_rule_too_coverage_based: The interview ended after required fields were covered even though credibility criteria, value thresholds, and workaround function remained under-specified.

## Missed High-Value Follow-Ups

- [high] What would make a warning feel accurate to you, and what would make it feel exaggerated or not worth trusting?
  Trigger: credibility cue
- [high] What does each tool help you avoid, and which kind of miss matters most when one of them fails?
  Trigger: workaround fragmentation cue
- [high] What kind of change would be large enough to make you do something different rather than just verify and move on?
  Trigger: consequence threshold cue
- [medium] If the same warning appeared when nothing time-sensitive was happening, would you still look, or would it feel irrelevant?
  Trigger: contrast cue
- [medium] Can you think of an existing alert or reminder you kept using or stopped using for similar reasons?
  Trigger: retention analogue cue

## Likely Misclassified Drivers

- The participant seemed to be managing mainly around near-term arrangements and verification. -> This may reflect several different causes, such as low complexity, low perceived relevance, limited time, or sufficient current tools, rather than one settled motive.
- The participant's main adoption barrier appeared to be permissions and trust. -> The stronger barrier may instead be unclear incremental value relative to the current workaround, with permission concerns acting as a secondary filter.

## Evidence Handling Issues

- [high] Hypothetical reactions to the concept were treated as stronger evidence of future usage and design fit than the interview supports.
- [medium] A causal explanation for current behavior was marked too confidently without ruling out plausible alternatives.
- [medium] Stopping after slot completion left unresolved ambiguity in the most decision-relevant parts of the evidence.

## Prompt Adjustments

- decision_rule: Do not mark a motivational explanation as supported unless the interview tested at least one plausible alternative explanation for the same observed behavior.
- followup_trigger_rule: If a participant says they need to see whether something is accurate, exaggerated, useful, or worth trusting, ask for the concrete threshold or example before moving on.
- followup_trigger_rule: If a participant describes a multi-tool workaround, ask what each tool covers and what failure or risk the workaround is protecting against.
- contrast_rule: After a participant names the ideal moment for a feature, test the opposite or lower-relevance moment to determine whether the value is situational or general.
- evidence_rule: Tag each conclusion as observed behavior, stated preference, or hypothetical reaction, and do not let later synthesis collapse those categories.
- stop_rule: Do not end solely because required coverage is complete if one of the following remains unresolved: credibility threshold, action threshold, workaround function, or contrast between use and non-use moments.
- question_priority_rule: When introducing a concept, keep the first reaction question focused on one variable only; separate capability, explanation style, access requirements, and pricing/value assumptions into later questions.

## Carry-Forward Rules

- cf_01: When participants express conditional trust, probe for the exact evidence that would make the output feel credible versus dismissible before shifting topics.
- cf_02: Treat fragmented workarounds as a signal to map function, failure, and protection, not just enumerate tools.
- cf_03: Use at least one threshold or consequence probe after a participant describes a verification step, so the interview distinguishes checking from action change.
- cf_04: Keep synthesis persona-bounded and method-bounded when it relies mainly on hypothetical concept responses.

## Blocked Feedback

- The interview did not adequately test whether deeper analytics capabilities would change decisions compared with simpler reminder-style outputs in this specific product area. (This observation is tied to the project's feature set and product framing rather than a universally reusable facilitation rule.)
- The synthesis turned one participant's workflow into design guidance about where this service should live in the banking journey. (The product-placement implication is too tied to the specific concept and domain context.)
