# Milestone 37: Live Interview Observability and Transcript Evidence Design Spec

Status: implemented.

Owner layer: Frontline Research Studio, SaaS runtime, evidence-query contract, facilitated-interview artifact bridge.

Last updated: 2026-07-02.

## Purpose

Milestone 37 makes the Frontline product trustworthy while a real LLM-backed study is running and after the study completes.

The current Frontline loop can run from plan approval to evidence, report, decision, and share. The next bottleneck is that users still see too little of what is happening during the synthetic interview and too much of the completed result as already-processed summary. This weakens evidence discipline because a user cannot easily inspect the raw interview, the facilitator's choices, or the synthetic participant driver trace behind a finding.

## Alignment Check

- Research bottleneck improved: users need to understand whether a run is actually interviewing synthetic participants, where it is in the interview loop, and which raw exchanges support each finding.
- Primary improvements: evidence quality, auditability, decision review, and scalable research throughput.
- North-star fit: replacing parts of interviewer-led work requires observable interview execution and inspectable transcript provenance, not only polished summaries.

## User-Facing Scope

M37 adds two connected user-facing capabilities:

1. Live interview run observability.
2. Transcript and trace-backed evidence review.

These capabilities belong under Study -> Run and Study -> Evidence, not as global navigation items.

## Capability 1: Live Interview Run Observability

The run monitor should show real progress while an LLM provider or worker is running the study.

Required states:

- `queued`: accepted and waiting for worker/provider capacity.
- `planning`: plan and participant panel are being prepared.
- `sampling_panel`: synthetic participants are being selected or validated.
- `interviewing`: facilitator and synthetic participant turns are being generated.
- `synthesizing`: transcript, findings, evidence slices, and report material are being derived.
- `auditing`: safety, evidence-boundary, and quality checks are being generated.
- `completed`: evidence review is available.
- `blocked`: user action, quota, artifact, provider, or governance condition prevents progress.
- `failed`: the run stopped unexpectedly and can be inspected or retried.

The Frontline UI should expose:

- current run phase
- participant-level progress
- latest visible interview turn when safe to show
- provider/runtime boundary
- retry or recovery action when blocked or failed
- clear copy that progress is synthetic simulation, not recruited human fieldwork

## Capability 2: Transcript and Trace-Backed Evidence Review

The evidence surface should let users move from summary to raw interview material.

Required review layers:

- Summary: high-level patterns, contradictions, objections, trust gaps, adoption barriers, and human-validation gaps.
- Evidence slices: structured findings with source references.
- Transcript: chronological facilitator and synthetic participant exchanges.
- Facilitator trace: why the facilitator chose questions, probes, phases, and stopping decisions.
- Synthetic participant driver trace: the simulated latent drivers, objections, uncertainty, and reasoning cues used to answer.
- Audit: quality, boundary, provider, plan, selected-persona, and prompt/model lineage.

The transcript and traces must be shown as inspectable synthetic artifacts, not as hidden truth or human proof.

## Evidence Boundary Rules

- Transcript is simulated interview evidence.
- Facilitator trace is an audit artifact explaining the synthetic moderator's behavior.
- Synthetic participant driver trace is a simulation clue source, not proof of a real person's inner psychology.
- Observed action traces are separate from interview self-report and must remain labeled as observed/action-grounded evidence only when an application or browser trace was actually captured.
- Reports and findings must cite transcript exchanges or trace artifacts when claims are derived from them.
- User-facing copy must not imply that a synthetic participant's "inner thoughts" are real human mind-reading.

Preferred user-facing terminology:

- English: `Transcript`, `Facilitator trace`, `Synthetic participant reasoning trace`, `Source exchange`, `Observed action trace`.
- `zh-Hant`: `訪談逐字稿`, `主持人追蹤`, `合成受訪者推理追蹤`, `來源對話`, `觀察行動追蹤`.

## Data and API Contract

The runtime should project existing artifacts into a stable run-observability contract instead of requiring the Frontline UI to read raw filesystem paths.

Target read APIs:

- `GET /api/v1/studies/{study_id}/runs/{run_id}/progress`
- `GET /api/v1/studies/{study_id}/runs/{run_id}/transcript`
- `GET /api/v1/studies/{study_id}/runs/{run_id}/trace`

Target event or polling model:

- Local-first implementation may use polling against persisted worker status and partial artifacts.
- Future hosted implementation may add SSE or websocket events after the polling contract is stable.

Target persisted records:

- append-only run progress events
- participant-level interview progress
- transcript exchanges with stable exchange IDs
- facilitator trace entries linked to exchange IDs
- synthetic participant driver trace entries linked to exchange IDs
- evidence-slice source references linked to exchange IDs or trace entries
- provider/model/prompt lineage attached to the run

## Frontline Route Placement

The existing route model remains valid:

- `/studio/studies/{study_id}/runs`: run list and high-level status.
- `/studio/studies/{study_id}/runs/{run_id}`: live monitor, transcript, trace tabs, artifacts, audit, and provider boundary.
- `/studio/studies/{study_id}/evidence`: evidence review with citation links back to source exchanges.
- `/studio/studies/{study_id}/reports/{study_report_id}`: report with cited evidence and links back to transcript exchanges.

No global route should be added for transcript or trace because both are run-scoped review contexts.

## Observed Interview and Observed Action Bridge

The platform already has observer-controlled interviews and observed-action trace support at the engine/artifact layer.

M37 should bridge these into Frontline as follows:

- Observer-controlled interview artifacts become a run-detail evidence source when a run uses observed interview mode.
- Observed action traces remain prototype/task evidence and are shown beside transcript evidence, not merged into it.
- If both interview transcript and observed action trace exist, the UI should privilege observed action for behavior claims and transcript for explanation, interpretation, objections, and trust gaps.

## Acceptance Criteria

- The Frontline run detail page can display live or near-live phase progress for a running LLM-backed study without relying on raw CLI output.
- A completed run exposes transcript exchanges, facilitator trace, synthetic participant reasoning trace, audit boundary, and provider lineage through route-safe Frontline pages.
- Evidence slices, reports, and decision logs can link back to transcript exchanges or trace entries.
- The UI distinguishes transcript evidence, facilitator trace, synthetic participant reasoning trace, observed action trace, summary, and human-validation gaps.
- Browser acceptance covers a run monitor transition from queued/interviewing/synthesizing to completed, then opens transcript and trace-backed evidence review.
- Unit/API acceptance verifies progress, transcript, and trace contracts for completed, running, blocked, and failed runs.

## Out of Scope

- Full real-time websocket infrastructure before a stable polling contract exists.
- Claiming synthetic transcript or reasoning trace as human proof.
- Replacing existing evidence summary/report surfaces.
- Production-grade multi-worker observability dashboards.
- Human interview recording or transcription from real participants.

## Roadmap Impact

M37 moved ahead of messaging validation because all future study types need visible run execution and inspectable evidence provenance.

Messaging validation remains important, but it depends on users being able to inspect whether a message finding came from transcript evidence, trace interpretation, or polished summary.

## Implemented Repository Evidence

- `src/ai_validation_swarm/saas/runtime.py` now exposes Frontline run progress, transcript, and trace projections through backend-owned contracts instead of raw filesystem reads.
- `src/ai_validation_swarm/saas/api.py` now exposes `GET /api/v1/studies/{study_id}/runs/{run_id}/progress`, `/transcript`, and `/trace`.
- `src/ai_validation_swarm/saas/evidence_query.py` now projects `source_exchange_refs` and `source_trace_refs` so evidence views, reports, and decision logs can cite transcript and trace provenance.
- `frontend/frontline_research_studio/src/main.jsx` now renders run monitor, transcript, and trace panels on the run detail route.
- `scripts/verify_frontline_studio_smoke.mjs` now verifies the run monitor, transcript panel, trace panel, source-exchange visibility, and route-safe review flow.
