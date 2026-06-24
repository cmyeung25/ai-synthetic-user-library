# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: The facilitator ran a reasonably natural, coverage-complete interview, but accepted several high-signal participant clues without enough depth and later allowed hypothetical concept reactions to carry too much evidentiary weight in synthesis.
- Primary failure mode: Coverage was completed before the facilitator isolated what the concept would actually replace, what behavior it would change, and which claims remained hypothetical rather than observed.
- Depth vs coverage: Coverage sequencing was efficient and conversational, but depth was too shallow at several key moments where one additional contrast or consequence probe would have materially improved evidence quality.

## Feedback Tags

- [medium] coverage_over_depth: The interview covered recent behavior, workaround, concept reaction, trust boundary, action follow-through, embedding, and repeat-use in 8 exchanges, then stopped once coverage was complete even though the participant had not been asked what the concept would replace or what she would still need to check elsewhere.
- [high] missed_contrast_probe: After the participant described using the concept only as a quick overview and still checking future expenses before acting, no direct contrast probe asked what the concept would save, what it would not replace, or whether it would change a real decision versus merely shorten an existing check.
- [high] hypothetical_as_behavior_risk: The facilitator asked hypothetical follow-through and repeat-use questions after concept introduction, but the resulting answers were later used in synthesis language that implied stronger behavioral support than the transcript warranted.
- [medium] solution_loaded_concept_intro: The first concept question introduced a free tool, inside an existing app, with unified visibility across accounts, before first probing what outcome the participant would want from such a tool.
- [medium] missed_near_miss_followup: When the participant said she adjusted liquidity a bit and stopped new contributions, the facilitator did not ask what would have had to be different for her to take a bigger action or no action at all.
- [medium] unisolated_adoption_condition: The participant volunteered multiple conditions for trust and reuse such as speed, no setup, concrete output, and no sales feel, but the facilitator did not separate must-have conditions from nice-to-have conditions or ask which one would break adoption first.

## Missed High-Value Follow-Ups

- [high] What would you still need to check after that overview before you would trust yourself to act?
  Trigger: participant said the concept would be only a quick overview
- [high] What would have had to be different for you to make a bigger change, or for you to leave everything untouched?
  Trigger: participant described a real action after a recent event
- [medium] Which part would make you close it first: the vague explanation, the request for more steps, or the feeling that it is steering you somewhere?
  Trigger: participant rejected vague scores and sales-like flow
- [high] Thinking back to the event you described earlier, if this tool had existed then, what exactly would it have changed in what you did, if anything?
  Trigger: participant described a hypothetical next step after a tool alert
- [medium] If only one of those were true on the first few uses, which one would matter most for you to come back?
  Trigger: participant gave a repeat-use condition bundle

## Likely Misclassified Drivers

- The participant seemed to want a portfolio-health feature that summarizes accounts. -> The more fundamental driver may have been reducing uncertainty before acting under time or consequence pressure, with summary only serving that broader control need.
- The participant seemed mainly sensitive to trust and onboarding friction. -> The deeper issue may have been skepticism toward tools that ask for commitment before proving immediate relevance.
- The participant seemed suitable for passive in-flow exposure rather than active exploration. -> The stronger pattern may be situational relevance: people engage when a current decision makes the information consequential, regardless of channel placement.

## Evidence Handling Issues

- [high] Hypothetical concept reactions were allowed to support synthesis claims with stronger language than the interview evidence justified.
- [high] Some conclusions implied workflow replacement even though the participant explicitly described continued manual verification before action.
- [medium] Untested fields were partially filled by inference from positive or negative reactions rather than direct probes.

## Prompt Adjustments

- followup_trigger_rule: When a participant says a concept would be only a quick check, must ask one follow-up on what it would not replace before moving on.
- evidence_rule: In concept validation, every synthesis claim must be labeled internally as observed past behavior, recalled-event comparison, or hypothetical concept reaction; hypothetical evidence cannot justify replacement or retention claims on its own.
- decision_rule: After a participant reports a real action in a recent event, ask one threshold or contrast probe before introducing the concept unless turn budget is already constrained.
- question_priority_rule: When a participant volunteers multiple adoption or abandonment conditions in one answer, prioritize isolating the strongest condition before opening a new coverage area.
- decision_rule: First concept-introduction questions should avoid stacking multiple favorable premises unless the test is specifically about those premises.
- stop_rule: Do not stop solely because coverage slots are complete if the interview still lacks a clear answer to whether the concept changes behavior, saves time only, or leaves the core workaround intact.

## Carry-Forward Rules

- CF-001: After a participant recalls a real action, ask at least one threshold, contrast, or near-miss follow-up before moving into concept reaction.
- CF-002: Treat participant statements about what they would do with a proposed concept as hypothetical until tied back to a specific recalled event comparison.
- CF-003: When multiple reasons for trust, drop-off, or reuse are volunteered together, isolate the break-point condition instead of carrying the bundle forward unchanged.
- CF-004: Before concluding a concept streamlines or replaces a workflow, ask what the participant would still need to check, verify, or do elsewhere.

## Blocked Feedback

- The interview should have compared specific analytics outputs tied to this product context earlier. (This is too tied to the specific product and research goal to be safely reused as facilitator-core guidance.)
- The facilitator should have probed whether this banking feature belongs in an account view versus a deeper investment page. (This is too specific to the current channel and product embedding context.)
