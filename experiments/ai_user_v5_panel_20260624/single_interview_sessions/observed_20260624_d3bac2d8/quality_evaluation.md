# Facilitator Quality Evaluation

> This audit evaluates a synthetic interview artifact, not human-subject research quality in the field. Findings judge methodological rigor and evidence discipline within the simulation workflow only.

Overall verdict: **warn**

## Scores

- neutrality: 3/5
- probing_quality: 4/5
- conversation_naturalness: 4/5
- evidence_discipline: 3/5
- causal_rigor: 4/5
- hypothesis_validation_rigor: 4/5
- synthesis_fidelity: 3/5
- overall: 4/5

## Findings

- [medium] The first concept question is somewhat solution-loaded and anchors the participant to a researcher-supplied output pattern. It introduces a specific synthetic finding, `合成用戶反覆問「做完呢步有咩用」`, before first asking what kind of additional input would have been useful in that real decision. That risks steering the reaction toward confirmation of an already-specified mechanism.
- [medium] The interview moved to concept exposure after only one follow-up on the real event. The observer explicitly steered toward missing evidence on what she was trying to defend publicly, what pressure existed, what evidence was missing, and what tradeoff she actually made, but those participant-facing probes never happened before concept introduction.
- [medium] Several `key_insights` convert one participant's concept reaction into broad product-direction statements using strong `This means the product should...` language. That exceeds what one synthetic concept-validation interview can justify, even with the synthetic-only disclaimer.
- [medium] The report makes workflow-fit claims mostly from stated future-use scenarios rather than changed actions. `continuation_reasons`, `workflow_effect`, and parts of `service_embedding` are still hypothetical because no concept was actually used in a live prioritization workflow.
- [low] The observer asked to learn what existing step the platform would shrink or replace, but the participant-facing questions did not isolate that. The interview established where the tool might fit, but not what current work would be removed versus added.

## Required Improvements

- Make the first concept introduction neutral and participant-led before testing any specific synthetic pattern.
- Deepen the recalled recent decision with explicit pressure, tradeoff, and missing-evidence probes before concept exposure.
- Constrain synthesis to persona-bounded implications; do not turn one synthetic interview into broad product-shaping guidance.
- Separate observed behavior from hypothetical future use more consistently in workflow-fit and retention claims.
- Add one direct probe on what current step the tool would replace or shorten.

## Improvement Hints

- Focus next: Ask for the exact tradeoff in the recent prioritization call: what she chose, what she delayed, and what she could or could not defend to stakeholders.
- Focus next: Probe what evidence was still missing after analytics plus call notes, before introducing any AI concept.
- Focus next: After neutral concept introduction, ask what existing step it would shrink, replace, or make easier.
- Focus next: Test a conflict case: if synthetic output points one way and analytics or notes point another way, what would she do?
- Close gap: Add a participant-facing probe on the current workflow step that would be displaced versus merely layered on top.
- Close gap: Get one concrete threshold example: what output format would be actionable enough to schedule a follow-up validation task.
- Close gap: If concept validation is rerun, distinguish curiosity, trial, and repeated use with explicit wording, while keeping all three labeled as hypothetical unless enacted.
- Prompt change: In `concept_validation`, require at least 3 participant turns on the recalled event before concept exposure unless the user explicitly asks for a shorter screen.
- Prompt change: Ban first concept turns that include a specific inferred pattern or quote; require an open usefulness probe first.
- Prompt change: When observer steering requests missing recent-event evidence, prioritize those gaps before advancing coverage bookkeeping.
- Prompt change: Add a synthesis rule that product implications from one synthetic interview must be phrased as `candidate hypothesis` or `persona-specific signal`, not `the product should`.
- Turn budget: The current turn budget was sufficient. Do not widen it yet; use the same budget but reallocate one early concept turn back into deeper recent-event probing before concept introduction.
