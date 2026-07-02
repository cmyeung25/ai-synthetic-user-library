# Milestone 35 Persona Library Readiness and Panel Contract Hardening Design Spec

Status: `implemented`

## Purpose

Milestone 35 hardens the persona-library and panel-selection layer before the platform expands into messaging validation, templates, integrations, or broader SaaS/cloud work.

The current Frontline Studio can select personas and preserve selected IDs through plan and run lineage, but the productized persona-library layer is still not explicit enough about readiness, generation lifecycle, coverage gaps, and selected-panel reproducibility.

## Alignment

1. Research bottleneck improved:
   study setup cannot reliably replace interviewer-led screening if persona readiness, coverage gaps, dynamic generation, and selected-panel snapshots are ambiguous.
2. Platform dimension improved:
   behavioral realism, panel coverage, evidence auditability, calibration, and scalable research throughput.
3. Replacement-work relevance:
   yes. The platform cannot credibly automate participant screening and early panel setup until users can see who is available, why the panel is sufficient, when more personas need to be generated, and exactly which persona versions were used in a run.

## Scope

- make persona-library readiness states explicit in backend and Frontline UI contracts
- align local persona catalog behavior with the accepted `artifact-first, SQL-indexed, object-store-ready` storage rule
- support explicit dynamic gap-fill generation jobs instead of hidden read-time mutation
- preserve selected persona IDs, persona versions, coverage snapshot, and readiness state through plan approval and run artifacts
- separate normal participant personas from public-figure, celebrity, expert, or influencer-inspired simulated lenses

## Non-Goals

- no Postgres or object-storage migration in this milestone
- no production SaaS/cloud deployment
- no replacement-grade persona coverage claim
- no claim that public-figure-inspired lenses represent the real person's view, endorsement, or behavior
- no use of public-figure-inspired lenses as normal participant evidence

## Architecture Boundary

This milestone keeps the local-first implementation shape:

- SQLite remains the local catalog and query layer.
- Local persona artifacts remain the durable source of truth.
- Frontline Studio reads persona readiness and coverage through API contracts instead of direct filesystem assumptions.
- Dynamic generation is represented as an explicit job state, even if the first implementation executes locally.

Future SaaS/cloud migration remains governed by [persona_library_storage_and_saas_contract.md](./persona_library_storage_and_saas_contract.md):

- Postgres for catalog, lifecycle, permissions, readiness, and generation jobs
- object storage for immutable artifacts, manifests, hashes, generation notes, and selected-persona snapshots

## Story Breakdown

1. `story.persona_readiness.catalog_and_state_contract` - `implemented` - `5 SP`
   Outcome: persona library responses expose `ready`, `empty`, `generating`, `failed`, `stale`, and `provisional` states without ambiguous preparing copy.

2. `story.persona_readiness.dynamic_generation_job` - `implemented` - `5 SP`
   Outcome: target-audience coverage gaps can create explicit persona-generation jobs, and newly generated personas start as `provisional` before validation and promotion.

3. `story.persona_readiness.frontline_picker_and_plan_gate` - `implemented` - `5 SP`
   Outcome: the Frontline persona picker blocks or warns on zero selected personas, shows coverage rationale, and preserves selected IDs plus coverage snapshot in the approved plan.

4. `story.persona_readiness.run_snapshot_and_audit_contract` - `implemented` - `3 SP`
   Outcome: every run proves which persona IDs and versions were used through selected-persona snapshots, artifact hashes, and plan lineage.

5. `story.persona_readiness.public_figure_lens_boundary` - `implemented` - `3 SP`
   Outcome: public-figure, celebrity, expert, and influencer-inspired simulated lenses are categorized separately from participant personas and carry explicit unaffiliated synthetic-lens boundary language.

Story point total: `21 SP`

## Exit Criteria

- `GET /api/v1/persona-library` or its successor exposes readiness, coverage, gaps, available personas, and failure states without silently generating personas.
- A separate explicit generation command or endpoint creates gap-fill personas as auditable generation jobs.
- Generated personas are marked `provisional` until validation, duplicate, and coverage checks promote them to `ready`.
- Frontline plan approval cannot accidentally proceed with zero selected personas unless the product explicitly records an allowed exception.
- The run artifact records selected persona IDs, version/hash lineage, coverage snapshot, and whether any selected persona was provisional.
- Public-figure-inspired lenses are not mixed into normal participant pools by default.
- Browser/unit acceptance covers the Frontline picker, zero-selection gate, generation-state handling, and selected-persona run snapshot.

## Implemented Repository Evidence

- `src/ai_validation_swarm/saas/runtime.py` now exposes `frontline-persona-library/v1-readiness`, explicit persona generation jobs, readiness states, lens boundaries, and selected-persona snapshot generation.
- `src/ai_validation_swarm/saas/api.py` exposes `GET /api/v1/persona-library` and `POST /api/v1/persona-library/generation-jobs`.
- `src/ai_validation_swarm/saas/job_store.py` persists workspace persona generation jobs.
- `frontend/frontline_research_studio/src/main.jsx` renders the readiness strip, coverage gaps, persona cards, explicit generation CTA, zero-selection plan/run gates, and selected-persona panel payloads.
- `tests/unit/test_saas_runtime.py::SaasRuntimeTest.test_frontline_studio_plan_revision_and_study_report_workflow` verifies empty readiness, zero-selection rejection, explicit generation job lifecycle, provisional-to-ready lineage, lens boundary exclusion, plan/revision selected IDs, run metadata, and `frontline_persona_panel_snapshot.json`.
- `scripts/verify_frontline_studio_smoke.mjs` verifies the browser path through the persona-library picker, generation CTA, selected-persona setup, plan approval, plan-linked run, evidence, report, decision, share, refresh, layout, and terminology gates.
- Latest acceptance run: `output/playwright/frontline_studio_smoke/2026-06-30T16-47-06-247Z`.

## Sequencing Decision

This milestone should run before Messaging and Positioning Validation.

Reason:

- messaging validation depends on clear target-audience and persona-panel interpretation
- weak persona readiness would make message comprehension evidence look more polished than it is
- hardening persona selection first improves later messaging, templates, and benchmark expansion work

## Boundary Statement

Milestone 35 improves panel setup discipline and persona-library operations. It does not prove human market demand, broad persona coverage, or replacement-grade reliability.
