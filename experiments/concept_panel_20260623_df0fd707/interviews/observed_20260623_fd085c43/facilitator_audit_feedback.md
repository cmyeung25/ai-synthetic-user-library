# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: Strong depth-first facilitation with good coverage discipline, but several prompts introduced assumptions about value and reuse, and the interview did not fully translate broad concept reactions into concrete decision-linked evidence.
- Primary failure mode: Mildly leading concept framing combined with insufficient probing from generic concept reaction into specific output-to-decision mapping.
- Depth vs coverage: Coverage and depth goals were met efficiently, but some depth was spent on generic feature fit rather than on which exact outputs would change a real decision or non-decision.

## Feedback Tags

- [medium] solution_loaded_concept_intro: The concept was introduced with built-in value language about helping the participant assess risk/concentration, rather than neutrally presenting a possible feature and letting usefulness emerge from the participant.
- [medium] presumed_reuse: The reuse probe framed regular use as the default before first establishing whether the participant would reopen the feature at all.
- [medium] generic_reaction_without_output_mapping: The interview captured trust, timing, and explanation needs, but did not sufficiently probe which specific output or explanation would change an actual decision or non-decision.
- [low] stated_vs_observed_blurring_risk: The interview itself was mostly disciplined, but several later implications rested on predicted future use, follow-through, or retention rather than observed concept use.

## Missed High-Value Follow-Ups

- [high] What is the minimum explanation you would need before the result feels credible enough to consider, rather than ignore?
  Trigger: participant requested transparency into how a judgment was reached
- [high] During that waiting period, what are you trying to confirm or rule out before deciding whether to act?
  Trigger: participant described waiting before acting
- [high] Which comparison would make that change feel most decision-useful: versus your prior state, your intended target, or a typical reference point?
  Trigger: participant defined value as change-based information
- [medium] What presentation boundary would preserve trust: diagnosis only, a separate optional next-step area, or some other clear separation?
  Trigger: participant expressed sales-motive concern

## Likely Misclassified Drivers

- Interest in a free feature -> Conditional evaluation based on neutrality, control, and explanation sufficiency rather than simple price or access appeal
- Desire for alerts at certain moments -> A broader need to preserve attention and decision control under limited cognitive bandwidth

## Evidence Handling Issues

- [medium] Hypothetical responses about future action, repeat use, and retention created a risk of being treated as stronger evidence than observed behavior warrants.
- [medium] The concept intro embedded benefit language, which weakens the evidentiary value of the immediate concept reaction.

## Prompt Adjustments

- decision_rule: In concept-validation mode, introduce concepts without built-in benefit claims; describe the feature neutrally before asking for reaction.
- question_priority_rule: Before asking when or how a feature should recur, first ask whether the participant would use it again at all and under what conditions.
- followup_trigger_rule: If a participant asks for explanation or transparency, require one follow-up that identifies the minimum explanation needed for credibility.
- followup_trigger_rule: If a participant says they would wait, monitor, or think before acting, require a follow-up on what uncertainty they are trying to resolve during that delay.
- evidence_rule: Do not treat predicted reuse, action, or trust as behavioral proof; label it explicitly as stated intention or conditional future behavior.
- contrast_rule: When a participant says information must be 'new' or 'useful,' ask which comparison baseline makes it meaningfully different from last time.

## Carry-Forward Rules

- CF-001: Use neutral concept introductions that avoid implying usefulness, benefit, or value before the participant reacts.
- CF-002: Sequence repeat-use probing as: would reuse at all, what would trigger reuse, then how it should appear.
- CF-003: When participants request transparency, probe for the minimum sufficient explanation rather than accepting explainability as a generic need.
- CF-004: When participants defer action, probe the uncertainty being resolved during the delay to uncover the real decision job.

## Blocked Feedback

- The interview did not sufficiently test which specific analytics functions would materially help with this particular portfolio-management concept. (This is tied to the named concept, domain, and research goal rather than being universally reusable as-is.)
- Later synthesis implied concrete product-design conclusions from one synthetic participant's hypothetical reactions. (The affected implications were expressed in project-shaped product terms.)
