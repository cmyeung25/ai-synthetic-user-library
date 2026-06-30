# Workspace Billing And Quota Surface Contract

## Status

- contract: `workspace_billing_quota_surface`
- version: `workspace-billing-surface/v0-draft`
- milestone: `Milestone 11`
- status: `in_progress`
- owner: `platform-system-architect`

## Purpose

This contract defines the first writable Milestone 11 billing and quota surface for the local SaaS runtime.

It exists so a real workspace operator can update:

- plan tier
- billing status
- seat count
- renewal visibility
- quota overrides

without editing SQLite rows, patching bootstrap code, or dropping into repo-local scripts.

This improves:

- `scalable_research_throughput` by making quota and seat changes take effect through product-visible controls
- `operational_auditability` by recording billing and quota mutations as audit events
- `evidence_quality` indirectly, because quota and retention policy now stay explicit in the same governance surface that frames synthetic evidence boundaries

## Product Boundary

This is not a real payment-provider integration.

Current scope is intentionally narrow:

- local SaaS runtime billing state
- plan-tier changes
- quota override changes
- visible renewal metadata

Out of scope:

- card collection
- invoice workflows
- customer portal integration
- tax logic
- provider webhooks

## Roles

Readable through authenticated workspace settings:

- `owner`
- `admin`
- `editor`
- `viewer`
- `billing_admin`

Writable through this contract:

- `owner`
- `billing_admin`

Rules:

- `admin` can manage members and tokens, but not billing state through this contract
- `billing_admin` can manage billing state, but not workspace membership

## Endpoint

### `POST /api/v1/workspace-billing`

Updates billing and effective quota state for the current workspace.

Request shape:

```json
{
  "plan_tier": "pro",
  "billing_status": "active",
  "seat_count": 4,
  "renewal_at": "2026-07-31T00:00:00+00:00",
  "daily_runs": 25,
  "max_concurrent_jobs": 3,
  "artifact_retention_days": 30,
  "note": "Upgrade pilot limits for the active design-partner workspace."
}
```

Field rules:

- `plan_tier` must be one of `trial`, `pro`, `enterprise`
- `billing_status` must be one of `trialing`, `active`, `past_due`, `canceled`
- `seat_count` must be greater than `0`
- quota override fields must be integers greater than or equal to `0`
- omitted fields keep current stored values
- `renewal_at` may be empty to clear the visible renewal value
- `note` is optional and is preserved in durable governance history when provided

Response shape:

```json
{
  "billing": {
    "workspace": {
      "workspace_id": "ws_api_demo",
      "plan_tier": "pro"
    },
    "billing_account": {
      "status": "active",
      "seat_count": 4,
      "price_book_id": "pro",
      "renewal_at": "2026-07-31T00:00:00+00:00"
    },
    "plan_limits": {
      "daily_runs": 25,
      "max_concurrent_jobs": 3,
      "artifact_retention_days": 30
    },
    "billing_governance": {
      "contract_version": "workspace-billing-governance/v0-draft",
      "billing_history": [],
      "policy_history": [],
      "latest_billing_change": null,
      "latest_policy_change": null
    }
  },
  "workspace_settings": {}
}
```

Behavior rules:

- changing `plan_tier` updates both `workspace.plan_tier` and `billing_account.price_book_id`
- quota overrides persist inside `workspace.settings`
- billing/account changes append to `billing_governance.billing_history`
- quota and retention changes append to `billing_governance.policy_history`
- the response includes a refreshed `workspace_settings` snapshot so the hosted shell stays on one governance object
- billing/account changes emit `workspace_billing.updated`
- quota/retention policy changes emit `workspace_policy.updated`

## Relationship To Workspace Settings

This contract is consumed as part of the broader Workspace settings surface.

The same hosted shell uses:

- `GET /api/v1/workspace-settings`
- `POST /api/v1/workspace-billing`
- `POST /api/v1/workspace-members`
- `POST /api/v1/api-tokens`
- `POST /api/v1/api-tokens/{token_id}/revoke`

The user should experience these as one secondary governance area, not as multiple unrelated admin pages.

## Runtime Effect

Billing and quota updates must affect the real runtime surfaces that already enforce limits.

Current repository-backed consequences:

- `describe_workspace_session()` returns the updated `plan_tier`, `billing_account`, and `plan_limits`
- validation-job submission uses the updated `daily_runs` and `max_concurrent_jobs`
- retention-aware artifact purge uses the updated `artifact_retention_days`
- support diagnostics and submission-gate summaries reflect the updated effective limits

## Hosted Shell Projection

The Stage 15 hosted shell consumes this contract through:

- `demo/workspace_ui_shared/workspace_shell_runtime_client.mjs`
- `demo/workspace_ui_shared/workspace_shell_app.mjs`
- `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs`
- `demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs`

Current visible shell behaviors:

- update plan tier
- update billing status
- update seat count
- update renewal visibility
- update daily-run, concurrent-run, and retention overrides
- immediately re-render billing and policy summaries from the refreshed `workspace_settings` payload

## Non-Goals

Not included in `v0-draft`:

- payment-provider sync
- invoice history
- overage metering
- seat-assignment workflows
- approval workflow for plan changes
- environment-specific pricing logic

## Verification

Repository evidence:

- `src/ai_validation_swarm/saas/runtime.py`
- `src/ai_validation_swarm/saas/api.py`
- `demo/workspace_ui_moss_stage15/index.html`
- `demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs`
- `tests/workspace_ui/test_workspace_shell_runtime_client.mjs`
- `tests/workspace_ui/test_workspace_shell_app.mjs`
- `tests/workspace_ui/test_workspace_shell_frontend_adapter.mjs`
- `tests/unit/test_saas_runtime.py`

Verification commands:

- `node --test tests/workspace_ui/*.mjs`
- `python -m unittest tests.unit.test_saas_runtime`
