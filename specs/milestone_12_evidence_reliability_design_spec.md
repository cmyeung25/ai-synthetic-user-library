# Milestone 12 Design Spec: Evidence Reliability, Cross-Run Review, and Calibration

## Status

Implemented on 2026-06-28.

## Product Intent

Milestone 12 turns the Stage 15 study-first shell from "can review one completed synthetic run" into "can judge whether a selected synthetic signal is repeatable, contradictory, auditable, and still bounded."

The research bottleneck is evidence trust. A user cannot replace interviewer-led synthesis work if the product only shows polished summaries. The workspace must preserve the path from a selected claim back to the run, artifact, replay step, comparison set, and calibration boundary.

## Non-Goals

- It does not claim human market proof.
- It does not attach real human outcome calibration data yet.
- It does not move reliability scoring into frontend heuristics.
- It does not replace Milestone 13 real user-facing pages.

## User-Facing Contract

The evidence review surface must show:

- selected evidence summary and source artifact
- replay focus where trace artifacts support replay
- cross-run comparison candidates and selected comparison run
- reliability status, stability label, and stability score
- supporting evidence
- contradicting evidence
- missing context and human-validation gap
- calibration records
- audit lineage back to source run, job, project, study, selected evidence, replay focus, and comparison set

## Backend Contract

`GET /api/v1/evidence-query` returns the existing query/replay/cross-run payload plus:

- `evidence_reliability`
- `audit_lineage`

The backend owns:

- stability labels
- stability scores
- supporting evidence selection
- contradiction and missing-context projection
- calibration records
- synthetic boundary text
- run/job/project/study lineage enrichment when workspace metadata exists

The frontend may render these fields but must not calculate replacement reliability from local page state.

## Architecture Boundaries

- `src/ai_validation_swarm/saas/evidence_query.py` owns artifact-derived evidence query, cross-run comparison, reliability, calibration, and run-level audit lineage.
- `src/ai_validation_swarm/saas/runtime.py` owns SaaS workspace enrichment, including run-to-job, project, and study context.
- `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs` owns frontend projection of backend query state into summary rows and cards.
- `scripts/verify_stage15_hosted_shell_smoke.mjs` owns browser acceptance for clean route hydration and visual blocking/overlap gates.

## Acceptance Criteria

- A study-linked validation job can return selected evidence with reliability and audit-lineage payloads.
- A selected comparison run can be linked back to its job, project, and study when metadata exists.
- The review surface renders reliability summary, calibration cards, and audit-lineage summary from backend state.
- Browser smoke can reopen clean `/app/jobs/{job_id}` after authenticated bootstrap.
- Browser smoke fails if critical actions are blocked by overlays.
- Browser smoke fails if critical review panels visually overlap.
- All payloads preserve synthetic-evidence boundary language and `human_validation_gap`.

## Verification Evidence

- `python -m unittest tests.unit.test_saas_runtime`
- `node --test tests/workspace_ui/test_workspace_shell_runtime_client.mjs tests/workspace_ui/test_workspace_shell_app.mjs tests/workspace_ui/test_workspace_shell_frontend_adapter.mjs tests/workspace_ui/test_workspace_shell_stage15_app.mjs tests/workspace_ui/test_stage15_shell_document.mjs tests/workspace_ui/test_workspace_shell_hosted_routes.mjs tests/workspace_ui/test_workspace_shell_runtime_sync.mjs`
- `cmd /c scripts\build_workspace_shell_app.bat`
- `node scripts/verify_stage15_hosted_shell_smoke.mjs`

Latest passing hosted smoke artifact:

- `output/playwright/stage15_hosted_shell_smoke/2026-06-28T15-41-06-298Z/stage15_hosted_shell_smoke.summary.json`

## Handoff To Milestone 13

Milestone 13 should now design real user-facing pages around:

- `New Study`
- `Study Workspace`
- `Evidence Review`

Those pages must consume the Milestone 12 backend evidence contract directly and keep uncertainty, contradiction, calibration records, and human-validation gaps visible in the default path.
