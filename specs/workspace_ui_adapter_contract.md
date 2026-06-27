# Workspace UI Adapter Contract (Draft)

## Purpose

This document defines the frontend adapter contract that sits between:

- conversational workspace state
- the application-layer `draft plan` object
- the remediation object
- the visible Workspace UI state

The goal is to let the frontend recompute one consistent UI state from one draft-centric source of truth, instead of hand-maintaining separate page text, button states, blockers, and sidecar summaries.

## Why this contract exists

Research bottleneck improved:

- the workspace needs to guide operators from intent to execution or remediation without making them learn internal platform schema

What this improves:

- evidence discipline
- scalable research throughput
- frontend consistency
- implementation clarity between UI and backend

Why it matters now:

- the repo already has Stage 6 and Stage 7 prototypes proving the flow conceptually
- the next implementation step needs a stable adapter boundary, not more page-local prototype logic

## Architecture role

This adapter contract is a frontend-facing projection layer.

It is:

- derived from application state, not a replacement for application state
- specific to the Workspace UI shell
- responsible for view-ready state, button state, and operator guidance

It is not:

- the source of truth for research planning
- the persistence model
- the execution contract sent to backend workers

## Contract layering

This document defines the `base Workspace UI adapter`.

That base adapter is responsible for:

- conversational intake state
- inferred draft-plan state
- remediation and blocker state
- confirmation readiness

It should remain separate from later view-specific derivations such as:

- queue and run status monitor state
- completed-run evidence browser state
- metadata-backed evidence query and replay state

Those later surfaces may compose on top of the same draft and run records, but they should not change the meaning of the base planning adapter.

Recommended layering:

1. conversation state
2. draft plan state
3. base Workspace UI adapter
4. run monitor adapter
5. evidence browser adapter
6. evidence query adapter
7. shell frontend adapter

This keeps the planning flow stable even as post-run review surfaces grow more complex.

## Source-of-truth rule

The source-of-truth order should be:

1. workspace conversation state
2. draft plan object
3. remediation object inside the draft plan
4. derived frontend adapter state

The adapter must be recomputable at any time from the upstream state.

Do not persist the adapter as the canonical platform record unless later implementation evidence proves a need for cached snapshots.

## Adapter scope

The adapter should decide:

1. which phase the page is currently in
2. which blockers are visible
3. which missing inputs or artifacts are still required
4. what the primary next action is
5. whether the draft is blocked, confirmable, queued, or paused
6. which summaries, warnings, and sidecar messages should be shown

## Input contracts

### 1. Conversation state

Minimum frontend conversation state:

```json
{
  "workspace_id": "ws_hk_ops",
  "thread_id": "thread_workspace_new_study",
  "latest_user_intent": "Where do new operators hesitate during onboarding, and do they continue after the first task?",
  "artifact_refs": [
    "founder-brief.json",
    "homepage-copy.md"
  ],
  "clarification_answers": {},
  "selected_fallback": null
}
```

Notes:

- this is UI/session state, not the planning source of truth
- it can contain unsaved local edits before the draft plan is recomputed

### 2. Draft plan object

The adapter expects the application-layer planning object described in [workspace_research_plan_contract.md](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/specs/workspace_research_plan_contract.md>).

Minimum consumed fields:

- `status`
- `source_intent`
- `artifact_refs`
- `inference.primary_mode`
- `inference.secondary_lenses`
- `proposed_run`
- `evidence_boundary`
- `confirmation`
- `remediation`

### 3. Local UI state

Some state is purely local to the shell:

```json
{
  "locale": "en",
  "expanded_sections": ["summary", "adapter_json"],
  "active_panel": "default"
}
```

This local state may affect presentation, but must not change the planning meaning of the draft.

## Output contract

The adapter should output one UI-facing object.

Example:

```json
{
  "ui_phase": "blocked",
  "run_state": "draft",
  "visible_blockers": [
    "missing_prototype_artifacts",
    "missing_first_task_anchor"
  ],
  "visible_waiting_for": [
    "onboarding_screenshot_set",
    "first_task_name"
  ],
  "primary_button": {
    "label": "request_screenshots_and_task_anchor",
    "action_type": "request_artifact_upload_and_clarification",
    "enabled": true
  },
  "secondary_button": {
    "label": "save_blocked_draft",
    "action_type": "save_blocked_draft",
    "enabled": true
  },
  "summary_view": {
    "primary_mode": "prototype_validation",
    "execution_status": "blocked",
    "first_task": null
  },
  "sidecar_view": {
    "status": "blocked",
    "waiting_for": [
      "onboarding screenshots",
      "first task anchor"
    ],
    "primary_action_copy": "Request artifact upload and one clarification"
  }
}
```

## Canonical fields

### `ui_phase`

Allowed values:

- `blocked`
- `ready_for_confirmation`
- `queued`
- `blocked_saved`

This is the primary page-state switch.

This field is intentionally limited to the intake-to-confirmation flow.
Do not overload it with post-run review states such as `running`, `completed_browser`, or `querying`.

### `run_state`

Allowed values:

- `draft`
- `queued`
- `completed`
- `failed`

This should be narrower and more operational than `ui_phase`.

### `visible_blockers`

A UI-ready projection of `draft_plan.remediation.blocking_reasons`.

This field exists so the page does not need to interpret backend-style reason codes at render time everywhere.

### `visible_waiting_for`

A normalized list of what the operator still needs to provide or confirm.

This may combine:

- `required_artifacts`
- `missing_inputs`
- confirmation prerequisites

### `primary_button`

Represents the next recommended operator action.

Fields:

- `label`
- `action_type`
- `enabled`

The adapter should ensure this button text always matches the current draft reality.

### `secondary_button`

Usually:

- save blocked draft
- keep blocked draft
- close and resume later

### `summary_view`

A reduced, stable subset of the draft plan for page summaries.

Do not make page summaries read directly from many nested fields if one normalized adapter subset can keep rendering predictable.

### `sidecar_view`

A normalized projection for:

- status
- waiting_for
- primary_action_copy
- boundary warning

## Derivation rules

### Rule 1: Draft plan wins

If conversation state and draft plan disagree after recomputation, the adapter should render from the latest accepted draft plan object, not from stale page text.

### Rule 2: Remediation drives blocked states

If `remediation.blocking_reasons.length > 0` and no explicit fallback path is confirmable, then:

- `ui_phase = blocked`
- `primary_button.action_type` should come from `remediation.recommended_next_action`

### Rule 3: Fallback can change execution mode

If the operator explicitly chooses a supported fallback:

- the draft plan should change first
- the adapter should then render the fallback as `ready_for_confirmation`

Do not silently downgrade in the adapter without a draft-plan change.

### Rule 4: Queueable means confirmable first

Queueable paths should pass through:

1. `ready_for_confirmation`
2. explicit user confirmation
3. queued state

The adapter should not jump directly from blocked to queued.

### Rule 5: Saved blocked drafts stay blocked

If the operator saves a blocked draft:

- `ui_phase = blocked_saved`
- the stronger research intent remains preserved
- the primary button becomes a resume-oriented or passive state, not a queue action

## Event contract

The adapter must support a finite set of UI events.

Recommended event types:

```json
[
  "artifact_uploaded",
  "clarification_answered",
  "fallback_selected",
  "fallback_cleared",
  "blocked_draft_saved",
  "confirmation_requested",
  "confirmation_accepted",
  "draft_reset"
]
```

Each event should trigger:

1. local state update
2. draft plan recomputation or fetch
3. adapter recomputation
4. UI rerender

## Transition examples

### Example A: blocked -> ready_for_confirmation

Condition:

- screenshots uploaded
- first-task anchor answered

Expected result:

- `visible_blockers = []`
- `ui_phase = ready_for_confirmation`
- `primary_button.action_type = confirm_queueable_plan`

### Example B: blocked -> ready_for_confirmation via fallback

Condition:

- operator selects concept fallback

Expected result:

- draft changes `primary_mode` to `concept_evaluation`
- adapter shows weaker evidence boundary
- `ui_phase = ready_for_confirmation`

### Example C: blocked -> blocked_saved

Condition:

- operator saves without supplementing

Expected result:

- no queue action
- draft remains resumable
- stronger evidence goal remains intact

### Example D: ready_for_confirmation -> queued

Condition:

- operator confirms current plan

Expected result:

- `ui_phase = queued`
- `run_state = queued`
- primary action becomes passive or run-monitoring oriented

## Frontend function boundary

Recommended implementation shape:

```ts
type WorkspaceUiAdapterInput = {
  conversationState: ConversationState;
  draftPlan: DraftPlan;
  localUiState: LocalUiState;
};

type WorkspaceUiAdapterOutput = {
  uiPhase: UiPhase;
  runState: RunState;
  visibleBlockers: string[];
  visibleWaitingFor: string[];
  primaryButton: AdapterButton;
  secondaryButton: AdapterButton;
  summaryView: SummaryView;
  sidecarView: SidecarView;
};

declare function deriveWorkspaceUiState(
  input: WorkspaceUiAdapterInput
): WorkspaceUiAdapterOutput;
```

This should stay a pure derivation function as long as that remains feasible.

Related pure derivation functions may exist beside it, for example:

- `deriveWorkspaceRunMonitorState(...)`
- `deriveWorkspaceEvidenceBrowserState(...)`
- `deriveWorkspaceEvidenceQueryState(...)`

But those should consume stable draft and run records and should not replace the base adapter contract defined here.

## Rendering rule

Every visible surface on the page should read from the adapter output or the draft plan object directly through one normalized rendering boundary.

Avoid:

- one summary reading from raw conversation state
- another summary reading from stale local form fields
- button state derived by independent ad hoc conditions in multiple components

## Verification plan

To know this contract is working:

1. snapshot tests for key adapter outputs:
   - blocked prototype path
   - fallback-ready path
   - queueable prototype path
   - blocked-saved path
2. manual review in the Stage 7 prototype that actions update:
   - conversation thread
   - visible summary
   - sidecar
   - JSON projections
3. future contract tests that ensure backend draft-plan changes still map to stable UI phases

## Current repository evidence

Current evidence for this contract boundary:

- [demo/workspace_ui_moss_stage7/index.html](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/demo/workspace_ui_moss_stage7/index.html>) models a local adapter-driven state machine
- [specs/workspace_research_plan_contract.md](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/specs/workspace_research_plan_contract.md>) defines the upstream planning object the adapter derives from
- [demo/workspace_ui_shared/workspace_ui_adapter.mjs](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/demo/workspace_ui_shared/workspace_ui_adapter.mjs>) now implements the shared executable adapter and related derivation helpers
- [tests/workspace_ui/test_workspace_ui_adapter.mjs](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/tests/workspace_ui/test_workspace_ui_adapter.mjs>) now fixes blocked, fallback-ready, queueable, queued, and blocked-saved transitions as executable contract coverage

This adapter contract exists so the next real frontend implementation does not have to infer state rules from prototype JavaScript.
