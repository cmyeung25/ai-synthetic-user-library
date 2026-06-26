# persona_ab_20260625_135606_agnes_v2_matched_pairs

## Setup
- Date: 2026-06-25T14:19:27+00:00
- Seeds: 101, 202, 303
- Baseline: Codex with `persona-enrichment/v1`
- Variant: Agnes with `persona-enrichment/v2`
- Judge: common Codex judge (`persona-judge/v1`)
- Note: scores above 10 are normalized by dividing by 10.

## Quality Averages
- Codex plausibility: 7.93
- Agnes plausibility: 7.27
- Delta plausibility: -0.66
- Codex stereotype risk: 3.07
- Agnes stereotype risk: 3.83
- Delta stereotype risk: 0.76
- Codex panel fit: 7.07
- Agnes panel fit: 7.1
- Delta panel fit: 0.03

## Reliability Notes
- Agnes seed 303 failed in the initial multi-seed run and was recovered with a separate single-seed rerun.
- The recovered Agnes seed 303 succeeded through chat_completions fallback on powershell_webrequest transport.
- Agnes attempt counts for seeds 101 and 202 were not persisted during the first run, so this report treats reliability as partial context and quality as the primary signal.

## Seed Notes
- Seed 101: Codex P7.8 / S3.4 / F6.9; Agnes P7.2 / S4.1 / F6.4
- Seed 202: Codex P8.2 / S2.4 / F7.4; Agnes P7.6 / S3.4 / F7.9
- Seed 303: Codex P7.8 / S3.4 / F6.9; Agnes P7.0 / S4.0 / F7.0
