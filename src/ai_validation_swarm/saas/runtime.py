from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any, Callable
import threading
import time
import uuid

from ai_validation_swarm.domain.models import PanelSpec, utc_now_iso
from ai_validation_swarm.domain.validators import load_and_validate_founder_brief, validate_panel_spec
from ai_validation_swarm.personas.generator import PANEL_ROLES
from ai_validation_swarm.providers.base import BaseProvider
from ai_validation_swarm.providers.factory import build_provider
from ai_validation_swarm.saas.evidence_query import build_pending_evidence_query, query_run_evidence
from ai_validation_swarm.saas import job_store
from ai_validation_swarm.saas.models import BillingAccount, TenantWorkspace, ValidationJob, WorkspaceMember
from ai_validation_swarm.validation.runner import run_validation


ACTIVE_BILLING_STATUSES = {"trialing", "active"}
SUBMITTER_ROLES = {"owner", "admin", "editor"}
VISIBLE_ROLES = {"owner", "admin", "editor", "viewer", "billing_admin"}
PLAN_LIMITS = {
    "trial": {"daily_runs": 3, "max_concurrent_jobs": 1, "artifact_retention_days": 7},
    "pro": {"daily_runs": 25, "max_concurrent_jobs": 3, "artifact_retention_days": 30},
    "enterprise": {"daily_runs": 100, "max_concurrent_jobs": 10, "artifact_retention_days": 90},
}


class AuthenticationError(ValueError):
    pass


class AuthorizationError(PermissionError):
    pass


@dataclass(slots=True)
class AuthContext:
    workspace_id: str
    user_id: str
    role: str
    token: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ValidationJobRequest:
    brief_path: str
    persona_dir: str
    panel_spec: PanelSpec
    provider_name: str = "mock"
    priority: str = "normal"
    max_retries: int = 1
    idempotency_key: str = ""
    run_root: str = "runs"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["panel_spec"] = self.panel_spec.to_dict()
        return payload


def _now() -> datetime:
    return datetime.now(UTC)


def _plan_limits(plan_tier: str, settings: dict[str, Any]) -> dict[str, int]:
    defaults = dict(PLAN_LIMITS.get(plan_tier, PLAN_LIMITS["trial"]))
    for key in ("daily_runs", "max_concurrent_jobs", "artifact_retention_days"):
        if isinstance(settings.get(key), int) and int(settings[key]) >= 0:
            defaults[key] = int(settings[key])
    return defaults


def _workspace_root(runtime_root: Path, workspace_id: str) -> Path:
    return runtime_root / "workspaces" / workspace_id


def _resolve_workspace_path(workspace_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    path = candidate if candidate.is_absolute() else workspace_root / candidate
    resolved = path.resolve()
    workspace_resolved = workspace_root.resolve()
    if resolved != workspace_resolved and workspace_resolved not in resolved.parents:
        raise AuthorizationError(f"Path '{raw_path}' escapes workspace boundary.")
    return resolved


class SaasRuntime:
    def __init__(
        self,
        runtime_root: Path,
        *,
        provider_builder: Callable[[str], BaseProvider] = build_provider,
    ) -> None:
        self.runtime_root = runtime_root
        self.provider_builder = provider_builder
        self.runtime_root.mkdir(parents=True, exist_ok=True)

    def bootstrap_workspace(
        self,
        *,
        workspace_id: str,
        slug: str,
        display_name: str,
        owner_user_id: str,
        api_token: str,
        plan_tier: str = "trial",
        billing_status: str = "trialing",
        region_code: str = "HK",
        data_residency_region: str = "ap-east-1",
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = utc_now_iso()
        workspace = TenantWorkspace(
            workspace_id=workspace_id,
            slug=slug,
            display_name=display_name,
            region_code=region_code,
            data_residency_region=data_residency_region,
            plan_tier=plan_tier,
            status="active",
            created_at=now,
            settings=dict(settings or {}),
            members=[WorkspaceMember(user_id=owner_user_id, role="owner", joined_at=now)],
        )
        billing = BillingAccount(
            workspace_id=workspace_id,
            provider_name="local-dev",
            provider_customer_ref=f"cust_{workspace_id}",
            provider_subscription_ref=f"sub_{workspace_id}",
            price_book_id=plan_tier,
            status=billing_status,
            seat_count=1,
            metadata={"bootstrap_mode": "local_dev"},
        )
        job_store.upsert_workspace(self.runtime_root, workspace)
        job_store.upsert_billing_account(self.runtime_root, billing)
        job_store.register_api_token(
            self.runtime_root,
            token=api_token,
            workspace_id=workspace_id,
            user_id=owner_user_id,
            role="owner",
            issued_at=now,
        )
        root = _workspace_root(self.runtime_root, workspace_id)
        (root / "briefs").mkdir(parents=True, exist_ok=True)
        (root / "personas").mkdir(parents=True, exist_ok=True)
        (root / "runs").mkdir(parents=True, exist_ok=True)
        return {
            "workspace": workspace.to_dict(),
            "billing_account": billing.to_dict(),
            "workspace_root": str(root),
            "api_token": api_token,
        }

    def authenticate(self, token: str) -> AuthContext:
        if not token.strip():
            raise AuthenticationError("Missing API token.")
        token_record = job_store.resolve_api_token(self.runtime_root, token)
        if token_record is None or not token_record.get("active"):
            raise AuthenticationError("Invalid API token.")
        if str(token_record["role"]) not in VISIBLE_ROLES:
            raise AuthorizationError(f"Unsupported workspace role '{token_record['role']}'.")
        return AuthContext(
            workspace_id=str(token_record["workspace_id"]),
            user_id=str(token_record["user_id"]),
            role=str(token_record["role"]),
            token=token,
        )

    def _workspace_and_billing(self, auth: AuthContext) -> tuple[TenantWorkspace, BillingAccount]:
        workspace = job_store.get_workspace(self.runtime_root, auth.workspace_id)
        if workspace is None:
            raise AuthorizationError(f"Unknown workspace '{auth.workspace_id}'.")
        if workspace.status != "active":
            raise AuthorizationError(f"Workspace '{auth.workspace_id}' is not active.")
        billing = job_store.get_billing_account(self.runtime_root, auth.workspace_id)
        if billing is None:
            raise AuthorizationError(f"Workspace '{auth.workspace_id}' has no billing account.")
        return workspace, billing

    def submit_validation_job(self, auth: AuthContext, request: ValidationJobRequest) -> dict[str, Any]:
        workspace, billing = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot submit validation jobs.")
        if billing.status not in ACTIVE_BILLING_STATUSES:
            raise AuthorizationError(f"Billing status '{billing.status}' does not allow new validation jobs.")
        limits = _plan_limits(workspace.plan_tier, workspace.settings)
        active_jobs = job_store.count_workspace_active_jobs(self.runtime_root, workspace.workspace_id)
        if active_jobs >= limits["max_concurrent_jobs"]:
            raise AuthorizationError(
                f"Workspace '{workspace.workspace_id}' reached the max concurrent job limit ({limits['max_concurrent_jobs']})."
            )
        today_floor = _now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        daily_jobs = job_store.count_workspace_jobs_created_since(self.runtime_root, workspace.workspace_id, today_floor)
        if daily_jobs >= limits["daily_runs"]:
            raise AuthorizationError(
                f"Workspace '{workspace.workspace_id}' reached the daily run limit ({limits['daily_runs']})."
            )

        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        brief_path = _resolve_workspace_path(workspace_root, request.brief_path)
        persona_dir = _resolve_workspace_path(workspace_root, request.persona_dir)
        run_root = _resolve_workspace_path(workspace_root, request.run_root)
        if not brief_path.exists():
            raise FileNotFoundError(f"Brief path not found: {brief_path}")
        if not persona_dir.exists():
            raise FileNotFoundError(f"Persona directory not found: {persona_dir}")
        run_root.mkdir(parents=True, exist_ok=True)

        brief = load_and_validate_founder_brief(brief_path)
        panel_spec = validate_panel_spec(request.panel_spec, allowed_panel_types=set(PANEL_ROLES))
        created_at = utc_now_iso()
        job = ValidationJob(
            job_id=f"job_{created_at[:19].replace('-', '').replace(':', '').replace('T', '_')}_{uuid.uuid4().hex[:8]}",
            workspace_id=workspace.workspace_id,
            brief_id=brief.brief_id,
            requested_by_user_id=auth.user_id,
            panel_spec=panel_spec,
            provider_name=request.provider_name,
            status="queued",
            priority=request.priority,
            input_artifact_path=str(brief_path),
            output_run_path=None,
            retry_count=0,
            created_at=created_at,
        )
        metadata = {
            **request.metadata,
            "brief_path": str(brief_path),
            "persona_dir": str(persona_dir),
            "run_root": str(run_root),
            "max_retries": request.max_retries,
            "submitted_by_role": auth.role,
            "plan_tier": workspace.plan_tier,
            "daily_run_limit": limits["daily_runs"],
            "max_concurrent_jobs": limits["max_concurrent_jobs"],
            "artifact_retention_days": limits["artifact_retention_days"],
        }
        return job_store.create_validation_job(
            self.runtime_root,
            job=job,
            persona_dir_path=str(persona_dir),
            idempotency_key=request.idempotency_key.strip(),
            metadata=metadata,
        )

    def list_workspace_jobs(self, auth: AuthContext) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        return job_store.list_workspace_jobs(self.runtime_root, auth.workspace_id)

    def get_validation_job(self, auth: AuthContext, job_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        job = job_store.get_validation_job(self.runtime_root, job_id)
        if job is None or str(job["workspace_id"]) != auth.workspace_id:
            raise AuthorizationError(f"Validation job '{job_id}' is not visible in this workspace.")
        return job

    def describe_workspace_session(self, auth: AuthContext) -> dict[str, Any]:
        workspace, billing = self._workspace_and_billing(auth)
        limits = _plan_limits(workspace.plan_tier, workspace.settings)
        jobs = job_store.list_workspace_jobs(self.runtime_root, auth.workspace_id)
        job_counts = {
            "total": len(jobs),
            "queued": sum(1 for job in jobs if str(job.get("status")) == "queued"),
            "running": sum(1 for job in jobs if str(job.get("status")) == "running"),
            "completed": sum(1 for job in jobs if str(job.get("status")) == "completed"),
            "failed": sum(1 for job in jobs if str(job.get("status")) == "failed"),
            "canceled": sum(1 for job in jobs if str(job.get("status")) == "canceled"),
        }
        workspace_root = _workspace_root(self.runtime_root, auth.workspace_id)
        return {
            "auth": auth.to_dict(),
            "workspace": workspace.to_dict(),
            "billing_account": billing.to_dict(),
            "plan_limits": limits,
            "job_counts": job_counts,
            "paths": {
                "workspace_root": str(workspace_root),
                "briefs_root": str(workspace_root / "briefs"),
                "personas_root": str(workspace_root / "personas"),
                "runs_root": str(workspace_root / "runs"),
            },
            "capabilities": {
                "validation_jobs": True,
                "evidence_query": True,
                "worker_runtime": True,
                "session_auth": True,
            },
            "synthetic_boundary": (
                "Synthetic evidence only. Authenticated workspace access does not change the evidence boundary."
            ),
        }

    def describe_workspace_shell(
        self,
        auth: AuthContext,
        *,
        job_id: str = "",
        query_text: str = "",
        active_family: str = "all",
        sort_by: str = "relevance",
        selected_result_id: str = "",
        selected_replay_step_id: str = "",
    ) -> dict[str, Any]:
        session = self.describe_workspace_session(auth)
        jobs = self.list_workspace_jobs(auth)
        selected_job = None

        if job_id.strip():
            selected_job = self.get_validation_job(auth, job_id.strip())
        elif jobs:
            selected_job = jobs[0]

        evidence_query = (
            self.query_workspace_evidence(
                auth,
                job_id=str(selected_job.get("job_id") or ""),
                query_text=query_text,
                active_family=active_family,
                sort_by=sort_by,
                selected_result_id=selected_result_id,
                selected_replay_step_id=selected_replay_step_id,
            )
            if selected_job
            else build_pending_evidence_query(
                run_id=None,
                query_text=query_text,
                active_family=active_family,
                sort_by=sort_by,
            )
        )

        return {
            "snapshot_version": "workspace-shell/v0-draft",
            "session": session,
            "jobs": jobs,
            "selected_job_id": str(selected_job.get("job_id") or "") if selected_job else None,
            "selected_job": selected_job,
            "evidence_query": evidence_query,
            "capabilities": {
                **dict(session.get("capabilities", {})),
                "workspace_shell_snapshot": True,
            },
            "runtime_sync": {
                "poll_recommended_ms": 4000,
                "snapshot_endpoint": "/api/v1/workspace-shell",
            },
            "synthetic_boundary": session.get("synthetic_boundary"),
        }

    def query_workspace_evidence(
        self,
        auth: AuthContext,
        *,
        run_id: str = "",
        job_id: str = "",
        query_text: str = "",
        active_family: str = "all",
        sort_by: str = "relevance",
        selected_result_id: str = "",
        selected_replay_step_id: str = "",
    ) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        resolved_run_id = run_id.strip()

        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            metadata = dict(job.get("metadata", {}))
            resolved_run_id = resolved_run_id or str(metadata.get("run_id") or "")
            if not resolved_run_id:
                output_run_path = str(job.get("output_run_path") or "")
                if output_run_path:
                    resolved_run_id = Path(output_run_path).name
            if str(job.get("status")) != "completed" or not resolved_run_id:
                return build_pending_evidence_query(
                    run_id=resolved_run_id or None,
                    query_text=query_text,
                    active_family=active_family,
                    sort_by=sort_by,
                )

        if not resolved_run_id:
            raise ValueError("Field 'run_id' or 'job_id' is required for evidence query.")

        workspace_root = _workspace_root(self.runtime_root, auth.workspace_id)
        run_root = workspace_root / "runs"
        return query_run_evidence(
            run_root,
            run_id=resolved_run_id,
            query_text=query_text,
            active_family=active_family,
            sort_by=sort_by,
            selected_result_id=selected_result_id,
            selected_replay_step_id=selected_replay_step_id,
        )

    def process_next_job(self) -> dict[str, Any] | None:
        leased = job_store.lease_next_validation_job(self.runtime_root)
        if leased is None:
            return None

        metadata = dict(leased.get("metadata", {}))
        workspace = job_store.get_workspace(self.runtime_root, str(leased["workspace_id"]))
        if workspace is None:
            return job_store.update_validation_job(
                self.runtime_root,
                job_id=str(leased["job_id"]),
                status="failed",
                last_error=f"Unknown workspace '{leased['workspace_id']}'.",
            )

        try:
            provider = self.provider_builder(str(leased["provider_name"]))
            run_dir = run_validation(
                Path(str(leased["input_artifact_path"])),
                Path(str(leased["persona_dir_path"])),
                PanelSpec(**dict(leased["panel_spec"])),
                provider,
                Path(str(metadata.get("run_root") or (_workspace_root(self.runtime_root, workspace.workspace_id) / "runs"))),
                max_retries=int(metadata.get("max_retries", 1)),
            )
            retention_days = int(metadata.get("artifact_retention_days", _plan_limits(workspace.plan_tier, workspace.settings)["artifact_retention_days"]))
            retention_until = (_now() + timedelta(days=retention_days)).replace(microsecond=0).isoformat()
            updated = job_store.update_validation_job(
                self.runtime_root,
                job_id=str(leased["job_id"]),
                status="completed",
                output_run_path=str(run_dir),
                metadata_updates={
                    "run_id": run_dir.name,
                    "artifact_retention_until": retention_until,
                    "artifact_deleted_at": "",
                },
            )
            return updated
        except Exception as exc:
            return job_store.update_validation_job(
                self.runtime_root,
                job_id=str(leased["job_id"]),
                status="failed",
                last_error=str(exc),
            )

    def purge_expired_run_artifacts(self, *, now: datetime | None = None) -> list[str]:
        current = now or _now()
        purged_job_ids: list[str] = []
        for workspace in self._list_workspaces():
            for job in job_store.list_workspace_jobs(self.runtime_root, workspace.workspace_id):
                output_run_path = str(job.get("output_run_path") or "")
                if not output_run_path:
                    continue
                metadata = dict(job.get("metadata", {}))
                artifact_deleted_at = str(metadata.get("artifact_deleted_at") or "")
                retention_until = str(metadata.get("artifact_retention_until") or "")
                if artifact_deleted_at or not retention_until:
                    continue
                try:
                    retention_deadline = datetime.fromisoformat(retention_until)
                except ValueError:
                    continue
                if retention_deadline > current:
                    continue
                run_path = Path(output_run_path)
                if run_path.exists():
                    for child in sorted(run_path.rglob("*"), reverse=True):
                        if child.is_file():
                            child.unlink()
                        elif child.is_dir():
                            child.rmdir()
                    run_path.rmdir()
                job_store.update_validation_job(
                    self.runtime_root,
                    job_id=str(job["job_id"]),
                    status=str(job["status"]),
                    output_run_path=output_run_path,
                    metadata_updates={"artifact_deleted_at": current.replace(microsecond=0).isoformat()},
                )
                purged_job_ids.append(str(job["job_id"]))
        return purged_job_ids

    def run_worker_loop(self, *, poll_seconds: float = 1.0, stop_after_one: bool = False, stop_event: threading.Event | None = None) -> int:
        processed = 0
        while True:
            if stop_event is not None and stop_event.is_set():
                return processed
            job = self.process_next_job()
            if job is not None:
                processed += 1
                if stop_after_one:
                    return processed
                continue
            if stop_after_one:
                return processed
            time.sleep(max(poll_seconds, 0.05))

    def _list_workspaces(self) -> list[TenantWorkspace]:
        return job_store.list_workspaces(self.runtime_root)
