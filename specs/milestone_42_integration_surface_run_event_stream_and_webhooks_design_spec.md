# Milestone 42 Design Spec: Integration Surface, Run Event Stream, and Webhooks

Status: `implemented`

Date: `2026-07-02`

## Product Intent

M42 closes two user-facing gaps after the Frontline Studio evidence loop and privacy/export gate became stable:

- Users need to see what is happening while synthetic participant interviews run, especially when a live LLM provider is slow, blocked, retrying, or producing participant turns.
- Teams need bounded integration events for study, run, evidence, decision, readiness, and support workflows without turning integrations into an unreviewed reporting channel.

This improves scalable research throughput and evidence quality. It does not improve the synthetic model itself, so every surface must preserve transcript/trace provenance, readiness state, privacy/export controls, and the simulated-evidence boundary.

## Contracts

### `workspace-run-event-stream/v1`

Endpoint:

- `GET /api/v1/studies/{study_id}/runs/{run_id}/events`

Purpose:

- Give the Frontline run detail page and future integration consumers one route-safe event stream shape for queued, interviewing, synthesizing, auditing, blocked, failed, and completed run states.
- Bridge observed-interview or observed-action trace artifacts into the same run monitor when such artifacts exist.
- Expose safe transcript previews and trace references without requiring users to inspect raw filesystem artifacts or CLI output.

Required fields:

- `workspace_id`, `project_id`, `study_id`, `run_id`, `job_id`
- `phase`, `status`, `progress_percent`
- `participant_progress`
- `latest_safe_turn`
- `events[]`
- `transport`
- `observed_interview_bridge`
- `privacy_export_controls`
- `provenance`
- `capabilities`
- `synthetic_boundary`

Boundary rules:

- `latest_safe_turn` may show only a bounded preview from the synthetic participant turn.
- Full transcript and reasoning trace remain available through the existing route-safe transcript and trace APIs.
- Provider/runtime details may exist in backend payloads for auditability, but product chrome must not make provider, job, runtime, payload, or debug concepts the user mental model.
- A future SSE or queue-backed stream must emit the same event shape; polling is the current transport.

### `workspace-integration-events/v1`

Endpoint:

- `GET /api/v1/integration-events`

Purpose:

- Project stable workspace audit and evidence-readiness events into an integration-ready feed.
- Keep external systems attached to durable research objects and review routes.

Supported event types:

- `study.created`
- `run.completed`
- `run.failed`
- `evidence_view.saved`
- `decision.logged`
- `readiness.changed`
- `support.handoff_changed`

Filter parameters:

- `study_id`
- `event_type`
- `limit`

Required event fields:

- `event_id`
- `event_type`
- `source_action`
- `workspace_id`, `project_id`, `study_id`, `job_id`, `run_id`
- `target_type`, `target_id`
- `occurred_at`
- `route_path`
- `payload`
- `delivery`
- `synthetic_boundary`

### `workspace-integration-event-payload/v1`

Purpose:

- Carry only boundary-preserving research state into integrations.
- Preserve provenance and privacy/export controls so downstream tools cannot accidentally present synthetic evidence as human proof.

Required fields:

- `event_type`
- `workspace_id`, `project_id`, `study_id`, `job_id`, `run_id`
- `target_type`, `target_id`
- `readiness_gate`
- `provider_runtime_boundary`
- `provenance.source_audit_event_id`
- `provenance.source_exchange_refs`
- `provenance.source_trace_refs`
- `privacy_export_controls`
- `human_validation_gaps`
- `human_validation_required`
- `synthetic_boundary`

Payload rules:

- `run.completed` and `run.failed` payloads must cite source exchange and trace refs when evidence exists.
- `evidence_view.saved`, `decision.logged`, and `readiness.changed` payloads must preserve readiness gates and human-validation gaps.
- Integration payloads are not launch claims, human validation, or replacement-readiness approval.

### Delivery Attempt Audit

Endpoint:

- `POST /api/v1/integration-events/delivery-attempts`

Purpose:

- Record delivery, retry, failure, skip, or queue state for an integration consumer without performing unaudited outbound delivery from local development.

Required request fields:

- `event_id`
- `consumer_id`
- `status`

Optional request fields:

- `response_code`
- `note`
- `retry_after_seconds`

Supported statuses:

- `queued`
- `delivered`
- `failed`
- `retrying`
- `skipped`

Rules:

- Delivery attempts are appended to workspace settings in the current local-first runtime.
- Each delivery attempt records a payload boundary hash and an audit event.
- Future SaaS/cloud implementation should move delivery attempts to a durable table and use an outbound queue, but must keep the same event and payload boundary.

## Frontline Product Surface

The Frontline Studio now includes:

- `#run-event-stream-panel` on `/studio/studies/{study_id}/runs/{run_id}` for interview phase, progress, participant completion, observed bridge status, safe latest turn preview, and event history.
- Existing run transcript and trace panels remain the primary place to inspect full synthetic exchanges, facilitator trace, and synthetic participant reasoning trace.
- `#integration-events-card` on the workspace home for bounded connected evidence events and delivery audit status.

The user-facing copy must describe this as interview progress, evidence events, transcript, trace, and connected evidence state. It must not make webhook, provider, job, runtime, payload, or internal-stage terms the default product language.

## Non-Goals

- M42 does not implement hosted outbound webhook delivery.
- M42 does not claim real-time SSE transport; current transport is polling with a stable future-compatible event shape.
- M42 does not turn summaries, reports, transcripts, traces, or integration events into human market proof.
- M42 does not replace calibration, human benchmark comparison, or replacement-readiness review.

## Acceptance

- Run event stream API returns queued and completed run states with participant progress, safe transcript preview, observed bridge metadata, transcript/trace provenance, and privacy/export controls.
- Integration event feed exposes stable study, run, evidence, decision, readiness, and support event types with boundary-preserving payloads.
- Delivery attempts can be recorded and audited with retry/failure visibility.
- Frontline UI renders run event stream and connected evidence events without exposing internal product terminology.
- Existing transcript and trace panels remain available so users can inspect rawer synthetic evidence behind processed summaries.

## Verification

Implemented verification includes:

- `python -m unittest tests.unit.test_saas_runtime.SaasRuntimeTest.test_frontline_studio_plan_revision_and_study_report_workflow`
- `python -m py_compile src\ai_validation_swarm\saas\runtime.py src\ai_validation_swarm\saas\api.py`
- `npm -C frontend\frontline_research_studio run build`
- `node scripts\verify_frontline_studio_smoke.mjs`

Outputs remain simulated evidence. M42 improves visibility, provenance, and delivery discipline; it does not validate replacement-grade reliability.
