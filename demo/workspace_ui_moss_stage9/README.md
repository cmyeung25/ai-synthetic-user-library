# Workspace UI Moss Stage 9

This prototype extends the Stage 8 run monitor into an evidence browser and replay surface.

What it demonstrates:

- a completed run can expose artifacts, replay-linked trace steps, and boundary-aware review inside the same workspace console
- evidence browsing is derived from explicit draft, run-record, and evidence-catalog state rather than page-local assumptions
- operators can filter artifacts by family and inspect replay context without dropping into raw filesystem folders

Shared implementation:

- `demo/workspace_ui_shared/workspace_ui_adapter.mjs` now includes evidence-browser derivation and Stage 9 demo bundle helpers
- `tests/workspace_ui/test_workspace_ui_evidence_browser.mjs` now fixes completed-only gating, artifact filtering, selection fallback, and replay-focus behavior as executable coverage

Open `demo/workspace_ui_moss_stage9/index.html` in a browser.
