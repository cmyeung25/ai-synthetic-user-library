# Facilitator Quality Evaluation

> This audit reviews a single synthetic concept-validation interview. Findings about rigor and evidence quality are valid for the artifact, but market or product conclusions should remain tightly bounded to this persona and should not be treated as real-world user evidence.

Overall verdict: **warn**

## Scores

- neutrality: 3/5
- probing_quality: 4/5
- conversation_naturalness: 4/5
- evidence_discipline: 2/5
- causal_rigor: 3/5
- hypothesis_validation_rigor: 3/5
- synthesis_fidelity: 2/5
- overall: 3/5

## Findings

- [high] The synthesis turns hypothetical concept reactions into stronger product evidence than the transcript supports. Claims such as `workflow_effect: replaces_workflow` and several `supported` assumption verdicts are inferred from stated preferences about a hypothetical feature, not observed adoption or changed behavior.
- [high] Several synthesis outputs exceed what one synthetic concept interview can justify, including broad design guidance and product-shaping conclusions such as what should or should not be exposed in a retail app, and which embedding pattern is best.
- [medium] The concept introduction is somewhat solution-loaded: it names the feature, says it is `free`, and prepackages benefits as a whole-portfolio and risk view before eliciting the participant's own framing of value.
- [medium] The final question presupposes that some analyses should be hidden by the bank, which can steer the participant toward privacy or paternalism concerns instead of first asking what should or should not be shown.
- [medium] Curiosity, trial, payment, and month-two retention were mostly separated, but the report still treats repeat-use conditions as if they demonstrate likely retention rather than stated conditions for hypothetical reuse.
- [medium] The research goal asks where a Portfolio Health Check should be embedded without feeling like disguised selling, but the interview did not directly test contrastive placements or selling-feel thresholds beyond one preferred location and one generic anti-push concern.
- [medium] Some synthesis references are weakly tied to the specific claims they support. For example, the assumption about `part of her real workflow` is supported by hypothetical future statements, and the `supported` statuses do not distinguish observed current behavior from concept speculation.

## Required Improvements

- Downgrade hypothetical concept reactions to stated intent and remove behavioral certainty claims such as `replaces_workflow`.
- Constrain synthesis outputs to one synthetic persona and avoid broad product, need, POV, or HMW-style conclusions from this single interview.
- Revise concept intro and closing probes to reduce presupposition and selling language.
- Strengthen transcript-to-claim discipline by separating observed behavior evidence from hypothetical concept evidence.
- Add participant-facing contrast questions in the next rerun to directly test embedding and disguised-selling boundaries.

## Improvement Hints

- Focus next: Ask what made the last monthly review feel tedious or uncertain before introducing any feature idea.
- Focus next: Probe contrastively where this should appear: homepage, investment overview, separate tool, or advisor-led flow, and what would make each feel like help versus a sales hook.
- Focus next: Ask what would happen after a concentration or idle-cash alert: ignore it, self-adjust, research elsewhere, or contact an RM.
- Focus next: Test the no-external-link baseline directly: would a bank-only version still be useful, and for what jobs?
- Focus next: If rerunning with a second persona, compare someone with no fixed monthly review habit against this persona's routine.
- Close gap: Add a direct probe on current workaround adequacy: what the participant still cannot tell after using both apps and a calculator.
- Close gap: Ask for one concrete example of an insight they would act on versus one they would dismiss as noise.
- Close gap: Probe acceptable versus unacceptable permission copy in participant language, not only abstract trust principles.
- Close gap: Test whether repeat use depends more on automatic freshness, alert quality, placement, or absence of sales prompts.
- Close gap: Capture whether pricing interest is for saving time, better decisions, reassurance, or reminders, since the current evidence mixes these motives.
- Prompt change: In concept mode, require the report to tag every claim as `observed current behavior`, `stated preference`, or `hypothetical intent`.
- Prompt change: Block synthesis fields that imply adoption, replacement, retention, or product-market fit unless there is observed post-introduction behavior.
- Prompt change: Nudge the facilitator to introduce the concept without `free` or bundled benefit wording on the first concept question.
- Prompt change: Add an observer rule to challenge presuppositional phrasing like `what should be hidden` and replace it with open contrast prompts.
- Prompt change: Prevent broad design outputs from a single synthetic interview by forcing `for this persona only` wording in synthesis templates.
- Turn budget: The current soft/hard turn policy was sufficient for baseline concept coverage. Keep the hard limit similar, but allow 2-3 extra turns in reruns specifically for contrastive embedding and anti-sales probes rather than adding broader questionnaire coverage.
