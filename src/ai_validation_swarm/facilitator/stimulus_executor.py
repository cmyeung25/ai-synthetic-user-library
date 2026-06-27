from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


SCRIPTED_CLICKABLE_EXECUTOR_VERSION = "clickable-prototype-executor/v1"

_TERMINAL_RESULTS = {"error", "failed", "failure", "stopped", "abandoned"}
_PARTIAL_RESULTS = {"backtrack", "partial_success"}


@dataclass(slots=True)
class StimulusExecutionError(ValueError):
    issues: list[str]

    def __str__(self) -> str:
        if not self.issues:
            return "Stimulus execution failed."
        return "Stimulus execution failed: " + "; ".join(self.issues)


class StimulusExecutor(Protocol):
    executor_id: str
    executor_version: str

    def can_execute(self, *, stimulus_type: str, payload: dict[str, Any], artifact_path: Path) -> bool:
        ...

    def execute(
        self,
        *,
        artifact_path: Path,
        payload: dict[str, Any],
        prototype_task: str,
    ) -> dict[str, Any]:
        ...


class ScriptedClickablePrototypeExecutor:
    executor_id = "scripted-clickable-manifest"
    executor_version = SCRIPTED_CLICKABLE_EXECUTOR_VERSION

    def can_execute(self, *, stimulus_type: str, payload: dict[str, Any], artifact_path: Path) -> bool:
        return (
            stimulus_type == "clickable"
            and isinstance(payload, dict)
            and isinstance(payload.get("screens"), list)
            and isinstance(payload.get("task_script"), list)
        )

    def execute(
        self,
        *,
        artifact_path: Path,
        payload: dict[str, Any],
        prototype_task: str,
    ) -> dict[str, Any]:
        issues: list[str] = []
        screens_raw = payload.get("screens", [])
        task_script_raw = payload.get("task_script", [])
        if not screens_raw:
            issues.append("Clickable prototype manifest requires a non-empty 'screens' array.")
        if not task_script_raw:
            issues.append("Clickable prototype manifest requires a non-empty 'task_script' array.")
        if issues:
            raise StimulusExecutionError(issues)

        screens: dict[str, dict[str, Any]] = {}
        ordered_screen_ids: list[str] = []
        for index, item in enumerate(screens_raw):
            if not isinstance(item, dict):
                issues.append(f"'screens[{index}]' must be an object.")
                continue
            screen_id = str(item.get("id", "")).strip()
            if not screen_id:
                issues.append(f"'screens[{index}].id' must be a non-empty string.")
                continue
            if screen_id in screens:
                issues.append(f"Duplicate screen id '{screen_id}' in clickable prototype manifest.")
                continue
            actions_raw = item.get("actions", [])
            if not isinstance(actions_raw, list) or not actions_raw:
                issues.append(f"'screens[{index}].actions' must be a non-empty array.")
                continue
            actions_by_id: dict[str, dict[str, Any]] = {}
            for action_index, action in enumerate(actions_raw):
                if not isinstance(action, dict):
                    issues.append(f"'screens[{index}].actions[{action_index}]' must be an object.")
                    continue
                action_id = str(action.get("id", "")).strip()
                if not action_id:
                    issues.append(f"'screens[{index}].actions[{action_index}].id' must be a non-empty string.")
                    continue
                if action_id in actions_by_id:
                    issues.append(f"Duplicate action id '{action_id}' inside screen '{screen_id}'.")
                    continue
                actions_by_id[action_id] = action
            screens[screen_id] = {
                "id": screen_id,
                "label": str(item.get("label", screen_id)).strip() or screen_id,
                "actions": actions_by_id,
            }
            ordered_screen_ids.append(screen_id)

        if issues:
            raise StimulusExecutionError(issues)

        start_screen = str(payload.get("start_screen", ordered_screen_ids[0])).strip() or ordered_screen_ids[0]
        if start_screen not in screens:
            raise StimulusExecutionError([f"start_screen '{start_screen}' does not exist in the clickable prototype manifest."])

        actions: list[dict[str, Any]] = []
        current_screen = start_screen
        visited_screens = [current_screen]
        first_error = str(payload.get("first_error", "")).strip()
        drop_off_point = str(payload.get("drop_off_point", "")).strip()

        for step_index, raw_step in enumerate(task_script_raw, start=1):
            if isinstance(raw_step, str):
                action_id = raw_step.strip()
                step_note = ""
                expected_result = ""
            elif isinstance(raw_step, dict):
                action_id = str(raw_step.get("action_id", raw_step.get("id", ""))).strip()
                step_note = str(raw_step.get("note", "")).strip()
                expected_result = str(raw_step.get("expect_result", "")).strip().lower()
            else:
                raise StimulusExecutionError([f"'task_script[{step_index - 1}]' must be a string or object."])

            if not action_id:
                raise StimulusExecutionError([f"'task_script[{step_index - 1}]' requires a non-empty action_id."])

            screen = screens[current_screen]
            action = screen["actions"].get(action_id)
            if action is None:
                raise StimulusExecutionError(
                    [f"Action '{action_id}' is not available on screen '{current_screen}' during task step {step_index}."]
                )

            result = expected_result or str(action.get("result", "success")).strip().lower() or "success"
            target = str(action.get("target", action.get("label", action_id))).strip() or action_id
            note = step_note or str(action.get("note", "")).strip()
            next_screen = str(action.get("next_screen", current_screen)).strip() or current_screen

            record = {
                "step": step_index,
                "action": str(action.get("action", action_id)).strip() or action_id,
                "target": target,
                "screen": screen["label"],
                "result": result,
                "note": note,
                "raw_metadata": {
                    "executor_id": self.executor_id,
                    "action_id": action_id,
                    "from_screen_id": current_screen,
                    "next_screen_id": next_screen,
                },
            }
            actions.append(record)

            if not first_error and result in _TERMINAL_RESULTS | _PARTIAL_RESULTS:
                first_error = note or f"{record['action']} ended with result={result}."
            if not drop_off_point and result in _TERMINAL_RESULTS | _PARTIAL_RESULTS:
                drop_off_point = target

            if next_screen not in screens:
                raise StimulusExecutionError(
                    [f"Action '{action_id}' points to unknown next_screen '{next_screen}' from screen '{current_screen}'."]
                )

            current_screen = next_screen
            if visited_screens[-1] != current_screen:
                visited_screens.append(current_screen)

            if bool(action.get("terminal", False)) or result in _TERMINAL_RESULTS:
                break

        task_outcome = str(payload.get("task_outcome", "")).strip().lower()
        if not task_outcome:
            task_outcome = self._derive_task_outcome(actions)
        summary = str(payload.get("summary", "")).strip() or self._build_summary(actions, task_outcome)
        observed_summary = _string_list(payload.get("observed_summary", payload.get("what_was_observed", [])))
        if not observed_summary:
            observed_summary = [
                f"Executed {len(actions)} scripted action(s) against the clickable prototype manifest.",
                f"Visited screens: {', '.join(screens[screen_id]['label'] for screen_id in visited_screens)}.",
                f"Prototype task: {prototype_task or '(none supplied)'}",
            ]
        missing_signals = _string_list(payload.get("missing_signals", payload.get("missing_observed_signals", [])))
        completion_notes = str(payload.get("completion_notes", "")).strip()
        if not completion_notes:
            completion_notes = (
                "Task path completed inside the scripted clickable manifest."
                if task_outcome == "success"
                else "Task path stopped before full completion inside the scripted clickable manifest."
            )

        return {
            "executor_id": self.executor_id,
            "executor_version": self.executor_version,
            "stimulus_analysis": {
                "analysis_type": "clickable_manifest",
                "summary": summary,
                "prototype_label": str(payload.get("prototype_label", artifact_path.stem)).strip() or artifact_path.stem,
                "screen_count": len(screens),
                "task_step_count": len(task_script_raw),
                "start_screen": screens[start_screen]["label"],
                "visited_screens": [screens[screen_id]["label"] for screen_id in visited_screens],
                "evidence_boundary": (
                    "Scripted clickable prototype execution only. Actions were executed from the supplied manifest task loop, "
                    "not captured from a live human session."
                ),
            },
            "observed_action_trace": {
                "trace_version": "observed-action-trace/v1",
                "trace_label": str(payload.get("trace_label", artifact_path.stem)).strip() or artifact_path.stem,
                "task_outcome": task_outcome,
                "summary": summary,
                "actions": actions,
                "observed_summary": observed_summary,
                "missing_signals": missing_signals,
                "first_error": first_error,
                "drop_off_point": drop_off_point,
                "completion_notes": completion_notes,
                "artifact_sha256": _file_sha256(artifact_path),
            },
        }

    @staticmethod
    def _derive_task_outcome(actions: list[dict[str, Any]]) -> str:
        results = [str(action.get("result", "")).strip().lower() for action in actions]
        if any(result in {"error", "failed", "failure"} for result in results):
            return "failure"
        if any(result in {"stopped", "abandoned"} for result in results):
            return "partial_success" if len(actions) > 1 else "abandoned"
        if any(result in _PARTIAL_RESULTS for result in results):
            return "partial_success"
        return "success"

    @staticmethod
    def _build_summary(actions: list[dict[str, Any]], task_outcome: str) -> str:
        if not actions:
            return "No scripted clickable actions were executed."
        last = actions[-1]
        return (
            f"Executed {len(actions)} scripted clickable step(s); final recorded action was "
            f"{last.get('action', 'unknown')} on {last.get('target', 'unknown')} with result={last.get('result', 'unknown')}. "
            f"Task outcome={task_outcome}."
        )


def _string_list(raw: Any) -> list[str]:
    if isinstance(raw, str):
        stripped = raw.strip()
        return [stripped] if stripped else []
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    for item in raw:
        stripped = str(item).strip()
        if stripped:
            normalized.append(stripped)
    return normalized


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
