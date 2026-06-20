# SaaS Backend Blueprint

## Objective

Move the current local POC into a SaaS-ready backend without rewriting the core domain logic.

The migration principle is:

1. keep persona generation, sampling, validation, aggregation, and reporting as reusable domain modules
2. replace local CLI ingress with authenticated API ingress
3. replace local filesystem orchestration with queue-driven workers
4. replace single-user artifacts with workspace-scoped storage, permissions, and audit logs

## Service Decomposition

### API Gateway

- accepts authenticated requests
- resolves workspace context
- applies rate limits and plan limits
- issues idempotency keys for validation-job creation

### Workspace Service

- manages tenant workspaces
- manages member roles and workspace settings
- stores data-residency and retention preferences

### Brief Service

- stores founder briefs and revision history
- validates brief schema before job creation
- tracks which brief revision produced which validation job

### Validation Orchestrator

- creates `ValidationJob` records
- pushes jobs onto queue topics
- coordinates retry policy and dead-letter handling
- writes status transitions visible to dashboard / API clients

### Validation Worker

- runs the existing domain pipeline:
  - load brief
  - select panel
  - run persona responses
  - skeptic review
  - sensitive audit
  - aggregation
  - report generation
- writes canonical run artifacts to object storage

### Persona Catalog Service

- owns the global persona catalog
- manages workspace overlays and market-distribution configs
- manages dedupe, similarity review, and quality score refresh jobs

### Report / Export Service

- resolves run artifacts into API responses
- serves Markdown / JSON / CSV exports
- can generate signed download URLs for large reports

### Billing / Plan Service

- enforces usage ceilings by plan
- tracks seats, run quotas, and overage policy
- integrates with payment provider

### Audit / Compliance Service

- stores immutable audit events
- tracks admin actions, export actions, and privacy-sensitive configuration changes
- supports retention, deletion, and incident investigation

## Queue / Async Design

### Core Queues

- `validation.jobs`
- `validation.retries`
- `persona.catalog.generate`
- `persona.catalog.dedupe`
- `persona.catalog.reaudit`
- `exports.render`
- `audit.events.flush`

### Job Lifecycle

1. API writes `ValidationJob(status=queued)`
2. Orchestrator publishes job envelope with workspace, brief, and panel references
3. Worker leases the job and marks it `running`
4. Worker writes intermediate stage artifacts and heartbeat timestamps
5. Worker marks job `completed` or `failed`
6. Failures exceeding retry budget move to dead-letter queue

### Idempotency Rules

- job creation must accept an idempotency key
- workers must treat run directory / object prefix as deterministic per job attempt
- export generation should be safe to rerun

### Concurrency Guardrails

- workspace-level max concurrent jobs
- plan-tier max daily runs
- provider-level circuit breaker if downstream LLM provider degrades
- backpressure when queue latency exceeds SLA threshold

## Storage Split

### PostgreSQL

- workspaces
- users and memberships
- briefs and brief revisions
- validation jobs
- validation run metadata
- billing accounts
- catalog metadata
- audit events

### Object Storage

- run artifacts
- reports
- exported CSV / Markdown / JSON packages
- persona artifact bundles when catalog entries are materialized

### Optional Secondary Indexes

- vector index for persona similarity search
- search index for briefs, reports, and audit events
- OLAP warehouse for usage analytics

## Auth / Billing / Privacy Design

### Auth

- tenant-aware RBAC with `owner`, `admin`, `editor`, `viewer`, `billing_admin`
- SSO can be added later, but RBAC contract should exist now
- every mutation must carry acting user ID and workspace ID

### Billing

- usage dimensions:
  - validation jobs
  - concurrent runs
  - stored persona overlays
  - export volume
- plan enforcement should happen before queue submission when possible

### Privacy

- workspace-level data residency field
- configurable artifact retention window
- hard separation between:
  - global catalog personas
  - workspace overlay personas
  - workspace run artifacts
- export and deletion events must be auditable

## Migration Path from POC

### What stays

- `domain`
- `personas`
- `sampling`
- `validation`
- `reporting`
- `evaluation`

### What changes

- CLI commands become API handlers or background jobs
- `runs/` becomes object-storage prefixes plus DB metadata rows
- `configs/markets/*.json` become admin-managed records with versioning

## Recommended Rollout

### Phase 1

- single-region API
- single queue
- PostgreSQL + object storage
- mock / one provider backend

### Phase 2

- workspace dashboard
- billing enforcement
- audit log UI
- persona overlay support

### Phase 3

- global catalog service
- market-distribution planner
- dedupe and governance jobs
- multi-region data residency

