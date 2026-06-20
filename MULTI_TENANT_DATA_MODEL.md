# Multi-Tenant Data Model

## Objective

Define the minimum backend contract that lets the POC become a multi-tenant SaaS system without losing deterministic run behavior.

## Core Entities

### TenantWorkspace

Workspace is the top-level ownership and isolation boundary.

```ts
type TenantWorkspace = {
  workspace_id: string;
  slug: string;
  display_name: string;
  region_code: string;
  data_residency_region: string;
  plan_tier: string;
  status: "active" | "suspended" | "archived";
  created_at: string;
  settings: Record<string, unknown>;
};
```

### WorkspaceMember

```ts
type WorkspaceMember = {
  workspace_id: string;
  user_id: string;
  role: "owner" | "admin" | "editor" | "viewer" | "billing_admin";
  joined_at: string;
};
```

### BriefRevision

```ts
type BriefRevision = {
  brief_revision_id: string;
  workspace_id: string;
  brief_id: string;
  revision_number: number;
  created_by_user_id: string;
  created_at: string;
  brief_payload_path: string;
  checksum: string;
};
```

### ValidationJob

```ts
type ValidationJob = {
  job_id: string;
  workspace_id: string;
  brief_id: string;
  brief_revision_id: string;
  requested_by_user_id: string;
  status: "queued" | "running" | "completed" | "failed" | "canceled";
  priority: "low" | "normal" | "high";
  provider_name: string;
  panel_spec_json: object;
  input_artifact_path: string;
  output_run_path?: string;
  retry_count: number;
  created_at: string;
  started_at?: string;
  finished_at?: string;
};
```

### ValidationRunMetadata

This wraps the existing `ValidationRun` artifact with tenant-aware references.

```ts
type ValidationRunMetadata = {
  run_id: string;
  workspace_id: string;
  job_id: string;
  brief_id: string;
  report_version: string;
  run_status: string;
  provider_name: string;
  selected_persona_count: number;
  successful_response_count: number;
  failed_response_count: number;
  error_count: number;
  object_prefix: string;
  created_at: string;
};
```

### BillingAccount

```ts
type BillingAccount = {
  workspace_id: string;
  provider_name: string;
  provider_customer_ref: string;
  provider_subscription_ref: string;
  price_book_id: string;
  status: "trialing" | "active" | "past_due" | "canceled";
  seat_count: number;
  renewal_at?: string;
};
```

### PersonaCatalogEntry

```ts
type PersonaCatalogEntry = {
  catalog_persona_id: string;
  synthetic_user_id: string;
  scope: "global" | "workspace_overlay";
  workspace_id?: string;
  locale_pack: string;
  market_tags: string[];
  panel_role: string;
  seed_version: string;
  generation_version: string;
  audit_version: string;
  quality_score: number;
  uniqueness_score: number;
  active: boolean;
  artifact_path: string;
  created_at: string;
  last_reviewed_at?: string;
};
```

### MarketDistributionConfig

```ts
type MarketDistributionConfig = {
  market_config_id: string;
  workspace_id?: string;
  config_version: string;
  market_id: string;
  display_name: string;
  default_locale: string;
  target_population: string;
  weights_json: object;
  quota_rules_json: object[];
  exclusion_rules_json: object[];
  overlays: string[];
  created_at: string;
};
```

### SimilarityDecision

```ts
type SimilarityDecision = {
  similarity_decision_id: string;
  source_persona_id: string;
  target_persona_id: string;
  similarity_score: number;
  decision: "keep" | "merge" | "rewrite" | "reject";
  rationale: string;
  reviewer_type: string;
  reviewed_at: string;
};
```

## Isolation Rules

- every brief, job, run, and export belongs to exactly one workspace
- global catalog personas are read-only to tenant workspaces
- workspace overlays can reference global personas but cannot mutate the global source artifact
- audit events must always include `workspace_id` and acting `user_id`

## Mapping from POC Artifacts

### Current POC

- `brief.json`
- `panel.json`
- `raw_responses.json`
- `report.json`
- `run.json`

### SaaS Mapping

- DB row stores ownership, indexing, lifecycle, and plan enforcement metadata
- object storage keeps full artifacts unchanged where possible
- canonical report payload remains useful as the export contract

## Minimal PostgreSQL Table Set

- `workspaces`
- `workspace_members`
- `briefs`
- `brief_revisions`
- `validation_jobs`
- `validation_runs`
- `billing_accounts`
- `persona_catalog_entries`
- `market_distribution_configs`
- `similarity_decisions`
- `audit_events`

## Why This Split

- deterministic domain logic stays file-like and portable
- tenant isolation and queryability move into relational metadata
- large artifacts and future export variants stay out of hot relational rows

