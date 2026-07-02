# Workspace UI Moss Stage 14

This prototype promotes the Stage 13 shared-shell review surface into a `backend-driven workspace shell`.

Current purpose:

- prove the workspace shell can hydrate session state, selected job state, and evidence-query focus through one backend `workspace-shell` snapshot contract
- prove the same shared shell app controller can drive a more product-like runtime path without falling back to page-local multi-endpoint orchestration
- prove the local shell can move one step closer to the eventual hosted workspace boundary while keeping debug traces secondary

What this stage now demonstrates:

- one shared shell app controller under `demo/workspace_ui_shared/workspace_shell_app.mjs`
- the same shared controller now owns editable research intent, desired-output, artifact, and first-task draft mutation instead of relying on scenario-only entry buttons
- runtime sync now centers on `GET /api/v1/workspace-shell`
- live evidence query focus and replay-step focus can now be refreshed through the same snapshot path
- cross-run comparison selection can now be refreshed through the same snapshot path
- backend replay focus can now be derived from concrete run artifacts such as `raw_responses.json`, `stage_results.json`, and `planner.json`
- the visible review surface now projects evidence coverage, selected replay focus, related evidence comparison cards, and initial cross-run comparison cards without making the operator read raw JSON first
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

1. double-click `scripts/start_local_workspace_demo.bat` and let it wait for the local API session endpoint before opening the page
2. open `demo/workspace_ui_moss_stage14/index.html`
3. keep or edit the research intent, desired output, and first-task anchor inside the intake panel
4. click `attach screenshots`
5. click `confirm plan` once the shell shows `ready_for_confirmation`
6. click `submit live job`
7. click `load shell snapshot`
8. use `start auto refresh` if you want the shell to keep polling
9. once a run completes, click the run card again or change the evidence query controls to re-hydrate the shell snapshot
10. click an evidence result, replay step, or comparable run card to verify the selected focus also comes back through the same snapshot endpoint
11. in the current demo data, the shell should show at least one replay card for the selected trace-bearing result after snapshot sync
12. when more than one completed run exists, the shell should also show one comparable run card plus a recommended comparison artifact for that run

This stage is still a prototype shell. It is not yet a framework-hosted frontend with persistent app session state or live push updates.

If you want the next Milestone 11 slice that adds visible project and study management above this shell, open `demo/workspace_ui_moss_stage15/index.html`.
