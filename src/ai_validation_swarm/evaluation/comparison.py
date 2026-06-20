from __future__ import annotations

from pathlib import Path

from ai_validation_swarm.storage.files import read_json, write_json


def compare_evaluation_payloads(
    baseline_payload: dict[str, object],
    candidate_payload: dict[str, object],
) -> dict[str, object]:
    baseline_fixtures = {
        fixture["fixture_id"]: fixture
        for fixture in baseline_payload.get("fixtures", [])
        if isinstance(fixture, dict) and "fixture_id" in fixture
    }
    candidate_fixtures = {
        fixture["fixture_id"]: fixture
        for fixture in candidate_payload.get("fixtures", [])
        if isinstance(fixture, dict) and "fixture_id" in fixture
    }

    fixture_ids = sorted(set(baseline_fixtures) | set(candidate_fixtures))
    results: list[dict[str, object]] = []
    changed_count = 0

    for fixture_id in fixture_ids:
        baseline_fixture = baseline_fixtures.get(fixture_id)
        candidate_fixture = candidate_fixtures.get(fixture_id)
        if baseline_fixture is None or candidate_fixture is None:
            changed = True
            result = {
                "fixture_id": fixture_id,
                "status": "changed",
                "reason": "missing_fixture",
                "baseline_present": baseline_fixture is not None,
                "candidate_present": candidate_fixture is not None,
            }
        else:
            baseline_scores = baseline_fixture.get("score_snapshot", {})
            candidate_scores = candidate_fixture.get("score_snapshot", {})
            score_keys = sorted(set(baseline_scores) | set(candidate_scores))
            score_deltas = {
                key: round(float(candidate_scores.get(key, 0)) - float(baseline_scores.get(key, 0)), 2)
                for key in score_keys
            }
            baseline_categories = set(baseline_fixture.get("audit_categories", []))
            candidate_categories = set(candidate_fixture.get("audit_categories", []))
            baseline_failed = set(baseline_fixture.get("failed_gates", []))
            candidate_failed = set(candidate_fixture.get("failed_gates", []))

            fingerprint_changed = (
                baseline_fixture.get("report_fingerprint") != candidate_fixture.get("report_fingerprint")
            )
            status_changed = baseline_fixture.get("status") != candidate_fixture.get("status")
            gate_changes = baseline_failed != candidate_failed
            category_changes = baseline_categories != candidate_categories
            changed = fingerprint_changed or status_changed or gate_changes or category_changes

            result = {
                "fixture_id": fixture_id,
                "status": "changed" if changed else "unchanged",
                "baseline_status": baseline_fixture.get("status"),
                "candidate_status": candidate_fixture.get("status"),
                "fingerprint_changed": fingerprint_changed,
                "score_deltas": score_deltas,
                "added_audit_categories": sorted(candidate_categories - baseline_categories),
                "removed_audit_categories": sorted(baseline_categories - candidate_categories),
                "added_failed_gates": sorted(candidate_failed - baseline_failed),
                "removed_failed_gates": sorted(baseline_failed - candidate_failed),
            }

        if changed:
            changed_count += 1
        results.append(result)

    return {
        "comparison_version": "evaluation-comparison/v1",
        "baseline_suite_id": baseline_payload.get("suite_id"),
        "candidate_suite_id": candidate_payload.get("suite_id"),
        "fixture_count": len(fixture_ids),
        "changed_fixture_count": changed_count,
        "unchanged_fixture_count": len(fixture_ids) - changed_count,
        "fixtures": results,
    }


def compare_evaluation_files(
    baseline_path: Path,
    candidate_path: Path,
    *,
    output_path: Path | None = None,
) -> dict[str, object]:
    comparison = compare_evaluation_payloads(
        baseline_payload=read_json(baseline_path),
        candidate_payload=read_json(candidate_path),
    )
    if output_path is not None:
        write_json(output_path, comparison)
    return comparison

