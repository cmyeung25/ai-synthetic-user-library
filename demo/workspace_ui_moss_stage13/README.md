# Workspace UI Moss Stage 13

This prototype promotes the Stage 12 workspace shell into a more product-facing review surface.

Current purpose:

- prove the workspace shell can depend on one shared shell app controller instead of page-local orchestration
- prove the same runtime bridge can be shown in a more product-first layout where plan, run, and evidence surfaces lead before raw JSON panels
- prove the local shell can move one step closer to the eventual hosted workspace boundary without changing the underlying runtime contract

What this stage now demonstrates:

- one shared shell app controller under `demo/workspace_ui_shared/workspace_shell_app.mjs`
- session, job, evidence-query, sample-mode, and runtime-sync actions routed through that shared app boundary
- a product-facing shell composition where runtime inputs, plan status, run queue, session health, and evidence review are foregrounded
- debug payloads still available behind collapsible details instead of dominating the page

Key linked artifacts:

- `demo/workspace_ui_shared/workspace_shell_app.mjs`
- `demo/workspace_ui_shared/workspace_shell_runtime_client.mjs`
- `demo/workspace_ui_shared/workspace_shell_runtime_sync.mjs`
- `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs`
- `tests/workspace_ui/test_workspace_shell_app.mjs`

How to try it:

1. double-click `scripts/start_stage12_demo.bat`
2. open `demo/workspace_ui_moss_stage13/index.html`
3. click `confirmed draft`
4. click `load workspace session`
5. click `submit live job`
6. use `sync now` or `start auto refresh`
7. once a run completes, click `load live evidence query`

This stage is still a prototype shell. It is not yet a framework-hosted frontend with persistent app session state.
