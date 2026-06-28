from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from ai_validation_swarm.domain.validators import InputValidationError, validate_observed_action_trace_payload


SCRIPTED_CLICKABLE_EXECUTOR_VERSION = "clickable-prototype-executor/v1"
BROWSER_BEHAVIOR_EXECUTOR_VERSION = "browser-behavior-executor/v1"
BROWSER_BEHAVIOR_TRACE_VERSION = "browser-behavior-trace/v1"

_TERMINAL_RESULTS = {"error", "failed", "failure", "stopped", "abandoned"}
_PARTIAL_RESULTS = {"backtrack", "partial_success"}
_LOCAL_BROWSER_HOSTS = {"", "localhost", "127.0.0.1", "::1"}
_DANGEROUS_EVENT_TOKENS = {
    "api_key",
    "apikey",
    "bank",
    "checkout",
    "credential",
    "delete",
    "destructive",
    "password",
    "payment",
    "publish",
    "revoke",
    "secret",
    "submit",
    "token",
    "transfer",
}
_SENSITIVE_PAYLOAD_FLAGS = {
    "credentialed_session",
    "destructive_actions_allowed",
    "external_network_allowed",
    "high_stakes",
    "requires_credentials",
}


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


class BrowserBehaviorTraceExecutor:
    executor_id = "browser-behavior-trace"
    executor_version = BROWSER_BEHAVIOR_EXECUTOR_VERSION

    def can_execute(self, *, stimulus_type: str, payload: dict[str, Any], artifact_path: Path) -> bool:
        if stimulus_type not in {"clickable", "live_app"} or not isinstance(payload, dict):
            return False
        if isinstance(payload.get("browser_events"), list) or isinstance(payload.get("browser_trace_events"), list):
            return True
        if payload.get("trace_version") == BROWSER_BEHAVIOR_TRACE_VERSION:
            return True
        return str(payload.get("capture_kind", "")).strip().lower() in {
            "browser",
            "browser_session",
            "browser_behavior",
            "live_app_browser_session",
        } and isinstance(payload.get("events"), list)

    def execute(
        self,
        *,
        artifact_path: Path,
        payload: dict[str, Any],
        prototype_task: str,
    ) -> dict[str, Any]:
        events = self._raw_events(payload)
        if not events:
            raise StimulusExecutionError(["Browser behavior trace requires a non-empty browser event array."])

        safety_gate = self._evaluate_safety(payload=payload, events=events)
        if safety_gate["status"] != "allowed":
            raise StimulusExecutionError(
                [
                    "Browser behavior trace blocked by safety gate: "
                    + "; ".join(safety_gate["blocked_reasons"])
                ]
            )

        session = payload.get("session", {})
        session = session if isinstance(session, dict) else {}
        driver = str(payload.get("driver", session.get("driver", "browser"))).strip() or "browser"
        normalized_actions = [
            self._normalize_event(event, step=index, driver=driver)
            for index, event in enumerate(events, start=1)
        ]
        task_outcome = str(payload.get("task_outcome", payload.get("outcome", ""))).strip().lower()
        if not task_outcome:
            task_outcome = self._derive_task_outcome(normalized_actions)
        first_error = str(payload.get("first_error", "")).strip()
        drop_off_point = str(payload.get("drop_off_point", "")).strip()
        if not first_error or not drop_off_point:
            first_error, drop_off_point = self._derive_failure_boundary(
                normalized_actions,
                first_error=first_error,
                drop_off_point=drop_off_point,
            )
        summary = str(payload.get("summary", "")).strip() or self._build_summary(normalized_actions, task_outcome)
        missing_signals = _string_list(payload.get("missing_signals", payload.get("missing_observed_signals", [])))
        if not missing_signals:
            missing_signals = [
                "Browser events were captured from an instrumented synthetic task run, not from a live human usability session.",
                "Intent, trust rationale, and adoption reasoning must come from the simulated interview layer, not from click telemetry alone.",
            ]
        observed_summary = _string_list(payload.get("observed_summary", payload.get("what_was_observed", [])))
        if not observed_summary:
            observed_summary = [
                f"Captured {len(normalized_actions)} browser-observed event(s) from an interactive surface.",
                f"Driver: {driver}.",
                f"Prototype task: {prototype_task or '(none supplied)'}",
            ]
        completion_notes = str(payload.get("completion_notes", "")).strip()
        if not completion_notes:
            completion_notes = (
                "Browser-observed task path reached a success outcome."
                if task_outcome == "success"
                else "Browser-observed task path stopped before a clean success outcome."
            )

        trace_payload = {
            "trace_version": "observed-action-trace/v1",
            "trace_label": str(payload.get("trace_label", artifact_path.stem)).strip() or artifact_path.stem,
            "task_outcome": task_outcome,
            "summary": summary,
            "actions": normalized_actions,
            "observed_summary": observed_summary,
            "missing_signals": missing_signals,
            "first_error": first_error,
            "drop_off_point": drop_off_point,
            "completion_notes": completion_notes,
        }
        try:
            trace = validate_observed_action_trace_payload(trace_payload, default_label=artifact_path.stem).to_dict()
        except InputValidationError as exc:
            raise StimulusExecutionError([str(exc)]) from exc
        trace["artifact_sha256"] = _file_sha256(artifact_path)

        start_url = _string(payload.get("start_url", session.get("start_url", "")))
        final_url = _string(payload.get("final_url", session.get("final_url", "")))
        analysis_type = "live_app_browser_trace" if _string(payload.get("surface_type", "")).lower() == "live_app" else "browser_clickable_trace"
        if _string(payload.get("stimulus_type", "")).lower() == "live_app":
            analysis_type = "live_app_browser_trace"
        return {
            "executor_id": self.executor_id,
            "executor_version": self.executor_version,
            "stimulus_analysis_prompt_version": self.executor_version,
            "stimulus_analysis": {
                "analysis_type": analysis_type,
                "summary": summary,
                "prototype_label": str(payload.get("prototype_label", artifact_path.stem)).strip() or artifact_path.stem,
                "driver": driver,
                "event_count": len(events),
                "normalized_action_count": len(normalized_actions),
                "start_url": start_url,
                "final_url": final_url,
                "viewport": payload.get("viewport", session.get("viewport", {})),
                "allowed_origins": self._allowed_origins(payload),
                "safety_gate": safety_gate,
                "evidence_boundary": (
                    "Browser-observed synthetic task execution only. Events came from an instrumented browser or live-app "
                    "driver and are not human market proof, credentialed-session proof, or permission to run destructive actions."
                ),
            },
            "observed_action_trace": trace,
        }

    @staticmethod
    def _raw_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
        raw = payload.get("browser_events", payload.get("browser_trace_events", payload.get("events", [])))
        if not isinstance(raw, list):
            return []
        return [item for item in raw if isinstance(item, dict)]

    @staticmethod
    def _normalize_event(event: dict[str, Any], *, step: int, driver: str) -> dict[str, Any]:
        event_type = _string(event.get("event_type", event.get("type", event.get("action", "")))).lower()
        action = {
            "goto": "navigate",
            "navigation": "navigate",
            "nav": "navigate",
            "fill": "input",
            "type": "input",
            "keypress": "input",
            "back": "backtrack",
            "assert": "assert_visible",
        }.get(event_type, event_type or "browser_event")
        target = _string(
            event.get(
                "target",
                event.get("selector", event.get("element", event.get("url", event.get("text", "")))),
            )
        ) or "browser_surface"
        screen = _string(event.get("screen", event.get("page_title", event.get("view", event.get("url", "")))))
        result = _string(event.get("result", event.get("outcome", "success"))).lower() or "success"
        raw_metadata = {
            "executor_id": BrowserBehaviorTraceExecutor.executor_id,
            "browser_event_type": event_type or "unknown",
            "driver": driver,
        }
        for key in ("selector", "url", "x", "y", "page_title", "frame", "navigation_type", "value_length"):
            if key in event:
                raw_metadata[key] = event[key]
        return {
            "step": int(event.get("step", step)) if isinstance(event.get("step", step), int) else step,
            "action": action,
            "target": target,
            "screen": screen,
            "result": result,
            "note": _string(event.get("note", event.get("detail", ""))),
            "timestamp_ms": event.get("timestamp_ms", event.get("ts_ms")),
            "duration_ms": event.get("duration_ms", event.get("elapsed_ms")),
            "raw_metadata": raw_metadata,
        }

    @staticmethod
    def _evaluate_safety(*, payload: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
        blocked_reasons: list[str] = []
        for flag in sorted(_SENSITIVE_PAYLOAD_FLAGS):
            if bool(payload.get(flag, False)):
                blocked_reasons.append(f"payload flag '{flag}' is not allowed for automatic browser execution")

        allowed_origins = BrowserBehaviorTraceExecutor._allowed_origins(payload)
        for label, url in BrowserBehaviorTraceExecutor._candidate_urls(payload, events):
            if not BrowserBehaviorTraceExecutor._url_allowed(url, allowed_origins=allowed_origins):
                blocked_reasons.append(f"{label} url '{url}' is outside local or allowed origins")

        for index, event in enumerate(events):
            haystack = " ".join(
                _string(event.get(key, ""))
                for key in ("event_type", "type", "action", "target", "selector", "text", "label", "name", "url")
            ).lower()
            matched = sorted(token for token in _DANGEROUS_EVENT_TOKENS if token in haystack.replace("-", "_") or token in haystack)
            if matched:
                blocked_reasons.append(f"event[{index}] contains blocked token(s): {', '.join(matched)}")

        return {
            "status": "blocked" if blocked_reasons else "allowed",
            "blocked_reasons": blocked_reasons,
            "policy_version": "browser-behavior-safety/v1",
        }

    @staticmethod
    def _candidate_urls(payload: dict[str, Any], events: list[dict[str, Any]]) -> list[tuple[str, str]]:
        session = payload.get("session", {})
        session = session if isinstance(session, dict) else {}
        candidates = [
            ("start", _string(payload.get("start_url", session.get("start_url", "")))),
            ("final", _string(payload.get("final_url", session.get("final_url", "")))),
        ]
        for index, event in enumerate(events):
            url = _string(event.get("url", ""))
            if url:
                candidates.append((f"event[{index}]", url))
        return [(label, url) for label, url in candidates if url]

    @staticmethod
    def _allowed_origins(payload: dict[str, Any]) -> list[str]:
        raw = payload.get("allowed_origins", payload.get("allowed_domains", []))
        if isinstance(raw, str):
            raw_values = [raw]
        elif isinstance(raw, list):
            raw_values = raw
        else:
            raw_values = []
        origins: list[str] = []
        for item in raw_values:
            origin = _origin(_string(item))
            if origin:
                origins.append(origin)
        return sorted(set(origins))

    @staticmethod
    def _url_allowed(url: str, *, allowed_origins: list[str]) -> bool:
        parsed = urlparse(url)
        if parsed.scheme == "file":
            return True
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.hostname in _LOCAL_BROWSER_HOSTS:
            return True
        return _origin(url) in set(allowed_origins)

    @staticmethod
    def _derive_task_outcome(actions: list[dict[str, Any]]) -> str:
        results = [_string(action.get("result", "")).lower() for action in actions]
        if any(result in {"error", "failed", "failure"} for result in results):
            return "failure"
        if any(result in {"stopped", "abandoned"} for result in results):
            return "abandoned"
        if any(result in {"backtrack", "partial_success"} for result in results):
            return "partial_success"
        return "success"

    @staticmethod
    def _derive_failure_boundary(
        actions: list[dict[str, Any]],
        *,
        first_error: str,
        drop_off_point: str,
    ) -> tuple[str, str]:
        for action in actions:
            result = _string(action.get("result", "")).lower()
            if result in _TERMINAL_RESULTS | _PARTIAL_RESULTS:
                if not first_error:
                    first_error = _string(action.get("note", "")) or f"{action.get('action', 'event')} ended with result={result}."
                if not drop_off_point:
                    drop_off_point = _string(action.get("target", ""))
                break
        return first_error, drop_off_point

    @staticmethod
    def _build_summary(actions: list[dict[str, Any]], task_outcome: str) -> str:
        if not actions:
            return "No browser events were captured."
        last = actions[-1]
        return (
            f"Captured {len(actions)} browser-observed event(s); final event was "
            f"{last.get('action', 'unknown')} on {last.get('target', 'unknown')} "
            f"with result={last.get('result', 'unknown')}. Task outcome={task_outcome}."
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


def _string(raw: Any) -> str:
    return str(raw).strip() if raw is not None else ""


def _origin(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        return ""
    if parsed.scheme == "file":
        return "file://"
    if not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}".lower()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
