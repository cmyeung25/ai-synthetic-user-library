# Milestone 16 Design Spec: Post-Login Workspace IA and Active-Route Shell

Status: `implemented`

Owner: `platform-development-chief`

Date: `2026-06-29`

## Purpose

Milestone 16 turns the accepted post-login IA into executable frontend behavior.

The research bottleneck is that a real user logging in still sees a long composed shell instead of a route-owned research workspace. That weakens study continuity, makes evidence review compete with settings/support/debug surfaces, and slows the path from research intent to decision.

## Alignment Check

- Research bottleneck improved: logged-in users need to continue a study, review evidence, compare runs, and decide without reconstructing context from a long admin-style page.
- Primary improvement: evidence discipline, decision workflow continuity, and scalable research throughput.
- Replacement-workflow relevance: the shell now follows the interviewer-led loop: frame the study, run, review evidence, compare, decide, and share with explicit boundaries.
- Boundary: this milestone improves product usability and evidence workflow continuity. It does not itself prove behavioral realism or replacement-grade reliability.

## Scope

Implemented:

- shared post-login IA route model for primary navigation, secondary navigation, active surfaces, landing rules, and deep-link handling
- active-route shell in `frontend/workspace_shell_app` where only the active primary or secondary surface is expanded
- default workspace landing rule for active-study versus no-study workspaces
- deep-link mapping so job and evidence routes open Evidence Review instead of raw job management
- secondary governance/support navigation that remains reachable without becoming the landing model
- source and CSS acceptance tests for hidden inactive surfaces, route metadata, nav order, and sidecar width regression

Out of scope:

- production hosted routing for every future `/app/settings/*` and `/app/support/*` path
- replacing the Stage 15 shared controller with React-owned form state
- claiming human market proof from synthetic outputs

## Architecture

The canonical model lives in:

- `demo/workspace_ui_shared/post_login_workspace_ia.mjs`

The React host consumes that model in:

- `frontend/workspace_shell_app/src/Stage15WorkspaceShellHost.jsx`
- `frontend/workspace_shell_app/src/RealUserWorkspaceNav.jsx`

The route model emits:

- `contract_version`
- `active_route_kind`
- `active_surface_id`
- `active_nav_id`
- `landing_rule`
- `preserves_study_context`
- `primary_navigation`
- `secondary_navigation`
- `acceptance_gates`

Inactive surfaces remain mounted but hidden. This preserves Stage 15 controller DOM anchors while preventing the visible product from behaving like one long page.

## Route Rules

| Route kind | Active surface | Active nav | Rule |
| --- | --- | --- | --- |
| `workspace` with active study | `study-workspace` | `studies` | continue latest study |
| `workspace` with no study | `new-study` | `new-study` | start conversational intake |
| `new_study` | `new-study` | `new-study` | explicit new-study route |
| `project` / `study` | `study-workspace` | `studies` | preserve project/study context |
| `job` / `evidence_view` | `evidence-review` | `evidence` | evidence-first deep link |
| `decision_log` | `evidence-review` | `decisions` | decision review inside evidence context |
| `export_bundle` / `share_bundle` | `evidence-review` | `evidence` | review before distribution |
| `support_snapshot` | `support` | `support` | secondary support surface |

## Acceptance Criteria

- post-login landing follows active-study, no-study, and deep-link rules
- only the active route surface is expanded in the visible shell
- primary nav is `New Study`, `Studies`, `Evidence`, `Decisions`, `Activity`
- secondary nav is `Workspace settings`, `Support`, `Billing`, `API tokens`, `Retention / governance`
- `/app/jobs/{job_id}` maps to Evidence Review and preserves study context intent
- settings, billing, API, support, and debug do not appear as default landing surfaces
- CSS prevents the previous fixed sidecar overlap regression and hides inactive surfaces
- tests prove research route surfaces are declared before settings/support/debug

## Verification

Automated coverage:

- `node --test tests/workspace_ui/test_milestone16_post_login_workspace_ia.mjs`
- `node --test tests/workspace_ui/test_milestone13_real_user_workspace.mjs`
- `npm --prefix frontend/workspace_shell_app run build`

Browser acceptance remains required for future hosted smoke runs:

- no critical overlap
- no text occlusion in dense evidence grids
- no fixed or sticky layer blocking primary research actions
