# Workspace UI Moss Stage 11

This prototype turns the earlier Workspace UI stages into one integrated operator shell.

Current purpose:

- keep conversational intake, plan confirmation, queue and run visibility, and evidence query review inside one page
- prove that the shared workspace adapter, run-monitor, evidence-browser, and evidence-query derivations can compose into one real review shell
- make the next review demo closer to the eventual product boundary instead of another isolated surface

What this stage now demonstrates:

- blocked intake, saved-draft, fallback, and ready-for-confirmation states on the same shell
- confirmed draft progression into queued, leased, running, completed, failed, and retry-ready states
- evidence query and replay-linked review unlocking only after completed state
- explicit runtime bridge mapping between the existing validation-job API and the still-pending metadata-backed query/replay endpoint

Linked implementation artifacts:

- `demo/workspace_ui_shared/workspace_ui_adapter.mjs` now includes a Stage 11 integrated shell bundle builder
- `tests/workspace_ui/test_workspace_ui_shell_bundle.mjs` fixes the Stage 11 integrated shell transitions as executable coverage
- `specs/workspace_ui_adapter_contract.md` remains the base planning adapter contract
- `specs/workspace_evidence_query_contract.md` remains the draft query/replay contract boundary

Open `demo/workspace_ui_moss_stage11/index.html` in a browser.
