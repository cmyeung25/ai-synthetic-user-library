## Purpose

This contract defines the current Milestone 26 public-launch-readiness layer for:

- one authenticated workspace launch-readiness summary
- one backend-owned `public_claims_boundary` object
- one backend-owned `customer_operations_support_boundary` object
- one backend-owned `self_serve_onboarding_pricing_boundary` object
- one backend-owned `privacy_export_controls` projection from `workspace-privacy-export-controls/v1`
- benchmark disclosure and customer-facing claim limits on export and share artifacts

The goal is to keep broader launch posture tied to benchmark-backed evidence and governed circulation state, not to page-local interpretation or marketing copy.

## Why this contract exists

Research bottleneck improved:

- the platform already supports bounded design-partner circulation, but broader public launch still needs one backend-owned answer to what can be claimed, what remains preview-only, and why

What this improves:

- evidence quality
- auditability
- calibration visibility
- scalable research throughput

Why it matters now:

- readiness-gate, launch-scope, promotion, partner-onboarding, release-review, and governed-boundary contracts already exist
- the next gap is one public-launch posture layer above those contracts

## Endpoints

The local SaaS runtime now exposes:

- `GET /api/v1/public-launch-readiness`

The same launch-readiness object is also embedded inside:

- `GET /api/v1/operations/summary`

## Workspace launch-readiness object

### `GET /api/v1/public-launch-readiness`

Response root:

```json
{
  "launch_readiness": {
    "contract_version": "workspace-public-launch-readiness/v0-draft",
    "workspace_id": "ws_123",
    "overall_status": "controlled_mvp_only",
    "self_serve_public_launch_allowed": false,
    "public_marketing_claims_allowed": true,
    "study_governance": {
      "study_count": 3,
      "high_stakes_study_count": 1,
      "governed_review_required_count": 1,
      "viewer_safe_redaction_required_count": 1
    },
    "benchmark_disclosure": {
      "completed_job_count": 2,
      "readiness_status_counts": {
        "scoped_external_ready": 1,
        "human_validation_required": 1
      },
      "calibration_status_counts": {
        "candidate_replacement_ready": 1,
        "unavailable": 1
      },
      "external_benchmark_status_counts": {
        "scoped_external_ready": 1
      },
      "benchmark_origin_counts": {
        "external_definition": 1
      },
      "source_type_counts": {
        "real_human_study": 1
      }
    },
    "distribution_readiness": {
      "export_bundle_count": 1,
      "share_bundle_count": 1,
      "design_partner_candidate_export_count": 1,
      "approved_public_share_count": 1,
      "claim_boundary_status_counts": {
        "controlled_mvp_only": 1
      }
    },
    "launch_blockers": [
      "public_self_serve_launch_not_yet_approved",
      "replacement_grade_claims_not_allowed"
    ],
    "privacy_export_controls": {
      "contract_version": "workspace-privacy-export-controls/v1",
      "privacy_readiness": {
        "status": "ready_for_customer_review",
        "blocked_reasons": []
      },
      "data_residency": {
        "data_residency_region": "us-east-1"
      },
      "retention_controls": {
        "artifact_retention_days": 30
      },
      "export_share_controls": {
        "export_bundle_count": 1,
        "share_bundle_count": 1
      }
    },
    "customer_operations_support_boundary": {
      "contract_version": "workspace-public-launch-support-boundary/v0-draft",
      "status": "bounded_operator_ready",
      "blocked_reasons": [],
      "supported_paths": [
        "workspace_support_snapshot_and_owner_admin_review",
        "ordinary_study_workspace_support"
      ],
      "unsupported_paths": [
        "unrestricted_public_self_serve_support",
        "replacement_grade_customer_assurance"
      ],
      "billing_and_quota_boundary": {
        "plan_tier": "pro",
        "billing_status": "active",
        "daily_run_limit": 25,
        "max_concurrent_jobs": 3,
        "artifact_retention_days": 30
      },
      "ordinary_study_submission_gate": {
        "status": "allowed",
        "blocked_reason_count": 0,
        "blocked_reasons": []
      },
      "support_playbook": {
        "status": "bounded_ready",
        "support_channel": "workspace_support_snapshot_and_owner_admin_review",
        "manual_operator_memory_required": false,
        "support_snapshot_count": 1,
        "failed_job_count": 0,
        "failed_jobs_missing_support_snapshot_count": 0,
        "open_handoff_count": 0,
        "handoff_status_counts": {
          "unassigned": 1
        },
        "latest_support_snapshot_at": "2026-06-29T09:00:00+00:00"
      },
      "note": "Customer-operations readiness stays backend-owned so support coverage, submission gates, and launch blockers do not depend on manual operator memory."
    },
    "self_serve_onboarding_pricing_boundary": {
      "contract_version": "workspace-self-serve-launch-boundary/v0-draft",
      "status": "bounded_self_serve_ready",
      "blocked_reasons": [],
      "supported_onboarding_paths": [
        "owner_bootstrap_workspace",
        "study_first_guided_intake",
        "workspace_settings_member_and_token_admin"
      ],
      "unsupported_onboarding_paths": [
        "unrestricted_anonymous_signup",
        "payment_provider_self_checkout",
        "enterprise_sso_auto_provisioning"
      ],
      "onboarding_boundary": {
        "status": "ready",
        "owner_count": 1,
        "submitter_member_count": 2,
        "active_token_count": 2,
        "required_steps": [
          "workspace_owner_present",
          "submitter_member_present",
          "active_workspace_token_present",
          "study_first_guided_intake_available"
        ]
      },
      "pricing_boundary": {
        "status": "active_paid_plan",
        "plan_tier": "pro",
        "billing_status": "active",
        "price_book_id": "pro",
        "seat_count": 3,
        "renewal_at": "2026-07-31T00:00:00+00:00",
        "payment_provider_integrated": false,
        "supported_pricing_model": "workspace_plan_tier_with_operator_managed_billing_state"
      },
      "quota_boundary": {
        "status": "ordinary_team_ready",
        "daily_run_limit": 25,
        "max_concurrent_jobs": 3,
        "artifact_retention_days": 30,
        "minimums_for_ordinary_team": {
          "daily_runs": 5,
          "max_concurrent_jobs": 2,
          "artifact_retention_days": 30
        }
      },
      "note": "Self-serve readiness is bounded to authenticated workspace onboarding with operator-managed billing. It does not imply open signup, payment-provider checkout, or replacement-grade customer assurance."
    },
    "customer_claim_boundary": {
      "status": "controlled_mvp_only",
      "blocked_reasons": [
        "public_self_serve_launch_not_yet_approved",
        "replacement_grade_claims_not_allowed"
      ],
      "required_customer_disclosures": [
        "Synthetic evidence only. This output is not human market proof."
      ]
    }
  }
}
```

## `public_claims_boundary`

`public_claims_boundary` is backend-owned.

It is derived from:

- `readiness_gate`
- `mvp_launch_scope`
- `regulated_review_boundary`
- `governed_review`
- `governed_redaction`
- `privacy_export_controls`

It must not be fabricated by frontend heuristics.

Minimum fields:

- `contract_version`
- `status`
- `customer_claim_status`
- `self_serve_public_launch_allowed`
- `allowed_audiences`
- `required_customer_disclosures`
- `prohibited_claims`
- `blocked_reasons`
- `benchmark_disclosure`
- `boundary_note`

Current status meanings:

- `research_preview_only`: synthetic evidence can support internal or bounded review, but public-facing claims remain preview-only
- `governed_preview_only`: high-stakes or governed-review conditions still block broader public-facing launch posture
- `controlled_mvp_only`: scoped external readiness may support bounded design-partner or pilot claims, but self-serve public launch remains blocked
- `bounded_public_candidate`: reserved for later M26 work once broader public-launch boundaries are explicitly approved

If `privacy_export_controls.privacy_readiness.status` is not `ready_for_customer_review`, launch readiness must include `privacy_export_controls_not_ready` in `launch_blockers`.

## Artifact projection rule

The runtime now also projects `public_claims_boundary` into:

- export-bundle summaries
- share-bundle summaries
- export manifests
- share payloads
- public-share payloads

This rule exists so distributed artifacts retain:

- customer-facing claim limits
- benchmark disclosure posture
- replacement-grade prohibitions
- the current launch boundary note

## `customer_operations_support_boundary`

`customer_operations_support_boundary` is backend-owned.

It is derived from:

- workspace billing state
- workspace plan and quota limits
- workspace submission-gate rules
- failed or canceled job coverage
- durable support-snapshot and handoff state

It must not be reconstructed from page-local heuristics or operator memory.

Minimum fields:

- `contract_version`
- `status`
- `blocked_reasons`
- `supported_paths`
- `unsupported_paths`
- `billing_and_quota_boundary`
- `ordinary_study_submission_gate`
- `support_playbook`
- `note`

Current status meanings:

- `bounded_operator_ready`: ordinary-study support coverage is backend-visible and bounded inside the current workspace support model
- `manual_operator_review_required`: customer operations still depend on missing support coverage, blocked submission state, inactive billing, unresolved handoffs, or non-launch-ready plan posture

The support playbook projection keeps these operator-facing launch checks backend-owned:

- whether the support playbook has been exercised
- whether failed jobs are missing support snapshots
- whether support handoffs remain open
- whether manual operator memory is still required to understand launch blockers

## `self_serve_onboarding_pricing_boundary`

`self_serve_onboarding_pricing_boundary` is backend-owned.

It is derived from:

- workspace plan tier
- billing status and price-book alignment
- seat count and renewal visibility
- effective daily-run, concurrency, and artifact-retention limits
- workspace owner, submitter member, and active token availability

It must not be inferred from public pricing copy or frontend-only onboarding state.

Minimum fields:

- `contract_version`
- `status`
- `blocked_reasons`
- `supported_onboarding_paths`
- `unsupported_onboarding_paths`
- `onboarding_boundary`
- `pricing_boundary`
- `quota_boundary`
- `note`

Current status meanings:

- `bounded_self_serve_ready`: the workspace has a supported paid plan, active billing, ordinary-team quota/retention limits, an owner, at least one submitter, and active workspace token coverage
- `self_serve_setup_required`: self-serve launch still depends on plan, billing, quota, retention, owner, submitter, or token setup work

This boundary is intentionally narrower than unrestricted public signup. Current unsupported paths include:

- anonymous open signup
- payment-provider self-checkout
- enterprise SSO auto-provisioning

## Operations-summary rule

`GET /api/v1/operations/summary` now embeds one `public_launch_readiness` object so operators can inspect launch posture from the same backend-owned operations payload instead of combining counts page-locally.

## Non-goals

This contract does not yet define:

- public pricing pages
- open public benchmark dashboards
- replacement-grade public claims
- enterprise procurement disclosure

Those remain later milestone work.
