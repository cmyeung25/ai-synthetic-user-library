# Milestone 39: Guided Research Playbooks and Rerun Templates Design Spec

Status: implemented.

Owner layer: Frontline Research Studio, SaaS runtime, study plan revision model, comparison-ready run lineage.

Last updated: 2026-07-02.

## Purpose

Milestone 39 makes common research workflows repeatable for ordinary users without turning the product into a workflow builder.

The platform should help users start discovery, concept evaluation, prototype validation, messaging validation, or adoption-barrier studies from guided playbooks, then rerun a study with a changed audience, artifact, message variant, prototype version, or moderator guide while preserving plan lineage.

## Alignment Check

- Research bottleneck improved: users should not need to learn internal research modes or rebuild a plan manually to repeat a study.
- Primary improvements: scalable research throughput, evidence quality, and comparison discipline.
- North-star fit: repeatable playbooks and reruns move the platform closer to replacing interviewer-led setup work while keeping final plan confirmation explicit.

## Product Rules

- Playbooks are conversational starting points and confirmation-sheet defaults, not rigid workflow-builder nodes.
- Every playbook must still flow through explicit plan confirmation before a run starts.
- Reruns must record what changed and preserve the source run, source plan revision, and comparison context.
- Reruns should make comparison easier than re-explaining the same study.

## Implemented Contract

- `GET /api/v1/research-playbooks` returns a backend-owned playbook catalog for discovery, concept evaluation, prototype validation, messaging validation, and adoption-barrier work.
- `POST /api/v1/studies/{study_id}/frontline-reruns` creates a rerun plan proposal with source run lineage, change summary, selected playbook, inferred mode, expected evidence types, and boundary text.
- Frontline Studio renders guided playbook quick starts in New Study and Study Setup.
- Run detail exposes a prepare-rerun action that creates a comparison-ready plan proposal.

## Acceptance Evidence

- `tests/unit/test_saas_runtime.py` verifies the playbook endpoint and rerun plan contract.
- `scripts/verify_frontline_studio_smoke.mjs` verifies playbook UI and run-detail review surfaces as part of the Frontline smoke path.
- Rerun proposals remain plan proposals until the user explicitly confirms the revised plan.

## Out of Scope

- A node-based workflow builder.
- Automated silent reruns without user confirmation.
- Treating playbook defaults as a substitute for evidence review or human-validation-gap disclosure.
