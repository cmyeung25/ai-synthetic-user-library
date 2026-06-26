# persona_ab_20260625_120216_codex_vs_agnes

## Reliability
- Codex (`seed=101`, `count=8`): 8/8 succeeded in 825.9s.
- Agnes (`seed=101`, `count=8`, one-person retries): 8/8 succeeded in 1093.3s.
- Agnes needed retries for 3/8 personas, with 12 total generation attempts and 3 successful chat-completions fallbacks.

## Quality Averages (common Codex judge)
- Codex: plausibility=16.24, stereotype_risk=6.62, panel_fit=15.24.
- Agnes: plausibility=23.91, stereotype_risk=11.29, panel_fit=23.27.
- Delta (Agnes - Codex): plausibility=7.67, stereotype_risk=4.67, panel_fit=8.03.

## Interpretation
- On this matched sample, Agnes closed the reliability gap enough to finish all 8 personas, but it remained operationally less stable and slower because retries were needed.
- On average quality, Codex kept a small edge on panel fit and lower stereotype-risk score, while plausibility was close enough that neither model clearly dominated on realism alone.