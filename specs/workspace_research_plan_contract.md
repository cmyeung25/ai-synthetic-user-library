# Workspace Research Plan Contract (Draft)

## Purpose

This document defines the draft plan contract that sits between:

- conversational workspace intake
- progressive clarification
- final user confirmation
- the current or future execution contract

The product goal is to keep the default user path conversational while still producing a structured, auditable object before any run is created.

## Why this contract exists now

Research bottleneck improved:

- users should not need to understand internal mode taxonomy, panel schema, or execution fields before they can start research

What it improves:

- scalable research throughput
- evidence quality
- auditability

Why it still matters before full UI implementation:

- it gives the product surface, future API layer, and backend orchestration a shared vocabulary
- it prevents the conversational intake flow from collapsing into hidden ad hoc state

## Contract position in the stack

The draft plan contract is an application-layer planning object.

It is:

- richer than the current `ValidationJobRequest`
- earlier than the final execution contract
- explicit enough for confirmation, audit, and replay

It should not:

- replace the existing run contract
- pretend unsupported backend capabilities are already executable

## Contract responsibilities

The draft plan contract should capture:

1. what the user is trying to learn
2. what artifacts are currently available
3. what the system inferred
4. what clarifications are still missing
5. what run the system proposes
6. what evidence boundary applies
7. what must be confirmed before execution
8. what human validation gaps remain

## Draft schema

```json
{
  "draft_plan_id": "draft_plan_20260627_proto_01",
  "workspace_id": "ws_hk_ops",
  "created_at": "2026-06-27T20:30:00Z",
  "updated_at": "2026-06-27T20:31:00Z",
  "status": "draft",
  "source_intent": {
    "user_text": "Will HK SMB operators trust this AI assistant enough to try it in the first week?",
    "requested_outcome": "understand trust, setup burden, and likely early abandonment"
  },
  "artifact_refs": [
    {
      "artifact_type": "brief",
      "path": "briefs/founder-brief.json",
      "role": "primary_context"
    },
    {
      "artifact_type": "screenshot",
      "path": "stimulus/screen-01.png",
      "role": "stimulus"
    }
  ],
  "inference": {
    "primary_mode": "prototype_validation",
    "secondary_lenses": ["adoption_barrier_validation"],
    "confidence": "medium",
    "rationale": [
      "screenshots imply prototype-oriented review",
      "first-week trial language implies adoption-risk synthesis"
    ]
  },
  "clarifications": [
    {
      "clarification_id": "panel_stance",
      "question": "Should the first pass use a mainstream or skeptical panel?",
      "status": "open",
      "why_it_matters": "changes synthesis emphasis and persona selection"
    }
  ],
  "proposed_run": {
    "panel_type": "mainstream",
    "sample_size": 5,
    "stimulus_type": "static_screenshot_set",
    "provider_name": "mock",
    "execution_status": "draft_only"
  },
  "evidence_boundary": {
    "allowed_evidence": ["stated_interpretation", "inferred_friction"],
    "forbidden_claims": ["observed_action_trace", "task_completion"],
    "boundary_note": "screenshots do not support observed task evidence"
  },
  "human_validation_gaps": [
    "real task completion remains unproven",
    "observed abandonment remains unproven"
  ],
  "remediation": {
    "blocking_reasons": ["open_clarifications"],
    "missing_inputs": ["panel_stance"],
    "required_artifacts": [],
    "fallback_options": ["save_blocked_draft"],
    "recommended_next_action": {
      "action_type": "answer_clarification",
      "label": "answer_panel_stance"
    }
  },
  "advanced_controls": {
    "mode_override_available": true,
    "persona_filters_available": true,
    "provider_override_available": true
  },
  "confirmation": {
    "required": true,
    "status": "pending",
    "blocking_reasons": ["open_clarifications"]
  },
  "audit": {
    "inferred_by": "workspace_ui",
    "contract_version": "workspace-research-plan/v0-draft"
  }
}
```

## Field notes

### `status`

Allowed values for the draft layer:

- `draft`
- `ready_for_confirmation`
- `confirmed`
- `blocked`
- `canceled`

### `source_intent`

Preserves the user's own framing before the system translates it into internal mode logic.

### `artifact_refs`

Stores all currently known inputs, even when the final backend run may only use a subset.

### `inference`

Captures:

- inferred primary mode
- optional secondary lenses
- confidence
- short rationale

This is what lets the product stay conversational without becoming opaque.

### `clarifications`

Only questions that materially affect:

- mode choice
- panel selection
- evidence quality
- execution feasibility

should appear here.

Do not store filler questions that merely restate the existing intent.

### `proposed_run`

This is the normalized execution proposal after inference and clarification.

It may still be:

- partially unresolved
- blocked by a backend gap
- convertible only for a subset of current runtime capabilities

### `evidence_boundary`

Must state not only what the system can say, but also what it must not imply.

This is essential for keeping synthetic evidence disciplined.

### `confirmation`

No run should be submitted from the conversational path until this section becomes confirmable and the user explicitly agrees.

### `remediation`

This object tells the product what to do when the draft is not queueable yet.

It should capture:

- `blocking_reasons`: why queueing is currently prevented
- `missing_inputs`: missing clarification or structured inputs
- `required_artifacts`: missing files or stimulus materials needed to support the requested evidence
- `fallback_options`: allowed downgrade or preservation paths
- `recommended_next_action`: the single next step the UI should guide by default

This keeps the product from collapsing into a dead disabled button.

## Mapping to the current backend

Today, only a subset of draft plans can map directly into the current backend runtime.

Current executable subset:

- prototype-oriented flows that can be expressed through the current validation job runtime

Example mapping to `ValidationJobRequest`:

- `artifact_refs[brief]` -> `brief_path`
- `artifact_refs[persona_library]` or workspace-default library -> `persona_dir`
- `proposed_run.panel_type` + `sample_size` -> `panel_spec`
- `proposed_run.provider_name` -> `provider_name`
- `confirmation.status == confirmed` -> gate before `submit_validation_job`

Non-directly-executable examples:

- concept-only flows that still lack a dedicated UI-to-backend execution bridge
- live-app requests that exceed the current runtime because live-app capture is not yet implemented

For these cases, the draft plan contract should remain valid while `proposed_run.execution_status` stays blocked or draft-only.

The UI should use `remediation.recommended_next_action` to decide whether to:

- ask one more conversational clarification
- request artifact upload
- confirm an explicit fallback run
- save a blocked draft for later resume

## Frontend adapter projection

The draft plan should remain the application-layer source of truth.

The frontend should derive a UI-facing adapter projection from it rather than inventing a second parallel state model by hand.

For the dedicated adapter boundary, see [workspace_ui_adapter_contract.md](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/specs/workspace_ui_adapter_contract.md>).

Example derived adapter:

```json
{
  "ui_phase": "blocked",
  "visible_blockers": ["missing_prototype_artifacts", "missing_first_task_anchor"],
  "visible_waiting_for": ["onboarding_screenshot_set", "first_task_name"],
  "primary_button": "request_screenshots_and_task_anchor",
  "button_action_type": "request_artifact_upload_and_clarification"
}
```

This adapter should be:

- derived from the draft plan object plus local conversation state
- cheap to recompute after every conversational turn or artifact change
- consistent with every visible summary, button state, and side rail explanation on the page

This lets the frontend behave like a state machine without making the user learn that internal machinery.

## Confirmation requirements

The final confirmation surface should always display:

1. inferred primary mode
2. secondary lenses
3. selected or pending panel shape
4. artifact set
5. evidence boundary
6. expected outputs
7. unresolved assumptions
8. human validation gaps

When a plan is not queueable, the same surface or its immediate next state should also display:

9. blocking reasons
10. minimum required inputs or artifacts
11. explicit fallback options
12. the recommended next action

## Architecture implications

This contract suggests a future application-layer boundary:

- conversational intake layer
- draft plan inference layer
- clarification state layer
- execution adapter layer

The current repository does not yet implement that full chain.

This spec exists so the UI and backend can converge on one planning object before deeper hosted orchestration work begins.
