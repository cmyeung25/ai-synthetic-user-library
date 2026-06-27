# Workspace UI Moss Stage 8

This prototype extends the Stage 7 adapter flow into a post-confirmation run monitor.

What it demonstrates:

- the same shared workspace adapter can survive the move from `ready_for_confirmation` into `queued`, `running`, `completed`, and `failed`
- operator-facing queue and worker status can be reviewed without dropping into backend-only concepts
- failure visibility and retry intent can be modeled as part of the same workspace console, not as a separate admin tool

Shared implementation:

- `demo/workspace_ui_shared/workspace_ui_adapter.mjs` now includes run-monitor derivation and Stage 8 demo bundle helpers
- `tests/workspace_ui/test_workspace_ui_run_monitor.mjs` now fixes queued, running, completed, failed, and retry-ready monitor states as executable coverage

Open `demo/workspace_ui_moss_stage8/index.html` in a browser.
