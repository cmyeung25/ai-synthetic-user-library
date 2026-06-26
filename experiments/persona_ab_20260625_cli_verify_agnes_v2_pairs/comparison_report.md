# persona_ab_20260625_cli_verify_agnes_v2_pairs

## Setup
- Date: 2026-06-25T14:29:00+00:00
- Seeds: 101, 202
- Baseline: Codex with `persona-enrichment/v1`
- Candidate: Agnes with `persona-enrichment/v2`
- Judge: Codex (`persona-judge/v1`)
- Note: Judge outputs mixed 0-10 and 0-100 scales. Scores above 10 were normalized by dividing by 10 before aggregation.

## Quality Averages
- Codex plausibility: 7.3
- Agnes plausibility: 7.85
- Delta plausibility: 0.55
- Codex stereotype risk: 3.9
- Agnes stereotype risk: 3.65
- Delta stereotype risk: -0.25
- Codex panel fit: 7.7
- Agnes panel fit: 7.55
- Delta panel fit: -0.15

## Reliability
- Codex total attempts: 2
- Agnes total attempts: 3
- Codex pairs using fallback: 0
- Agnes pairs using fallback: 1

## Seed Notes
- Seed 101: Codex P7.6 / S3.8 / F8.4; Agnes P8.1 / S4.2 / F8.7 (Agnes attempts=1, fallback_used=False)
- Seed 202: Codex P7.0 / S4.0 / F7.0; Agnes P7.6 / S3.1 / F6.4 (Agnes attempts=2, fallback_used=True)
