# Facilitator Audit Feedback

- Scope: interview
- Safe for global reuse: False

## Summary

- Overall: Solid coverage with natural questioning, but the facilitator introduced the concept too early and too specifically, which reduced the chance to deepen the recalled real decision and increased anchoring risk.
- Primary failure mode: Coverage advanced ahead of deeper causal probing on the recent real event, especially once a concrete concept output was introduced.
- Depth vs coverage: The interview achieved required coverage and some depth, but left high-value depth on pressure, missing evidence, tradeoffs, and evidence-conflict handling unexplored.

## Feedback Tags

- [high] early_concept_exposure: After one follow-up on the recent decision, the facilitator moved into concept testing instead of staying longer on the real event.
- [high] solution_anchoring: The first concept question included a concrete inferred output pattern rather than first asking what additional input would have helped in that decision.
- [medium] missed_causal_depth_on_real_event: The participant described using multiple evidence sources, but the facilitator did not probe what remained uncertain, what was at stake, or what alternative was consciously deprioritized.
- [medium] hypothetical_behavior_blur: Several later answers were hypothetical concept-use statements, but the interview did not explicitly separate intended behavior from enacted behavior.
- [low] replacement_step_omission: The interview established likely insertion points but did not isolate which existing activity would be reduced or replaced.

## Missed High-Value Follow-Ups

- [high] After combining those sources, what was still uncertain enough that the decision still felt risky or debatable?
  Trigger: multi-source evidence workaround
- [high] What tradeoff did you knowingly accept by choosing against the preferred option, and what part of that choice was hardest to defend?
  Trigger: stakeholder override cue
- [high] If the new output partly matched your existing evidence but conflicted on one important point, how would you resolve that conflict?
  Trigger: trust threshold statement
- [high] What specific threshold made that situation unsuitable: time left, consequence severity, or the number of teams that needed to trust the result?
  Trigger: non-use boundary
- [medium] If this were useful in practice, which current step would become shorter, easier, or unnecessary?
  Trigger: workflow fit claim
- [medium] What is the minimum output that would be strong enough for you to schedule a real follow-up action instead of just reading and moving on?
  Trigger: repeat-use condition

## Likely Misclassified Drivers

- The participant appears mainly to want a faster way to prioritize earlier. -> The stronger driver may be the need for decisions that remain defensible under scrutiny, with speed only acceptable when evidence remains explainable.
- The participant appears generally open to the concept in early-stage work. -> The underlying condition may be low added verification cost rather than broad openness to synthetic evidence.
- The participant's non-use case appears to be only about urgent timing. -> The deeper blocker may be consequence severity and cross-functional accountability, with timing acting as an amplifier.

## Evidence Handling Issues

- [high] The first concept probe embedded a specific hypothetical finding, which risks converting participant reaction into confirmation of a facilitator-supplied interpretation.
- [medium] Observed past behavior and hypothetical future use were not kept sharply distinct throughout later probing, creating downstream risk of overstating workflow fit.
- [medium] The interview stopped without testing an evidence-conflict scenario, leaving the participant's actual decision rule under disagreement unverified.

## Prompt Adjustments

- decision_rule: In concept-validation interviews, do not introduce the concept until the facilitator has elicited the recalled decision, the evidence used, the missing evidence, and the key tradeoff accepted in that real event.
- followup_trigger_rule: If a participant mentions multiple evidence sources, ask what uncertainty remained after combining them and what the unresolved risk was.
- followup_trigger_rule: If a participant mentions stakeholder disagreement or pressure, ask what they could defend publicly versus what they still worried about privately.
- evidence_rule: Do not let the first concept question contain a specific inferred output pattern, quote, or conclusion; start with a neutral usefulness probe tied to the recalled event.
- contrast_rule: When a participant gives a non-use case, separate time pressure, consequence severity, and coordination burden with at least one clarifying probe before generalizing the boundary.
- evidence_rule: Treat workflow insertion, repeat use, and action follow-through as hypothetical unless the participant describes an enacted behavior or simulated task response.
- question_priority_rule: Before adding more coverage questions, prioritize one probe on what current step the tool would shorten, replace, or make easier.
- stop_rule: Do not stop immediately after coverage is complete if a high-signal unresolved cue remains about tradeoff, evidence conflict, or replacement-vs-layering; spend one final turn resolving it.

## Carry-Forward Rules

- fac_rule_recent_event_min_depth: Before concept exposure, get at least one concrete probe each on missing evidence, decision tradeoff, and pressure or accountability within the recalled real event.
- fac_rule_neutral_first_concept_turn: Make the first concept turn neutral and participant-led; ask what additional input would have helped before testing any named output from the proposed solution.
- fac_rule_conflict_case_probe: When a participant says a new input would be cross-checked, ask how they would act if that input conflicts with their current evidence.
- fac_rule_replace_not_layer: For any proposed tool or workflow change, ask what existing step becomes shorter, easier, skipped, or unchanged.
- fac_rule_hypothetical_labeling: Keep observed behavior and stated future intent explicitly separated in both interview notes and synthesis claims.

## Blocked Feedback

- The facilitator missed a chance to probe the participant's specific concern about using synthetic evidence in relation to analytics, call notes, legal/support review, and release-stage product decisions. (This bundles project-specific evidence sources, functions, and operating context too tightly to reuse safely in facilitator-core guidance.)
- The synthesis overreached into product-direction claims about where this platform should focus first and what interface features it should emphasize. (Those claims are too tied to the current product concept and interview topic to feed back as generic facilitator learning.)
