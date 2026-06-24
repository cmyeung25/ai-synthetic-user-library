# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: Coverage was completed efficiently, but the facilitator accepted several high-signal cues without enough depth and let a somewhat solution-loaded concept framing shape the evidence too early.
- Primary failure mode: Coverage over depth after concept introduction, especially around function-specific value, trust causality, and action thresholds.
- Depth vs coverage: Strong breadth across required areas, but several participant clues that could have produced more decision-useful causal evidence were left at the surface level.

## Feedback Tags

- [medium] solution_loaded_concept_intro: The concept was introduced with built-in value language and free pricing before the participant's reaction was elicited.
- [high] coverage_over_depth: Once all required coverage areas were touched, the interview moved forward rather than deepening on trust concerns, explanation thresholds, or partial-coverage tradeoffs.
- [high] missed_threshold_probe: The participant named conditions like 'clear explanation', 'meaningful change', and 'not too pushy', but the facilitator did not quantify or operationalize them.
- [medium] missed_contrast_probe: Aggregation, analytics, explanation clarity, and non-sales handling stayed bundled rather than being compared against each other.
- [medium] surface_acceptance_of_trust_concern: The participant raised suspicion about motive and data use, but the facilitator only captured acceptable data scope and did not probe what specifically created distrust.
- [high] hypothetical_evidence_overextension: Later synthesis language leaned beyond what one real behavior example plus several hypothetical responses could support.

## Missed High-Value Follow-Ups

- [high] What would make this feel like a neutral service rather than a sales path, and what would make you stop trusting it immediately?
  Trigger: trust_signal
- [high] What specific explanation or comparison would be clear enough for you to change what you do, and what would still feel too vague?
  Trigger: threshold_signal
- [high] If you could have only one first, a complete consolidated view or a strong diagnostic explanation, which would change your behavior more and why?
  Trigger: contrast_signal
- [high] If the tool covered only part of your portfolio at first, in what situations would that still be useful, and when would it become not worth using?
  Trigger: partial_coverage_tradeoff
- [medium] Can you describe one reminder you would open and one you would ignore, and what makes the difference?
  Trigger: embedding_signal
- [medium] How do those personal categories affect how you judge whether the portfolio is off, and would a generic view miss something important?
  Trigger: workaround_signal

## Likely Misclassified Drivers

- The participant seems mainly to want convenience from having everything in one place. -> The stronger driver may be preventive control under time pressure: reducing the chance of being surprised at the wrong moment, not just saving effort.
- The participant is privacy-sensitive about data access. -> The deeper issue may be motive distrust and fear of commercial pressure rather than data minimization alone.
- The participant wants plain-language risk explanation. -> They may actually need a diagnosis that preserves independent judgment by separating signal from noise and mapping to low-pressure options.

## Evidence Handling Issues

- [high] Hypothetical reactions and stated conditions were allowed to support design-direction language more strongly than the transcript warranted.
- [medium] Single-participant resistance was framed too categorically in places where persona-scoped weakening would have been more accurate than broad invalidation.
- [low] Distinct requirements were sometimes grouped together without preserving exact evidence traceability for each subclaim.

## Prompt Adjustments

- decision_rule: In concept-validation mode, introduce the concept without built-in benefit claims or price cues unless those specific variables are being tested.
- followup_trigger_rule: If a participant spontaneously questions motive, fairness, or hidden intent, ask at least one follow-up on what would increase trust and one on what would break trust before advancing.
- followup_trigger_rule: When a participant uses vague acceptance thresholds such as 'clear enough', 'meaningful change', or 'too pushy', convert at least one into a concrete threshold, example, or contrast probe.
- question_priority_rule: If the research goal asks which functions matter, prioritize at least one forced comparison that isolates feature components by expected decision change.
- evidence_rule: Tag every major synthesis claim as observed, stated, or inferred, and prevent inferred claims from being summarized as validated behavior.
- stop_rule: Do not stop immediately after coverage completion if a participant has surfaced an unquantified trust boundary, action threshold, or feature tradeoff that could be resolved in one or two short probes.

## Carry-Forward Rules

- cf_01: When a participant raises an unsolicited trust concern, probe the causal source of the concern before narrowing into implementation details.
- cf_02: Use at least one threshold or contrast follow-up to separate stated usefulness from behavior-changing usefulness.
- cf_03: Treat participant statements about future routine use as conditions to test, not as evidence of retention.
- cf_04: When multiple benefits are bundled in a concept reaction, isolate the primary driver with a forced tradeoff before concluding what matters most.

## Blocked Feedback

- The interview should have asked earlier about which specific analytics outputs from this banking portfolio-health concept matter most, such as drift, concentration, or other embedded analytics. (This is anchored to the product domain and named concept framing rather than a fully domain-agnostic interviewing rule.)
- The facilitator should have probed the value of partial visibility across external versus in-bank holdings for this investment portfolio workflow. (This is tied to a specific financial aggregation context.)
