# persona_ab_20260625_120216_codex_vs_agnes

## Reliability
- Codex matched batch (`seed=101`, `count=8`): 8/8 succeeded in 825.9s.
- Agnes matched batch (`seed=101`, `count=8`): 0/8 succeeded before failure after 281.8s.

## Quality Pair (`seed=11`)
- Codex judge on Codex persona: verdict=pass_with_revisions, plausibility=78, stereotype_risk=28, panel_fit=72.
- Codex judge on Agnes persona: verdict=usable_with_revisions, plausibility=78, stereotype_risk=34, panel_fit=68.
- Delta (Agnes - Codex): plausibility=0, stereotype_risk=6, panel_fit=-4.

## Constraint
- Quality scoring is based on one matched successful pair because the Agnes endpoint was operationally unstable during the 8-person matched run.