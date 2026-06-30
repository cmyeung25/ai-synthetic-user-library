# Frontline Research Studio UX Component Design Spec

Status: `planned implementation guide`

Owner layer: Frontline Research Studio product surface.

## Purpose

This spec defines the user-facing screen model, component hierarchy, CTA placement, and UX audit criteria for Frontline Research Studio.

The product must feel like a research workspace for founders, product leads, and researchers.
It must not expose roadmap language, milestone labels, runtime internals, provider controls, job IDs, debug payloads, or engineering progress terms in the default user experience.

## Alignment Check

- Research bottleneck improved: users need to move from a messy research question to a confirmed study, then to evidence-backed decisions without learning internal platform machinery.
- Primary improvements: scalable research throughput, evidence discipline, decision quality, and auditability.
- Why this moves toward replacing interviewer-led work: the interface makes guided study setup, evidence review, comparison, and decision logging understandable enough for a user to complete the research loop without an operator.

## Product UX Doctrine

Use this mental model:

```text
Workspace -> Project -> Study -> Plan -> Run -> Evidence -> Report -> Decision -> Share
```

Do not use this as the visible product model:

```text
milestone -> provider -> job -> runtime -> payload -> debug panel
```

Persistent left navigation shows one drill-down IA level at a time.
It must not flatten every durable object into Level 1, and it must not keep Project and Study navigation permanently visible together.

Left navigation levels:

- Projects level: the rail shows the project list plus an All projects entry. `/studio` remains the workspace homepage route, but it does not need to occupy a permanent nav row when the user's next orientation task is choosing a project.
- Project level: after a project is selected, the rail changes to that project context, shows a back button to Projects, and lists Project overview, New study, and studies inside that project.
- Study level: after a study is selected, the rail changes to that study context, shows a back button to the parent project, and lists Study home, Guided setup, Research attempts, Evidence, Report, Decision, and Share.

`Studies`, `Evidence`, `Decisions`, and `Share` are not unconditional Level 1 nav items. They are contextual routes inside the current Project or Study unless the product later introduces an explicit cross-project aggregate view with a clear user job.

Study-local progress shows the research loop:

- Ask
- Clarify
- Confirm Plan
- Run
- Review Evidence
- Compare
- Decide

## Global Shell

### Components

- Fixed left navigation rail with drill-down levels
- Workspace switcher or workspace identity
- Main route canvas
- Study context header when inside a study
- Evidence boundary strip
- Fixed rail-bottom workspace/account area
- Optional right detail drawer for provenance, source evidence, or plan assumptions

### CTA Placement

- Primary CTA belongs in the main canvas header or the first actionable card.
- Secondary CTAs belong near the object they affect.
- Destructive, governance, export, and advanced controls stay in secondary menus or bottom review panels.

### UX Rationale

The shell should reduce orientation cost.
Users should always know which product object they are looking at and what the next research action is.

### UX Audit Criteria

- A new user can tell whether they are in a workspace, project, study, evidence view, report, or decision.
- Browser refresh preserves the selected object.
- Left navigation never becomes a workflow stepper or a flat list of study-owned objects.
- Only one left-nav level is visible at a time: Projects, Project, or Study.
- Project list is visible from the left navigation at the Projects level when projects exist.
- Project and Study levels expose a back button to the parent level.
- Study-owned routes appear as Study-level navigation only after a study is selected.
- Workspace/account identity stays anchored in the rail bottom instead of competing with research navigation.
- No visible milestone, roadmap, provider, job, runtime, payload, or debug wording appears in the default surface.

## Screen 1: Workspace Home

Route: `/studio`

### User Job To Be Done

As a user, I want to see my active research work and start a new study quickly, so I can move from an open question to a structured research plan.

### Layout

- Top hero: user-facing value statement, not roadmap status.
- Primary CTA card: `Start a new study`.
- Recent studies list: title, project, status, last activity, next action.
- Evidence boundary strip: explains synthetic evidence limits in plain language.
- Secondary area: recent decisions and reports.

### Components

- `WorkspaceHero`
- `StartStudyCard`
- `RecentStudiesList`
- `RecentDecisionsList`
- `EvidenceBoundaryNotice`

### CTA Placement

- Primary CTA: `Start a new study`, top-right of hero or first card.
- Secondary CTA: `Open recent study`, inside each recent study row.
- Tertiary CTA: `View all projects`, under recent studies.

### UX Audit Criteria

- User can start a study in one obvious action.
- User does not need to choose a research mode before describing the question.
- Empty state explains what to do next, not what has not been built yet.

## Screen 2: Projects

Route: `/studio/projects`

### User Job To Be Done

As a user, I want to organize studies by product area, initiative, or client context, so research decisions stay grouped over time.

### Layout

- Project list with study count, active decisions, recent evidence.
- Create project panel.
- Search/filter by active, archived, or collaborator.

### Components

- `ProjectList`
- `ProjectCard`
- `CreateProjectPanel`
- `ProjectFilters`

### CTA Placement

- Primary CTA: `Create project`, top of the list.
- Row CTA: `Open project`.
- Secondary CTA: `Archive project`, hidden in row action menu.

### UX Audit Criteria

- User understands Project as a long-lived research context, not a task.
- Project cards show research usefulness: active studies, recent decisions, evidence gaps.

## Screen 3: Project Detail

Route: `/studio/projects/{project_id}`

### User Job To Be Done

As a user, I want to see all studies and decisions inside one project, so I can continue research without losing prior context.

### Layout

- Project header with project purpose and collaborators.
- Primary CTA: `Start study in this project`.
- Study table grouped by status.
- Recent decisions and open validation gaps.

### Components

- `ProjectHeader`
- `ProjectStudyTable`
- `ProjectDecisionDigest`
- `OpenValidationGapList`

### CTA Placement

- Primary CTA: `Start study in this project`, in header.
- Row CTA: `Open study`.
- Secondary CTA: `Invite collaborator`, in project header utility area.

### UX Audit Criteria

- User can tell what has already been learned inside the project.
- User can distinguish active research from completed decisions.

## Screen 4: New Study Guided Setup

Route: `/studio/studies/new`

### User Job To Be Done

As a user, I want to describe the research I need in my own words, so the system can help me form a valid study without forcing me to learn internal modes.

### Layout

- Conversational intent input as the main focus.
- Optional artifact dropzone below the intent.
- Small context fields: project, study title.
- Research Copilot side panel with one next useful question.
- Draft plan preview appears only after enough context exists.

### Components

- `ResearchIntentComposer`
- `ArtifactDropzone`
- `ProjectStudyFields`
- `ResearchCopilotPanel`
- `DraftPlanPreview`

### CTA Placement

- Primary CTA before plan exists: `Continue`.
- Primary CTA after plan is ready: `Review research plan`.
- Secondary CTA: `Save draft`.
- Tertiary CTA: `Add artifact`, adjacent to artifact area.

### UX Audit Criteria

- User can begin with plain language.
- The page asks only high-signal clarification questions.
- Internal mode labels are hidden or translated into plain-language study type labels.

## Screen 5: Study Home

Route: `/studio/studies/{study_id}`

### User Job To Be Done

As a user, I want one home for the study question, plan state, latest evidence, and open decisions, so I know what to do next.

### Layout

- Study title, purpose, status, and next recommended action.
- Plan state card.
- Latest run card.
- Evidence summary card.
- Open decision card.
- Activity timeline in a lower section.

### Components

- `StudyHeader`
- `NextActionCard`
- `PlanStatusCard`
- `LatestRunCard`
- `EvidenceSummaryCard`
- `DecisionStatusCard`
- `StudyActivityTimeline`

### CTA Placement

- Primary CTA depends on status:
  - Draft/planning: `Continue setup`
  - Ready: `Start research run`
  - Running: `View run progress`
  - Reviewing: `Review evidence`
  - Completed: `Open decision`
- Secondary CTAs: `Revise plan`, `Create report`, `Share findings`.

### UX Audit Criteria

- User knows the next action within five seconds.
- Status labels are human-readable: `Draft`, `Planning`, `Ready to run`, `Running`, `Reviewing`, `Completed`, `Blocked`.
- The page does not expose run IDs, provider names, raw files, or debug state by default.

## Screen 6: Study Setup

Route: `/studio/studies/{study_id}/setup`

### User Job To Be Done

As a user, I want to review what the system inferred before anything runs, so I can prevent wrong target segments, wrong artifacts, or wrong research goals.

### Layout

- Research Copilot conversation on the left or main column.
- Confirmable plan summary on the right.
- Plan sections: goal, target participant, persona panel, artifacts, study type, guide, expected evidence, limitations.
- Persona panel selection should show selectable synthetic participants, panel role, human-difference signals, coverage gaps, and the synthetic-evidence boundary before confirmation.
- Human-validation gap notice before confirmation.

### Components

- `ResearchCopilotThread`
- `PlanSummaryCard`
- `TargetParticipantCard`
- `PersonaLibraryPicker`
- `ArtifactScopeCard`
- `ModeratorGuidePreview`
- `ExpectedEvidenceList`
- `HumanValidationGapNotice`

### CTA Placement

- Primary CTA: `Approve plan`.
- Secondary CTA: `Ask Copilot to revise`.
- Tertiary CTA: `Save draft`.
- Persona picker changes are plan-basis changes. They must update the draft plan preview and must be visible in the final confirmation before execution.

### UX Audit Criteria

- User can inspect all assumptions before execution.
- Plan confirmation is explicit.
- The system does not silently convert chat into a run.
- Selected persona IDs, panel type, sample size, target-audience criteria, and moderator-guide questions are carried into run lineage.

## Screen 7: Runs

Route: `/studio/studies/{study_id}/runs`

### User Job To Be Done

As a user, I want to see the study's research attempts, so I can understand what has been run and whether more evidence is needed.

### Layout

- Run list grouped by status.
- Each row shows purpose, started time, status, evidence readiness, and boundary.
- CTA to start another run only when a confirmed plan exists.

### Components

- `RunList`
- `RunStatusBadge`
- `RunEvidenceReadiness`
- `StartRunPanel`

### CTA Placement

- Primary CTA: `Start another run`, top-right when eligible.
- Row CTA: `Open run`.
- Secondary CTA: `Compare runs`, visible when two or more completed runs exist.

### UX Audit Criteria

- Runs are presented as study attempts, not as jobs.
- Failure and blocked states explain user-relevant next actions.

## Screen 8: Run Detail

Route: `/studio/studies/{study_id}/runs/{run_id}`

### User Job To Be Done

As a user, I want to inspect what happened in one run, so I can judge whether its evidence is usable.

### Layout

- Run status and plan basis at the top.
- Transcript or scenario evidence in the main column.
- Evidence extraction and audit notes in the side column.
- Boundary and limitations visible near the evidence.

### Components

- `RunHeader`
- `RunPlanBasis`
- `TranscriptViewer`
- `EvidenceSliceList`
- `RunAuditSummary`
- `BoundaryNotice`

### CTA Placement

- Primary CTA when completed: `Review evidence`.
- Primary CTA when failed/blocked: `Resolve issue`.
- Secondary CTA: `Save evidence view`.

### UX Audit Criteria

- User sees evidence before accepting summary.
- Run detail preserves plan basis and evidence boundary.
- Technical provider details are available only behind audit/provenance disclosure.

## Screen 9: Evidence Workspace

Route: `/studio/studies/{study_id}/evidence`

### User Job To Be Done

As a user, I want to review and compare evidence, so I can separate stable patterns from uncertain or contradictory signals.

### Layout

- Evidence filter rail: evidence type, run, artifact, theme.
- Main evidence board: slices grouped by objection, trust gap, adoption barrier, confusion, pain, contradiction.
- Comparison panel for run-to-run or segment-to-segment differences.
- Save view panel.

### Components

- `EvidenceFilterRail`
- `EvidenceGroup`
- `EvidenceSliceCard`
- `ComparisonPanel`
- `ContradictionBanner`
- `SaveEvidenceViewPanel`

### CTA Placement

- Primary CTA: `Save evidence view`.
- Secondary CTA: `Compare selected evidence`.
- Tertiary CTA: `Create report from evidence`.

### UX Audit Criteria

- User can tell source evidence from interpretation.
- Contradictions and human-validation gaps are not hidden.
- The page supports comparison without re-explaining the study.

## Screen 10: Saved Evidence View

Route: `/studio/studies/{study_id}/evidence-views/{evidence_view_id}`

### User Job To Be Done

As a user, I want to reopen a named slice of evidence, so I can cite it in a decision or share it with collaborators.

### Layout

- View title, scope, and saved filters.
- Evidence cards.
- Source/provenance drawer.
- Linked decisions and reports.

### Components

- `EvidenceViewHeader`
- `SavedFilterSummary`
- `EvidenceSliceCard`
- `SourceDrawer`
- `LinkedDecisionList`

### CTA Placement

- Primary CTA: `Use in decision`.
- Secondary CTA: `Update saved view`.
- Tertiary CTA: `Share view`.

### UX Audit Criteria

- User can understand why the view was saved.
- Provenance is one click away.
- The evidence boundary travels with the saved view.

## Screen 11: Study Report

Route: `/studio/studies/{study_id}/reports/{study_report_id}`

### User Job To Be Done

As a user, I want a study-level synthesis, so I can understand what the simulated evidence supports and what remains unproven.

### Layout

- Report summary with boundary notice.
- Stable patterns.
- Divergent signals.
- Objections, trust gaps, adoption barriers, confusions.
- Human-validation gaps.
- Evidence citations and included runs.

### Components

- `ReportHeader`
- `BoundaryNotice`
- `PatternSection`
- `DivergenceSection`
- `RiskSignalSection`
- `HumanValidationGapSection`
- `EvidenceCitationList`

### CTA Placement

- Primary CTA: `Create decision from report`.
- Secondary CTA: `Review cited evidence`.
- Tertiary CTA: `Export report`.

### UX Audit Criteria

- Report does not overstate synthetic evidence as proof.
- User can jump from conclusion to evidence.
- Contradictions and gaps are visible before sharing.

## Screen 12: Decision Review

Route: `/studio/studies/{study_id}/decisions/{decision_log_id}`

### User Job To Be Done

As a user, I want to record what I currently believe and why, so the team can act without confusing synthetic signal with human proof.

### Layout

- Decision statement editor.
- Evidence basis panel.
- Confidence and uncertainty section.
- Required human follow-up section.
- Review history.

### Components

- `DecisionStatementEditor`
- `EvidenceBasisPanel`
- `ConfidenceBoundarySelector`
- `HumanFollowUpChecklist`
- `DecisionReviewHistory`

### CTA Placement

- Primary CTA: `Save decision`.
- Secondary CTA: `Attach more evidence`.
- Tertiary CTA: `Mark needs human validation`.

### UX Audit Criteria

- User must separate current belief from proven fact.
- Decision has linked evidence.
- Human follow-up is not optional when evidence is weak or synthetic-only.

## Screen 13: Share View

Route: `/studio/share/{share_bundle_id}`

### User Job To Be Done

As a user, I want to share findings safely, so collaborators understand the decision, evidence, and limits without over-trusting synthetic results.

### Layout

- Share title and audience.
- Current decision.
- Evidence summary.
- Boundary and human-validation gap notice.
- Included report/evidence links.

### Components

- `ShareHeader`
- `DecisionSummaryForShare`
- `EvidenceDigest`
- `BoundaryNotice`
- `IncludedArtifactsList`

### CTA Placement

- Primary CTA: `Copy share link`.
- Secondary CTA: `Export PDF`.
- Tertiary CTA: `Revoke share`.

### UX Audit Criteria

- Shared view keeps evidence boundary visible.
- Public/shared readers can understand what is synthetic-only.
- No internal runtime, milestone, provider, or job terminology appears.

## Current Studio Copy Rules

Replace internal terms in user-facing copy:

- `M29`, `M30`, `milestone`, `roadmap`, `Stage` -> do not show.
- `operator shell` -> do not show in Frontline UI.
- `provider`, `job ID`, `runtime payload`, `API payload`, `debug` -> hide behind audit/provenance if needed.
- `immutable revision` -> `approved plan` or `confirmed plan`.
- `plan revision` -> `plan version` only when the version matters to the user.
- `Product IA` -> `Workspace`.
- `Research workspace IA, not a stepper` -> user-facing research promise.

## Acceptance Checklist

- Every route has one primary user job.
- Every route has one dominant primary CTA.
- Every card has a reason to exist in the research loop.
- The UI starts from user intent, not internal mode taxonomy.
- Evidence is visible before summary.
- Decision logging preserves current belief, evidence basis, and human-validation gaps.
- External users never see milestone, roadmap, provider, job, runtime, payload, debug, or operator wording in the default Studio UI.
