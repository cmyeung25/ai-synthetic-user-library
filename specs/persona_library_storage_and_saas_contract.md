# Persona Library Storage and SaaS Contract

Status: `accepted`

## Purpose

This contract records the platform decision for how persona libraries should be stored, indexed, backed up, and migrated from local-first development into a future SaaS or cloud environment.

The decision exists because personas are both:

- product data that must be searchable, filterable, selectable, and governable from the UI
- research evidence inputs that must remain auditable, reproducible, versioned, and restorable

## Alignment

1. Research bottleneck improved:
   persona selection, coverage gaps, and dynamic panel generation cannot be trusted if the platform cannot query, audit, restore, and replay the persona records used in a study.
2. Platform dimension improved:
   behavioral realism, panel coverage, evidence auditability, calibration, and scalable research throughput.
3. Replacement-work relevance:
   yes. A system that cannot prove which synthetic humans were selected, generated, validated, and snapshotted for a run cannot credibly replace interviewer-led screening or panel setup work.

## Storage Decision

The accepted direction is `artifact-first, SQL-indexed, object-store-ready`.

Local-first implementation:

- SQLite is the local catalog and query layer.
- Local file artifacts remain the durable source of truth.
- Markdown is a human-readable projection, not the canonical machine record.

Future SaaS/cloud implementation:

- Postgres is the catalog, query, state, permission, and lifecycle layer.
- Object storage is the durable artifact layer for immutable persona JSON and Markdown artifacts.
- Server local disk is cache/export/temp storage only, not the production source of truth.

## Responsibility Split

SQL or Postgres owns:

- persona catalog rows
- workspace/project/library ownership
- readiness status such as `ready`, `provisional`, `generating`, `failed`, `archived`, or `stale`
- search, filtering, and target-audience matching
- human-difference trait indexes
- selected persona IDs
- generation job state
- validation, duplicate, and coverage-check status
- permissions, retention, and tenant boundaries

Artifacts own:

- `profile.json`
- `audit.json`
- `persona.md`
- `generation_notes.json`
- prompt, provider, model, seed, and schema version lineage
- content hash and artifact manifest
- concept sidecars such as `concept_outputs.json`
- run-time selected-persona snapshots

## Versioning Rule

Persona artifacts are append-only once used by a study run.

When a persona changes materially:

- create a new persona version
- preserve the old version
- keep run snapshots pointing to the exact version used at execution time
- do not rewrite prior run evidence to point at a newer persona

## Dynamic Generation Rule

Dynamic generation is a core platform capability, but it must be explicit and auditable.

Rules:

- Reuse existing ready personas first.
- If target-audience coverage is insufficient, the system may recommend generating missing personas.
- Generation should run as an explicit job, not as a hidden side effect of a read request.
- Newly generated personas start as `provisional`.
- Validation, duplicate detection, and coverage checks must pass before promotion to `ready`.
- Runs may use provisional personas only when the plan or audit record explicitly permits it.
- Every generated persona must retain provider, model, prompt, seed, schema, validation, and coverage metadata.

## API Rule

Read endpoints must not silently generate new personas.

Allowed:

- `GET /persona-library` returns library state, readiness, coverage, gaps, and available personas.
- `POST /persona-library/generation-jobs` or an equivalent command creates an explicit generation job.
- `POST /persona-library/imports` or an equivalent command imports existing artifacts into the catalog.

Disallowed:

- a read endpoint that mutates the library without visible user or system action
- a picker that hides `empty`, `failed`, `generating`, or `stale` states behind a generic preparing message

## SaaS Backup and Restore Rule

Future SaaS/cloud storage must restore the database and artifacts as one evidence system.

Database backup expectations:

- point-in-time recovery
- scheduled snapshots
- migration version tracking
- tenant-level export path for governed support or offboarding

Object storage backup expectations:

- object versioning
- content hash or checksum verification
- replication or secondary backup for audit-critical artifacts
- lifecycle policy for failed, temporary, and expired generation artifacts

Restore expectations:

- restore SQL state and object versions together
- verify each artifact against the cataloged content hash
- fail closed when a catalog row points to a missing or hash-mismatched artifact

## Public-Figure and Expert Lens Boundary

Public-figure, celebrity, expert, or influencer-inspired personas must not be mixed into the normal participant persona pool by default.

They should be modeled as lenses such as:

- `public_figure_lens`
- `expert_advisor_lens`
- `influencer_style_lens`
- `founder_critique_lens`

Boundary:

- These lenses can support concept critique, messaging stress tests, and strategy review.
- They are not recruited human evidence.
- They are not proof of the real person's views, endorsement, or likely behavior.
- UI and reports must label them as simulated and unaffiliated.

## Non-Goals

- Do not replace all artifacts with opaque database blobs.
- Do not rely on production local disk as the source of truth in SaaS/cloud.
- Do not bake study-specific concept conclusions into reusable persona core.
- Do not treat generated or public-figure-inspired personas as human market proof.

## Implementation Sequence

1. Keep the current local shape: SQLite indexes plus local persona artifacts.
2. Add explicit catalog/import/readiness rules before expanding Frontline persona management.
3. Add explicit generation jobs for coverage gap-fill rather than hidden read-time generation.
4. When moving to SaaS/cloud, migrate the catalog to Postgres and artifact storage to object storage.
5. Preserve the same artifact manifest, content hash, versioning, and selected-persona snapshot contracts across local and cloud.
