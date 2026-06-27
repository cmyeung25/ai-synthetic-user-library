# Workspace UI Moss Stage 10

This prototype extends the Stage 9 evidence browser into a metadata-backed evidence query and replay surface.

What it demonstrates:

- completed-run evidence can be queried through a normalized metadata-backed projection instead of only browsed sequentially
- operators can combine query text, family facets, sort order, result selection, and replay focus inside the same workspace shell
- the frontend can stay aligned with one explicit evidence-query contract before a real metadata-backed API is wired in

Shared implementation:

- `demo/workspace_ui_shared/workspace_ui_adapter.mjs` now includes evidence-query derivation and Stage 10 demo bundle helpers
- `tests/workspace_ui/test_workspace_ui_evidence_query.mjs` now fixes query gating, relevance behavior, facet filtering, selection fallback, and replay-linked selection as executable coverage
- `specs/workspace_evidence_query_contract.md` now defines the draft query-and-replay contract for future metadata-backed implementation

Open `demo/workspace_ui_moss_stage10/index.html` in a browser.
