from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, UTC
from pathlib import Path
import mimetypes
from typing import Any, Callable
import threading
import time
import re
import uuid

from ai_validation_swarm.domain.models import PanelSpec, utc_now_iso
from ai_validation_swarm.domain.validators import load_and_validate_founder_brief, validate_panel_spec
from ai_validation_swarm.personas.generator import PANEL_ROLES
from ai_validation_swarm.providers.base import BaseProvider
from ai_validation_swarm.providers.factory import build_provider
from ai_validation_swarm.reporting.exporters import render_report_csv
from ai_validation_swarm.saas.evidence_query import build_pending_evidence_query, query_run_evidence
from ai_validation_swarm.saas import job_store
from ai_validation_swarm.saas.models import (
    AuditEvent,
    BillingAccount,
    TenantWorkspace,
    ValidationJob,
    WorkspaceBrowserSession,
    WorkspaceDecisionComment,
    WorkspaceDecisionLog,
    WorkspaceEvidenceView,
    WorkspaceExportBundle,
    WorkspaceMember,
    WorkspaceProject,
    WorkspaceShareBundle,
    WorkspaceSupportSnapshot,
    WorkspaceStudy,
)
from ai_validation_swarm.storage.files import export_file, read_json, write_json, write_markdown
from ai_validation_swarm.validation.runner import run_validation


ACTIVE_BILLING_STATUSES = {"trialing", "active"}
SUBMITTER_ROLES = {"owner", "admin", "editor"}
VISIBLE_ROLES = {"owner", "admin", "editor", "viewer", "billing_admin"}
PLAN_LIMITS = {
    "trial": {"daily_runs": 3, "max_concurrent_jobs": 1, "artifact_retention_days": 7},
    "pro": {"daily_runs": 25, "max_concurrent_jobs": 3, "artifact_retention_days": 30},
    "enterprise": {"daily_runs": 100, "max_concurrent_jobs": 10, "artifact_retention_days": 90},
}
EXPORTABLE_ROLE_SET = {"owner", "admin", "editor"}
SHAREABLE_ROLE_SET = {"owner", "admin", "editor"}
WORKSPACE_SETTINGS_MUTATION_ROLES = {"owner", "admin"}
WORKSPACE_BILLING_MUTATION_ROLES = {"owner", "billing_admin"}
DEFAULT_EXPORT_ARTIFACT_IDS = ("report.json", "report.md", "summary.json", "run_contract.json")
MAX_AUDIT_EVENT_QUERY_LIMIT = 100
DECISION_REVIEW_STATUSES = {"draft", "in_review", "approved", "needs_revision"}
DECISION_COMMENT_ANCHOR_KINDS = {"general", "decision_summary", "rationale", "evidence_view", "comparison"}
BROWSER_SESSION_TTL = timedelta(hours=12)


class AuthenticationError(ValueError):
    pass


class AuthorizationError(PermissionError):
    pass


class ShareUnavailableError(FileNotFoundError):
    pass


@dataclass(slots=True)
class AuthContext:
    workspace_id: str
    user_id: str
    role: str
    token: str = ""
    auth_type: str = "api_token"
    session_id: str = ""

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


def _slugify_label(value: str, *, fallback: str) -> str:
    lowered = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    normalized = lowered.strip("-")
    return normalized or fallback


def _resolve_workspace_path(workspace_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    path = candidate if candidate.is_absolute() else workspace_root / candidate
    resolved = path.resolve()
    workspace_resolved = workspace_root.resolve()
    if resolved != workspace_resolved and workspace_resolved not in resolved.parents:
        raise AuthorizationError(f"Path '{raw_path}' escapes workspace boundary.")
    return resolved


def _mask_token(token: str) -> str:
    value = str(token or "").strip()
    if len(value) <= 10:
        return value
    return f"{value[:6]}...{value[-4:]}"


def _job_run_id(job: dict[str, Any]) -> str:
    metadata = dict(job.get("metadata", {}))
    run_id = str(metadata.get("run_id") or "").strip()
    if run_id:
        return run_id
    output_run_path = str(job.get("output_run_path") or "").strip()
    if output_run_path:
        return Path(output_run_path).name
    return ""


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
            auth_type="api_token",
        )

    def issue_browser_session(
        self,
        auth: AuthContext,
        *,
        source: str = "hosted_shell",
        ttl: timedelta = BROWSER_SESSION_TTL,
    ) -> dict[str, Any]:
        issued_at = _now()
        expires_at = issued_at + ttl
        session = job_store.create_browser_session(
            self.runtime_root,
            WorkspaceBrowserSession(
                session_id=f"session_{uuid.uuid4().hex}",
                workspace_id=auth.workspace_id,
                user_id=auth.user_id,
                role=auth.role,
                source_token=auth.token or None,
                created_at=issued_at.isoformat(),
                last_seen_at=issued_at.isoformat(),
                expires_at=expires_at.isoformat(),
                metadata={"source": source},
            ),
        )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=auth.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="browser_session.issued",
                target_type="browser_session",
                target_id=session.session_id,
                event_payload={
                    "source": source,
                    "expires_at": session.expires_at,
                    "source_token_hint": _mask_token(auth.token) if auth.token else "",
                },
                created_at=issued_at.isoformat(),
            ),
        )
        return session.to_dict()

    def authenticate_browser_session(self, session_id: str) -> AuthContext:
        clean_session_id = session_id.strip()
        if not clean_session_id:
            raise AuthenticationError("Missing browser session.")
        session = job_store.resolve_browser_session(self.runtime_root, clean_session_id)
        if session is None or session.revoked_at:
            raise AuthenticationError("Invalid browser session.")
        now = _now()
        try:
            expires_at = datetime.fromisoformat(session.expires_at)
        except ValueError as exc:
            raise AuthenticationError("Invalid browser session.") from exc
        if expires_at <= now:
            job_store.revoke_browser_session(self.runtime_root, clean_session_id, revoked_at=now.isoformat())
            raise AuthenticationError("Browser session expired.")
        if session.source_token:
            token_record = job_store.resolve_api_token(self.runtime_root, session.source_token)
            if token_record is None or not token_record.get("active"):
                job_store.revoke_browser_session(self.runtime_root, clean_session_id, revoked_at=now.isoformat())
                raise AuthenticationError("Browser session is no longer active.")
        workspace = job_store.get_workspace(self.runtime_root, session.workspace_id)
        if workspace is None or workspace.status != "active":
            raise AuthorizationError(f"Workspace '{session.workspace_id}' is not active.")
        member = next((item for item in workspace.members if item.user_id == session.user_id), None)
        if member is None:
            job_store.revoke_browser_session(self.runtime_root, clean_session_id, revoked_at=now.isoformat())
            raise AuthenticationError("Browser session user is no longer active in this workspace.")
        if member.role not in VISIBLE_ROLES:
            raise AuthorizationError(f"Unsupported workspace role '{member.role}'.")
        refreshed = job_store.touch_browser_session(
            self.runtime_root,
            clean_session_id,
            role=member.role,
            last_seen_at=now.isoformat(),
            expires_at=(now + BROWSER_SESSION_TTL).isoformat(),
        )
        effective_session = refreshed or session
        return AuthContext(
            workspace_id=effective_session.workspace_id,
            user_id=effective_session.user_id,
            role=member.role,
            auth_type="browser_session",
            session_id=effective_session.session_id,
        )

    def revoke_browser_session(self, auth: AuthContext, session_id: str, *, reason: str = "user_logout") -> dict[str, Any]:
        clean_session_id = session_id.strip()
        if not clean_session_id:
            raise AuthenticationError("Missing browser session.")
        session = job_store.resolve_browser_session(self.runtime_root, clean_session_id)
        if session is None or session.workspace_id != auth.workspace_id:
            raise AuthorizationError("Browser session is not visible in this workspace.")
        revoked = job_store.revoke_browser_session(self.runtime_root, clean_session_id, revoked_at=utc_now_iso())
        if revoked is None:
            raise AuthorizationError("Browser session is not visible in this workspace.")
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=auth.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="browser_session.revoked",
                target_type="browser_session",
                target_id=clean_session_id,
                event_payload={"reason": reason},
                created_at=utc_now_iso(),
            ),
        )
        return revoked.to_dict()

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

    def describe_workspace_settings(self, auth: AuthContext) -> dict[str, Any]:
        workspace, billing = self._workspace_and_billing(auth)
        limits = _plan_limits(workspace.plan_tier, workspace.settings)
        token_rows = job_store.list_api_tokens(self.runtime_root, auth.workspace_id)
        return {
            "contract_version": "workspace-settings-surface/v0-draft",
            "auth": auth.to_dict(),
            "workspace": workspace.to_dict(),
            "billing_account": billing.to_dict(),
            "plan_limits": limits,
            "members": [member.to_dict() for member in workspace.members],
            "api_tokens": [
                {
                    "token_id": str(token_row["token"]),
                    "token_hint": _mask_token(str(token_row["token"])),
                    "user_id": str(token_row["user_id"]),
                    "role": str(token_row["role"]),
                    "issued_at": str(token_row["issued_at"]),
                    "active": bool(token_row["active"]),
                    "current": str(token_row["token"]) == auth.token,
                }
                for token_row in token_rows
            ],
            "capabilities": {
                "workspace_settings": True,
                "member_admin": auth.role in WORKSPACE_SETTINGS_MUTATION_ROLES,
                "token_admin": auth.role in WORKSPACE_SETTINGS_MUTATION_ROLES,
                "billing_mutation": auth.role in WORKSPACE_BILLING_MUTATION_ROLES,
                "billing_overview": True,
                "audit_history": True,
            },
            "policies": {
                "region_code": workspace.region_code,
                "data_residency_region": workspace.data_residency_region,
                "artifact_retention_days": limits["artifact_retention_days"],
                "daily_runs": limits["daily_runs"],
                "max_concurrent_jobs": limits["max_concurrent_jobs"],
            },
            "synthetic_boundary": (
                "Synthetic evidence only. Workspace governance controls do not change the evidence boundary."
            ),
        }

    def upsert_workspace_member(self, auth: AuthContext, *, user_id: str, role: str) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in WORKSPACE_SETTINGS_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot manage workspace members.")
        clean_user_id = user_id.strip()
        clean_role = role.strip()
        if not clean_user_id:
            raise ValueError("Field 'user_id' is required.")
        if clean_role not in VISIBLE_ROLES:
            raise ValueError(f"Unsupported workspace role '{clean_role}'.")
        if clean_role == "owner" and auth.role != "owner":
            raise AuthorizationError("Only an owner can assign the owner role.")

        members_by_user_id = {member.user_id: member for member in workspace.members}
        existing_member = members_by_user_id.get(clean_user_id)
        if existing_member and existing_member.role == "owner" and clean_role != "owner":
            raise AuthorizationError("Owner role changes are not supported through the workspace settings surface.")

        members_by_user_id[clean_user_id] = WorkspaceMember(
            user_id=clean_user_id,
            role=clean_role,
            joined_at=existing_member.joined_at if existing_member else utc_now_iso(),
        )
        updated_workspace = TenantWorkspace(
            workspace_id=workspace.workspace_id,
            slug=workspace.slug,
            display_name=workspace.display_name,
            region_code=workspace.region_code,
            data_residency_region=workspace.data_residency_region,
            plan_tier=workspace.plan_tier,
            status=workspace.status,
            created_at=workspace.created_at,
            settings=dict(workspace.settings),
            members=sorted(members_by_user_id.values(), key=lambda member: (member.user_id, member.joined_at)),
        )
        saved_workspace = job_store.upsert_workspace(self.runtime_root, updated_workspace)
        job_store.update_api_tokens_for_member(
            self.runtime_root,
            workspace_id=workspace.workspace_id,
            user_id=clean_user_id,
            role=clean_role,
        )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="workspace_member.upserted",
                target_type="workspace_member",
                target_id=clean_user_id,
                event_payload={
                    "member_role": clean_role,
                    "member_count": len(saved_workspace.members),
                },
                created_at=utc_now_iso(),
            ),
        )
        return next(member.to_dict() for member in saved_workspace.members if member.user_id == clean_user_id)

    def issue_workspace_api_token(self, auth: AuthContext, *, user_id: str) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in WORKSPACE_SETTINGS_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot issue API tokens.")
        clean_user_id = user_id.strip()
        if not clean_user_id:
            raise ValueError("Field 'user_id' is required.")
        member = next((item for item in workspace.members if item.user_id == clean_user_id), None)
        if member is None:
            raise AuthorizationError(f"Workspace member '{clean_user_id}' is not visible in this workspace.")
        if member.role == "owner" and auth.role != "owner":
            raise AuthorizationError("Only an owner can issue a token for an owner account.")
        token = f"token_{uuid.uuid4().hex}"
        issued_at = utc_now_iso()
        job_store.register_api_token(
            self.runtime_root,
            token=token,
            workspace_id=workspace.workspace_id,
            user_id=member.user_id,
            role=member.role,
            issued_at=issued_at,
        )
        token_hint = _mask_token(token)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="api_token.issued",
                target_type="api_token",
                target_id=token_hint,
                event_payload={
                    "user_id": member.user_id,
                    "role": member.role,
                },
                created_at=issued_at,
            ),
        )
        return {
            "token": token,
            "token_hint": token_hint,
            "user_id": member.user_id,
            "role": member.role,
            "issued_at": issued_at,
            "active": True,
            "current": token == auth.token,
        }

    def revoke_workspace_api_token(self, auth: AuthContext, token_id: str) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in WORKSPACE_SETTINGS_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot revoke API tokens.")
        token_record = job_store.resolve_api_token(self.runtime_root, token_id.strip())
        if token_record is None or str(token_record["workspace_id"]) != workspace.workspace_id:
            raise AuthorizationError("API token is not visible in this workspace.")
        if str(token_record["role"]) == "owner" and auth.role != "owner":
            raise AuthorizationError("Only an owner can revoke an owner token.")
        revoked = job_store.deactivate_api_token(self.runtime_root, token_id.strip())
        if revoked is None:
            raise AuthorizationError("API token is not visible in this workspace.")
        revoked_browser_sessions = job_store.revoke_browser_sessions_for_token(
            self.runtime_root,
            token_id.strip(),
            revoked_at=utc_now_iso(),
        )
        token_hint = _mask_token(str(revoked["token"]))
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="api_token.revoked",
                target_type="api_token",
                target_id=token_hint,
                event_payload={
                    "user_id": str(revoked["user_id"]),
                    "role": str(revoked["role"]),
                    "current": str(revoked["token"]) == auth.token,
                    "revoked_browser_sessions": revoked_browser_sessions,
                },
                created_at=utc_now_iso(),
            ),
        )
        return {
            "token_id": str(revoked["token"]),
            "token_hint": token_hint,
            "user_id": str(revoked["user_id"]),
            "role": str(revoked["role"]),
            "issued_at": str(revoked["issued_at"]),
            "active": bool(revoked["active"]),
            "current": str(revoked["token"]) == auth.token,
        }

    def update_workspace_billing(
        self,
        auth: AuthContext,
        *,
        plan_tier: str = "",
        billing_status: str = "",
        seat_count: int | None = None,
        renewal_at: str | None = None,
        daily_runs: int | None = None,
        max_concurrent_jobs: int | None = None,
        artifact_retention_days: int | None = None,
    ) -> dict[str, Any]:
        workspace, billing = self._workspace_and_billing(auth)
        if auth.role not in WORKSPACE_BILLING_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot manage workspace billing.")

        clean_plan_tier = plan_tier.strip() if isinstance(plan_tier, str) else ""
        clean_billing_status = billing_status.strip() if isinstance(billing_status, str) else ""
        if clean_plan_tier and clean_plan_tier not in PLAN_LIMITS:
            raise ValueError(f"Unsupported plan tier '{clean_plan_tier}'.")
        if clean_billing_status and clean_billing_status not in {"trialing", "active", "past_due", "canceled"}:
            raise ValueError(f"Unsupported billing status '{clean_billing_status}'.")
        if seat_count is not None and int(seat_count) <= 0:
            raise ValueError("Field 'seat_count' must be greater than 0.")

        limit_updates = {
            "daily_runs": daily_runs,
            "max_concurrent_jobs": max_concurrent_jobs,
            "artifact_retention_days": artifact_retention_days,
        }
        next_settings = dict(workspace.settings)
        applied_limit_updates: dict[str, int] = {}
        for key, value in limit_updates.items():
            if value is None:
                continue
            numeric_value = int(value)
            if numeric_value < 0:
                raise ValueError(f"Field '{key}' must be greater than or equal to 0.")
            next_settings[key] = numeric_value
            applied_limit_updates[key] = numeric_value

        next_renewal_at = billing.renewal_at
        if renewal_at is not None:
            clean_renewal_at = str(renewal_at).strip()
            next_renewal_at = clean_renewal_at or None

        next_plan_tier = clean_plan_tier or workspace.plan_tier
        updated_workspace = TenantWorkspace(
            workspace_id=workspace.workspace_id,
            slug=workspace.slug,
            display_name=workspace.display_name,
            region_code=workspace.region_code,
            data_residency_region=workspace.data_residency_region,
            plan_tier=next_plan_tier,
            status=workspace.status,
            created_at=workspace.created_at,
            settings=next_settings,
            members=list(workspace.members),
        )
        updated_billing = BillingAccount(
            workspace_id=billing.workspace_id,
            provider_name=billing.provider_name,
            provider_customer_ref=billing.provider_customer_ref,
            provider_subscription_ref=billing.provider_subscription_ref,
            price_book_id=next_plan_tier,
            status=clean_billing_status or billing.status,
            seat_count=int(seat_count) if seat_count is not None else billing.seat_count,
            renewal_at=next_renewal_at,
            metadata=dict(billing.metadata),
        )
        saved_workspace = job_store.upsert_workspace(self.runtime_root, updated_workspace)
        saved_billing = job_store.upsert_billing_account(self.runtime_root, updated_billing)
        limits = _plan_limits(saved_workspace.plan_tier, saved_workspace.settings)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="workspace_billing.updated",
                target_type="billing_account",
                target_id=saved_billing.workspace_id,
                event_payload={
                    "plan_tier": saved_workspace.plan_tier,
                    "billing_status": saved_billing.status,
                    "seat_count": saved_billing.seat_count,
                    "renewal_at": saved_billing.renewal_at,
                    "applied_limit_updates": applied_limit_updates,
                    "effective_limits": limits,
                },
                created_at=utc_now_iso(),
            ),
        )
        return {
            "workspace": saved_workspace.to_dict(),
            "billing_account": saved_billing.to_dict(),
            "plan_limits": limits,
        }

    def list_workspace_audit_events(
        self,
        auth: AuthContext,
        *,
        target_type: str = "",
        action_prefix: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        numeric_limit = max(1, min(int(limit), MAX_AUDIT_EVENT_QUERY_LIMIT))
        clean_target_type = target_type.strip()
        clean_action_prefix = action_prefix.strip()
        audit_events = job_store.list_audit_events(
            self.runtime_root,
            auth.workspace_id,
            target_type=clean_target_type,
            action_prefix=clean_action_prefix,
            limit=numeric_limit,
        )
        return {
            "contract_version": "workspace-audit-history-surface/v0-draft",
            "auth": auth.to_dict(),
            "filters": {
                "target_type": clean_target_type or None,
                "action_prefix": clean_action_prefix or None,
                "limit": numeric_limit,
            },
            "audit_events": [event.to_dict() for event in audit_events],
            "capabilities": {
                "workspace_settings": True,
                "audit_history": True,
            },
            "synthetic_boundary": (
                "Synthetic evidence only. Audit history shows simulated-research operations and governance events, not human validation."
            ),
        }

    def create_workspace_project(
        self,
        auth: AuthContext,
        *,
        name: str,
        description: str = "",
        slug: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot create projects.")
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Field 'name' is required.")
        candidate_slug = _slugify_label(slug or clean_name, fallback=f"project-{uuid.uuid4().hex[:6]}")
        if any(existing["slug"] == candidate_slug for existing in self.list_workspace_projects(auth)):
            raise ValueError(f"Project slug '{candidate_slug}' already exists in this workspace.")
        project = WorkspaceProject(
            project_id=f"project_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace.workspace_id,
            slug=candidate_slug,
            name=clean_name,
            description=description.strip(),
            created_by_user_id=auth.user_id,
            status="active",
            created_at=utc_now_iso(),
            updated_at=utc_now_iso(),
            metadata=dict(metadata or {}),
        )
        created = job_store.create_workspace_project(self.runtime_root, project)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="project.created",
                target_type="project",
                target_id=created.project_id,
                event_payload={
                    "project_id": created.project_id,
                    "project_slug": created.slug,
                    "project_name": created.name,
                },
                created_at=created.created_at,
            ),
        )
        return self._project_summary(created)

    def list_workspace_projects(self, auth: AuthContext) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        return [self._project_summary(project) for project in job_store.list_workspace_projects(self.runtime_root, auth.workspace_id)]

    def get_workspace_project(self, auth: AuthContext, project_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        project = job_store.get_workspace_project(self.runtime_root, project_id)
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{project_id}' is not visible in this workspace.")
        return self._project_summary(project)

    def create_workspace_study(
        self,
        auth: AuthContext,
        *,
        project_id: str,
        title: str,
        research_intent: str = "",
        desired_output: str = "",
        first_task: str = "",
        artifact_refs: list[str] | None = None,
        draft_plan: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot create studies.")
        project = job_store.get_workspace_project(self.runtime_root, project_id.strip())
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{project_id}' is not visible in this workspace.")
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Field 'title' is required.")
        now = utc_now_iso()
        study = WorkspaceStudy(
            study_id=f"study_{uuid.uuid4().hex[:12]}",
            workspace_id=auth.workspace_id,
            project_id=project.project_id,
            title=clean_title,
            created_by_user_id=auth.user_id,
            status="draft",
            research_intent=research_intent.strip(),
            desired_output=desired_output.strip(),
            first_task=first_task.strip(),
            artifact_refs=[str(item).strip() for item in (artifact_refs or []) if str(item).strip()],
            draft_plan=dict(draft_plan or {}),
            latest_job_id=None,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )
        created = job_store.create_workspace_study(self.runtime_root, study)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=auth.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="study.created",
                target_type="study",
                target_id=created.study_id,
                event_payload={
                    "project_id": created.project_id,
                    "study_id": created.study_id,
                    "study_title": created.title,
                    "first_task": created.first_task,
                },
                created_at=created.created_at,
            ),
        )
        return self._study_summary(created)

    def list_workspace_studies(self, auth: AuthContext, *, project_id: str = "") -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if project_id.strip():
            project = job_store.get_workspace_project(self.runtime_root, project_id.strip())
            if project is None or project.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace project '{project_id}' is not visible in this workspace.")
        return [
            self._study_summary(study)
            for study in job_store.list_workspace_studies(self.runtime_root, auth.workspace_id, project_id=project_id.strip())
        ]

    def get_workspace_study(self, auth: AuthContext, study_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        study = job_store.get_workspace_study(self.runtime_root, study_id)
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        return self._study_summary(study)

    def list_workspace_study_activity(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        numeric_limit = max(1, min(int(limit), 100))
        candidate_events = job_store.list_audit_events(
            self.runtime_root,
            auth.workspace_id,
            limit=max(100, numeric_limit * 8),
        )
        activity_events = [
            self._study_activity_event_summary(event)
            for event in candidate_events
            if self._audit_event_matches_study(event, study.study_id)
        ][:numeric_limit]
        return {
            "contract_version": "workspace-study-activity/v0-draft",
            "study_id": study.study_id,
            "project_id": study.project_id,
            "study_title": study.title,
            "activity_events": activity_events,
            "filters": {
                "study_id": study.study_id,
                "limit": numeric_limit,
            },
            "capabilities": {
                "study_activity": True,
                "route_links": True,
            },
            "synthetic_boundary": (
                "Synthetic evidence only. Study activity describes simulated-research operations and collaboration state, not human validation."
            ),
        }

    def create_workspace_evidence_view(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        job_id: str = "",
        title: str = "",
        note: str = "",
        query_text: str = "",
        active_family: str = "all",
        sort_by: str = "relevance",
        selected_result_id: str = "",
        selected_replay_step_id: str = "",
        selected_comparison_run_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot save evidence views.")
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")

        job = None
        run_id = ""
        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            if str(dict(job.get("metadata", {})).get("study_id") or "") != study.study_id:
                raise AuthorizationError("The selected validation job does not belong to the selected study.")
            if str(job.get("status") or "") != "completed":
                raise ValueError("Only completed validation jobs can be saved as evidence views.")
            run_id = _job_run_id(job)

        project = job_store.get_workspace_project(self.runtime_root, study.project_id)
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{study.project_id}' is not visible in this workspace.")

        now = utc_now_iso()
        evidence_view_id = f"view_{uuid.uuid4().hex[:12]}"
        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        evidence_view_root = workspace_root / "collaboration" / "evidence_views" / evidence_view_id
        evidence_view_root.mkdir(parents=True, exist_ok=True)
        payload_path = evidence_view_root / "evidence_view.json"
        saved_title = title.strip() or f"{study.title} evidence view"
        payload = {
            "evidence_view_id": evidence_view_id,
            "workspace_id": workspace.workspace_id,
            "project_id": project.project_id,
            "study_id": study.study_id,
            "job_id": str(job.get("job_id") or "") if job else None,
            "run_id": run_id or None,
            "title": saved_title,
            "note": note.strip(),
            "query_text": query_text.strip(),
            "active_family": active_family.strip() or "all",
            "sort_by": sort_by.strip() or "relevance",
            "selected_result_id": selected_result_id.strip() or None,
            "selected_replay_step_id": selected_replay_step_id.strip() or None,
            "selected_comparison_run_id": selected_comparison_run_id.strip() or None,
            "created_at": now,
            "created_by_user_id": auth.user_id,
            "metadata": dict(metadata or {}),
        }
        write_json(payload_path, payload)
        write_markdown(
            evidence_view_root / "README.md",
            "\n".join(
                [
                    f"# {saved_title}",
                    "",
                    f"- study_id: {study.study_id}",
                    f"- job_id: {payload['job_id'] or '-'}",
                    f"- run_id: {payload['run_id'] or '-'}",
                    f"- family: {payload['active_family']}",
                    f"- sort: {payload['sort_by']}",
                    "",
                    payload["note"] or "No note provided.",
                ]
            ),
        )
        evidence_view = WorkspaceEvidenceView(
            evidence_view_id=evidence_view_id,
            workspace_id=workspace.workspace_id,
            project_id=project.project_id,
            study_id=study.study_id,
            job_id=str(job.get("job_id") or "") if job else None,
            run_id=run_id or None,
            title=saved_title,
            note=note.strip(),
            query_text=query_text.strip(),
            active_family=active_family.strip() or "all",
            sort_by=sort_by.strip() or "relevance",
            selected_result_id=selected_result_id.strip() or None,
            selected_replay_step_id=selected_replay_step_id.strip() or None,
            selected_comparison_run_id=selected_comparison_run_id.strip() or None,
            payload_path=str(payload_path),
            created_by_user_id=auth.user_id,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )
        created = job_store.create_workspace_evidence_view(self.runtime_root, evidence_view)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="evidence_view.saved",
                target_type="evidence_view",
                target_id=created.evidence_view_id,
                event_payload={
                    "study_id": created.study_id,
                    "job_id": created.job_id,
                    "active_family": created.active_family,
                    "sort_by": created.sort_by,
                },
                created_at=now,
            ),
        )
        return self._evidence_view_summary(created)

    def list_workspace_evidence_views(
        self,
        auth: AuthContext,
        *,
        study_id: str = "",
        job_id: str = "",
    ) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if study_id.strip():
            study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            if str(job.get("workspace_id") or "") != auth.workspace_id:
                raise AuthorizationError(f"Validation job '{job_id}' is not visible in this workspace.")
        return [
            self._evidence_view_summary(view)
            for view in job_store.list_workspace_evidence_views(
                self.runtime_root,
                auth.workspace_id,
                study_id=study_id.strip(),
                job_id=job_id.strip(),
            )
        ]

    def get_workspace_evidence_view(self, auth: AuthContext, evidence_view_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        view = job_store.get_workspace_evidence_view(self.runtime_root, evidence_view_id)
        if view is None or view.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace evidence view '{evidence_view_id}' is not visible in this workspace.")
        return self._evidence_view_summary(view)

    def create_workspace_decision_log(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        title: str = "",
        decision_summary: str = "",
        rationale: str = "",
        job_id: str = "",
        evidence_view_id: str = "",
        selected_result_id: str = "",
        selected_comparison_run_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot create decision logs.")
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        clean_decision_summary = decision_summary.strip()
        if not clean_decision_summary:
            raise ValueError("Field 'decision_summary' is required.")

        job = None
        run_id = ""
        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            if str(dict(job.get("metadata", {})).get("study_id") or "") != study.study_id:
                raise AuthorizationError("The selected validation job does not belong to the selected study.")
            run_id = _job_run_id(job)

        linked_evidence_view = None
        if evidence_view_id.strip():
            linked_evidence_view = job_store.get_workspace_evidence_view(self.runtime_root, evidence_view_id.strip())
            if linked_evidence_view is None or linked_evidence_view.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace evidence view '{evidence_view_id}' is not visible in this workspace.")
            if linked_evidence_view.study_id != study.study_id:
                raise AuthorizationError("The selected evidence view does not belong to the selected study.")

        project = job_store.get_workspace_project(self.runtime_root, study.project_id)
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{study.project_id}' is not visible in this workspace.")

        now = utc_now_iso()
        decision_metadata = dict(metadata or {})
        review_history = decision_metadata.get("review_status_history")
        if not isinstance(review_history, list):
            review_history = []
        review_status = str(decision_metadata.get("review_status") or "draft").strip() or "draft"
        if review_status not in DECISION_REVIEW_STATUSES:
            review_status = "draft"
        if not review_history:
            review_history = [{
                "status": review_status,
                "changed_at": now,
                "changed_by_user_id": auth.user_id,
                "note": "Decision log created."
            }]
        decision_metadata.update({
            "review_status": review_status,
            "review_status_history": review_history,
            "review_status_updated_at": str(decision_metadata.get("review_status_updated_at") or now),
            "review_status_updated_by_user_id": str(
                decision_metadata.get("review_status_updated_by_user_id") or auth.user_id
            ),
            "latest_review_note": str(decision_metadata.get("latest_review_note") or ""),
        })
        decision_log_id = f"decision_{uuid.uuid4().hex[:12]}"
        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        decision_log_root = workspace_root / "collaboration" / "decision_logs" / decision_log_id
        decision_log_root.mkdir(parents=True, exist_ok=True)
        payload_path = decision_log_root / "decision_log.json"
        saved_title = title.strip() or f"{study.title} decision"
        decision_log = WorkspaceDecisionLog(
            decision_log_id=decision_log_id,
            workspace_id=workspace.workspace_id,
            project_id=project.project_id,
            study_id=study.study_id,
            job_id=str(job.get("job_id") or "") if job else None,
            run_id=run_id or None,
            evidence_view_id=linked_evidence_view.evidence_view_id if linked_evidence_view else None,
            title=saved_title,
            decision_summary=clean_decision_summary,
            rationale=rationale.strip(),
            selected_result_id=selected_result_id.strip() or None,
            selected_comparison_run_id=selected_comparison_run_id.strip() or None,
            payload_path=str(payload_path),
            created_by_user_id=auth.user_id,
            created_at=now,
            updated_at=now,
            metadata=decision_metadata,
        )
        self._materialize_decision_log_artifacts(decision_log, comment_summaries=[])
        created = job_store.create_workspace_decision_log(self.runtime_root, decision_log)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="decision_log.created",
                target_type="decision_log",
                target_id=created.decision_log_id,
                event_payload={
                    "study_id": created.study_id,
                    "job_id": created.job_id,
                    "evidence_view_id": created.evidence_view_id,
                },
                created_at=now,
            ),
        )
        return self._decision_log_summary(created)

    def create_workspace_decision_comment(
        self,
        auth: AuthContext,
        *,
        decision_log_id: str,
        body: str,
        parent_comment_id: str = "",
        anchor_kind: str = "general",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot comment on decision logs.")
        decision_log = job_store.get_workspace_decision_log(self.runtime_root, decision_log_id.strip())
        if decision_log is None or decision_log.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace decision log '{decision_log_id}' is not visible in this workspace.")
        clean_body = body.strip()
        if not clean_body:
            raise ValueError("Field 'body' is required.")
        normalized_anchor_kind = str(anchor_kind or "general").strip() or "general"
        if normalized_anchor_kind not in DECISION_COMMENT_ANCHOR_KINDS:
            raise ValueError(f"Unsupported decision comment anchor '{normalized_anchor_kind}'.")
        parent_comment = None
        if parent_comment_id.strip():
            parent_comment = job_store.get_workspace_decision_comment(self.runtime_root, parent_comment_id.strip())
            if parent_comment is None or parent_comment.workspace_id != auth.workspace_id:
                raise AuthorizationError(
                    f"Workspace decision comment '{parent_comment_id}' is not visible in this workspace."
                )
            if parent_comment.decision_log_id != decision_log.decision_log_id:
                raise AuthorizationError("Reply comments must stay inside the same decision-log thread.")

        now = utc_now_iso()
        decision_comment = WorkspaceDecisionComment(
            decision_comment_id=f"decision_comment_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace.workspace_id,
            project_id=decision_log.project_id,
            study_id=decision_log.study_id,
            decision_log_id=decision_log.decision_log_id,
            parent_comment_id=parent_comment.decision_comment_id if parent_comment else None,
            anchor_kind=normalized_anchor_kind,
            body=clean_body,
            created_by_user_id=auth.user_id,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )
        created = job_store.create_workspace_decision_comment(self.runtime_root, decision_comment)
        updated_decision_log = job_store.update_workspace_decision_log_metadata(
            self.runtime_root,
            decision_log_id=decision_log.decision_log_id,
            metadata_updates={
                "last_commented_at": now,
                "last_commented_by_user_id": auth.user_id,
            },
            updated_at=now,
        ) or decision_log
        comment_summaries = self.list_workspace_decision_comments(auth, decision_log_id=decision_log.decision_log_id)
        self._materialize_decision_log_artifacts(updated_decision_log, comment_summaries=comment_summaries)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="decision_log.commented",
                target_type="decision_log",
                target_id=decision_log.decision_log_id,
                event_payload={
                    "study_id": decision_log.study_id,
                    "decision_comment_id": created.decision_comment_id,
                    "parent_comment_id": created.parent_comment_id,
                    "anchor_kind": created.anchor_kind,
                },
                created_at=now,
            ),
        )
        return next(
            (
                comment_summary
                for comment_summary in comment_summaries
                if str(comment_summary.get("decision_comment_id") or "") == created.decision_comment_id
            ),
            self._decision_comment_summary(created, decision_comments=[created]),
        )

    def list_workspace_decision_logs(
        self,
        auth: AuthContext,
        *,
        study_id: str = "",
        job_id: str = "",
        evidence_view_id: str = "",
    ) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if study_id.strip():
            study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            if str(job.get("workspace_id") or "") != auth.workspace_id:
                raise AuthorizationError(f"Validation job '{job_id}' is not visible in this workspace.")
        if evidence_view_id.strip():
            view = job_store.get_workspace_evidence_view(self.runtime_root, evidence_view_id.strip())
            if view is None or view.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace evidence view '{evidence_view_id}' is not visible in this workspace.")
        return [
            self._decision_log_summary(log)
            for log in job_store.list_workspace_decision_logs(
                self.runtime_root,
                auth.workspace_id,
                study_id=study_id.strip(),
                job_id=job_id.strip(),
                evidence_view_id=evidence_view_id.strip(),
            )
        ]

    def get_workspace_decision_log(self, auth: AuthContext, decision_log_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        log = job_store.get_workspace_decision_log(self.runtime_root, decision_log_id)
        if log is None or log.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace decision log '{decision_log_id}' is not visible in this workspace.")
        return self._decision_log_summary(log)

    def list_workspace_decision_comments(
        self,
        auth: AuthContext,
        *,
        decision_log_id: str = "",
        study_id: str = "",
    ) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if decision_log_id.strip():
            decision_log = job_store.get_workspace_decision_log(self.runtime_root, decision_log_id.strip())
            if decision_log is None or decision_log.workspace_id != auth.workspace_id:
                raise AuthorizationError(
                    f"Workspace decision log '{decision_log_id}' is not visible in this workspace."
                )
        if study_id.strip():
            study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        comments = job_store.list_workspace_decision_comments(
            self.runtime_root,
            auth.workspace_id,
            decision_log_id=decision_log_id.strip(),
            study_id=study_id.strip(),
        )
        return [self._decision_comment_summary(comment, decision_comments=comments) for comment in comments]

    def update_workspace_decision_review_status(
        self,
        auth: AuthContext,
        *,
        decision_log_id: str,
        review_status: str,
        note: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot update decision review status.")
        decision_log = job_store.get_workspace_decision_log(self.runtime_root, decision_log_id.strip())
        if decision_log is None or decision_log.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace decision log '{decision_log_id}' is not visible in this workspace.")
        normalized_status = str(review_status or "").strip()
        if normalized_status not in DECISION_REVIEW_STATUSES:
            raise ValueError(f"Unsupported decision review status '{normalized_status}'.")
        now = utc_now_iso()
        merged_metadata = dict(decision_log.metadata)
        merged_metadata.update(dict(metadata or {}))
        history = merged_metadata.get("review_status_history")
        if not isinstance(history, list):
            history = []
        history = [
            item for item in history
            if isinstance(item, dict) and str(item.get("status") or "").strip()
        ]
        history.append({
            "status": normalized_status,
            "changed_at": now,
            "changed_by_user_id": auth.user_id,
            "note": note.strip(),
        })
        merged_metadata.update({
            "review_status": normalized_status,
            "review_status_history": history,
            "review_status_updated_at": now,
            "review_status_updated_by_user_id": auth.user_id,
            "latest_review_note": note.strip(),
        })
        updated = job_store.update_workspace_decision_log_metadata(
            self.runtime_root,
            decision_log_id=decision_log.decision_log_id,
            metadata_updates=merged_metadata,
            updated_at=now,
        )
        if updated is None:
            raise FileNotFoundError(f"Workspace decision log '{decision_log_id}' could not be updated.")
        comment_summaries = self.list_workspace_decision_comments(auth, decision_log_id=decision_log.decision_log_id)
        self._materialize_decision_log_artifacts(updated, comment_summaries=comment_summaries)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="decision_log.review_status_updated",
                target_type="decision_log",
                target_id=decision_log.decision_log_id,
                event_payload={
                    "study_id": decision_log.study_id,
                    "review_status": normalized_status,
                    "note": note.strip() or None,
                },
                created_at=now,
            ),
        )
        return self._decision_log_summary(updated)

    def create_workspace_export_bundle(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        job_id: str,
        title: str = "",
        export_format: str = "bundle_json",
        artifact_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in EXPORTABLE_ROLE_SET:
            raise AuthorizationError(f"Role '{auth.role}' cannot create export bundles.")

        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        job = self.get_validation_job(auth, job_id.strip())
        if str(job.get("status")) != "completed":
            raise ValueError("Only completed validation jobs can be exported.")

        job_metadata = dict(job.get("metadata", {}))
        if str(job_metadata.get("study_id") or "") != study.study_id:
            raise AuthorizationError("The selected validation job does not belong to the selected study.")

        run_id = str(job_metadata.get("run_id") or "")
        if not run_id:
            output_run_path = str(job.get("output_run_path") or "")
            run_id = Path(output_run_path).name if output_run_path else ""
        if not run_id:
            raise ValueError("The selected validation job has no exportable run id.")
        output_run_path = str(job.get("output_run_path") or "")
        run_dir = Path(output_run_path)
        if not output_run_path or not run_dir.exists():
            raise FileNotFoundError("The selected validation job has no available run artifact directory.")

        project = job_store.get_workspace_project(self.runtime_root, study.project_id)
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{study.project_id}' is not visible in this workspace.")

        normalized_format = str(export_format or "bundle_json").strip() or "bundle_json"
        if normalized_format not in {"bundle_json", "report_markdown", "report_json", "report_csv"}:
            raise ValueError(f"Unsupported export format '{normalized_format}'.")

        now = utc_now_iso()
        export_bundle_id = f"export_{uuid.uuid4().hex[:12]}"
        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        bundle_root = workspace_root / "exports" / export_bundle_id
        bundle_root.mkdir(parents=True, exist_ok=True)

        synthetic_boundary = (
            "Synthetic evidence only. This export is derived from synthetic-user research and is not human market proof."
        )
        exported_files = self._materialize_export_bundle_files(
            bundle_root=bundle_root,
            run_dir=run_dir,
            export_format=normalized_format,
            artifact_ids=artifact_ids or [],
            study=study,
            job=job,
            synthetic_boundary=synthetic_boundary,
        )
        manifest_path = bundle_root / "export_manifest.json"
        manifest_payload = {
            "export_bundle_id": export_bundle_id,
            "workspace_id": workspace.workspace_id,
            "project_id": project.project_id,
            "study_id": study.study_id,
            "job_id": str(job.get("job_id") or ""),
            "run_id": run_id,
            "title": title.strip() or f"{study.title} export",
            "status": "published",
            "export_format": normalized_format,
            "synthetic_boundary": synthetic_boundary,
            "created_at": now,
            "created_by_user_id": auth.user_id,
            "exported_files": exported_files,
            "study_context": {
                "title": study.title,
                "research_intent": study.research_intent,
                "desired_output": study.desired_output,
                "first_task": study.first_task,
            },
            "job_context": {
                "provider_name": str(job.get("provider_name") or ""),
                "status": str(job.get("status") or ""),
                "output_run_path": output_run_path,
            },
            "metadata": dict(metadata or {}),
        }
        write_json(manifest_path, manifest_payload)
        write_markdown(
            bundle_root / "README.md",
            "\n".join(
                [
                    f"# {manifest_payload['title']}",
                    "",
                    f"- synthetic boundary: {synthetic_boundary}",
                    f"- project_id: {project.project_id}",
                    f"- study_id: {study.study_id}",
                    f"- job_id: {job['job_id']}",
                    f"- run_id: {run_id}",
                    f"- export_format: {normalized_format}",
                    "",
                    "This bundle preserves study and run lineage for synthetic evidence review.",
                ]
            ),
        )

        export_bundle = WorkspaceExportBundle(
            export_bundle_id=export_bundle_id,
            workspace_id=workspace.workspace_id,
            project_id=project.project_id,
            study_id=study.study_id,
            job_id=str(job.get("job_id") or ""),
            run_id=run_id,
            title=str(manifest_payload["title"]),
            status="published",
            export_format=normalized_format,
            created_by_user_id=auth.user_id,
            bundle_root=str(bundle_root),
            manifest_path=str(manifest_path),
            exported_files=exported_files,
            synthetic_boundary=synthetic_boundary,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )
        created = job_store.create_workspace_export_bundle(self.runtime_root, export_bundle)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="export_bundle.created",
                target_type="export_bundle",
                target_id=created.export_bundle_id,
                event_payload={
                    "project_id": created.project_id,
                    "study_id": created.study_id,
                    "job_id": created.job_id,
                    "run_id": created.run_id,
                    "export_format": created.export_format,
                    "manifest_path": created.manifest_path,
                },
                created_at=now,
            ),
        )
        return self._export_bundle_summary(created)

    def list_workspace_export_bundles(
        self,
        auth: AuthContext,
        *,
        study_id: str = "",
        job_id: str = "",
    ) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if study_id.strip():
            study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            if str(job.get("workspace_id") or "") != auth.workspace_id:
                raise AuthorizationError(f"Validation job '{job_id}' is not visible in this workspace.")
        return [
            self._export_bundle_summary(bundle)
            for bundle in job_store.list_workspace_export_bundles(
                self.runtime_root,
                auth.workspace_id,
                study_id=study_id.strip(),
                job_id=job_id.strip(),
            )
        ]

    def get_workspace_export_bundle(self, auth: AuthContext, export_bundle_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        export_bundle = job_store.get_workspace_export_bundle(self.runtime_root, export_bundle_id)
        if export_bundle is None or export_bundle.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace export bundle '{export_bundle_id}' is not visible in this workspace.")
        return self._export_bundle_summary(export_bundle)

    def create_workspace_share_bundle(
        self,
        auth: AuthContext,
        *,
        export_bundle_id: str,
        title: str = "",
        expires_in_days: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SHAREABLE_ROLE_SET:
            raise AuthorizationError(f"Role '{auth.role}' cannot create share bundles.")

        export_bundle = job_store.get_workspace_export_bundle(self.runtime_root, export_bundle_id.strip())
        if export_bundle is None or export_bundle.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace export bundle '{export_bundle_id}' is not visible in this workspace.")
        if str(export_bundle.status) != "published":
            raise ValueError("Only published export bundles can be shared.")

        project = job_store.get_workspace_project(self.runtime_root, export_bundle.project_id)
        study = job_store.get_workspace_study(self.runtime_root, export_bundle.study_id)
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{export_bundle.project_id}' is not visible in this workspace.")
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{export_bundle.study_id}' is not visible in this workspace.")

        if expires_in_days is not None and int(expires_in_days) < 1:
            raise ValueError("Field 'expires_in_days' must be at least 1 when provided.")

        now = utc_now_iso()
        share_bundle_id = f"share_{uuid.uuid4().hex[:12]}"
        share_key = f"shk_{uuid.uuid4().hex[:20]}"
        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        share_root = workspace_root / "shares" / share_bundle_id
        share_root.mkdir(parents=True, exist_ok=True)
        public_files_root = share_root / "files"
        public_files_root.mkdir(parents=True, exist_ok=True)
        public_path = f"/public/v1/share-bundles/{share_key}"
        share_payload_path = share_root / "share_payload.json"
        expires_at = None
        if expires_in_days is not None:
            expires_at = (_now() + timedelta(days=int(expires_in_days))).replace(microsecond=0).isoformat()

        public_files: list[dict[str, Any]] = []
        for file_entry in export_bundle.exported_files:
            bundle_path = Path(str(file_entry.get("bundle_path") or ""))
            if not bundle_path.exists() or not bundle_path.is_file():
                raise FileNotFoundError(f"Exported file not found for share delivery: {bundle_path}")
            destination = public_files_root / bundle_path.name
            export_file(bundle_path, destination)
            public_files.append(
                {
                    "artifact_id": str(file_entry.get("artifact_id") or bundle_path.name),
                    "export_kind": str(file_entry.get("export_kind") or "bundle_artifact"),
                    "mime_type": str(file_entry.get("mime_type") or (mimetypes.guess_type(destination.name)[0] or "application/octet-stream")),
                    "file_name": destination.name,
                    "relative_path": f"files/{destination.name}",
                }
            )

        share_payload = {
            "contract_version": "workspace-share-bundle/v0-draft",
            "share_bundle_id": share_bundle_id,
            "share_key": share_key,
            "public_path": public_path,
            "title": title.strip() or export_bundle.title,
            "status": "published",
            "synthetic_boundary": export_bundle.synthetic_boundary,
            "published_at": now,
            "expires_at": expires_at,
            "source": {
                "export_bundle_id": export_bundle.export_bundle_id,
                "project_id": export_bundle.project_id,
                "study_id": export_bundle.study_id,
                "job_id": export_bundle.job_id,
                "run_id": export_bundle.run_id,
                "export_format": export_bundle.export_format,
            },
            "study_context": {
                "title": study.title,
                "status": study.status,
                "research_intent": study.research_intent,
                "desired_output": study.desired_output,
                "first_task": study.first_task,
            },
            "files": public_files,
            "viewer_guidance": {
                "share_intent": "Viewer-safe synthetic evidence delivery",
                "lineage_rule": "Study, job, and run lineage stay visible in every shared bundle.",
            },
            "metadata": dict(metadata or {}),
        }
        write_json(share_payload_path, share_payload)
        write_markdown(
            share_root / "README.md",
            "\n".join(
                [
                    f"# {share_payload['title']}",
                    "",
                    f"- public_path: {public_path}",
                    f"- export_bundle_id: {export_bundle.export_bundle_id}",
                    f"- project_id: {export_bundle.project_id}",
                    f"- study_id: {export_bundle.study_id}",
                    f"- job_id: {export_bundle.job_id}",
                    f"- run_id: {export_bundle.run_id}",
                    f"- synthetic boundary: {export_bundle.synthetic_boundary}",
                    "",
                    "This share bundle exposes a viewer-safe payload without requiring workspace filesystem inspection.",
                ]
            ),
        )

        share_bundle = WorkspaceShareBundle(
            share_bundle_id=share_bundle_id,
            workspace_id=workspace.workspace_id,
            export_bundle_id=export_bundle.export_bundle_id,
            project_id=export_bundle.project_id,
            study_id=export_bundle.study_id,
            job_id=export_bundle.job_id,
            run_id=export_bundle.run_id,
            title=str(share_payload["title"]),
            status="published",
            share_key=share_key,
            public_path=public_path,
            share_root=str(share_root),
            share_payload_path=str(share_payload_path),
            created_by_user_id=auth.user_id,
            synthetic_boundary=export_bundle.synthetic_boundary,
            published_at=now,
            expires_at=expires_at,
            revoked_at=None,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )
        created = job_store.create_workspace_share_bundle(self.runtime_root, share_bundle)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="share_bundle.created",
                target_type="share_bundle",
                target_id=created.share_bundle_id,
                event_payload={
                    "export_bundle_id": created.export_bundle_id,
                    "project_id": created.project_id,
                    "study_id": created.study_id,
                    "job_id": created.job_id,
                    "run_id": created.run_id,
                    "public_path": created.public_path,
                    "expires_at": created.expires_at,
                },
                created_at=now,
            ),
        )
        return self._share_bundle_summary(created)

    def list_workspace_share_bundles(
        self,
        auth: AuthContext,
        *,
        study_id: str = "",
        export_bundle_id: str = "",
    ) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if study_id.strip():
            study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        if export_bundle_id.strip():
            export_bundle = job_store.get_workspace_export_bundle(self.runtime_root, export_bundle_id.strip())
            if export_bundle is None or export_bundle.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace export bundle '{export_bundle_id}' is not visible in this workspace.")
        return [
            self._share_bundle_summary(self._refresh_share_bundle_status(bundle))
            for bundle in job_store.list_workspace_share_bundles(
                self.runtime_root,
                auth.workspace_id,
                study_id=study_id.strip(),
                export_bundle_id=export_bundle_id.strip(),
            )
        ]

    def get_workspace_share_bundle(self, auth: AuthContext, share_bundle_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        share_bundle = job_store.get_workspace_share_bundle(self.runtime_root, share_bundle_id)
        if share_bundle is None or share_bundle.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace share bundle '{share_bundle_id}' is not visible in this workspace.")
        share_bundle = self._refresh_share_bundle_status(share_bundle)
        return self._share_bundle_summary(share_bundle)

    def revoke_workspace_share_bundle(self, auth: AuthContext, share_bundle_id: str) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SHAREABLE_ROLE_SET:
            raise AuthorizationError(f"Role '{auth.role}' cannot revoke share bundles.")
        share_bundle = job_store.get_workspace_share_bundle(self.runtime_root, share_bundle_id)
        if share_bundle is None or share_bundle.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace share bundle '{share_bundle_id}' is not visible in this workspace.")
        now = utc_now_iso()
        updated = job_store.update_workspace_share_bundle(
            self.runtime_root,
            share_bundle_id=share_bundle.share_bundle_id,
            status="revoked",
            revoked_at=share_bundle.revoked_at or now,
        )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="share_bundle.revoked",
                target_type="share_bundle",
                target_id=updated.share_bundle_id,
                event_payload={
                    "export_bundle_id": updated.export_bundle_id,
                    "project_id": updated.project_id,
                    "study_id": updated.study_id,
                    "job_id": updated.job_id,
                    "run_id": updated.run_id,
                    "public_path": updated.public_path,
                    "revoked_at": updated.revoked_at,
                },
                created_at=now,
            ),
        )
        return self._share_bundle_summary(updated)

    def get_public_share_bundle(self, share_key: str) -> dict[str, Any]:
        share_bundle = job_store.get_workspace_share_bundle_by_key(self.runtime_root, share_key.strip())
        if share_bundle is None:
            raise FileNotFoundError(f"Unknown public share bundle '{share_key}'.")
        share_bundle = self._refresh_share_bundle_status(share_bundle)
        if share_bundle.status == "revoked":
            raise ShareUnavailableError(f"Share bundle '{share_bundle.share_bundle_id}' has been revoked.")
        if share_bundle.status == "expired":
            raise ShareUnavailableError(f"Share bundle '{share_bundle.share_bundle_id}' has expired.")
        payload_path = Path(share_bundle.share_payload_path)
        if not payload_path.exists():
            raise FileNotFoundError(f"Share payload not found: {payload_path}")
        payload = read_json(payload_path)
        if not isinstance(payload, dict):
            raise ValueError("Share payload must contain an object payload.")
        payload["status"] = share_bundle.status
        payload["published_at"] = share_bundle.published_at
        payload["expires_at"] = share_bundle.expires_at
        payload["public_path"] = share_bundle.public_path
        return payload

    def describe_workspace_support(
        self,
        auth: AuthContext,
        *,
        job_id: str = "",
    ) -> dict[str, Any]:
        workspace, billing = self._workspace_and_billing(auth)
        limits = _plan_limits(workspace.plan_tier, workspace.settings)
        jobs = job_store.list_workspace_jobs(self.runtime_root, auth.workspace_id)
        job = self.get_validation_job(auth, job_id.strip()) if job_id.strip() else None
        submission_gate = self._support_submission_gate(auth, workspace, billing, limits, jobs)
        support_summary = self._support_summary_for_job(job) if job is not None else None
        recent_failed_jobs = [
            self._support_job_digest(candidate)
            for candidate in jobs
            if str(candidate.get("status") or "") in {"failed", "canceled"}
        ][:5]
        return {
            "contract_version": "workspace-support-surface/v0-draft",
            "workspace_id": auth.workspace_id,
            "selected_job_id": str(job.get("job_id") or "") if job else None,
            "submission_gate": submission_gate,
            "job_diagnostic": support_summary,
            "recent_failed_jobs": recent_failed_jobs,
            "support_snapshot_count": len(job_store.list_workspace_support_snapshots(self.runtime_root, auth.workspace_id)),
            "synthetic_boundary": (
                "Synthetic evidence only. Support diagnostics describe synthetic research runtime state, not human market proof."
            ),
        }

    def create_workspace_support_snapshot(
        self,
        auth: AuthContext,
        *,
        job_id: str,
        title: str = "",
        notes: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        job = self.get_validation_job(auth, job_id.strip())
        support_payload = self.describe_workspace_support(auth, job_id=str(job.get("job_id") or ""))
        job_metadata = dict(job.get("metadata", {}))
        project_id = str(job_metadata.get("project_id") or "").strip() or None
        study_id = str(job_metadata.get("study_id") or "").strip() or None
        run_id = str(job_metadata.get("run_id") or "").strip() or None
        now = utc_now_iso()
        support_snapshot_id = f"support_{uuid.uuid4().hex[:12]}"
        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        support_root = workspace_root / "support" / support_snapshot_id
        support_root.mkdir(parents=True, exist_ok=True)
        snapshot_path = support_root / "support_snapshot.json"
        summary = str(
            support_payload.get("job_diagnostic", {}) and support_payload["job_diagnostic"].get("summary")
            or "Workspace support snapshot"
        )
        snapshot_payload = {
            "support_snapshot_id": support_snapshot_id,
            "workspace_id": workspace.workspace_id,
            "project_id": project_id,
            "study_id": study_id,
            "job_id": str(job.get("job_id") or ""),
            "run_id": run_id,
            "title": title.strip() or f"Support snapshot for {job['job_id']}",
            "summary": summary,
            "notes": notes.strip(),
            "created_at": now,
            "created_by_user_id": auth.user_id,
            "diagnostic": support_payload,
            "metadata": dict(metadata or {}),
        }
        write_json(snapshot_path, snapshot_payload)
        write_markdown(
            support_root / "README.md",
            "\n".join(
                [
                    f"# {snapshot_payload['title']}",
                    "",
                    f"- job_id: {snapshot_payload['job_id']}",
                    f"- project_id: {project_id or '-'}",
                    f"- study_id: {study_id or '-'}",
                    f"- run_id: {run_id or '-'}",
                    f"- summary: {summary}",
                    "",
                    snapshot_payload["notes"] or "No operator notes provided.",
                ]
            ),
        )
        support_snapshot = WorkspaceSupportSnapshot(
            support_snapshot_id=support_snapshot_id,
            workspace_id=workspace.workspace_id,
            project_id=project_id,
            study_id=study_id,
            job_id=str(job.get("job_id") or ""),
            run_id=run_id,
            title=str(snapshot_payload["title"]),
            status="generated",
            summary=summary,
            support_root=str(support_root),
            snapshot_path=str(snapshot_path),
            created_by_user_id=auth.user_id,
            created_at=now,
            updated_at=now,
            metadata={
                **dict(metadata or {}),
                "notes": notes.strip(),
            },
        )
        created = job_store.create_workspace_support_snapshot(self.runtime_root, support_snapshot)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="support_snapshot.created",
                target_type="support_snapshot",
                target_id=created.support_snapshot_id,
                event_payload={
                    "project_id": created.project_id,
                    "study_id": created.study_id,
                    "job_id": created.job_id,
                    "run_id": created.run_id,
                    "summary": created.summary,
                },
                created_at=created.created_at,
            ),
        )
        return self._support_snapshot_summary(created)

    def list_workspace_support_snapshots(
        self,
        auth: AuthContext,
        *,
        study_id: str = "",
        job_id: str = "",
    ) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if study_id.strip():
            study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            if str(job.get("workspace_id") or "") != auth.workspace_id:
                raise AuthorizationError(f"Validation job '{job_id}' is not visible in this workspace.")
        return [
            self._support_snapshot_summary(snapshot)
            for snapshot in job_store.list_workspace_support_snapshots(
                self.runtime_root,
                auth.workspace_id,
                study_id=study_id.strip(),
                job_id=job_id.strip(),
            )
        ]

    def get_workspace_support_snapshot(self, auth: AuthContext, support_snapshot_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        snapshot = job_store.get_workspace_support_snapshot(self.runtime_root, support_snapshot_id)
        if snapshot is None or snapshot.workspace_id != auth.workspace_id:
            raise AuthorizationError(
                f"Workspace support snapshot '{support_snapshot_id}' is not visible in this workspace."
            )
        return self._support_snapshot_summary(snapshot)

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
        project_id = str(request.metadata.get("project_id") or "").strip()
        study_id = str(request.metadata.get("study_id") or "").strip()
        study: WorkspaceStudy | None = None
        project: WorkspaceProject | None = None
        if study_id:
            study = job_store.get_workspace_study(self.runtime_root, study_id)
            if study is None or study.workspace_id != workspace.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
            project = job_store.get_workspace_project(self.runtime_root, study.project_id)
            project_id = study.project_id
        if project_id:
            project = job_store.get_workspace_project(self.runtime_root, project_id)
            if project is None or project.workspace_id != workspace.workspace_id:
                raise AuthorizationError(f"Workspace project '{project_id}' is not visible in this workspace.")
        if study is not None and project is not None and study.project_id != project.project_id:
            raise AuthorizationError("The selected study does not belong to the selected project.")

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
        if project is not None:
            metadata["project_id"] = project.project_id
        if study is not None:
            metadata["study_id"] = study.study_id
        created = job_store.create_validation_job(
            self.runtime_root,
            job=job,
            persona_dir_path=str(persona_dir),
            idempotency_key=request.idempotency_key.strip(),
            metadata=metadata,
        )
        if study is not None:
            status = "ready" if created["status"] == "queued" else None
            job_store.update_workspace_study(
                self.runtime_root,
                study_id=study.study_id,
                latest_job_id=str(created["job_id"]),
                status=status,
                metadata_updates={"last_submitted_job_id": str(created["job_id"])},
            )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="validation_job.submitted",
                target_type="validation_job",
                target_id=str(created["job_id"]),
                event_payload={
                    "project_id": metadata.get("project_id") or None,
                    "study_id": metadata.get("study_id") or None,
                    "brief_id": brief.brief_id,
                    "provider_name": request.provider_name,
                    "panel_type": panel_spec.panel_type,
                    "sample_size": panel_spec.sample_size,
                    "job_status": str(created.get("status") or ""),
                },
                created_at=created_at,
            ),
        )
        return created

    def list_workspace_jobs(self, auth: AuthContext) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        return job_store.list_workspace_jobs(self.runtime_root, auth.workspace_id)

    def get_validation_job(self, auth: AuthContext, job_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        job = job_store.get_validation_job(self.runtime_root, job_id)
        if job is None or str(job["workspace_id"]) != auth.workspace_id:
            raise AuthorizationError(f"Validation job '{job_id}' is not visible in this workspace.")
        return job

    def cancel_validation_job(
        self,
        auth: AuthContext,
        job_id: str,
        *,
        reason: str = "",
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot cancel validation jobs.")

        job = self.get_validation_job(auth, job_id)
        status = str(job.get("status") or "")
        if status != "queued":
            raise ValueError("Only queued validation jobs can be canceled.")

        cancel_reason = reason.strip() or "Canceled from the workspace product surface before worker lease."
        updated = job_store.update_validation_job(
            self.runtime_root,
            job_id=job_id,
            status="canceled",
            last_error=cancel_reason,
            metadata_updates={
                "canceled_by_user_id": auth.user_id,
                "canceled_by_role": auth.role,
                "cancel_reason": cancel_reason,
            },
        )
        metadata = dict(updated.get("metadata", {}))
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="validation_job.canceled",
                target_type="validation_job",
                target_id=str(updated.get("job_id") or ""),
                event_payload={
                    "project_id": str(metadata.get("project_id") or "") or None,
                    "study_id": str(metadata.get("study_id") or "") or None,
                    "job_status": str(updated.get("status") or ""),
                    "cancel_reason": cancel_reason,
                },
                created_at=utc_now_iso(),
            ),
        )
        return updated

    def retry_validation_job(self, auth: AuthContext, job_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot retry validation jobs.")

        source_job = self.get_validation_job(auth, job_id)
        source_status = str(source_job.get("status") or "")
        if source_status not in {"failed", "canceled"}:
            raise ValueError("Only failed or canceled validation jobs can be retried.")

        source_metadata = dict(source_job.get("metadata", {}))
        retry_metadata = dict(source_metadata)
        for field in (
            "run_id",
            "artifact_retention_until",
            "artifact_deleted_at",
            "canceled_by_user_id",
            "canceled_by_role",
            "cancel_reason",
            "retry_of_job_id",
            "retry_source_job_id",
            "retry_source_status",
            "last_retry_job_id",
        ):
            retry_metadata.pop(field, None)
        retry_metadata["retry_of_job_id"] = str(source_job.get("job_id") or "")
        retry_metadata["retry_source_status"] = source_status

        retried = self.submit_validation_job(
            auth,
            ValidationJobRequest(
                brief_path=str(source_metadata.get("brief_path") or source_job.get("input_artifact_path") or ""),
                persona_dir=str(source_metadata.get("persona_dir") or source_job.get("persona_dir_path") or ""),
                panel_spec=PanelSpec(**dict(source_job.get("panel_spec") or {})),
                provider_name=str(source_job.get("provider_name") or "mock"),
                priority=str(source_job.get("priority") or "normal"),
                max_retries=int(source_metadata.get("max_retries", 1)),
                run_root=str(source_metadata.get("run_root") or "runs"),
                metadata=retry_metadata,
            ),
        )
        retried_metadata = dict(retried.get("metadata", {}))
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=auth.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="validation_job.retried",
                target_type="validation_job",
                target_id=str(retried.get("job_id") or ""),
                event_payload={
                    "source_job_id": str(source_job.get("job_id") or ""),
                    "source_status": source_status,
                    "project_id": str(retried_metadata.get("project_id") or "") or None,
                    "study_id": str(retried_metadata.get("study_id") or "") or None,
                },
                created_at=utc_now_iso(),
            ),
        )
        return retried

    def describe_workspace_session(self, auth: AuthContext) -> dict[str, Any]:
        workspace, billing = self._workspace_and_billing(auth)
        limits = _plan_limits(workspace.plan_tier, workspace.settings)
        jobs = job_store.list_workspace_jobs(self.runtime_root, auth.workspace_id)
        projects = job_store.list_workspace_projects(self.runtime_root, auth.workspace_id)
        studies = job_store.list_workspace_studies(self.runtime_root, auth.workspace_id)
        evidence_views = job_store.list_workspace_evidence_views(self.runtime_root, auth.workspace_id)
        decision_logs = job_store.list_workspace_decision_logs(self.runtime_root, auth.workspace_id)
        decision_comments = job_store.list_workspace_decision_comments(self.runtime_root, auth.workspace_id)
        export_bundles = job_store.list_workspace_export_bundles(self.runtime_root, auth.workspace_id)
        share_bundles = job_store.list_workspace_share_bundles(self.runtime_root, auth.workspace_id)
        support_snapshots = job_store.list_workspace_support_snapshots(self.runtime_root, auth.workspace_id)
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
                "workspace_settings": True,
                "billing_surface": True,
                "study_collaboration": True,
                "study_activity": True,
                "decision_review": True,
                "audit_history": True,
                "project_studies": True,
                "export_bundles": True,
                "share_bundles": True,
                "support_surface": True,
            },
            "product_counts": {
                "projects": len(projects),
                "studies": len(studies),
                "evidence_views": len(evidence_views),
                "decision_logs": len(decision_logs),
                "decision_comments": len(decision_comments),
                "export_bundles": len(export_bundles),
                "share_bundles": len(share_bundles),
                "support_snapshots": len(support_snapshots),
            },
            "synthetic_boundary": (
                "Synthetic evidence only. Authenticated workspace access does not change the evidence boundary."
            ),
        }

    def describe_workspace_shell(
        self,
        auth: AuthContext,
        *,
        project_id: str = "",
        study_id: str = "",
        job_id: str = "",
        query_text: str = "",
        active_family: str = "all",
        sort_by: str = "relevance",
        selected_result_id: str = "",
        selected_replay_step_id: str = "",
        selected_comparison_run_id: str = "",
    ) -> dict[str, Any]:
        session = self.describe_workspace_session(auth)
        jobs = self.list_workspace_jobs(auth)
        projects = self.list_workspace_projects(auth)
        selected_project = None
        selected_study = None
        selected_job = None

        if study_id.strip():
            selected_study = self.get_workspace_study(auth, study_id.strip())
            selected_project = self.get_workspace_project(auth, str(selected_study["project_id"]))
        elif project_id.strip():
            selected_project = self.get_workspace_project(auth, project_id.strip())
        elif projects:
            selected_project = projects[0]

        studies = self.list_workspace_studies(
            auth,
            project_id=str(selected_project.get("project_id") or "") if selected_project else "",
        )
        if selected_study is None and studies:
            selected_study = studies[0]
        if selected_project is None and selected_study is not None:
            selected_project = self.get_workspace_project(auth, str(selected_study["project_id"]))

        if job_id.strip():
            selected_job = self.get_validation_job(auth, job_id.strip())
        elif selected_study and str(selected_study.get("latest_job_id") or "").strip():
            try:
                selected_job = self.get_validation_job(auth, str(selected_study["latest_job_id"]))
            except AuthorizationError:
                selected_job = None
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
                selected_comparison_run_id=selected_comparison_run_id,
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
            "projects": projects,
            "selected_project_id": str(selected_project.get("project_id") or "") if selected_project else None,
            "selected_project": selected_project,
            "studies": studies,
            "selected_study_id": str(selected_study.get("study_id") or "") if selected_study else None,
            "selected_study": selected_study,
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
        selected_comparison_run_id: str = "",
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
        query_payload = query_run_evidence(
            run_root,
            run_id=resolved_run_id,
            query_text=query_text,
            active_family=active_family,
            sort_by=sort_by,
            selected_result_id=selected_result_id,
            selected_replay_step_id=selected_replay_step_id,
            selected_comparison_run_id=selected_comparison_run_id,
        )
        run_job_lookup: dict[str, str] = {}
        run_job_context_lookup: dict[str, dict[str, Any]] = {}
        for job in job_store.list_workspace_jobs(self.runtime_root, auth.workspace_id):
            metadata = dict(job.get("metadata", {}))
            candidate_run_id = str(metadata.get("run_id") or "")
            if not candidate_run_id:
                output_run_path = str(job.get("output_run_path") or "")
                if output_run_path:
                    candidate_run_id = Path(output_run_path).name
            if candidate_run_id:
                candidate_job_id = str(job.get("job_id") or "")
                run_job_lookup[candidate_run_id] = candidate_job_id
                run_job_context_lookup[candidate_run_id] = {
                    "run_id": candidate_run_id,
                    "job_id": candidate_job_id or None,
                    "project_id": str(metadata.get("project_id") or "") or None,
                    "study_id": str(metadata.get("study_id") or "") or None,
                    "job_status": str(job.get("status") or "") or None,
                }

        cross_run_comparison = dict(query_payload.get("cross_run_comparison", {}))
        candidate_runs = cross_run_comparison.get("candidate_runs")
        if isinstance(candidate_runs, list):
            for item in candidate_runs:
                if isinstance(item, dict):
                    item["job_id"] = run_job_lookup.get(str(item.get("run_id") or "")) or None
        selected_comparison_run = cross_run_comparison.get("selected_comparison_run")
        if isinstance(selected_comparison_run, dict):
            selected_job_id = run_job_lookup.get(str(selected_comparison_run.get("run_id") or ""))
            selected_comparison_run["job_id"] = selected_job_id or None
            cross_run_comparison["selected_comparison_job_id"] = selected_job_id or None
        else:
            cross_run_comparison["selected_comparison_job_id"] = None
        query_payload["cross_run_comparison"] = cross_run_comparison

        audit_lineage = dict(query_payload.get("audit_lineage", {}))
        source_run = dict(audit_lineage.get("source_run", {}))
        source_context = run_job_context_lookup.get(resolved_run_id, {})
        source_run.update(
            {
                "job_id": source_context.get("job_id"),
                "project_id": source_context.get("project_id"),
                "study_id": source_context.get("study_id"),
                "job_status": source_context.get("job_status"),
            }
        )

        comparison_set = dict(audit_lineage.get("comparison_set", {}))
        comparison_set["candidate_jobs"] = [
            run_job_context_lookup.get(str(item.get("run_id") or ""), {
                "run_id": str(item.get("run_id") or ""),
                "job_id": None,
                "project_id": None,
                "study_id": None,
                "job_status": None,
            })
            for item in cross_run_comparison.get("candidate_runs", [])
            if isinstance(item, dict) and item.get("run_id")
        ]
        selected_comparison_run_id = str(comparison_set.get("selected_comparison_run_id") or "")
        selected_context = run_job_context_lookup.get(selected_comparison_run_id, {})
        comparison_set.update(
            {
                "selected_comparison_job_id": selected_context.get("job_id"),
                "selected_comparison_project_id": selected_context.get("project_id"),
                "selected_comparison_study_id": selected_context.get("study_id"),
            }
        )
        audit_lineage["source_run"] = source_run
        audit_lineage["comparison_set"] = comparison_set
        query_payload["audit_lineage"] = audit_lineage

        evidence_reliability = query_payload.get("evidence_reliability")
        if isinstance(evidence_reliability, dict):
            evidence_reliability["audit_lineage"] = audit_lineage
            query_payload["evidence_reliability"] = evidence_reliability
        return query_payload

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

        started_at = utc_now_iso()
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id="system_worker",
                actor_role="system",
                action="validation_job.started",
                target_type="validation_job",
                target_id=str(leased.get("job_id") or ""),
                event_payload={
                    "project_id": str(metadata.get("project_id") or "") or None,
                    "study_id": str(metadata.get("study_id") or "") or None,
                    "job_status": "running",
                    "provider_name": str(leased.get("provider_name") or ""),
                },
                created_at=started_at,
            ),
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
            completed_metadata = dict(updated.get("metadata", {}))
            job_store.create_audit_event(
                self.runtime_root,
                AuditEvent(
                    audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                    workspace_id=workspace.workspace_id,
                    actor_user_id="system_worker",
                    actor_role="system",
                    action="validation_job.completed",
                    target_type="validation_job",
                    target_id=str(updated.get("job_id") or ""),
                    event_payload={
                        "project_id": str(completed_metadata.get("project_id") or "") or None,
                        "study_id": str(completed_metadata.get("study_id") or "") or None,
                        "job_status": str(updated.get("status") or ""),
                        "run_id": str(completed_metadata.get("run_id") or "") or run_dir.name,
                        "artifact_retention_until": str(completed_metadata.get("artifact_retention_until") or "") or None,
                    },
                    created_at=utc_now_iso(),
                ),
            )
            return updated
        except Exception as exc:
            failed = job_store.update_validation_job(
                self.runtime_root,
                job_id=str(leased["job_id"]),
                status="failed",
                last_error=str(exc),
            )
            failed_metadata = dict(failed.get("metadata", {}))
            job_store.create_audit_event(
                self.runtime_root,
                AuditEvent(
                    audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                    workspace_id=workspace.workspace_id,
                    actor_user_id="system_worker",
                    actor_role="system",
                    action="validation_job.failed",
                    target_type="validation_job",
                    target_id=str(failed.get("job_id") or ""),
                    event_payload={
                        "project_id": str(failed_metadata.get("project_id") or "") or None,
                        "study_id": str(failed_metadata.get("study_id") or "") or None,
                        "job_status": str(failed.get("status") or ""),
                        "last_error": str(exc),
                    },
                    created_at=utc_now_iso(),
                ),
            )
            return failed

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

    def _decision_review_status(self, decision_log: WorkspaceDecisionLog) -> str:
        metadata = dict(decision_log.metadata or {})
        review_status = str(metadata.get("review_status") or "draft").strip() or "draft"
        return review_status if review_status in DECISION_REVIEW_STATUSES else "draft"

    def _decision_review_history(self, decision_log: WorkspaceDecisionLog) -> list[dict[str, Any]]:
        history = dict(decision_log.metadata or {}).get("review_status_history")
        if not isinstance(history, list):
            return []
        return [item for item in history if isinstance(item, dict)]

    def _materialize_decision_log_artifacts(
        self,
        decision_log: WorkspaceDecisionLog,
        *,
        comment_summaries: list[dict[str, Any]] | None = None,
    ) -> None:
        payload_path = Path(decision_log.payload_path)
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        review_status = self._decision_review_status(decision_log)
        latest_review_note = str(dict(decision_log.metadata or {}).get("latest_review_note") or "").strip()
        comments = list(comment_summaries or [])
        write_json(
            payload_path,
            {
                "decision_log_id": decision_log.decision_log_id,
                "workspace_id": decision_log.workspace_id,
                "project_id": decision_log.project_id,
                "study_id": decision_log.study_id,
                "job_id": decision_log.job_id,
                "run_id": decision_log.run_id,
                "evidence_view_id": decision_log.evidence_view_id,
                "title": decision_log.title,
                "decision_summary": decision_log.decision_summary,
                "rationale": decision_log.rationale,
                "selected_result_id": decision_log.selected_result_id,
                "selected_comparison_run_id": decision_log.selected_comparison_run_id,
                "review_status": review_status,
                "comment_count": len(comments),
                "review_status_history": self._decision_review_history(decision_log),
                "created_at": decision_log.created_at,
                "updated_at": decision_log.updated_at,
                "created_by_user_id": decision_log.created_by_user_id,
                "metadata": dict(decision_log.metadata or {}),
                "comments": comments,
            },
        )
        write_markdown(
            payload_path.parent / "README.md",
            "\n".join(
                [
                    f"# {decision_log.title}",
                    "",
                    f"- study_id: {decision_log.study_id}",
                    f"- job_id: {decision_log.job_id or '-'}",
                    f"- evidence_view_id: {decision_log.evidence_view_id or '-'}",
                    f"- review_status: {review_status}",
                    f"- comment_count: {len(comments)}",
                    "",
                    decision_log.decision_summary,
                    "",
                    decision_log.rationale or "No rationale provided.",
                    "",
                    latest_review_note or "No latest review note recorded.",
                ]
            ),
        )

    def _decision_comment_summary(
        self,
        decision_comment: WorkspaceDecisionComment,
        *,
        decision_comments: list[WorkspaceDecisionComment] | None = None,
    ) -> dict[str, Any]:
        sibling_comments = list(decision_comments or [])
        reply_count = sum(
            1
            for item in sibling_comments
            if str(item.parent_comment_id or "") == decision_comment.decision_comment_id
        )
        return {
            **decision_comment.to_dict(),
            "reply_count": reply_count,
            "is_reply": bool(decision_comment.parent_comment_id),
        }

    def _audit_event_matches_study(self, event: AuditEvent, study_id: str) -> bool:
        if event.target_type == "study" and event.target_id == study_id:
            return True
        event_payload = dict(event.event_payload or {})
        return str(event_payload.get("study_id") or "").strip() == study_id

    def _study_activity_route(self, event: AuditEvent) -> dict[str, str | None]:
        event_payload = dict(event.event_payload or {})
        if event.target_type == "study":
            return {
                "route_kind": "study",
                "route_id": event.target_id,
                "route_path": f"/app/studies/{event.target_id}",
            }
        if event.target_type == "validation_job":
            return {
                "route_kind": "job",
                "route_id": event.target_id,
                "route_path": f"/app/jobs/{event.target_id}",
            }
        route_map = {
            "evidence_view": ("evidence_view", f"/app/evidence-views/{event.target_id}"),
            "decision_log": ("decision_log", f"/app/decision-logs/{event.target_id}"),
            "export_bundle": ("export_bundle", f"/app/export-bundles/{event.target_id}"),
            "share_bundle": ("share_bundle", f"/app/share-bundles/{event.target_id}"),
            "support_snapshot": ("support_snapshot", f"/app/support-snapshots/{event.target_id}"),
        }
        mapped = route_map.get(event.target_type)
        if mapped is not None:
            route_kind, route_path = mapped
            return {
                "route_kind": route_kind,
                "route_id": event.target_id,
                "route_path": route_path,
            }
        if str(event_payload.get("study_id") or "").strip():
            return {
                "route_kind": "study",
                "route_id": str(event_payload.get("study_id") or "").strip(),
                "route_path": f"/app/studies/{str(event_payload.get('study_id') or '').strip()}",
            }
        return {
            "route_kind": None,
            "route_id": None,
            "route_path": None,
        }

    def _study_activity_event_summary(self, event: AuditEvent) -> dict[str, Any]:
        payload = dict(event.event_payload or {})
        route = self._study_activity_route(event)
        family = "study"
        tone = "queued"
        headline = event.action.replace(".", " ")
        summary = "Study activity recorded."

        if event.action == "study.created":
            family = "study"
            tone = "completed"
            headline = "Study created"
            summary = f"{payload.get('study_title') or 'Study'} is ready for intake and run setup."
        elif event.action == "validation_job.submitted":
            family = "run"
            tone = "queued"
            headline = "Run queued"
            summary = (
                f"{payload.get('provider_name') or 'provider'} | "
                f"{payload.get('panel_type') or 'panel'} | "
                f"{payload.get('sample_size') or '?'} participants"
            )
        elif event.action == "validation_job.started":
            family = "run"
            tone = "running"
            headline = "Run started"
            summary = "Worker execution started for the selected study run."
        elif event.action == "validation_job.completed":
            family = "run"
            tone = "completed"
            headline = "Run completed"
            summary = f"Completed run {payload.get('run_id') or event.target_id} is ready for evidence review."
        elif event.action == "validation_job.failed":
            family = "run"
            tone = "failed"
            headline = "Run failed"
            summary = str(payload.get("last_error") or "The study run failed before evidence review.")
        elif event.action == "validation_job.canceled":
            family = "run"
            tone = "queued"
            headline = "Queued run canceled"
            summary = str(payload.get("cancel_reason") or "Canceled from the product surface.")
        elif event.action == "validation_job.retried":
            family = "run"
            tone = "queued"
            headline = "Retry queued"
            summary = f"Retry queued from {payload.get('source_job_id') or 'the selected failed run'}."
        elif event.action == "evidence_view.saved":
            family = "evidence"
            tone = "completed"
            headline = "Evidence view saved"
            summary = "One evidence slice was preserved for later study review."
        elif event.action == "decision_log.created":
            family = "decision"
            tone = "completed"
            headline = "Decision recorded"
            summary = "A study decision was attached to evidence and run lineage."
        elif event.action == "decision_log.commented":
            family = "decision"
            tone = "running"
            headline = "Decision comment added"
            summary = f"{payload.get('comment_count') or 0} comment(s) now attached to the review thread."
        elif event.action == "decision_log.review_status_updated":
            family = "decision"
            tone = "completed" if str(payload.get("review_status") or "") == "approved" else "running"
            headline = "Decision review updated"
            summary = f"Review status changed to {payload.get('review_status') or 'draft'}."
        elif event.action == "export_bundle.created":
            family = "export"
            tone = "completed"
            headline = "Export created"
            summary = f"{payload.get('export_format') or 'bundle'} export is ready for delivery."
        elif event.action == "share_bundle.created":
            family = "share"
            tone = "completed"
            headline = "Share published"
            summary = "A viewer-safe share bundle is available from this study."
        elif event.action == "share_bundle.revoked":
            family = "share"
            tone = "queued"
            headline = "Share revoked"
            summary = "The public share path was revoked from the study surface."
        elif event.action == "support_snapshot.created":
            family = "support"
            tone = "completed"
            headline = "Support snapshot created"
            summary = str(payload.get("summary") or "A support handoff bundle was generated for this study.")

        return {
            "activity_id": event.audit_event_id,
            "action": event.action,
            "event_family": family,
            "tone": tone,
            "headline": headline,
            "summary": summary,
            "actor_user_id": event.actor_user_id,
            "actor_role": event.actor_role,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "created_at": event.created_at,
            "project_id": str(payload.get("project_id") or "").strip() or None,
            "study_id": str(payload.get("study_id") or "").strip() or None,
            "job_id": str(payload.get("job_id") or "").strip() or (event.target_id if event.target_type == "validation_job" else None),
            "route_kind": route["route_kind"],
            "route_id": route["route_id"],
            "route_path": route["route_path"],
        }

    def _project_summary(self, project: WorkspaceProject) -> dict[str, Any]:
        studies = job_store.list_workspace_studies(self.runtime_root, project.workspace_id, project_id=project.project_id)
        export_bundles = [
            bundle
            for bundle in job_store.list_workspace_export_bundles(self.runtime_root, project.workspace_id)
            if bundle.project_id == project.project_id
        ]
        share_bundles = [
            bundle
            for bundle in job_store.list_workspace_share_bundles(self.runtime_root, project.workspace_id)
            if bundle.project_id == project.project_id
        ]
        support_snapshots = [
            snapshot
            for snapshot in job_store.list_workspace_support_snapshots(self.runtime_root, project.workspace_id)
            if snapshot.project_id == project.project_id
        ]
        evidence_views = [
            view
            for view in job_store.list_workspace_evidence_views(self.runtime_root, project.workspace_id)
            if view.project_id == project.project_id
        ]
        decision_logs = [
            log
            for log in job_store.list_workspace_decision_logs(self.runtime_root, project.workspace_id)
            if log.project_id == project.project_id
        ]
        decision_comments = [
            comment
            for comment in job_store.list_workspace_decision_comments(self.runtime_root, project.workspace_id)
            if comment.project_id == project.project_id
        ]
        return {
            **project.to_dict(),
            "study_count": len(studies),
            "latest_study_id": studies[0].study_id if studies else None,
            "evidence_view_count": len(evidence_views),
            "decision_log_count": len(decision_logs),
            "decision_comment_count": len(decision_comments),
            "approved_decision_count": sum(
                1 for log in decision_logs if self._decision_review_status(log) == "approved"
            ),
            "export_bundle_count": len(export_bundles),
            "share_bundle_count": len(share_bundles),
            "support_snapshot_count": len(support_snapshots),
        }

    def _study_summary(self, study: WorkspaceStudy) -> dict[str, Any]:
        jobs = [
            job
            for job in job_store.list_workspace_jobs(self.runtime_root, study.workspace_id)
            if str(dict(job.get("metadata", {})).get("study_id") or "") == study.study_id
        ]
        latest_job = None
        if study.latest_job_id:
            latest_job = next((job for job in jobs if str(job.get("job_id")) == study.latest_job_id), None)
        elif jobs:
            latest_job = jobs[0]
        export_bundles = job_store.list_workspace_export_bundles(
            self.runtime_root,
            study.workspace_id,
            study_id=study.study_id,
        )
        share_bundles = job_store.list_workspace_share_bundles(
            self.runtime_root,
            study.workspace_id,
            study_id=study.study_id,
        )
        support_snapshots = job_store.list_workspace_support_snapshots(
            self.runtime_root,
            study.workspace_id,
            study_id=study.study_id,
        )
        evidence_views = job_store.list_workspace_evidence_views(
            self.runtime_root,
            study.workspace_id,
            study_id=study.study_id,
        )
        decision_logs = job_store.list_workspace_decision_logs(
            self.runtime_root,
            study.workspace_id,
            study_id=study.study_id,
        )
        decision_comments = job_store.list_workspace_decision_comments(
            self.runtime_root,
            study.workspace_id,
            study_id=study.study_id,
        )
        return {
            **study.to_dict(),
            "run_count": len(jobs),
            "latest_job_status": str(latest_job.get("status") or "") if latest_job else None,
            "evidence_view_count": len(evidence_views),
            "decision_log_count": len(decision_logs),
            "decision_comment_count": len(decision_comments),
            "approved_decision_count": sum(
                1 for log in decision_logs if self._decision_review_status(log) == "approved"
            ),
            "export_bundle_count": len(export_bundles),
            "share_bundle_count": len(share_bundles),
            "support_snapshot_count": len(support_snapshots),
        }

    def _evidence_view_summary(self, evidence_view: WorkspaceEvidenceView) -> dict[str, Any]:
        return {
            **evidence_view.to_dict(),
            "has_replay_focus": bool(evidence_view.selected_replay_step_id),
            "has_comparison_focus": bool(evidence_view.selected_comparison_run_id),
        }

    def _decision_log_summary(self, decision_log: WorkspaceDecisionLog) -> dict[str, Any]:
        decision_comments = job_store.list_workspace_decision_comments(
            self.runtime_root,
            decision_log.workspace_id,
            decision_log_id=decision_log.decision_log_id,
        )
        comment_summaries = [
            self._decision_comment_summary(comment, decision_comments=decision_comments)
            for comment in decision_comments
        ]
        metadata = dict(decision_log.metadata or {})
        return {
            **decision_log.to_dict(),
            "has_linked_evidence_view": bool(decision_log.evidence_view_id),
            "has_comparison_focus": bool(decision_log.selected_comparison_run_id),
            "review_status": self._decision_review_status(decision_log),
            "review_status_history": self._decision_review_history(decision_log),
            "review_status_updated_at": metadata.get("review_status_updated_at") or None,
            "review_status_updated_by_user_id": metadata.get("review_status_updated_by_user_id") or None,
            "latest_review_note": metadata.get("latest_review_note") or "",
            "comment_count": len(decision_comments),
            "review_thread_count": sum(1 for comment in decision_comments if not comment.parent_comment_id),
            "latest_comment_preview": comment_summaries[-1]["body"] if comment_summaries else "",
        }

    def _export_bundle_summary(self, export_bundle: WorkspaceExportBundle) -> dict[str, Any]:
        share_bundles = job_store.list_workspace_share_bundles(
            self.runtime_root,
            export_bundle.workspace_id,
            export_bundle_id=export_bundle.export_bundle_id,
        )
        return {
            **export_bundle.to_dict(),
            "exported_file_count": len(export_bundle.exported_files),
            "share_bundle_count": len(share_bundles),
        }

    def _share_bundle_summary(self, share_bundle: WorkspaceShareBundle) -> dict[str, Any]:
        return {
            **share_bundle.to_dict(),
            "share_file_count": len(self._share_payload_files(share_bundle)),
        }

    def _support_snapshot_summary(self, snapshot: WorkspaceSupportSnapshot) -> dict[str, Any]:
        return snapshot.to_dict()

    def _support_submission_gate(
        self,
        auth: AuthContext,
        workspace: TenantWorkspace,
        billing: BillingAccount,
        limits: dict[str, int],
        jobs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        blocked_reasons: list[dict[str, Any]] = []
        if auth.role not in SUBMITTER_ROLES:
            blocked_reasons.append(
                {
                    "code": "role_forbidden",
                    "message": f"Role '{auth.role}' cannot submit validation jobs.",
                    "next_action": "Use an owner, admin, or editor seat to submit or rerun the study.",
                }
            )
        if billing.status not in ACTIVE_BILLING_STATUSES:
            blocked_reasons.append(
                {
                    "code": "billing_inactive",
                    "message": f"Billing status '{billing.status}' does not allow new validation jobs.",
                    "next_action": "Restore an active billing state before retrying submission.",
                }
            )
        active_jobs = sum(1 for job in jobs if str(job.get("status") or "") in {"queued", "running"})
        if active_jobs >= limits["max_concurrent_jobs"]:
            blocked_reasons.append(
                {
                    "code": "concurrency_limit_reached",
                    "message": (
                        f"Workspace '{workspace.workspace_id}' reached the max concurrent job limit "
                        f"({limits['max_concurrent_jobs']})."
                    ),
                    "next_action": "Wait for an in-flight run to finish or move to a higher plan limit.",
                }
            )
        today_floor = _now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        daily_jobs = job_store.count_workspace_jobs_created_since(self.runtime_root, workspace.workspace_id, today_floor)
        if daily_jobs >= limits["daily_runs"]:
            blocked_reasons.append(
                {
                    "code": "daily_limit_reached",
                    "message": (
                        f"Workspace '{workspace.workspace_id}' reached the daily run limit "
                        f"({limits['daily_runs']})."
                    ),
                    "next_action": "Retry after the daily limit window resets or move to a higher plan limit.",
                }
            )
        return {
            "status": "blocked" if blocked_reasons else "allowed",
            "blocked_reason_count": len(blocked_reasons),
            "blocked_reasons": blocked_reasons,
            "limits": {
                "daily_runs": limits["daily_runs"],
                "max_concurrent_jobs": limits["max_concurrent_jobs"],
                "artifact_retention_days": limits["artifact_retention_days"],
                "active_jobs": active_jobs,
                "daily_jobs_created": daily_jobs,
            },
        }

    def _support_summary_for_job(self, job: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(job.get("metadata", {}))
        status = str(job.get("status") or "")
        artifact_deleted_at = str(metadata.get("artifact_deleted_at") or "").strip()
        last_error = str(job.get("last_error") or "").strip()
        failure_category = self._support_failure_category(status=status, last_error=last_error, artifact_deleted_at=artifact_deleted_at)
        summary = self._support_summary_text(status=status, last_error=last_error, artifact_deleted_at=artifact_deleted_at)
        return {
            "job_id": str(job.get("job_id") or ""),
            "status": status,
            "provider_name": str(job.get("provider_name") or ""),
            "project_id": str(metadata.get("project_id") or "") or None,
            "study_id": str(metadata.get("study_id") or "") or None,
            "run_id": str(metadata.get("run_id") or "") or None,
            "output_run_path": str(job.get("output_run_path") or "") or None,
            "requested_by_user_id": str(job.get("requested_by_user_id") or "") or None,
            "retry_count": int(job.get("retry_count") or 0),
            "created_at": str(job.get("created_at") or "") or None,
            "started_at": str(job.get("started_at") or "") or None,
            "finished_at": str(job.get("finished_at") or "") or None,
            "last_error": last_error or None,
            "failure_category": failure_category,
            "summary": summary,
            "artifact_deleted_at": artifact_deleted_at or None,
            "can_retry": status in {"failed", "canceled"},
            "can_cancel": status == "queued",
            "next_actions": self._support_next_actions(status=status, last_error=last_error, artifact_deleted_at=artifact_deleted_at),
        }

    def _support_failure_category(self, *, status: str, last_error: str, artifact_deleted_at: str) -> str:
        if artifact_deleted_at:
            return "artifact_retention_expired"
        lowered = last_error.lower()
        if status == "canceled":
            return "job_canceled"
        if status == "failed":
            if "unknown provider" in lowered or "provider" in lowered and "unknown" in lowered:
                return "provider_configuration"
            if "not found" in lowered or "missing" in lowered:
                return "missing_input_artifact"
            if "path" in lowered and "workspace boundary" in lowered:
                return "workspace_boundary_violation"
            return "runtime_failure"
        if status == "queued":
            return "awaiting_worker"
        if status == "running":
            return "in_progress"
        return "no_failure"

    def _support_summary_text(self, *, status: str, last_error: str, artifact_deleted_at: str) -> str:
        if artifact_deleted_at:
            return "Run artifacts were purged by retention policy. The study can still be rerun, but the prior artifact set is no longer present."
        if status == "failed":
            return last_error or "The run failed before a completed evidence set was produced."
        if status == "canceled":
            return "The run was canceled before completion."
        if status == "running":
            return "The run is still executing. Wait for the worker to finish before exporting, sharing, or generating a support handoff."
        if status == "queued":
            return "The run is still queued. Wait for a worker lease before diagnosing runtime output."
        return "The selected run completed. Support can still capture the current diagnostic state for audit or handoff."

    def _support_next_actions(self, *, status: str, last_error: str, artifact_deleted_at: str) -> list[str]:
        if artifact_deleted_at:
            return [
                "Rerun the study if you need a fresh evidence set.",
                "Export or share from a newer completed run instead of the purged artifact set.",
            ]
        if status == "failed":
            actions = ["Inspect the failed run inputs and retry from the study surface."]
            lowered = last_error.lower()
            if "provider" in lowered:
                actions.append("Check provider_name or backend configuration before retrying.")
            if "not found" in lowered or "missing" in lowered:
                actions.append("Verify that the referenced brief or persona directory still exists inside the workspace.")
            return actions
        if status == "canceled":
            return ["Resubmit the study when you are ready to continue."]
        if status == "running":
            return ["Wait for worker completion and refresh the study shell.", "Generate a snapshot only if you need operator handoff while the run is still in progress."]
        if status == "queued":
            return ["Wait for an available worker lease.", "If the queue remains blocked, inspect billing and concurrent run limits."]
        return ["Review evidence, export or share if needed, and generate a support snapshot only for operator handoff or audit."]

    def _support_job_digest(self, job: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(job.get("metadata", {}))
        return {
            "job_id": str(job.get("job_id") or ""),
            "status": str(job.get("status") or ""),
            "provider_name": str(job.get("provider_name") or "") or None,
            "retry_count": int(job.get("retry_count") or 0),
            "study_id": str(metadata.get("study_id") or "") or None,
            "project_id": str(metadata.get("project_id") or "") or None,
            "run_id": str(metadata.get("run_id") or "") or None,
            "created_at": str(job.get("created_at") or "") or None,
            "started_at": str(job.get("started_at") or "") or None,
            "finished_at": str(job.get("finished_at") or "") or None,
            "last_error": str(job.get("last_error") or "") or None,
        }

    def _share_payload_files(self, share_bundle: WorkspaceShareBundle) -> list[dict[str, Any]]:
        payload_path = Path(share_bundle.share_payload_path)
        if not payload_path.exists():
            return []
        payload = read_json(payload_path)
        if not isinstance(payload, dict):
            return []
        files = payload.get("files")
        return list(files) if isinstance(files, list) else []

    def _refresh_share_bundle_status(self, share_bundle: WorkspaceShareBundle) -> WorkspaceShareBundle:
        if share_bundle.status in {"revoked", "expired"}:
            return share_bundle
        if share_bundle.expires_at:
            try:
                expires_at = datetime.fromisoformat(share_bundle.expires_at)
            except ValueError:
                return share_bundle
            if expires_at <= _now():
                return job_store.update_workspace_share_bundle(
                    self.runtime_root,
                    share_bundle_id=share_bundle.share_bundle_id,
                    status="expired",
                )
        return share_bundle

    def _materialize_export_bundle_files(
        self,
        *,
        bundle_root: Path,
        run_dir: Path,
        export_format: str,
        artifact_ids: list[str],
        study: WorkspaceStudy,
        job: dict[str, Any],
        synthetic_boundary: str,
    ) -> list[dict[str, Any]]:
        if export_format == "report_markdown":
            source = run_dir / "report.md"
            if not source.exists():
                raise FileNotFoundError(f"Run artifact not found: {source}")
            destination = bundle_root / "report.md"
            export_file(source, destination)
            return [self._exported_file_entry(source, destination, "report_markdown")]

        if export_format == "report_json":
            source = run_dir / "report.json"
            if not source.exists():
                raise FileNotFoundError(f"Run artifact not found: {source}")
            destination = bundle_root / "report.json"
            export_file(source, destination)
            return [self._exported_file_entry(source, destination, "report_json")]

        if export_format == "report_csv":
            source = run_dir / "report.json"
            if not source.exists():
                raise FileNotFoundError(f"Run artifact not found: {source}")
            destination = bundle_root / "report.csv"
            report_payload = read_json(source)
            if not isinstance(report_payload, dict):
                raise ValueError("report.json must contain an object payload.")
            destination.write_text(render_report_csv(report_payload), encoding="utf-8")
            return [self._exported_file_entry(source, destination, "report_csv")]

        selected_artifact_ids = [str(item).strip() for item in artifact_ids if str(item).strip()]
        if not selected_artifact_ids:
            selected_artifact_ids = [artifact_id for artifact_id in DEFAULT_EXPORT_ARTIFACT_IDS if (run_dir / artifact_id).exists()]
        if not selected_artifact_ids:
            raise ValueError("No exportable run artifacts were found for the selected validation job.")

        exported_files: list[dict[str, Any]] = []
        artifact_root = bundle_root / "artifacts"
        artifact_root.mkdir(parents=True, exist_ok=True)
        for artifact_id in selected_artifact_ids:
            source = (run_dir / artifact_id).resolve()
            if run_dir.resolve() not in source.parents or not source.exists() or not source.is_file():
                raise FileNotFoundError(f"Run artifact not found: {artifact_id}")
            relative_name = Path(artifact_id).name
            destination = artifact_root / relative_name
            export_file(source, destination)
            exported_files.append(self._exported_file_entry(source, destination, "bundle_artifact"))

        notes_payload = {
            "synthetic_boundary": synthetic_boundary,
            "study_title": study.title,
            "job_id": str(job.get("job_id") or ""),
            "exported_file_count": len(exported_files),
        }
        notes_path = bundle_root / "bundle_notes.json"
        write_json(notes_path, notes_payload)
        exported_files.append(self._exported_file_entry(notes_path, notes_path, "bundle_notes"))
        return exported_files

    def _exported_file_entry(self, source: Path, destination: Path, export_kind: str) -> dict[str, Any]:
        mime_type = mimetypes.guess_type(destination.name)[0] or "application/octet-stream"
        return {
            "artifact_id": source.name,
            "export_kind": export_kind,
            "mime_type": mime_type,
            "source_path": str(source),
            "bundle_path": str(destination),
        }
