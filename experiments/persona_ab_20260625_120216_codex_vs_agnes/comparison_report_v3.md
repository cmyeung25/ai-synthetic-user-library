# persona_ab_20260625_120216_codex_vs_agnes

## Reliability
- Codex (`seed=101`, `count=8`): 8/8 succeeded in 825.9s.
- Agnes (`seed=101`, `count=8`, one-person retries): 8/8 succeeded in 1093.3s.
- Agnes needed retries for 3/8 personas, across 12 total attempts, with 3 successful fallbacks.

## Quality Averages (normalized common Codex judge)
- Codex: plausibility=7.46, stereotype_risk=3.48, panel_fit=6.91.
- Agnes: plausibility=7.04, stereotype_risk=3.64, panel_fit=6.51.
- Delta (Agnes - Codex): plausibility=-0.42, stereotype_risk=0.16, panel_fit=-0.4.

## Caveat
- The common Codex judge returned a mixed score scale (0-10 and 0-100). This report normalizes all scores above 10 by dividing by 10 before aggregation.