# Workspace UI Moss Stage 7

This prototype adds a simple frontend state machine on top of the converged single-page flow:

- operator actions mutate the same draft
- the page recomputes queue readiness
- `conversation state`, `draft plan`, `remediation`, and `frontend adapter` views stay aligned
- the page now imports a shared adapter module instead of keeping the derivation logic inline

Open `demo/workspace_ui_moss_stage7/index.html` in a browser.

Shared implementation:

- `demo/workspace_ui_shared/workspace_ui_adapter.mjs` now holds the executable adapter derivation and Stage 7 demo bundle builder
- `tests/workspace_ui/test_workspace_ui_adapter.mjs` now fixes blocked, fallback-ready, queueable, blocked-saved, and queued paths as contract tests

What it demonstrates:

- the workspace UI can be modeled as a derived adapter around one draft plan object
- queueability, fallback readiness, and blocked-draft persistence can be represented as state transitions rather than separate static screens
- the same page can update visible summaries and JSON contracts together when the operator acts
