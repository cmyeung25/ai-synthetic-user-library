# Repository Working Agreement

## Product North Star

- The platform is a `human behavior simulation platform` powered by synthetic users.
- The long-term goal is to replace parts of traditional user research workflows that currently depend on human interviews.
- The first target stages are `discovery`, `concept evaluation`, and `prototype validation`.
- The core value is not automated fake opinions. The core value is behaviorally plausible simulation that helps predict real human decisions, objections, trust gaps, and adoption barriers.

## Current Evidence Boundary

- Do not present current outputs as human market proof.
- Treat current outputs as simulated evidence while the system is being calibrated toward replacement-grade reliability.
- Keep safety, compliance, and high-stakes review boundaries explicit.

## Skill Routing Rule

- Always use [$platform-development-chief](C:\Users\user\.codex\skills\platform-development-chief\SKILL.md) for this repository when making platform-level roadmap, backlog, milestone, status, prioritization, or capability-sequencing decisions.
- When `platform-development-chief` is used for platform UI, UX, workflow, intake, evidence-review, or workspace information-architecture decisions, it must also read and follow `PLATFORM_UI_DESIGN_SYSTEM_PRINCIPLES.md` and `UX_OPERATING_MODEL.md` in the same turn. Treat both as mandatory product-surface doctrine, not optional references.
- If the task also involves system architecture, module boundaries, API contracts, worker design, persistence, deployment, or observability, also consult [$platform-system-architect](C:\Users\user\.codex\skills\platform-system-architect\SKILL.md) in the same turn.

## Mandatory Alignment Check Before Any Work

Before starting a task, confirm:

1. Which research bottleneck does this improve?
2. Does it improve behavioral realism, decision prediction, evidence quality, or scalable research throughput?
3. Does it move the platform closer to replacing interviewer-led work instead of only polishing peripheral workflow?
4. If the answer is no, explicitly justify why the task is still necessary.

## Priority Order

1. Behavioral realism and human difference modeling
2. Decision and adoption prediction quality
3. Evidence discipline, auditability, and calibration
4. Reusable workflows for discovery, concept evaluation, and prototype validation
5. Tooling, reporting, and infrastructure that directly support the items above

## Avoid

- optimizing for polished output without stronger research signal
- baking concept conclusions into personas up front
- treating agreement or eloquence as evidence of realism
- spending cycles on broad SaaS surface area that does not strengthen the core simulation engine
- exposing internal mode taxonomy as the default product mental model
- defaulting to workflow-builder panels, oversized setup forms, or chat-only transient surfaces when a study-first research workspace would preserve stronger evidence discipline
