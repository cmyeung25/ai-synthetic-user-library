# Workspace UI Moss Stage 15

This stage is the first Milestone 11 product-surface prototype built on top of the shared workspace shell contracts.

What it demonstrates:

- project creation and selection through the live SaaS runtime API
- study creation and selection inside a project context
- study-first conversational intake bound to the selected study
- live run submission that carries `project_id` and `study_id`
- backend-driven study shell refresh through `GET /api/v1/workspace-shell`
- evidence review that stays contextualized by the selected study instead of floating as a raw run tool
- durable saved evidence views, decision logs, and first-pass decision review threads that preserve review and decision continuity inside the same study
- a study-scoped activity timeline that summarizes cross-artifact run, collaboration, export/share, and support actions from the same study
- export-bundle creation that preserves synthetic boundary, study lineage, job lineage, and durable workspace-local bundle artifacts
- share-bundle creation and revocation with public viewer-safe delivery paths, expiry, and preserved synthetic boundary
- support diagnostics, recent failure digest, and support-snapshot generation for blocked submissions, queued/running visibility, or failed runs
- a first same-origin hosted shell entrypoint through the local SaaS server instead of requiring a separate static server
- route-aware deep links for project, study, saved-evidence-view, decision-log, export, share, support-snapshot, and job context through the same hosted shell
- a framework-owned frontend host under `frontend/workspace_shell_app/` that now fronts those hosted routes, directly owns the full visible Stage 15 shell surface in React, and reuses the same shared controller for route bootstrap and interaction wiring instead of injecting product sections from the prototype document

Why it matters:

- Milestone 10 proved the operator shell
- Milestone 11 needs a real user-facing layer above that shell
- this stage is the first slice where project, study, run, and evidence appear in one coherent product surface

Key linked artifacts:

- `demo/workspace_ui_moss_stage15/index.html`
- `demo/workspace_ui_shared/workspace_shell_app.mjs`
- `demo/workspace_ui_shared/workspace_shell_runtime_client.mjs`
- `src/ai_validation_swarm/saas/api.py`
- `specs/milestone_11_full_saas_product_surface_design_spec.md`
- `specs/workspace_decision_review_surface_contract.md`
- `specs/workspace_project_study_contract.md`
- `specs/workspace_study_activity_surface_contract.md`
- `specs/workspace_support_surface_contract.md`

How to try it:

1. start the local SaaS API with `scripts/start_local_workspace_demo.bat`
2. open `http://127.0.0.1:8011/app/workspace?token=token-api` for the first authenticated bootstrap
3. click `refresh workspace`
4. create or select a project
5. create or select a study
6. write the research intent, desired output, and first task
7. attach artifacts or use the sample-artifact action
8. confirm the plan
9. submit the live job
10. use `load study shell` or `refresh evidence` after the run advances
11. record a decision log, then use the selected decision review area to request review, approve, or leave threaded comments
12. reload the study activity timeline when you want the latest cross-artifact continuity view for the selected study
13. create an export bundle once a completed run is selected
14. create a share bundle from the selected export when you need a viewer-safe public payload
15. load support diagnostics when submission is blocked or a run fails
16. generate a support snapshot when you need a durable operator handoff bundle

The demo launcher now also rebuilds the framework-hosted workspace shell before restarting the API, so `/app/*` routes keep serving the latest frontend host instead of stale build output.

Hosted deep-link routes:

- `/app/workspace`
- `/app/projects/{project_id}`
- `/app/studies/{study_id}`
- `/app/evidence-views/{evidence_view_id}`
- `/app/decision-logs/{decision_log_id}`
- `/app/export-bundles/{export_bundle_id}`
- `/app/share-bundles/{share_bundle_id}`
- `/app/support-snapshots/{support_snapshot_id}`
- `/app/jobs/{job_id}`

The server injects `window.__WORKSPACE_ROUTE_CONTEXT__`, and the shared shell controller bootstraps the matching product object through detail loaders before hydrating the normal workspace-shell snapshot path.

After one successful authenticated bootstrap, the same browser can revisit clean `/app/*` routes without repeating `?token=token-api` because the hosted shell now exchanges that token for a server-backed same-origin browser session. Explicit query tokens still win when provided, and the shell exposes an `end browser session` control so that the hosted session can be cleared from the product surface.

Current limitation:

- this is now server-hosted, route-aware, and fronted by a framework host through the local SaaS wrapper, but it is still not the final fully component-owned Milestone 11 application
- it proves the first hosted study-first shell entrypoint, framework-owned ownership of the full visible Stage 15 operating surface, a first server-backed browser-session bootstrap, first-pass decision-log review workflow, and a first cross-artifact study activity timeline, not the final broader notification layer, broader identity integration, or deeper observability surfaces
