# Workspace UI Moss Stage 12

This prototype connects the integrated workspace shell to the existing authenticated session, `validation-jobs`, and evidence-query APIs.

Current purpose:

- prove the frontend can map a confirmed draft into the current validation-job request contract
- prove live or sample job records can normalize back into shell run-monitor state
- prove completed runs can now query metadata-backed evidence from the local API while moving the shell closer to real runtime behavior

What this stage now demonstrates:

- sample blocked, ready, completed, and failed shell states
- authenticated workspace session loading from `GET /api/v1/session`
- request mapping from draft-plan state into `POST /api/v1/validation-jobs`
- live job listing and detail loading from `GET /api/v1/validation-jobs`
- live completed-run evidence querying from `GET /api/v1/evidence-query`
- shared runtime heartbeat, sync-now, and optional auto-refresh behavior for session, selected job, and completed-run evidence query state
- visible evidence result cards, selected evidence detail, and replay-focus review sourced from either local projection or the backend query response
- selected job normalization back into the shell's run-monitor projection
- explicit separation between real job ingress, backend evidence query, and richer replay work that still depends on trace-bearing artifacts

Linked implementation artifacts:

- `demo/workspace_ui_shared/workspace_runtime_bridge.mjs` now defines the request/response bridge helpers for the validation-job API
- `demo/workspace_ui_shared/workspace_session_runtime_bridge.mjs` now defines the session-aware runtime bridge helpers for authenticated workspace state
- `demo/workspace_ui_shared/workspace_shell_runtime_client.mjs` now defines the shared live runtime client for session, job, and evidence-query fetch/state transitions
- `demo/workspace_ui_shared/workspace_shell_runtime_sync.mjs` now defines the shared polling and heartbeat layer that can keep session, selected job, and completed-run evidence-query state aligned
- `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs` now defines the page-level frontend adapter that the Stage 12 shell can render directly, including a stable review-surface projection for evidence results, selected detail, and replay focus
- `specs/workspace_validation_job_bridge_contract.md` now defines the draft bridge contract
- `specs/workspace_session_runtime_contract.md` now defines the authenticated workspace-session runtime contract
- `specs/workspace_shell_frontend_adapter_contract.md` now defines the page-facing frontend adapter contract on top of the shell bundle and runtime bridge
- `src/ai_validation_swarm/saas/evidence_query.py` now defines the metadata-backed completed-run evidence query projection for the local SaaS runtime
- `demo/workspace_ui_moss_stage12/TESTING_GUIDE.md` now documents how to test Stage 11 and Stage 12 in local-only, sample-mode, and live-mode paths
- `demo/workspace_ui_moss_stage12/ENGINEERING_DEMO_TESTING_ZH.md` now provides a Chinese testing guide for the current engineering demo
- `tests/workspace_ui/test_workspace_runtime_bridge.mjs` now fixes request mapping, submission gating, and job normalization as executable coverage
- `tests/workspace_ui/test_workspace_shell_runtime_client.mjs` now fixes session load, job submission, job listing/detail, evidence-query loading, sample-mode switching, and runtime error handling as executable coverage
- `tests/workspace_ui/test_workspace_shell_runtime_sync.mjs` now fixes missing-token, session-sync, live selected-job sync, evidence-query refresh, and attention-state behavior as executable coverage
- `tests/workspace_ui/test_workspace_shell_frontend_adapter.mjs` now fixes blocked, submission-ready, completed-live, warning-visible, and backend-review-surface frontend adapter projections as executable coverage
- `src/ai_validation_swarm/saas/api.py` now exposes browser-callable CORS headers for both the validation-job and evidence-query routes so this stage can call the local API directly

Optional live mode:

1. bootstrap one local runtime workspace with `bootstrap-saas-workspace`
2. place `briefs/brief.json` and a `personas/` library under that workspace root
3. run `serve-saas-api`
4. open `demo/workspace_ui_moss_stage12/index.html`

Fast local helper:

- double-click `scripts/start_stage12_demo.bat` to bootstrap `ws_api_demo`, sync sample brief and personas, start the static server, restart the SaaS API and worker loop against the current repo code, wait for the authenticated session endpoint to respond, and open the Stage 14 page with the default demo token
- follow `demo/workspace_ui_moss_stage12/TESTING_GUIDE.md` for a structured manual test pass over Stage 11 and Stage 12, including a short smoke test, live-mode checks, and direct API sanity checks
- follow `demo/workspace_ui_moss_stage12/ENGINEERING_DEMO_TESTING_ZH.md` if you want the same testing flow in Chinese

Open `demo/workspace_ui_moss_stage12/index.html` in a browser.
