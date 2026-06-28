# Workspace Shell Framework Host

This app is the framework-owned Milestone 11 frontend host and the implemented Milestone 13 real user research workspace.

Purpose:

- keep `/app/*` route entry inside a repository-owned frontend app
- preserve the existing Stage 15 shared shell controller, route bootstrap, and study-first behavior
- keep the research workflow pages ahead of settings/support/debug surfaces
- own the Milestone 13 `New Study`, `Study Workspace`, and `Evidence Review` page components without moving backend-owned evidence reliability into frontend heuristics

Current implementation shape:

- the app imports the Stage 15 shell document as raw source
- it extracts the shell markup, inline stage styles, and title through `demo/workspace_ui_shared/stage15_shell_document.mjs`
- it mounts the existing shared Stage 15 shell behavior through `demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs`
- it derives the active Milestone 13 page from backend-injected hosted route context
- it renders framework-owned `NewStudyPage`, `StudyWorkspacePage`, and `EvidenceReviewPage` components while preserving shared-controller DOM anchors
- the local SaaS wrapper serves the built app from `dist/` for `/app/*` routes when that build exists

Commands:

- `npm install`
- `npm run build`
- `scripts\build_workspace_shell_app.bat`

Current boundary:

- this app owns page composition and visual hierarchy, while the shared Stage 15 controller remains the runtime action boundary until controller logic is safely migrated behind typed React-facing contracts
