# Facilitator Quality Evaluation

> Synthetic pre-validation only; not human market evidence.

Overall verdict: **warn**

## Scores

- neutrality: 3/5
- probing_quality: 3/5
- conversation_naturalness: 3/5
- evidence_discipline: 3/5
- causal_rigor: 3/5
- hypothesis_validation_rigor: 3/5
- synthesis_fidelity: 3/5
- overall: 3/5

## Findings

- [low] 
- [low] 

## Required Improvements

- Review the transcript and synthesis manually before treating this run as calibrated evidence.

## Improvement Hints

- Focus next: Introduce the concept neutrally only after `concept_intro_allowed` flips to true. Immediately probe trust boundaries (data sharing limits, family/partner visibility), repeat-use triggers (specific friction points that would cause abandonment vs continued reliance), and service embedding (how it slots into the existing MTR/app/notes batch workflow).
- Close gap: Ask directly: 'What information would you absolutely refuse to share with anyone else?' 'Under what exact circumstance would you delete this tool after trying it?' 'How would you expect this to sit alongside your current month-end spreadsheet or notes app?'
- Prompt change: Enforce a strict 'no design implication until concept-tested' rule in synthesis. Add a mandatory checkpoint in the facilitator prompt to explicitly defer concept introduction until prerequisites (pressure, defensible_vs_uncertain) are satisfied, preventing premature product framing.
- Turn budget: Current 7-turn soft/hard limit is optimal for the pre-concept phase. Expand to 10-12 turns only after concept introduction to accommodate trial simulation, retention questioning, pricing calibration, and disconfirmation probes.
