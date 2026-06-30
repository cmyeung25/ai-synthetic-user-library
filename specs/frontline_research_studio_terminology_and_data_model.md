# Frontline Research Studio Terminology and Data Model

Status: `implemented foundation`

Owner layer: Frontline Research Studio product surface, SaaS runtime metadata, study planning contract.

Companion UX spec: `specs/frontline_research_studio_ux_component_design_spec.md`.

## Purpose

This document defines the canonical terminology and entity boundaries for the next Frontline Research Studio layer.

The goal is to make the product understandable to real users while keeping the research record auditable enough for evidence review, cross-run comparison, calibration, and decision logging.

## Alignment Check

- Research bottleneck improved: users need to move from a messy research intent to a valid, confirmed study without learning internal mode, provider, job, or artifact schemas.
- Primary improvement: scalable research throughput, evidence discipline, auditability, and decision-quality review.
- Why this moves the platform closer to replacing interviewer-led work: the product can guide study setup, preserve the confirmed plan, run repeatable synthetic research, and aggregate evidence into durable study-level decisions instead of leaving the user with one-off transcripts or opaque chat memory.

## Terminology Doctrine

Use `study` as the primary product object.

Do not make `job`, `run`, `prompt`, `provider`, or `chat thread` the default user mental model.

The Frontline product should teach this hierarchy through use:

```text
Workspace
User
Project
ProjectMember
Study
PlanningConversation
PlanProposal
TargetAudience
PersonaPanelSelection
StudyPlanRevision
Run
RunArtifact
EvidenceSlice
Finding
RunAuditReport
StudyReport
SavedEvidenceView
DecisionLog
ShareBundle / ExportBundle
```

## UI Boundary Decision

Decision: Frontline Research Studio must be implemented as a separate frontend package from the current operator shell.

Chosen package boundary:

```text
frontend/workspace_shell_app        = Operator / Engineering Shell
frontend/frontline_research_studio  = Frontline Research Studio
```

Route boundary for the next implementation milestone:

```text
/app/workspace  = existing operator shell
/studio         = new frontline user app
```

Route architecture rule:

```text
one persistent shell != one page app
```

The Frontline Studio should use route-aware product pages for durable objects while keeping shared navigation, session, and study context persistent.
The target Frontline route map is:

```text
/studio
/studio/projects
/studio/projects/{project_id}
/studio/studies/new
/studio/studies/{study_id}
/studio/studies/{study_id}/setup
/studio/studies/{study_id}/runs
/studio/studies/{study_id}/runs/{run_id}
/studio/studies/{study_id}/evidence
/studio/studies/{study_id}/evidence-views/{evidence_view_id}
/studio/studies/{study_id}/reports/{study_report_id}
/studio/studies/{study_id}/decisions/{decision_log_id}
/studio/share/{share_bundle_id}
```

Route ownership rules:

- Durable research objects need routes when users can revisit, share, compare, or cite them.
- Temporary guided-setup micro-steps do not need separate routes unless they create durable state.
- `Ask`, `Clarify`, and `Confirm Plan` should usually live inside `/studio/studies/{study_id}/setup`.
- `Run`, `Evidence`, `Report`, `DecisionLog`, and `ShareBundle` should be deep-linkable because they carry audit, review, or distribution meaning.
- The left navigation should point to product IA pages and object collections, not to operating-loop anchors.

This is a product and architecture boundary, not a new research engine.

The Frontline package must share:

- the same SaaS runtime API
- the same workspace session and authentication boundary
- the same Project, Study, Run, Evidence, DecisionLog, ExportBundle, and ShareBundle contracts
- the same Codex-backed validation-job worker runtime
- the same synthetic-evidence, calibration, governed-review, and public-claims boundaries

The Frontline package must not depend on:

- Stage 15 DOM anchors
- the Stage 15 shared controller as its primary interaction model
- operator-only debug panels
- raw validation-job payloads as user-facing state

Default hidden fields in Frontline UI:

- `provider_name`
- `job_id`
- `mode_override`
- filesystem paths
- raw API payloads
- quota/admin/debug panels
- provider runtime catalog

Those details remain available in the operator shell, audit surfaces, support diagnostics, export manifests, and internal debug routes.

Rationale:

- the current Stage 15 shell is useful as an engineering/operator console, but it exposes too much runtime machinery for ordinary founders, researchers, or product leads
- a separate package prevents the Frontline Studio from inheriting job-first, provider-first, or debug-first layout debt
- the shared runtime contract keeps evidence discipline and auditability while allowing the user-facing product to optimize for study-first comprehension

## Relationship Model

```text
Workspace 1 -> many Project
User many -> many Project, through ProjectMember
Project 1 -> many Study
Study 1 -> many PlanningConversation
Study 1 -> many PlanProposal
Study 1 -> many StudyPlanRevision
Study.current_plan_revision_id -> StudyPlanRevision
Study 1 -> many Run
Run 1 -> many Transcript
Run 1 -> many EvidenceSlice
Run 1 -> many Finding
Run 1 -> many RunAuditReport
Study 1 -> many StudyReport
Study 1 -> many SavedEvidenceView
Study 1 -> many DecisionLog
Study 1 -> many ExportBundle
ExportBundle 1 -> many ShareBundle
```

Workspace remains the tenancy and isolation boundary. Project membership can narrow who can access a project, but every project still belongs to exactly one workspace.

## Canonical Entities

### User

A human account that can own, edit, review, or view research work.

User is not the same as `SyntheticUser`.

Minimum fields:

```ts
type User = {
  user_id: string;
  email?: string;
  display_name: string;
  status: "active" | "invited" | "suspended";
};
```

### Project

A long-lived container for a product, startup idea, product area, market, or initiative.

Project is where multiple users collaborate over related studies.

Minimum fields:

```ts
type Project = {
  project_id: string;
  workspace_id: string;
  name: string;
  description?: string;
  status: "active" | "archived";
  created_by_user_id: string;
  latest_study_id?: string;
  study_count: number;
};
```

### ProjectMember

The many-to-many boundary between users and projects.

Minimum fields:

```ts
type ProjectMember = {
  project_id: string;
  user_id: string;
  role: "owner" | "editor" | "reviewer" | "viewer";
  joined_at: string;
};
```

### Study

The main user-facing research object.

A Study represents one research question or decision context, not one execution.

Minimum fields:

```ts
type Study = {
  study_id: string;
  workspace_id: string;
  project_id: string;
  title: string;
  purpose: string;
  status:
    | "draft"
    | "planning"
    | "ready_to_run"
    | "running"
    | "reviewing"
    | "completed"
    | "blocked"
    | "archived";
  current_plan_revision_id?: string;
  latest_run_id?: string;
  latest_report_id?: string;
  run_count: number;
  created_by_user_id: string;
};
```

Status rules:

- `draft`: a study exists, but the system does not yet have enough context to propose a run.
- `planning`: the LLM-guided setup is gathering target segment, purpose, artifacts, mode, or moderator guide details.
- `ready_to_run`: a plan proposal is complete enough for user confirmation.
- `running`: at least one run is queued or running from a confirmed plan revision.
- `reviewing`: one or more runs completed and the user is reviewing evidence, comparisons, findings, or decision logs.
- `completed`: the study has a study-level report or decision log that records the current judgment and remaining validation gaps.
- `blocked`: the study cannot proceed because of missing artifacts, unsupported execution, quota/permission issue, or governed-review boundary.
- `archived`: the study is no longer active, but audit/evidence records remain preserved.

Status transition rules:

```text
draft -> planning
planning -> ready_to_run
ready_to_run -> running
running -> reviewing
reviewing -> completed
draft|planning|ready_to_run|running|reviewing -> blocked
blocked -> planning|ready_to_run|running
draft|planning|ready_to_run|reviewing|completed|blocked -> archived
```

Transition ownership:

- Frontline UI may request a transition by creating or updating planning context, confirming a plan, submitting a run, saving a report, or recording a decision.
- SaaS runtime owns the persisted status value and must derive status from durable evidence where possible.
- A completed run should move the study to `reviewing`, not directly to `completed`.
- A study becomes `completed` only when a study-level report or decision log records the current judgment and remaining human-validation gaps.
- A study can become `blocked` from missing artifacts, unsupported mode, quota or permission failure, governed-review gate, provider-runtime failure, or explicit user pause.
- `archived` never deletes run artifacts, plan revisions, evidence views, or decision logs.

### PlanningConversation

The LLM-guided intake session that helps the user create or revise a study plan.

This is product interaction state, not the final research plan.

Minimum fields:

```ts
type PlanningConversation = {
  conversation_id: string;
  study_id: string;
  created_by_user_id: string;
  status: "active" | "converted_to_plan" | "abandoned" | "archived";
  source: "frontline_chat" | "operator_shell" | "api";
  transcript_ref: string;
  extracted_context: Record<string, unknown>;
  latest_plan_proposal_id?: string;
};
```

Boundary:

- The conversation may ask questions, make suggestions, and infer missing context.
- It must not become the audit source for a run unless converted into a confirmed `StudyPlanRevision`.
- Chat-only memory is not enough for evidence audit.

LLM-guided intake responsibilities:

- capture the user's research intent in plain language
- ask only high-signal clarification questions that change study purpose, target segment, artifact needs, evidence quality, or execution feasibility
- infer the likely study purpose and mode without requiring the user to choose internal taxonomy
- propose the minimum artifact set needed for the requested evidence class
- draft a moderator interview guide with required probes, disconfirmation checks, and evidence targets
- surface known limitations and human-validation gaps before execution
- convert the planning conversation into a `PlanProposal`, not directly into a run

LLM-guided intake must not:

- silently start a run
- hide the inferred plan from the user
- treat chat transcript as the durable research artifact
- present synthetic evidence as human proof
- embed the user's desired conclusion into the target segment or synthetic personas
- ask broad form-like setup questions when one targeted clarification is enough

Minimum conversation exit states:

- `needs_clarification`: one or more material inputs are missing
- `ready_for_confirmation`: the plan can be reviewed and approved
- `blocked`: execution cannot proceed because of missing artifacts, unsupported mode, quota/permission, governed-review, or provider readiness
- `converted_to_plan`: the user confirmed a proposal and the runtime created a `StudyPlanRevision`

### PlanProposal

The mutable proposal produced during LLM-guided planning.

Minimum fields:

```ts
type PlanProposal = {
  plan_proposal_id: string;
  study_id: string;
  conversation_id?: string;
  status: "draft" | "needs_clarification" | "ready_for_confirmation" | "rejected" | "confirmed";
  user_goal: string;
  target_segment: string;
  target_audience: TargetAudience;
  artifact_refs: ArtifactRef[];
  study_purpose: "discovery" | "concept_evaluation" | "prototype_validation" | "messaging_validation" | "workflow_mapping" | "other";
  mode_inference: ModeInference;
  moderator_interview_guide?: ModeratorInterviewGuide;
  persona_panel: PersonaPanelSelection;
  evidence_boundary: EvidenceBoundary;
  open_questions: ClarificationQuestion[];
  proposed_by: "llm" | "user" | "system";
};
```

Boundary:

- A proposal can change during conversation.
- A proposal can include LLM suggestions and unresolved assumptions.
- A proposal must keep target-audience assumptions separate from selected synthetic participants. The target audience describes who the study simulates; the persona panel records which synthetic profiles will run.
- A proposal is not executable until the user confirms it.

Proposal conversion rules:

- A `PlanProposal` can be replaced or revised multiple times during one `PlanningConversation`.
- Only the latest user-confirmed proposal can become a `StudyPlanRevision`.
- Confirmation must show user goal, target segment, target-audience criteria, selected persona panel, artifacts, study purpose, mode inference, moderator guide, expected evidence, known limits, and human-validation gaps.
- Rejected proposals remain audit context but cannot start a run.
- A proposal with open blocking questions stays `needs_clarification`.
- A proposal can be `ready_for_confirmation` only when required artifacts, target segment, study purpose, and evidence boundary are explicit enough for the user to approve.

### TargetAudience

The user-facing description of who the study should simulate.

Minimum fields:

```ts
type TargetAudience = {
  summary: string;
  inclusion_criteria: string[];
  excluded_context?: string;
  source: "user" | "llm" | "system";
};
```

Boundary:

- Target audience is an assumption in the plan, not recruited human sampling proof.
- Inclusion criteria should clarify the behavior, decision context, or workflow that matters.
- Exclusions should prevent the platform from turning broad persona descriptions into overclaimed market proof.

### PersonaPanelSelection

The selected synthetic participant set used by the plan.

Minimum fields:

```ts
type PersonaPanelSelection = {
  contract_version: string;
  panel_type: string;
  sample_size: number;
  random_seed: number;
  selected_persona_ids: string[];
  filters: Record<string, unknown>;
  selected_personas: Array<{
    synthetic_user_id: string;
    name: string;
    panel_role?: string;
    occupation?: string;
    location?: string;
    human_difference_axes?: Record<string, unknown>;
    decision_policy?: Record<string, unknown>;
  }>;
  coverage_snapshot: Record<string, unknown>;
  selection_mode: "system_suggested" | "user_selected";
  selection_rationale: string;
  synthetic_boundary: string;
};
```

Boundary:

- Persona panel selection is part of the confirmed plan basis and must be preserved in plan proposals, plan revisions, run metadata, and selected-persona artifacts.
- Selected persona IDs should constrain the actual run panel through deterministic filters when present.
- Coverage gaps should stay visible. The picker improves behavioral-difference coverage, but it does not create human market proof.

### StudyPlanRevision

The immutable, confirmed plan snapshot used by one or more runs.

Minimum fields:

```ts
type StudyPlanRevision = {
  plan_revision_id: string;
  study_id: string;
  revision_number: number;
  confirmed_by_user_id: string;
  confirmed_at: string;
  source_plan_proposal_id?: string;
  user_goal: string;
  target_segment: string;
  target_audience: TargetAudience;
  artifact_refs: ArtifactRef[];
  study_purpose: "discovery" | "concept_evaluation" | "prototype_validation" | "messaging_validation" | "workflow_mapping" | "other";
  mode_inference: ModeInference;
  selected_mode: string;
  selected_secondary_lenses: string[];
  moderator_interview_guide?: ModeratorInterviewGuide;
  persona_panel: PersonaPanelSelection;
  panel_spec: Record<string, unknown>;
  evidence_boundary: EvidenceBoundary;
  human_validation_gaps: string[];
  prompt_version_refs: string[];
};
```

Boundary:

- Every run must reference exactly one `StudyPlanRevision`.
- Plan revisions are append-only.
- Updating a study plan creates a new revision; it does not mutate prior run basis.
- Cross-run comparison must compare runs against their referenced plan revision and explain plan drift when revisions differ.
- `panel_spec` is the execution-facing projection derived from `persona_panel`; the user-facing plan should show `persona_panel`, not raw execution filters.

Revision creation rules:

- The first confirmed plan for a study creates revision `1`.
- Revising target segment, target-audience criteria, selected persona panel, study purpose, artifact scope, selected mode, moderator guide, panel spec, or evidence boundary creates a new revision.
- Cosmetic copy changes in the Frontline UI do not create a revision unless they change the confirmed research basis.
- A `Run` cannot be queued without `plan_revision_id`.
- Study-level reports must list included plan revision IDs.
- Decision logs must preserve the plan revision and evidence context used at the time of decision.

### ModeInference

Mode information belongs to the plan layer, not the user-facing default navigation.

Minimum fields:

```ts
type ModeInference = {
  primary_mode: string;
  secondary_lenses: string[];
  source: "auto_inferred" | "user_override" | "template_default" | "operator_override";
  confidence: "low" | "medium" | "high";
  rationale: string[];
  user_visible_label: string;
  internal_mode_exposed_to_user: boolean;
};
```

Rules:

- Users should describe intent in ordinary language.
- The product may show a plain-language label such as `Concept test`, `Prototype comprehension`, or `Pain discovery`.
- Internal mode IDs such as `pain_point_discovery` or `prototype_validation` can appear in expert or audit views, not as the default choice users must understand.

### ModeratorInterviewGuide

The planned facilitation structure for the study.

Minimum fields:

```ts
type ModeratorInterviewGuide = {
  guide_id: string;
  opening_prompt: string;
  question_sequence: string[];
  required_probes: string[];
  disconfirmation_checks: string[];
  avoid_questions: string[];
  evidence_targets: string[];
};
```

Boundary:

- The guide is part of the confirmed plan revision.
- The actual transcript can diverge, but divergence should be auditable through facilitator trace or run audit.

### Run

One execution of a confirmed plan revision.

Run is not the top-level product object.

Minimum fields:

```ts
type Run = {
  run_id: string;
  study_id: string;
  plan_revision_id: string;
  requested_by_user_id: string;
  provider_name: string;
  status: "queued" | "running" | "completed" | "failed" | "canceled";
  started_at?: string;
  finished_at?: string;
  output_run_path?: string;
  provider_runtime_boundary: "mock_demo" | "live_synthetic" | "unsupported";
};
```

Boundary:

- Run owns execution lifecycle, provider lineage, raw outputs, and run-level artifacts.
- Run does not own the research question, team decision, or study-level conclusion.

### Transcript

The record of simulated participant/facilitator exchanges for one run or one synthetic participant inside a run.

Minimum fields:

```ts
type Transcript = {
  transcript_id: string;
  run_id: string;
  synthetic_user_id?: string;
  transcript_ref: string;
  evidence_boundary: EvidenceBoundary;
};
```

### EvidenceSlice

A queryable, traceable evidence unit extracted from run artifacts.

Minimum fields:

```ts
type EvidenceSlice = {
  evidence_slice_id: string;
  run_id: string;
  study_id: string;
  source_artifact_ref: string;
  evidence_type:
    | "stated_belief"
    | "recalled_behavior"
    | "decision_reconstruction"
    | "stimulus_interpretation"
    | "observed_action"
    | "simulated_risk"
    | "human_validation_gap";
  summary: string;
  quote_or_trace_ref?: string;
  confidence: "low" | "medium" | "high";
};
```

### Finding

A synthesis claim derived from one or more evidence slices.

Minimum fields:

```ts
type Finding = {
  finding_id: string;
  run_id: string;
  study_id: string;
  title: string;
  finding_type: "objection" | "trust_gap" | "adoption_barrier" | "confusion" | "pain_signal" | "contradiction" | "opportunity" | "risk";
  evidence_slice_ids: string[];
  boundary_note: string;
  human_validation_required: boolean;
};
```

Boundary:

- Findings must preserve links back to evidence slices.
- Findings are not human market proof.

### RunAuditReport

Run-level quality, safety, and boundary review.

Minimum fields:

```ts
type RunAuditReport = {
  audit_report_id: string;
  run_id: string;
  audit_type: "quality" | "safety" | "evidence_boundary" | "provider_runtime" | "calibration";
  status: "passed" | "warning" | "failed";
  findings: string[];
  recommended_action?: string;
};
```

### StudyReport

The study-level synthesis across one or more runs.

Minimum fields:

```ts
type StudyReport = {
  study_report_id: string;
  study_id: string;
  included_run_ids: string[];
  included_plan_revision_ids: string[];
  status: "draft" | "ready_for_review" | "final";
  stable_patterns: string[];
  divergent_signals: string[];
  key_objections: string[];
  trust_gaps: string[];
  adoption_barriers: string[];
  prototype_confusions: string[];
  contradictions: string[];
  human_validation_gaps: string[];
  boundary_note: string;
};
```

Boundary:

- A study report aggregates evidence across runs.
- It should explicitly mention plan drift if included runs use different plan revisions.
- It should not overwrite run-level artifacts.

### SavedEvidenceView

A durable review slice created by the user or system.

Examples:

- all trust-gap evidence from run 1 and run 2
- prototype confusion evidence for one CTA
- contradiction review for one target segment

### DecisionLog

The durable judgment artifact.

It records what the team currently believes, what evidence supports it, and what remains unproven.

Decision logs are separate from study reports because users may make multiple decisions from one study.

## ArtifactRef

Artifacts include concept docs, screenshots, prototypes, copy, URLs, browser traces, and generated outputs.

Minimum fields:

```ts
type ArtifactRef = {
  artifact_id: string;
  role: "input_context" | "stimulus" | "prototype" | "copy" | "trace" | "generated_output" | "audit";
  artifact_type: "text" | "image" | "url" | "json" | "video" | "file" | "trace";
  path_or_url: string;
  version?: string;
  checksum?: string;
};
```

## Frontline UX Implications

For detailed route-level screen design, component hierarchy, CTA placement, and UX audit criteria, see `specs/frontline_research_studio_ux_component_design_spec.md`.

The Frontline Research Studio should expose:

- Project as the collaboration and long-lived product context.
- Study as the main working object.
- Plan as the confirmed setup the user approves before execution.
- Run as execution history inside the study.
- Evidence and findings before polished summaries.
- Decision logs as the durable outcome.

The persistent left navigation should reflect the current IA level: project list before selection, project-specific study list after project selection, and study-specific setup/runs/evidence/report/decision/share navigation after study selection.
The research loop `Ask -> Clarify -> Confirm Plan -> Run -> Review Evidence -> Compare -> Decide` is study-local workflow state and should appear inside `Research Copilot` or `Guided Setup`, not as the global navigation model.

The Frontline UI should hide by default:

- provider selection
- raw job IDs
- internal mode taxonomy
- filesystem paths
- API/debug payloads

Those details remain available in operator/debug views and audit surfaces.

## Frontline MVP Scope

The first Frontline MVP must support:

1. Create or select a project.
2. Start a new study through LLM-guided conversational intake.
3. Let the LLM propose target segment, artifact needs, study purpose, inferred mode, and moderator guide.
4. Require explicit user confirmation of the plan.
5. Create an immutable `StudyPlanRevision`.
6. Run at least one live Codex-backed synthetic run from the confirmed plan.
7. Review evidence, findings, and audit/boundary notes inside the study.
8. Generate a study-level report across the included runs.
9. Capture at least one decision log with supporting evidence and human-validation gaps.

## Migration Notes from Current Shell

Current operator shell fields map as follows:

```text
research_intent -> Study.purpose + PlanProposal.user_goal
desired_output -> PlanProposal.study_purpose + StudyReport expected focus
first_task -> ModeratorInterviewGuide evidence target or prototype task
artifact_refs -> ArtifactRef[]
mode_override -> ModeInference source=user_override when explicitly selected
provider_name -> Run.provider_name, hidden from Frontline default UI
job_id -> Run execution metadata, hidden from Frontline default UI
evidence views -> SavedEvidenceView
decision logs -> DecisionLog
```

## Non-Goals

- This spec does not claim the current operator shell already implements the final Frontline UX.
- This spec does not convert synthetic evidence into human proof.
- This spec does not require a production database migration before the Frontline MVP; the local SaaS runtime can implement the model incrementally while preserving file-backed run artifacts.
