# Workspace UI Moss Stage 14

This prototype promotes the Stage 13 shared-shell review surface into a `backend-driven workspace shell`.

Current purpose:

- prove the workspace shell can hydrate session state, selected job state, and evidence-query focus through one backend `workspace-shell` snapshot contract
- prove the same shared shell app controller can drive a more product-like runtime path without falling back to page-local multi-endpoint orchestration
- prove the local shell can move one step closer to the eventual hosted workspace boundary while keeping debug traces secondary

What this stage now demonstrates:

- one shared shell app controller under `demo/workspace_ui_shared/workspace_shell_app.mjs`
- runtime sync now centers on `GET /api/v1/workspace-shell`
- live evidence query focus and replay-step focus can now be refreshed through the same snapshot path
- a product-facing shell composition where runtime inputs, plan status, run queue, session health, and evidence review are foregrounded
- debug payloads still exist behind collapsible details instead of dominating the page

Key linked artifacts:

- `demo/workspace_ui_shared/workspace_shell_app.mjs`
- `demo/workspace_ui_shared/workspace_shell_runtime_client.mjs`
- `demo/workspace_ui_shared/workspace_shell_runtime_sync.mjs`
- `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs`
- `specs/workspace_shell_snapshot_contract.md`
- `tests/workspace_ui/test_workspace_shell_app.mjs`

How to try it:

1. double-click `scripts/start_stage12_demo.bat`
2. open `demo/workspace_ui_moss_stage14/index.html`
3. click `confirmed draft`
4. click `submit live job`
5. click `load shell snapshot`
6. use `start auto refresh` if you want the shell to keep polling
7. once a run completes, click the run card again or change the evidence query controls to re-hydrate the shell snapshot
8. click an evidence result or replay step to verify the selected focus also comes back through the same snapshot endpoint

This stage is still a prototype shell. It is not yet a framework-hosted frontend with persistent app session state or live push updates.
