from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import PersonaSkill
from ai_validation_swarm.storage.files import load_persona, save_persona


@dataclass(slots=True)
class PersonaBatchResult:
    processed_count: int
    succeeded_count: int
    failed_count: int
    skipped_count: int
    failures: list[dict[str, str]]
    processed_persona_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "processed_count": self.processed_count,
            "succeeded_count": self.succeeded_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "failures": self.failures,
            "processed_persona_ids": self.processed_persona_ids,
        }


@dataclass(slots=True)
class PersonaBatchRoundResult:
    round_index: int
    requested_limit: int
    valid_count_before: int
    valid_count_after: int
    newly_excluded_persona_ids: list[str]
    batch: PersonaBatchResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index,
            "requested_limit": self.requested_limit,
            "valid_count_before": self.valid_count_before,
            "valid_count_after": self.valid_count_after,
            "newly_excluded_persona_ids": self.newly_excluded_persona_ids,
            "batch": self.batch.to_dict(),
        }


@dataclass(slots=True)
class PersonaBatchTargetResult:
    target_count: int
    available_input_count: int
    initial_valid_count: int
    final_valid_count: int
    completed: bool
    stopped_reason: str
    excluded_persona_ids: list[str]
    failure_counts_by_persona: dict[str, int]
    rounds: list[PersonaBatchRoundResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_count": self.target_count,
            "available_input_count": self.available_input_count,
            "initial_valid_count": self.initial_valid_count,
            "final_valid_count": self.final_valid_count,
            "completed": self.completed,
            "stopped_reason": self.stopped_reason,
            "excluded_persona_ids": self.excluded_persona_ids,
            "failure_counts_by_persona": self.failure_counts_by_persona,
            "rounds": [round_result.to_dict() for round_result in self.rounds],
        }


def list_valid_persona_ids(persona_dir: Path) -> list[str]:
    valid_ids: list[str] = []
    if not persona_dir.exists():
        return valid_ids
    for folder in sorted(entry for entry in persona_dir.iterdir() if entry.is_dir()):
        try:
            load_persona(folder)
        except Exception:
            continue
        valid_ids.append(folder.name)
    return valid_ids


def enrich_persona_library(
    *,
    input_dir: Path,
    output_dir: Path,
    enricher: object | None,
    judge: object | None,
    limit: int | None = None,
    resume: bool = True,
    workers: int = 1,
    exclude_persona_ids: set[str] | None = None,
) -> PersonaBatchResult:
    persona_dirs = sorted(folder for folder in input_dir.iterdir() if folder.is_dir()) if input_dir.exists() else []
    processed_persona_ids: list[str] = []
    failures: list[dict[str, str]] = []
    succeeded_count = 0
    skipped_count = 0
    pending_folders: list[Path] = []
    excluded_ids = exclude_persona_ids or set()

    for folder in persona_dirs:
        persona_id = folder.name
        if persona_id in excluded_ids:
            continue
        processed_persona_ids.append(persona_id)
        destination_folder = output_dir / persona_id
        if resume and destination_folder.exists():
            try:
                load_persona(destination_folder)
                skipped_count += 1
                continue
            except Exception:
                pass
        pending_folders.append(folder)
        if limit is not None and len(pending_folders) >= limit:
            break

    def _process_folder(folder: Path) -> dict[str, str]:
        persona_id = folder.name
        try:
            persona = load_persona(folder)
            if enricher is not None:
                persona = enricher.enrich(persona)
            if judge is not None:
                persona.audit["judge_review"] = judge.judge(persona)
            save_persona(persona, output_dir)
            return {"persona_id": persona_id, "status": "succeeded"}
        except Exception as exc:
            return {"persona_id": persona_id, "status": "failed", "error": str(exc)}

    normalized_workers = max(1, int(workers))
    if normalized_workers == 1:
        results = [_process_folder(folder) for folder in pending_folders]
    else:
        with ThreadPoolExecutor(max_workers=normalized_workers) as executor:
            results = list(executor.map(_process_folder, pending_folders))

    for result in results:
        if result["status"] == "succeeded":
            succeeded_count += 1
            continue
        failures.append({"persona_id": result["persona_id"], "error": result.get("error", "unknown error")})

    return PersonaBatchResult(
        processed_count=skipped_count + len(pending_folders),
        succeeded_count=succeeded_count,
        failed_count=len(failures),
        skipped_count=skipped_count,
        failures=failures,
        processed_persona_ids=processed_persona_ids,
    )


def enrich_persona_library_to_target(
    *,
    input_dir: Path,
    output_dir: Path,
    enricher: object | None,
    judge: object | None,
    target_count: int,
    batch_size: int,
    resume: bool = True,
    workers: int = 1,
    max_rounds: int | None = None,
    max_stall_rounds: int = 1,
    max_persona_failures: int = 2,
) -> PersonaBatchTargetResult:
    if target_count <= 0:
        raise ValueError("target_count must be greater than 0.")
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0.")
    if max_stall_rounds <= 0:
        raise ValueError("max_stall_rounds must be greater than 0.")
    if max_persona_failures <= 0:
        raise ValueError("max_persona_failures must be greater than 0.")

    input_persona_ids = [folder.name for folder in sorted(input_dir.iterdir()) if folder.is_dir()] if input_dir.exists() else []
    available_input_count = len(input_persona_ids)
    effective_target_count = min(target_count, available_input_count)
    valid_persona_ids = list_valid_persona_ids(output_dir)
    initial_valid_count = len(valid_persona_ids)
    rounds: list[PersonaBatchRoundResult] = []
    stopped_reason = "target_reached" if initial_valid_count >= effective_target_count else "unknown"
    consecutive_stall_rounds = 0
    failure_counts_by_persona: dict[str, int] = {}
    excluded_persona_ids: set[str] = set()

    while len(valid_persona_ids) < effective_target_count:
        if max_rounds is not None and len(rounds) >= max_rounds:
            stopped_reason = "max_rounds_reached"
            break
        remaining_eligible_count = len(
            [persona_id for persona_id in input_persona_ids if persona_id not in valid_persona_ids and persona_id not in excluded_persona_ids]
        )
        if remaining_eligible_count <= 0:
            stopped_reason = "no_remaining_eligible_personas"
            break

        valid_count_before = len(valid_persona_ids)
        requested_limit = min(batch_size, effective_target_count - valid_count_before)
        batch_result = enrich_persona_library(
            input_dir=input_dir,
            output_dir=output_dir,
            enricher=enricher,
            judge=judge,
            limit=requested_limit,
            resume=resume,
            workers=workers,
            exclude_persona_ids=excluded_persona_ids,
        )
        newly_excluded_persona_ids: list[str] = []
        for failure in batch_result.failures:
            persona_id = failure["persona_id"]
            failure_counts_by_persona[persona_id] = failure_counts_by_persona.get(persona_id, 0) + 1
            if failure_counts_by_persona[persona_id] >= max_persona_failures and persona_id not in excluded_persona_ids:
                excluded_persona_ids.add(persona_id)
                newly_excluded_persona_ids.append(persona_id)
        valid_persona_ids = list_valid_persona_ids(output_dir)
        round_result = PersonaBatchRoundResult(
            round_index=len(rounds) + 1,
            requested_limit=requested_limit,
            valid_count_before=valid_count_before,
            valid_count_after=len(valid_persona_ids),
            newly_excluded_persona_ids=newly_excluded_persona_ids,
            batch=batch_result,
        )
        rounds.append(round_result)

        if len(valid_persona_ids) >= effective_target_count:
            stopped_reason = "target_reached"
            break
        if len(valid_persona_ids) == valid_count_before:
            if newly_excluded_persona_ids:
                consecutive_stall_rounds = 0
                continue
            consecutive_stall_rounds += 1
            if batch_result.failed_count == 0:
                stopped_reason = "no_progress"
                break
            if consecutive_stall_rounds >= max_stall_rounds:
                stopped_reason = "max_stall_rounds_reached_with_failures"
                break
            continue
        consecutive_stall_rounds = 0

    completed = len(valid_persona_ids) >= effective_target_count
    if not rounds and not completed:
        stopped_reason = "no_progress"

    return PersonaBatchTargetResult(
        target_count=effective_target_count,
        available_input_count=available_input_count,
        initial_valid_count=initial_valid_count,
        final_valid_count=len(valid_persona_ids),
        completed=completed,
        stopped_reason=stopped_reason,
        excluded_persona_ids=sorted(excluded_persona_ids),
        failure_counts_by_persona=dict(sorted(failure_counts_by_persona.items())),
        rounds=rounds,
    )
