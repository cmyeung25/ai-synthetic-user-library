# Workspace Project and Study Contract (Draft)

## Purpose

This document defines the first Milestone 11 product-layer contract for:

- `workspace projects`
- `workspace studies`
- study-to-run linkage
- project/study hydration inside the backend-driven workspace shell snapshot

The goal is to introduce durable product objects above raw validation jobs so the hosted frontend can organize research work by `project` and `study` rather than by filesystem paths or standalone run records.

## Why this contract exists

Research bottleneck improved:

- the platform can already execute and review runs, but real teams still need a durable way to group related research work and revisit it later

What this improves:

- scalable research throughput
- evidence discipline
- product usability for real teams
- promotion path from operator shell to full SaaS product surface

Why it matters now:

- Milestone 10 proved the operator workflow
- Milestone 11 requires a project/study structure before share, export, support, and governance surfaces can behave like a real product

## Endpoints

The local SaaS runtime now exposes:

- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `POST /api/v1/studies`
- `GET /api/v1/studies`
- `GET /api/v1/studies/{study_id}`

## Object intent

### Project

Project is the long-lived container for a product area, initiative, or concept family.

Minimum fields:

- `project_id`
- `workspace_id`
- `slug`
- `name`
- `description`
- `status`
- `study_count`
- `latest_study_id`

### Study

Study is the main user-facing research object.

Minimum fields:

- `study_id`
- `workspace_id`
- `project_id`
- `title`
- `status`
- `research_intent`
- `desired_output`
- `first_task`
- `artifact_refs`
- `latest_job_id`
- `run_count`
- `latest_job_status`

## Creation rules

### `POST /api/v1/projects`

Request body:

```json
{
  "name": "Inbox Coach Launch",
  "description": "Operator-facing evidence workspace launch research.",
  "slug": "inbox-coach-launch"
}
```

Response:

```json
{
  "project": {
    "project_id": "project_123",
    "workspace_id": "ws_api_demo",
    "slug": "inbox-coach-launch",
    "name": "Inbox Coach Launch",
    "study_count": 0
  }
}
```

### `POST /api/v1/studies`

Request body:

```json
{
  "project_id": "project_123",
  "title": "Onboarding hesitation study",
  "research_intent": "Find where new operators hesitate during onboarding.",
  "desired_output": "task-friction and continuation risk",
  "first_task": "complete the first onboarding task",
  "artifact_refs": ["sample-onboarding-01.png", "sample-onboarding-02.png"]
}
```

Response:

```json
{
  "study": {
    "study_id": "study_123",
    "project_id": "project_123",
    "status": "draft",
    "run_count": 0
  }
}
```

## Study-to-run linkage

Validation-job submission can now carry:

- `metadata.project_id`
- `metadata.study_id`

When a job is submitted with a visible study:

1. the runtime validates that the study belongs to the same workspace
2. the runtime validates the project/study relationship when both are present
3. the submitted job metadata preserves the product-layer linkage
4. the study updates `latest_job_id`
5. the study can move from `draft` toward `ready`

This keeps product organization outside the research engine while still linking product objects to run artifacts.

## Workspace shell snapshot integration

`GET /api/v1/workspace-shell` now accepts:

- `project_id`
- `study_id`

The response can now include:

- `projects`
- `selected_project_id`
- `selected_project`
- `studies`
- `selected_study_id`
- `selected_study`

This lets the hosted product shell hydrate its project/study context from the same backend-owned snapshot as session, jobs, and evidence review.

## Non-goals

This contract does not yet define:

- project-scoped permission overrides
- threaded comments or approval workflows
- share bundles or export revocation policy
- billing UX
- API token scopes
- support snapshot bundles

Export bundles are now tracked separately in `specs/workspace_export_bundle_contract.md`.
Study collaboration objects are now tracked separately in `specs/workspace_study_collaboration_surface_contract.md`.
The remaining items are later Milestone 11 layers built on top of this contract.

## Verification

Repository coverage:

- `tests/unit/test_saas_runtime.py`

Current implementation entrypoints:

- `src/ai_validation_swarm/saas/job_store.py`
- `src/ai_validation_swarm/saas/runtime.py`
- `src/ai_validation_swarm/saas/api.py`
