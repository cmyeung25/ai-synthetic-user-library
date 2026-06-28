from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import utc_now_iso
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


RUNTIME_DB_FILENAME = "saas_runtime.sqlite3"
RUNTIME_SCHEMA_VERSION = "saas-runtime/v1"


def runtime_db_path(runtime_root: Path) -> Path:
    return runtime_root / RUNTIME_DB_FILENAME


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _json_loads(payload: str) -> Any:
    return json.loads(payload) if payload else {}


def _connect(db_path: Path) -> sqlite3.Connection:
    _ensure_parent(db_path)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    _ensure_schema(connection)
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS runtime_store_info (
            info_key TEXT PRIMARY KEY,
            info_value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS workspaces (
            workspace_id TEXT PRIMARY KEY,
            slug TEXT NOT NULL,
            display_name TEXT NOT NULL,
            region_code TEXT NOT NULL,
            data_residency_region TEXT NOT NULL,
            plan_tier TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            settings_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS workspace_members (
            workspace_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            joined_at TEXT NOT NULL,
            PRIMARY KEY (workspace_id, user_id),
            FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS billing_accounts (
            workspace_id TEXT PRIMARY KEY,
            provider_name TEXT NOT NULL,
            provider_customer_ref TEXT NOT NULL,
            provider_subscription_ref TEXT NOT NULL,
            price_book_id TEXT NOT NULL,
            status TEXT NOT NULL,
            seat_count INTEGER NOT NULL,
            renewal_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS api_tokens (
            token TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            issued_at TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (workspace_id, user_id) REFERENCES workspace_members(workspace_id, user_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS workspace_browser_sessions (
            session_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            source_token TEXT,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (workspace_id, user_id) REFERENCES workspace_members(workspace_id, user_id) ON DELETE CASCADE,
            FOREIGN KEY (source_token) REFERENCES api_tokens(token) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_workspace_browser_sessions_workspace_last_seen
            ON workspace_browser_sessions(workspace_id, last_seen_at DESC, session_id DESC);

        CREATE INDEX IF NOT EXISTS idx_workspace_browser_sessions_source_token
            ON workspace_browser_sessions(source_token, session_id);

        CREATE TABLE IF NOT EXISTS workspace_projects (
            project_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            slug TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            created_by_user_id TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_projects_workspace_slug
            ON workspace_projects(workspace_id, slug);

        CREATE INDEX IF NOT EXISTS idx_workspace_projects_workspace_updated
            ON workspace_projects(workspace_id, updated_at DESC, project_id DESC);

        CREATE TABLE IF NOT EXISTS workspace_studies (
            study_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_by_user_id TEXT NOT NULL,
            status TEXT NOT NULL,
            research_intent TEXT NOT NULL DEFAULT '',
            desired_output TEXT NOT NULL DEFAULT '',
            first_task TEXT NOT NULL DEFAULT '',
            artifact_refs_json TEXT NOT NULL DEFAULT '[]',
            draft_plan_json TEXT NOT NULL DEFAULT '{}',
            latest_job_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES workspace_projects(project_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_workspace_studies_workspace_project_updated
            ON workspace_studies(workspace_id, project_id, updated_at DESC, study_id DESC);

        CREATE TABLE IF NOT EXISTS workspace_export_bundles (
            export_bundle_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            study_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            export_format TEXT NOT NULL,
            created_by_user_id TEXT NOT NULL,
            bundle_root TEXT NOT NULL,
            manifest_path TEXT NOT NULL,
            exported_files_json TEXT NOT NULL DEFAULT '[]',
            synthetic_boundary TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES workspace_projects(project_id) ON DELETE CASCADE,
            FOREIGN KEY (study_id) REFERENCES workspace_studies(study_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_workspace_export_bundles_workspace_study_updated
            ON workspace_export_bundles(workspace_id, study_id, updated_at DESC, export_bundle_id DESC);

        CREATE INDEX IF NOT EXISTS idx_workspace_export_bundles_workspace_job_updated
            ON workspace_export_bundles(workspace_id, job_id, updated_at DESC, export_bundle_id DESC);

        CREATE TABLE IF NOT EXISTS workspace_share_bundles (
            share_bundle_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            export_bundle_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            study_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            share_key TEXT NOT NULL,
            public_path TEXT NOT NULL,
            share_root TEXT NOT NULL,
            share_payload_path TEXT NOT NULL,
            created_by_user_id TEXT NOT NULL,
            synthetic_boundary TEXT NOT NULL DEFAULT '',
            published_at TEXT NOT NULL,
            expires_at TEXT,
            revoked_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE,
            FOREIGN KEY (export_bundle_id) REFERENCES workspace_export_bundles(export_bundle_id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES workspace_projects(project_id) ON DELETE CASCADE,
            FOREIGN KEY (study_id) REFERENCES workspace_studies(study_id) ON DELETE CASCADE
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_share_bundles_share_key
            ON workspace_share_bundles(share_key);

        CREATE INDEX IF NOT EXISTS idx_workspace_share_bundles_workspace_study_updated
            ON workspace_share_bundles(workspace_id, study_id, updated_at DESC, share_bundle_id DESC);

        CREATE INDEX IF NOT EXISTS idx_workspace_share_bundles_workspace_export_updated
            ON workspace_share_bundles(workspace_id, export_bundle_id, updated_at DESC, share_bundle_id DESC);

        CREATE TABLE IF NOT EXISTS workspace_support_snapshots (
            support_snapshot_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            project_id TEXT,
            study_id TEXT,
            job_id TEXT,
            run_id TEXT,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            support_root TEXT NOT NULL,
            snapshot_path TEXT NOT NULL,
            created_by_user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES workspace_projects(project_id) ON DELETE SET NULL,
            FOREIGN KEY (study_id) REFERENCES workspace_studies(study_id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_workspace_support_snapshots_workspace_study_updated
            ON workspace_support_snapshots(workspace_id, study_id, updated_at DESC, support_snapshot_id DESC);

        CREATE INDEX IF NOT EXISTS idx_workspace_support_snapshots_workspace_job_updated
            ON workspace_support_snapshots(workspace_id, job_id, updated_at DESC, support_snapshot_id DESC);

        CREATE TABLE IF NOT EXISTS workspace_evidence_views (
            evidence_view_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            study_id TEXT NOT NULL,
            job_id TEXT,
            run_id TEXT,
            title TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            query_text TEXT NOT NULL DEFAULT '',
            active_family TEXT NOT NULL DEFAULT 'all',
            sort_by TEXT NOT NULL DEFAULT 'relevance',
            selected_result_id TEXT,
            selected_replay_step_id TEXT,
            selected_comparison_run_id TEXT,
            payload_path TEXT NOT NULL,
            created_by_user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES workspace_projects(project_id) ON DELETE CASCADE,
            FOREIGN KEY (study_id) REFERENCES workspace_studies(study_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_workspace_evidence_views_workspace_study_updated
            ON workspace_evidence_views(workspace_id, study_id, updated_at DESC, evidence_view_id DESC);

        CREATE INDEX IF NOT EXISTS idx_workspace_evidence_views_workspace_job_updated
            ON workspace_evidence_views(workspace_id, job_id, updated_at DESC, evidence_view_id DESC);

        CREATE TABLE IF NOT EXISTS workspace_decision_logs (
            decision_log_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            study_id TEXT NOT NULL,
            job_id TEXT,
            run_id TEXT,
            evidence_view_id TEXT,
            title TEXT NOT NULL,
            decision_summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            selected_result_id TEXT,
            selected_comparison_run_id TEXT,
            payload_path TEXT NOT NULL,
            created_by_user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES workspace_projects(project_id) ON DELETE CASCADE,
            FOREIGN KEY (study_id) REFERENCES workspace_studies(study_id) ON DELETE CASCADE,
            FOREIGN KEY (evidence_view_id) REFERENCES workspace_evidence_views(evidence_view_id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_workspace_decision_logs_workspace_study_updated
            ON workspace_decision_logs(workspace_id, study_id, updated_at DESC, decision_log_id DESC);

        CREATE INDEX IF NOT EXISTS idx_workspace_decision_logs_workspace_job_updated
            ON workspace_decision_logs(workspace_id, job_id, updated_at DESC, decision_log_id DESC);

        CREATE TABLE IF NOT EXISTS workspace_decision_comments (
            decision_comment_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            study_id TEXT NOT NULL,
            decision_log_id TEXT NOT NULL,
            parent_comment_id TEXT,
            anchor_kind TEXT NOT NULL DEFAULT 'general',
            body TEXT NOT NULL,
            created_by_user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES workspace_projects(project_id) ON DELETE CASCADE,
            FOREIGN KEY (study_id) REFERENCES workspace_studies(study_id) ON DELETE CASCADE,
            FOREIGN KEY (decision_log_id) REFERENCES workspace_decision_logs(decision_log_id) ON DELETE CASCADE,
            FOREIGN KEY (parent_comment_id) REFERENCES workspace_decision_comments(decision_comment_id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_workspace_decision_comments_workspace_decision_created
            ON workspace_decision_comments(workspace_id, decision_log_id, created_at, decision_comment_id);

        CREATE INDEX IF NOT EXISTS idx_workspace_decision_comments_workspace_study_created
            ON workspace_decision_comments(workspace_id, study_id, created_at, decision_comment_id);

        CREATE TABLE IF NOT EXISTS validation_jobs (
            job_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            brief_id TEXT NOT NULL,
            requested_by_user_id TEXT NOT NULL,
            panel_spec_json TEXT NOT NULL,
            provider_name TEXT NOT NULL,
            status TEXT NOT NULL,
            priority TEXT NOT NULL,
            input_artifact_path TEXT NOT NULL,
            persona_dir_path TEXT NOT NULL,
            output_run_path TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            idempotency_key TEXT NOT NULL DEFAULT '',
            last_error TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_validation_jobs_workspace_idempotency
            ON validation_jobs(workspace_id, idempotency_key)
            WHERE idempotency_key <> '';

        CREATE INDEX IF NOT EXISTS idx_validation_jobs_workspace_status_created
            ON validation_jobs(workspace_id, status, created_at);

        CREATE TABLE IF NOT EXISTS audit_events (
            audit_event_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            actor_user_id TEXT NOT NULL,
            actor_role TEXT NOT NULL,
            action TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            event_payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_audit_events_workspace_created
            ON audit_events(workspace_id, created_at DESC, audit_event_id DESC);
        """
    )
    connection.execute(
        """
        INSERT INTO runtime_store_info(info_key, info_value)
        VALUES('schema_version', ?)
        ON CONFLICT(info_key) DO UPDATE SET info_value=excluded.info_value
        """,
        (RUNTIME_SCHEMA_VERSION,),
    )
    connection.commit()


def _workspace_from_row(connection: sqlite3.Connection, row: sqlite3.Row | None) -> TenantWorkspace | None:
    if row is None:
        return None
    members = [
        WorkspaceMember(
            user_id=str(member_row["user_id"]),
            role=str(member_row["role"]),
            joined_at=str(member_row["joined_at"]),
        )
        for member_row in connection.execute(
            """
            SELECT user_id, role, joined_at
            FROM workspace_members
            WHERE workspace_id = ?
            ORDER BY joined_at, user_id
            """,
            (str(row["workspace_id"]),),
        ).fetchall()
    ]
    return TenantWorkspace(
        workspace_id=str(row["workspace_id"]),
        slug=str(row["slug"]),
        display_name=str(row["display_name"]),
        region_code=str(row["region_code"]),
        data_residency_region=str(row["data_residency_region"]),
        plan_tier=str(row["plan_tier"]),
        status=str(row["status"]),
        created_at=str(row["created_at"]),
        settings=dict(_json_loads(str(row["settings_json"]))) if str(row["settings_json"]) else {},
        members=members,
    )


def _billing_from_row(row: sqlite3.Row | None) -> BillingAccount | None:
    if row is None:
        return None
    return BillingAccount(
        workspace_id=str(row["workspace_id"]),
        provider_name=str(row["provider_name"]),
        provider_customer_ref=str(row["provider_customer_ref"]),
        provider_subscription_ref=str(row["provider_subscription_ref"]),
        price_book_id=str(row["price_book_id"]),
        status=str(row["status"]),
        seat_count=int(row["seat_count"]),
        renewal_at=str(row["renewal_at"]) if row["renewal_at"] is not None else None,
        metadata=dict(_json_loads(str(row["metadata_json"]))) if str(row["metadata_json"]) else {},
    )


def _browser_session_from_row(row: sqlite3.Row | None) -> WorkspaceBrowserSession | None:
    if row is None:
        return None
    return WorkspaceBrowserSession(
        session_id=str(row["session_id"]),
        workspace_id=str(row["workspace_id"]),
        user_id=str(row["user_id"]),
        role=str(row["role"]),
        source_token=str(row["source_token"]) if row["source_token"] is not None else None,
        created_at=str(row["created_at"]),
        last_seen_at=str(row["last_seen_at"]),
        expires_at=str(row["expires_at"]),
        revoked_at=str(row["revoked_at"]) if row["revoked_at"] is not None else None,
        metadata=dict(_json_loads(str(row["metadata_json"]))) if str(row["metadata_json"]) else {},
    )


def _project_from_row(row: sqlite3.Row | None) -> WorkspaceProject | None:
    if row is None:
        return None
    return WorkspaceProject(
        project_id=str(row["project_id"]),
        workspace_id=str(row["workspace_id"]),
        slug=str(row["slug"]),
        name=str(row["name"]),
        description=str(row["description"]),
        created_by_user_id=str(row["created_by_user_id"]),
        status=str(row["status"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        metadata=dict(_json_loads(str(row["metadata_json"]))) if str(row["metadata_json"]) else {},
    )


def _study_from_row(row: sqlite3.Row | None) -> WorkspaceStudy | None:
    if row is None:
        return None
    return WorkspaceStudy(
        study_id=str(row["study_id"]),
        workspace_id=str(row["workspace_id"]),
        project_id=str(row["project_id"]),
        title=str(row["title"]),
        created_by_user_id=str(row["created_by_user_id"]),
        status=str(row["status"]),
        research_intent=str(row["research_intent"]),
        desired_output=str(row["desired_output"]),
        first_task=str(row["first_task"]),
        artifact_refs=list(_json_loads(str(row["artifact_refs_json"]))) if str(row["artifact_refs_json"]) else [],
        draft_plan=dict(_json_loads(str(row["draft_plan_json"]))) if str(row["draft_plan_json"]) else {},
        latest_job_id=str(row["latest_job_id"]) if row["latest_job_id"] is not None else None,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        metadata=dict(_json_loads(str(row["metadata_json"]))) if str(row["metadata_json"]) else {},
    )


def _export_bundle_from_row(row: sqlite3.Row | None) -> WorkspaceExportBundle | None:
    if row is None:
        return None
    return WorkspaceExportBundle(
        export_bundle_id=str(row["export_bundle_id"]),
        workspace_id=str(row["workspace_id"]),
        project_id=str(row["project_id"]),
        study_id=str(row["study_id"]),
        job_id=str(row["job_id"]),
        run_id=str(row["run_id"]),
        title=str(row["title"]),
        status=str(row["status"]),
        export_format=str(row["export_format"]),
        created_by_user_id=str(row["created_by_user_id"]),
        bundle_root=str(row["bundle_root"]),
        manifest_path=str(row["manifest_path"]),
        exported_files=list(_json_loads(str(row["exported_files_json"]))) if str(row["exported_files_json"]) else [],
        synthetic_boundary=str(row["synthetic_boundary"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        metadata=dict(_json_loads(str(row["metadata_json"]))) if str(row["metadata_json"]) else {},
    )


def _share_bundle_from_row(row: sqlite3.Row | None) -> WorkspaceShareBundle | None:
    if row is None:
        return None
    return WorkspaceShareBundle(
        share_bundle_id=str(row["share_bundle_id"]),
        workspace_id=str(row["workspace_id"]),
        export_bundle_id=str(row["export_bundle_id"]),
        project_id=str(row["project_id"]),
        study_id=str(row["study_id"]),
        job_id=str(row["job_id"]),
        run_id=str(row["run_id"]),
        title=str(row["title"]),
        status=str(row["status"]),
        share_key=str(row["share_key"]),
        public_path=str(row["public_path"]),
        share_root=str(row["share_root"]),
        share_payload_path=str(row["share_payload_path"]),
        created_by_user_id=str(row["created_by_user_id"]),
        synthetic_boundary=str(row["synthetic_boundary"]),
        published_at=str(row["published_at"]),
        expires_at=str(row["expires_at"]) if row["expires_at"] is not None else None,
        revoked_at=str(row["revoked_at"]) if row["revoked_at"] is not None else None,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        metadata=dict(_json_loads(str(row["metadata_json"]))) if str(row["metadata_json"]) else {},
    )


def _support_snapshot_from_row(row: sqlite3.Row | None) -> WorkspaceSupportSnapshot | None:
    if row is None:
        return None
    return WorkspaceSupportSnapshot(
        support_snapshot_id=str(row["support_snapshot_id"]),
        workspace_id=str(row["workspace_id"]),
        project_id=str(row["project_id"]) if row["project_id"] is not None else None,
        study_id=str(row["study_id"]) if row["study_id"] is not None else None,
        job_id=str(row["job_id"]) if row["job_id"] is not None else None,
        run_id=str(row["run_id"]) if row["run_id"] is not None else None,
        title=str(row["title"]),
        status=str(row["status"]),
        summary=str(row["summary"]),
        support_root=str(row["support_root"]),
        snapshot_path=str(row["snapshot_path"]),
        created_by_user_id=str(row["created_by_user_id"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        metadata=dict(_json_loads(str(row["metadata_json"]))) if str(row["metadata_json"]) else {},
    )


def _audit_event_from_row(row: sqlite3.Row | None) -> AuditEvent | None:
    if row is None:
        return None
    return AuditEvent(
        audit_event_id=str(row["audit_event_id"]),
        workspace_id=str(row["workspace_id"]),
        actor_user_id=str(row["actor_user_id"]),
        actor_role=str(row["actor_role"]),
        action=str(row["action"]),
        target_type=str(row["target_type"]),
        target_id=str(row["target_id"]),
        event_payload=dict(_json_loads(str(row["event_payload_json"]))) if str(row["event_payload_json"]) else {},
        created_at=str(row["created_at"]),
    )


def _evidence_view_from_row(row: sqlite3.Row | None) -> WorkspaceEvidenceView | None:
    if row is None:
        return None
    return WorkspaceEvidenceView(
        evidence_view_id=str(row["evidence_view_id"]),
        workspace_id=str(row["workspace_id"]),
        project_id=str(row["project_id"]),
        study_id=str(row["study_id"]),
        job_id=str(row["job_id"]) if row["job_id"] is not None else None,
        run_id=str(row["run_id"]) if row["run_id"] is not None else None,
        title=str(row["title"]),
        note=str(row["note"]),
        query_text=str(row["query_text"]),
        active_family=str(row["active_family"]),
        sort_by=str(row["sort_by"]),
        selected_result_id=str(row["selected_result_id"]) if row["selected_result_id"] is not None else None,
        selected_replay_step_id=(
            str(row["selected_replay_step_id"]) if row["selected_replay_step_id"] is not None else None
        ),
        selected_comparison_run_id=(
            str(row["selected_comparison_run_id"]) if row["selected_comparison_run_id"] is not None else None
        ),
        payload_path=str(row["payload_path"]),
        created_by_user_id=str(row["created_by_user_id"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        metadata=dict(_json_loads(str(row["metadata_json"]))) if str(row["metadata_json"]) else {},
    )


def _decision_log_from_row(row: sqlite3.Row | None) -> WorkspaceDecisionLog | None:
    if row is None:
        return None
    return WorkspaceDecisionLog(
        decision_log_id=str(row["decision_log_id"]),
        workspace_id=str(row["workspace_id"]),
        project_id=str(row["project_id"]),
        study_id=str(row["study_id"]),
        job_id=str(row["job_id"]) if row["job_id"] is not None else None,
        run_id=str(row["run_id"]) if row["run_id"] is not None else None,
        evidence_view_id=str(row["evidence_view_id"]) if row["evidence_view_id"] is not None else None,
        title=str(row["title"]),
        decision_summary=str(row["decision_summary"]),
        rationale=str(row["rationale"]),
        selected_result_id=str(row["selected_result_id"]) if row["selected_result_id"] is not None else None,
        selected_comparison_run_id=(
            str(row["selected_comparison_run_id"]) if row["selected_comparison_run_id"] is not None else None
        ),
        payload_path=str(row["payload_path"]),
        created_by_user_id=str(row["created_by_user_id"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        metadata=dict(_json_loads(str(row["metadata_json"]))) if str(row["metadata_json"]) else {},
    )


def _decision_comment_from_row(row: sqlite3.Row | None) -> WorkspaceDecisionComment | None:
    if row is None:
        return None
    return WorkspaceDecisionComment(
        decision_comment_id=str(row["decision_comment_id"]),
        workspace_id=str(row["workspace_id"]),
        project_id=str(row["project_id"]),
        study_id=str(row["study_id"]),
        decision_log_id=str(row["decision_log_id"]),
        parent_comment_id=str(row["parent_comment_id"]) if row["parent_comment_id"] is not None else None,
        anchor_kind=str(row["anchor_kind"]),
        body=str(row["body"]),
        created_by_user_id=str(row["created_by_user_id"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        metadata=dict(_json_loads(str(row["metadata_json"]))) if str(row["metadata_json"]) else {},
    )


def _job_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "job_id": str(row["job_id"]),
        "workspace_id": str(row["workspace_id"]),
        "brief_id": str(row["brief_id"]),
        "requested_by_user_id": str(row["requested_by_user_id"]),
        "panel_spec": dict(_json_loads(str(row["panel_spec_json"]))),
        "provider_name": str(row["provider_name"]),
        "status": str(row["status"]),
        "priority": str(row["priority"]),
        "input_artifact_path": str(row["input_artifact_path"]),
        "persona_dir_path": str(row["persona_dir_path"]),
        "output_run_path": str(row["output_run_path"]) if row["output_run_path"] is not None else None,
        "retry_count": int(row["retry_count"]),
        "created_at": str(row["created_at"]),
        "started_at": str(row["started_at"]) if row["started_at"] is not None else None,
        "finished_at": str(row["finished_at"]) if row["finished_at"] is not None else None,
        "idempotency_key": str(row["idempotency_key"]),
        "last_error": str(row["last_error"]),
        "metadata": dict(_json_loads(str(row["metadata_json"]))) if str(row["metadata_json"]) else {},
    }


def upsert_workspace(runtime_root: Path, workspace: TenantWorkspace) -> TenantWorkspace:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            INSERT INTO workspaces(
                workspace_id,
                slug,
                display_name,
                region_code,
                data_residency_region,
                plan_tier,
                status,
                created_at,
                settings_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(workspace_id) DO UPDATE SET
                slug=excluded.slug,
                display_name=excluded.display_name,
                region_code=excluded.region_code,
                data_residency_region=excluded.data_residency_region,
                plan_tier=excluded.plan_tier,
                status=excluded.status,
                settings_json=excluded.settings_json
            """,
            (
                workspace.workspace_id,
                workspace.slug,
                workspace.display_name,
                workspace.region_code,
                workspace.data_residency_region,
                workspace.plan_tier,
                workspace.status,
                workspace.created_at,
                _json_dumps(workspace.settings),
            ),
        )
        for member in workspace.members:
            connection.execute(
                """
                INSERT INTO workspace_members(workspace_id, user_id, role, joined_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(workspace_id, user_id) DO UPDATE SET
                    role=excluded.role,
                    joined_at=excluded.joined_at
                """,
                (workspace.workspace_id, member.user_id, member.role, member.joined_at),
            )
        desired_user_ids = [member.user_id for member in workspace.members]
        if desired_user_ids:
            placeholders = ",".join("?" for _ in desired_user_ids)
            connection.execute(
                f"""
                DELETE FROM workspace_members
                WHERE workspace_id = ? AND user_id NOT IN ({placeholders})
                """,
                (workspace.workspace_id, *desired_user_ids),
            )
        else:
            connection.execute("DELETE FROM workspace_members WHERE workspace_id = ?", (workspace.workspace_id,))
        connection.commit()
        return _workspace_from_row(
            connection,
            connection.execute("SELECT * FROM workspaces WHERE workspace_id = ?", (workspace.workspace_id,)).fetchone(),
        )  # type: ignore[return-value]


def get_workspace(runtime_root: Path, workspace_id: str) -> TenantWorkspace | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        return _workspace_from_row(
            connection,
            connection.execute("SELECT * FROM workspaces WHERE workspace_id = ?", (workspace_id,)).fetchone(),
        )


def list_workspaces(runtime_root: Path) -> list[TenantWorkspace]:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        rows = connection.execute("SELECT * FROM workspaces ORDER BY workspace_id").fetchall()
        workspaces: list[TenantWorkspace] = []
        for row in rows:
            workspace = _workspace_from_row(connection, row)
            if workspace is not None:
                workspaces.append(workspace)
        return workspaces


def upsert_billing_account(runtime_root: Path, billing_account: BillingAccount) -> BillingAccount:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            INSERT INTO billing_accounts(
                workspace_id,
                provider_name,
                provider_customer_ref,
                provider_subscription_ref,
                price_book_id,
                status,
                seat_count,
                renewal_at,
                metadata_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(workspace_id) DO UPDATE SET
                provider_name=excluded.provider_name,
                provider_customer_ref=excluded.provider_customer_ref,
                provider_subscription_ref=excluded.provider_subscription_ref,
                price_book_id=excluded.price_book_id,
                status=excluded.status,
                seat_count=excluded.seat_count,
                renewal_at=excluded.renewal_at,
                metadata_json=excluded.metadata_json
            """,
            (
                billing_account.workspace_id,
                billing_account.provider_name,
                billing_account.provider_customer_ref,
                billing_account.provider_subscription_ref,
                billing_account.price_book_id,
                billing_account.status,
                billing_account.seat_count,
                billing_account.renewal_at,
                _json_dumps(billing_account.metadata),
            ),
        )
        connection.commit()
        return _billing_from_row(
            connection.execute("SELECT * FROM billing_accounts WHERE workspace_id = ?", (billing_account.workspace_id,)).fetchone()
        )  # type: ignore[return-value]


def get_billing_account(runtime_root: Path, workspace_id: str) -> BillingAccount | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        return _billing_from_row(
            connection.execute("SELECT * FROM billing_accounts WHERE workspace_id = ?", (workspace_id,)).fetchone()
        )


def create_workspace_project(runtime_root: Path, project: WorkspaceProject) -> WorkspaceProject:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            INSERT INTO workspace_projects(
                project_id,
                workspace_id,
                slug,
                name,
                description,
                created_by_user_id,
                status,
                created_at,
                updated_at,
                metadata_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                project.workspace_id,
                project.slug,
                project.name,
                project.description,
                project.created_by_user_id,
                project.status,
                project.created_at,
                project.updated_at,
                _json_dumps(project.metadata),
            ),
        )
        connection.commit()
        return _project_from_row(
            connection.execute("SELECT * FROM workspace_projects WHERE project_id = ?", (project.project_id,)).fetchone()
        )  # type: ignore[return-value]


def get_workspace_project(runtime_root: Path, project_id: str) -> WorkspaceProject | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        return _project_from_row(
            connection.execute("SELECT * FROM workspace_projects WHERE project_id = ?", (project_id,)).fetchone()
        )


def list_workspace_projects(runtime_root: Path, workspace_id: str) -> list[WorkspaceProject]:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM workspace_projects
            WHERE workspace_id = ?
            ORDER BY updated_at DESC, project_id DESC
            """,
            (workspace_id,),
        ).fetchall()
        return [project for row in rows if (project := _project_from_row(row)) is not None]


def create_workspace_study(runtime_root: Path, study: WorkspaceStudy) -> WorkspaceStudy:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            INSERT INTO workspace_studies(
                study_id,
                workspace_id,
                project_id,
                title,
                created_by_user_id,
                status,
                research_intent,
                desired_output,
                first_task,
                artifact_refs_json,
                draft_plan_json,
                latest_job_id,
                created_at,
                updated_at,
                metadata_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                study.study_id,
                study.workspace_id,
                study.project_id,
                study.title,
                study.created_by_user_id,
                study.status,
                study.research_intent,
                study.desired_output,
                study.first_task,
                _json_dumps(study.artifact_refs),
                _json_dumps(study.draft_plan),
                study.latest_job_id,
                study.created_at,
                study.updated_at,
                _json_dumps(study.metadata),
            ),
        )
        connection.commit()
        return _study_from_row(
            connection.execute("SELECT * FROM workspace_studies WHERE study_id = ?", (study.study_id,)).fetchone()
        )  # type: ignore[return-value]


def get_workspace_study(runtime_root: Path, study_id: str) -> WorkspaceStudy | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        return _study_from_row(
            connection.execute("SELECT * FROM workspace_studies WHERE study_id = ?", (study_id,)).fetchone()
        )


def list_workspace_studies(runtime_root: Path, workspace_id: str, *, project_id: str = "") -> list[WorkspaceStudy]:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        if project_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_studies
                WHERE workspace_id = ? AND project_id = ?
                ORDER BY updated_at DESC, study_id DESC
                """,
                (workspace_id, project_id),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_studies
                WHERE workspace_id = ?
                ORDER BY updated_at DESC, study_id DESC
                """,
                (workspace_id,),
            ).fetchall()
        return [study for row in rows if (study := _study_from_row(row)) is not None]


def update_workspace_study(
    runtime_root: Path,
    *,
    study_id: str,
    status: str | None = None,
    latest_job_id: str | None = None,
    draft_plan: dict[str, Any] | None = None,
    metadata_updates: dict[str, Any] | None = None,
) -> WorkspaceStudy:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        current = connection.execute("SELECT * FROM workspace_studies WHERE study_id = ?", (study_id,)).fetchone()
        if current is None:
            raise ValueError(f"Unknown workspace study '{study_id}'.")
        metadata = dict(_json_loads(str(current["metadata_json"]))) if str(current["metadata_json"]) else {}
        metadata.update(metadata_updates or {})
        next_draft_plan = (
            draft_plan if draft_plan is not None else dict(_json_loads(str(current["draft_plan_json"]))) if str(current["draft_plan_json"]) else {}
        )
        connection.execute(
            """
            UPDATE workspace_studies
            SET status = COALESCE(?, status),
                latest_job_id = COALESCE(?, latest_job_id),
                draft_plan_json = ?,
                metadata_json = ?,
                updated_at = ?
            WHERE study_id = ?
            """,
            (
                status,
                latest_job_id,
                _json_dumps(next_draft_plan),
                _json_dumps(metadata),
                utc_now_iso(),
                study_id,
            ),
        )
        connection.commit()
        return _study_from_row(
            connection.execute("SELECT * FROM workspace_studies WHERE study_id = ?", (study_id,)).fetchone()
        )  # type: ignore[return-value]


def create_workspace_export_bundle(runtime_root: Path, export_bundle: WorkspaceExportBundle) -> WorkspaceExportBundle:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            INSERT INTO workspace_export_bundles(
                export_bundle_id,
                workspace_id,
                project_id,
                study_id,
                job_id,
                run_id,
                title,
                status,
                export_format,
                created_by_user_id,
                bundle_root,
                manifest_path,
                exported_files_json,
                synthetic_boundary,
                created_at,
                updated_at,
                metadata_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                export_bundle.export_bundle_id,
                export_bundle.workspace_id,
                export_bundle.project_id,
                export_bundle.study_id,
                export_bundle.job_id,
                export_bundle.run_id,
                export_bundle.title,
                export_bundle.status,
                export_bundle.export_format,
                export_bundle.created_by_user_id,
                export_bundle.bundle_root,
                export_bundle.manifest_path,
                _json_dumps(export_bundle.exported_files),
                export_bundle.synthetic_boundary,
                export_bundle.created_at,
                export_bundle.updated_at,
                _json_dumps(export_bundle.metadata),
            ),
        )
        connection.commit()
        return _export_bundle_from_row(
            connection.execute(
                "SELECT * FROM workspace_export_bundles WHERE export_bundle_id = ?",
                (export_bundle.export_bundle_id,),
            ).fetchone()
        )  # type: ignore[return-value]


def get_workspace_export_bundle(runtime_root: Path, export_bundle_id: str) -> WorkspaceExportBundle | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        return _export_bundle_from_row(
            connection.execute(
                "SELECT * FROM workspace_export_bundles WHERE export_bundle_id = ?",
                (export_bundle_id,),
            ).fetchone()
        )


def list_workspace_export_bundles(
    runtime_root: Path,
    workspace_id: str,
    *,
    study_id: str = "",
    job_id: str = "",
) -> list[WorkspaceExportBundle]:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        if study_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_export_bundles
                WHERE workspace_id = ? AND study_id = ?
                ORDER BY updated_at DESC, export_bundle_id DESC
                """,
                (workspace_id, study_id.strip()),
            ).fetchall()
        elif job_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_export_bundles
                WHERE workspace_id = ? AND job_id = ?
                ORDER BY updated_at DESC, export_bundle_id DESC
                """,
                (workspace_id, job_id.strip()),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_export_bundles
                WHERE workspace_id = ?
                ORDER BY updated_at DESC, export_bundle_id DESC
                """,
                (workspace_id,),
            ).fetchall()
        return [bundle for row in rows if (bundle := _export_bundle_from_row(row)) is not None]


def create_workspace_share_bundle(runtime_root: Path, share_bundle: WorkspaceShareBundle) -> WorkspaceShareBundle:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            INSERT INTO workspace_share_bundles(
                share_bundle_id,
                workspace_id,
                export_bundle_id,
                project_id,
                study_id,
                job_id,
                run_id,
                title,
                status,
                share_key,
                public_path,
                share_root,
                share_payload_path,
                created_by_user_id,
                synthetic_boundary,
                published_at,
                expires_at,
                revoked_at,
                created_at,
                updated_at,
                metadata_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                share_bundle.share_bundle_id,
                share_bundle.workspace_id,
                share_bundle.export_bundle_id,
                share_bundle.project_id,
                share_bundle.study_id,
                share_bundle.job_id,
                share_bundle.run_id,
                share_bundle.title,
                share_bundle.status,
                share_bundle.share_key,
                share_bundle.public_path,
                share_bundle.share_root,
                share_bundle.share_payload_path,
                share_bundle.created_by_user_id,
                share_bundle.synthetic_boundary,
                share_bundle.published_at,
                share_bundle.expires_at,
                share_bundle.revoked_at,
                share_bundle.created_at,
                share_bundle.updated_at,
                _json_dumps(share_bundle.metadata),
            ),
        )
        connection.commit()
        return _share_bundle_from_row(
            connection.execute(
                "SELECT * FROM workspace_share_bundles WHERE share_bundle_id = ?",
                (share_bundle.share_bundle_id,),
            ).fetchone()
        )  # type: ignore[return-value]


def get_workspace_share_bundle(runtime_root: Path, share_bundle_id: str) -> WorkspaceShareBundle | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        return _share_bundle_from_row(
            connection.execute(
                "SELECT * FROM workspace_share_bundles WHERE share_bundle_id = ?",
                (share_bundle_id,),
            ).fetchone()
        )


def get_workspace_share_bundle_by_key(runtime_root: Path, share_key: str) -> WorkspaceShareBundle | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        return _share_bundle_from_row(
            connection.execute(
                "SELECT * FROM workspace_share_bundles WHERE share_key = ?",
                (share_key,),
            ).fetchone()
        )


def list_workspace_share_bundles(
    runtime_root: Path,
    workspace_id: str,
    *,
    study_id: str = "",
    export_bundle_id: str = "",
) -> list[WorkspaceShareBundle]:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        if study_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_share_bundles
                WHERE workspace_id = ? AND study_id = ?
                ORDER BY updated_at DESC, share_bundle_id DESC
                """,
                (workspace_id, study_id.strip()),
            ).fetchall()
        elif export_bundle_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_share_bundles
                WHERE workspace_id = ? AND export_bundle_id = ?
                ORDER BY updated_at DESC, share_bundle_id DESC
                """,
                (workspace_id, export_bundle_id.strip()),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_share_bundles
                WHERE workspace_id = ?
                ORDER BY updated_at DESC, share_bundle_id DESC
                """,
                (workspace_id,),
            ).fetchall()
        return [bundle for row in rows if (bundle := _share_bundle_from_row(row)) is not None]


def update_workspace_share_bundle(
    runtime_root: Path,
    *,
    share_bundle_id: str,
    status: str | None = None,
    expires_at: str | None = None,
    revoked_at: str | None = None,
    metadata_updates: dict[str, Any] | None = None,
) -> WorkspaceShareBundle:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        current = connection.execute("SELECT * FROM workspace_share_bundles WHERE share_bundle_id = ?", (share_bundle_id,)).fetchone()
        if current is None:
            raise ValueError(f"Unknown workspace share bundle '{share_bundle_id}'.")
        metadata = dict(_json_loads(str(current["metadata_json"]))) if str(current["metadata_json"]) else {}
        metadata.update(metadata_updates or {})
        connection.execute(
            """
            UPDATE workspace_share_bundles
            SET status = COALESCE(?, status),
                expires_at = COALESCE(?, expires_at),
                revoked_at = COALESCE(?, revoked_at),
                metadata_json = ?,
                updated_at = ?
            WHERE share_bundle_id = ?
            """,
            (
                status,
                expires_at,
                revoked_at,
                _json_dumps(metadata),
                utc_now_iso(),
                share_bundle_id,
            ),
        )
        connection.commit()
        return _share_bundle_from_row(
            connection.execute("SELECT * FROM workspace_share_bundles WHERE share_bundle_id = ?", (share_bundle_id,)).fetchone()
        )  # type: ignore[return-value]


def create_workspace_support_snapshot(
    runtime_root: Path,
    support_snapshot: WorkspaceSupportSnapshot,
) -> WorkspaceSupportSnapshot:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            INSERT INTO workspace_support_snapshots(
                support_snapshot_id,
                workspace_id,
                project_id,
                study_id,
                job_id,
                run_id,
                title,
                status,
                summary,
                support_root,
                snapshot_path,
                created_by_user_id,
                created_at,
                updated_at,
                metadata_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                support_snapshot.support_snapshot_id,
                support_snapshot.workspace_id,
                support_snapshot.project_id,
                support_snapshot.study_id,
                support_snapshot.job_id,
                support_snapshot.run_id,
                support_snapshot.title,
                support_snapshot.status,
                support_snapshot.summary,
                support_snapshot.support_root,
                support_snapshot.snapshot_path,
                support_snapshot.created_by_user_id,
                support_snapshot.created_at,
                support_snapshot.updated_at,
                _json_dumps(support_snapshot.metadata),
            ),
        )
        connection.commit()
        return _support_snapshot_from_row(
            connection.execute(
                "SELECT * FROM workspace_support_snapshots WHERE support_snapshot_id = ?",
                (support_snapshot.support_snapshot_id,),
            ).fetchone()
        )  # type: ignore[return-value]


def get_workspace_support_snapshot(runtime_root: Path, support_snapshot_id: str) -> WorkspaceSupportSnapshot | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        return _support_snapshot_from_row(
            connection.execute(
                "SELECT * FROM workspace_support_snapshots WHERE support_snapshot_id = ?",
                (support_snapshot_id,),
            ).fetchone()
        )


def list_workspace_support_snapshots(
    runtime_root: Path,
    workspace_id: str,
    *,
    study_id: str = "",
    job_id: str = "",
) -> list[WorkspaceSupportSnapshot]:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        if study_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_support_snapshots
                WHERE workspace_id = ? AND study_id = ?
                ORDER BY updated_at DESC, support_snapshot_id DESC
                """,
                (workspace_id, study_id.strip()),
            ).fetchall()
        elif job_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_support_snapshots
                WHERE workspace_id = ? AND job_id = ?
                ORDER BY updated_at DESC, support_snapshot_id DESC
                """,
                (workspace_id, job_id.strip()),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_support_snapshots
                WHERE workspace_id = ?
                ORDER BY updated_at DESC, support_snapshot_id DESC
                """,
                (workspace_id,),
            ).fetchall()
        return [snapshot for row in rows if (snapshot := _support_snapshot_from_row(row)) is not None]


def create_workspace_evidence_view(runtime_root: Path, evidence_view: WorkspaceEvidenceView) -> WorkspaceEvidenceView:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            INSERT INTO workspace_evidence_views(
                evidence_view_id,
                workspace_id,
                project_id,
                study_id,
                job_id,
                run_id,
                title,
                note,
                query_text,
                active_family,
                sort_by,
                selected_result_id,
                selected_replay_step_id,
                selected_comparison_run_id,
                payload_path,
                created_by_user_id,
                created_at,
                updated_at,
                metadata_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_view.evidence_view_id,
                evidence_view.workspace_id,
                evidence_view.project_id,
                evidence_view.study_id,
                evidence_view.job_id,
                evidence_view.run_id,
                evidence_view.title,
                evidence_view.note,
                evidence_view.query_text,
                evidence_view.active_family,
                evidence_view.sort_by,
                evidence_view.selected_result_id,
                evidence_view.selected_replay_step_id,
                evidence_view.selected_comparison_run_id,
                evidence_view.payload_path,
                evidence_view.created_by_user_id,
                evidence_view.created_at,
                evidence_view.updated_at,
                _json_dumps(evidence_view.metadata),
            ),
        )
        connection.commit()
        return _evidence_view_from_row(
            connection.execute(
                "SELECT * FROM workspace_evidence_views WHERE evidence_view_id = ?",
                (evidence_view.evidence_view_id,),
            ).fetchone()
        )  # type: ignore[return-value]


def get_workspace_evidence_view(runtime_root: Path, evidence_view_id: str) -> WorkspaceEvidenceView | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        return _evidence_view_from_row(
            connection.execute(
                "SELECT * FROM workspace_evidence_views WHERE evidence_view_id = ?",
                (evidence_view_id,),
            ).fetchone()
        )


def list_workspace_evidence_views(
    runtime_root: Path,
    workspace_id: str,
    *,
    study_id: str = "",
    job_id: str = "",
) -> list[WorkspaceEvidenceView]:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        if study_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_evidence_views
                WHERE workspace_id = ? AND study_id = ?
                ORDER BY updated_at DESC, evidence_view_id DESC
                """,
                (workspace_id, study_id.strip()),
            ).fetchall()
        elif job_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_evidence_views
                WHERE workspace_id = ? AND job_id = ?
                ORDER BY updated_at DESC, evidence_view_id DESC
                """,
                (workspace_id, job_id.strip()),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_evidence_views
                WHERE workspace_id = ?
                ORDER BY updated_at DESC, evidence_view_id DESC
                """,
                (workspace_id,),
            ).fetchall()
        return [view for row in rows if (view := _evidence_view_from_row(row)) is not None]


def create_workspace_decision_log(runtime_root: Path, decision_log: WorkspaceDecisionLog) -> WorkspaceDecisionLog:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            INSERT INTO workspace_decision_logs(
                decision_log_id,
                workspace_id,
                project_id,
                study_id,
                job_id,
                run_id,
                evidence_view_id,
                title,
                decision_summary,
                rationale,
                selected_result_id,
                selected_comparison_run_id,
                payload_path,
                created_by_user_id,
                created_at,
                updated_at,
                metadata_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_log.decision_log_id,
                decision_log.workspace_id,
                decision_log.project_id,
                decision_log.study_id,
                decision_log.job_id,
                decision_log.run_id,
                decision_log.evidence_view_id,
                decision_log.title,
                decision_log.decision_summary,
                decision_log.rationale,
                decision_log.selected_result_id,
                decision_log.selected_comparison_run_id,
                decision_log.payload_path,
                decision_log.created_by_user_id,
                decision_log.created_at,
                decision_log.updated_at,
                _json_dumps(decision_log.metadata),
            ),
        )
        connection.commit()
        return _decision_log_from_row(
            connection.execute(
                "SELECT * FROM workspace_decision_logs WHERE decision_log_id = ?",
                (decision_log.decision_log_id,),
            ).fetchone()
        )  # type: ignore[return-value]


def update_workspace_decision_log_metadata(
    runtime_root: Path,
    *,
    decision_log_id: str,
    metadata_updates: dict[str, Any] | None = None,
    updated_at: str = "",
) -> WorkspaceDecisionLog | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        current = connection.execute(
            "SELECT * FROM workspace_decision_logs WHERE decision_log_id = ?",
            (decision_log_id,),
        ).fetchone()
        current_log = _decision_log_from_row(current)
        if current_log is None:
            return None
        merged_metadata = dict(current_log.metadata)
        merged_metadata.update(dict(metadata_updates or {}))
        connection.execute(
            """
            UPDATE workspace_decision_logs
            SET metadata_json = ?, updated_at = ?
            WHERE decision_log_id = ?
            """,
            (
                _json_dumps(merged_metadata),
                updated_at.strip() or utc_now_iso(),
                decision_log_id,
            ),
        )
        connection.commit()
        return _decision_log_from_row(
            connection.execute(
                "SELECT * FROM workspace_decision_logs WHERE decision_log_id = ?",
                (decision_log_id,),
            ).fetchone()
        )


def get_workspace_decision_log(runtime_root: Path, decision_log_id: str) -> WorkspaceDecisionLog | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        return _decision_log_from_row(
            connection.execute(
                "SELECT * FROM workspace_decision_logs WHERE decision_log_id = ?",
                (decision_log_id,),
            ).fetchone()
        )


def list_workspace_decision_logs(
    runtime_root: Path,
    workspace_id: str,
    *,
    study_id: str = "",
    job_id: str = "",
    evidence_view_id: str = "",
) -> list[WorkspaceDecisionLog]:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        if study_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_decision_logs
                WHERE workspace_id = ? AND study_id = ?
                ORDER BY updated_at DESC, decision_log_id DESC
                """,
                (workspace_id, study_id.strip()),
            ).fetchall()
        elif job_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_decision_logs
                WHERE workspace_id = ? AND job_id = ?
                ORDER BY updated_at DESC, decision_log_id DESC
                """,
                (workspace_id, job_id.strip()),
            ).fetchall()
        elif evidence_view_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_decision_logs
                WHERE workspace_id = ? AND evidence_view_id = ?
                ORDER BY updated_at DESC, decision_log_id DESC
                """,
                (workspace_id, evidence_view_id.strip()),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_decision_logs
                WHERE workspace_id = ?
                ORDER BY updated_at DESC, decision_log_id DESC
                """,
                (workspace_id,),
            ).fetchall()
        return [log for row in rows if (log := _decision_log_from_row(row)) is not None]


def create_workspace_decision_comment(
    runtime_root: Path,
    decision_comment: WorkspaceDecisionComment,
) -> WorkspaceDecisionComment:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            INSERT INTO workspace_decision_comments(
                decision_comment_id,
                workspace_id,
                project_id,
                study_id,
                decision_log_id,
                parent_comment_id,
                anchor_kind,
                body,
                created_by_user_id,
                created_at,
                updated_at,
                metadata_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_comment.decision_comment_id,
                decision_comment.workspace_id,
                decision_comment.project_id,
                decision_comment.study_id,
                decision_comment.decision_log_id,
                decision_comment.parent_comment_id,
                decision_comment.anchor_kind,
                decision_comment.body,
                decision_comment.created_by_user_id,
                decision_comment.created_at,
                decision_comment.updated_at,
                _json_dumps(decision_comment.metadata),
            ),
        )
        connection.commit()
        return _decision_comment_from_row(
            connection.execute(
                "SELECT * FROM workspace_decision_comments WHERE decision_comment_id = ?",
                (decision_comment.decision_comment_id,),
            ).fetchone()
        )  # type: ignore[return-value]


def get_workspace_decision_comment(runtime_root: Path, decision_comment_id: str) -> WorkspaceDecisionComment | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        return _decision_comment_from_row(
            connection.execute(
                "SELECT * FROM workspace_decision_comments WHERE decision_comment_id = ?",
                (decision_comment_id,),
            ).fetchone()
        )


def list_workspace_decision_comments(
    runtime_root: Path,
    workspace_id: str,
    *,
    decision_log_id: str = "",
    study_id: str = "",
) -> list[WorkspaceDecisionComment]:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        if decision_log_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_decision_comments
                WHERE workspace_id = ? AND decision_log_id = ?
                ORDER BY created_at, decision_comment_id
                """,
                (workspace_id, decision_log_id.strip()),
            ).fetchall()
        elif study_id.strip():
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_decision_comments
                WHERE workspace_id = ? AND study_id = ?
                ORDER BY created_at, decision_comment_id
                """,
                (workspace_id, study_id.strip()),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM workspace_decision_comments
                WHERE workspace_id = ?
                ORDER BY created_at, decision_comment_id
                """,
                (workspace_id,),
            ).fetchall()
        return [comment for row in rows if (comment := _decision_comment_from_row(row)) is not None]


def create_audit_event(runtime_root: Path, event: AuditEvent) -> AuditEvent:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            INSERT INTO audit_events(
                audit_event_id,
                workspace_id,
                actor_user_id,
                actor_role,
                action,
                target_type,
                target_id,
                event_payload_json,
                created_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.audit_event_id,
                event.workspace_id,
                event.actor_user_id,
                event.actor_role,
                event.action,
                event.target_type,
                event.target_id,
                _json_dumps(event.event_payload),
                event.created_at,
            ),
        )
        connection.commit()
        return _audit_event_from_row(
            connection.execute("SELECT * FROM audit_events WHERE audit_event_id = ?", (event.audit_event_id,)).fetchone()
        )  # type: ignore[return-value]


def list_audit_events(
    runtime_root: Path,
    workspace_id: str,
    *,
    target_type: str = "",
    action_prefix: str = "",
    limit: int = 20,
) -> list[AuditEvent]:
    query = """
        SELECT *
        FROM audit_events
        WHERE workspace_id = ?
    """
    params: list[Any] = [workspace_id]
    if target_type.strip():
        query += " AND target_type = ?"
        params.append(target_type.strip())
    if action_prefix.strip():
        query += " AND action LIKE ?"
        params.append(f"{action_prefix.strip()}%")
    query += """
        ORDER BY created_at DESC, audit_event_id DESC
        LIMIT ?
    """
    params.append(max(1, int(limit)))
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
        return [event for row in rows if (event := _audit_event_from_row(row)) is not None]


def create_browser_session(runtime_root: Path, session: WorkspaceBrowserSession) -> WorkspaceBrowserSession:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            INSERT INTO workspace_browser_sessions(
                session_id,
                workspace_id,
                user_id,
                role,
                source_token,
                created_at,
                last_seen_at,
                expires_at,
                revoked_at,
                metadata_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                workspace_id=excluded.workspace_id,
                user_id=excluded.user_id,
                role=excluded.role,
                source_token=excluded.source_token,
                created_at=excluded.created_at,
                last_seen_at=excluded.last_seen_at,
                expires_at=excluded.expires_at,
                revoked_at=excluded.revoked_at,
                metadata_json=excluded.metadata_json
            """,
            (
                session.session_id,
                session.workspace_id,
                session.user_id,
                session.role,
                session.source_token,
                session.created_at,
                session.last_seen_at,
                session.expires_at,
                session.revoked_at,
                _json_dumps(session.metadata),
            ),
        )
        connection.commit()
        return _browser_session_from_row(
            connection.execute(
                "SELECT * FROM workspace_browser_sessions WHERE session_id = ?",
                (session.session_id,),
            ).fetchone()
        )  # type: ignore[return-value]


def resolve_browser_session(runtime_root: Path, session_id: str) -> WorkspaceBrowserSession | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        return _browser_session_from_row(
            connection.execute(
                """
                SELECT *
                FROM workspace_browser_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        )


def touch_browser_session(
    runtime_root: Path,
    session_id: str,
    *,
    last_seen_at: str,
    expires_at: str,
    role: str | None = None,
) -> WorkspaceBrowserSession | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        if role is None:
            connection.execute(
                """
                UPDATE workspace_browser_sessions
                SET last_seen_at = ?, expires_at = ?
                WHERE session_id = ?
                """,
                (last_seen_at, expires_at, session_id),
            )
        else:
            connection.execute(
                """
                UPDATE workspace_browser_sessions
                SET role = ?, last_seen_at = ?, expires_at = ?
                WHERE session_id = ?
                """,
                (role, last_seen_at, expires_at, session_id),
            )
        connection.commit()
    return resolve_browser_session(runtime_root, session_id)


def revoke_browser_session(runtime_root: Path, session_id: str, *, revoked_at: str | None = None) -> WorkspaceBrowserSession | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            UPDATE workspace_browser_sessions
            SET revoked_at = COALESCE(revoked_at, ?)
            WHERE session_id = ?
            """,
            (revoked_at or utc_now_iso(), session_id),
        )
        connection.commit()
    return resolve_browser_session(runtime_root, session_id)


def revoke_browser_sessions_for_token(runtime_root: Path, token: str, *, revoked_at: str | None = None) -> int:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        cursor = connection.execute(
            """
            UPDATE workspace_browser_sessions
            SET revoked_at = COALESCE(revoked_at, ?)
            WHERE source_token = ?
            """,
            (revoked_at or utc_now_iso(), token),
        )
        connection.commit()
        return int(cursor.rowcount or 0)


def register_api_token(
    runtime_root: Path,
    *,
    token: str,
    workspace_id: str,
    user_id: str,
    role: str,
    issued_at: str | None = None,
    active: bool = True,
) -> None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            INSERT INTO api_tokens(token, workspace_id, user_id, role, issued_at, active)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(token) DO UPDATE SET
                workspace_id=excluded.workspace_id,
                user_id=excluded.user_id,
                role=excluded.role,
                issued_at=excluded.issued_at,
                active=excluded.active
            """,
            (token, workspace_id, user_id, role, issued_at or utc_now_iso(), 1 if active else 0),
        )
        connection.commit()


def resolve_api_token(runtime_root: Path, token: str) -> dict[str, Any] | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        row = connection.execute(
            """
            SELECT token, workspace_id, user_id, role, issued_at, active
            FROM api_tokens
            WHERE token = ?
            """,
            (token,),
        ).fetchone()
        if row is None:
            return None
        return {
            "token": str(row["token"]),
            "workspace_id": str(row["workspace_id"]),
            "user_id": str(row["user_id"]),
            "role": str(row["role"]),
            "issued_at": str(row["issued_at"]),
            "active": bool(row["active"]),
        }


def list_api_tokens(runtime_root: Path, workspace_id: str) -> list[dict[str, Any]]:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        rows = connection.execute(
            """
            SELECT token, workspace_id, user_id, role, issued_at, active
            FROM api_tokens
            WHERE workspace_id = ?
            ORDER BY issued_at DESC, token DESC
            """,
            (workspace_id,),
        ).fetchall()
        return [
            {
                "token": str(row["token"]),
                "workspace_id": str(row["workspace_id"]),
                "user_id": str(row["user_id"]),
                "role": str(row["role"]),
                "issued_at": str(row["issued_at"]),
                "active": bool(row["active"]),
            }
            for row in rows
        ]


def update_api_tokens_for_member(runtime_root: Path, *, workspace_id: str, user_id: str, role: str) -> None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            UPDATE api_tokens
            SET role = ?
            WHERE workspace_id = ? AND user_id = ?
            """,
            (role, workspace_id, user_id),
        )
        connection.commit()


def deactivate_api_token(runtime_root: Path, token: str) -> dict[str, Any] | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute(
            """
            UPDATE api_tokens
            SET active = 0
            WHERE token = ?
            """,
            (token,),
        )
        connection.commit()
    return resolve_api_token(runtime_root, token)


def create_validation_job(
    runtime_root: Path,
    *,
    job: ValidationJob,
    persona_dir_path: str,
    idempotency_key: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        if idempotency_key:
            existing = connection.execute(
                """
                SELECT *
                FROM validation_jobs
                WHERE workspace_id = ? AND idempotency_key = ?
                """,
                (job.workspace_id, idempotency_key),
            ).fetchone()
            if existing is not None:
                return _job_from_row(existing)  # type: ignore[return-value]
        connection.execute(
            """
            INSERT INTO validation_jobs(
                job_id,
                workspace_id,
                brief_id,
                requested_by_user_id,
                panel_spec_json,
                provider_name,
                status,
                priority,
                input_artifact_path,
                persona_dir_path,
                output_run_path,
                retry_count,
                created_at,
                started_at,
                finished_at,
                idempotency_key,
                last_error,
                metadata_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.job_id,
                job.workspace_id,
                job.brief_id,
                job.requested_by_user_id,
                _json_dumps(job.panel_spec.to_dict()),
                job.provider_name,
                job.status,
                job.priority,
                job.input_artifact_path,
                persona_dir_path,
                job.output_run_path,
                job.retry_count,
                job.created_at,
                job.started_at,
                job.finished_at,
                idempotency_key,
                "",
                _json_dumps(metadata or {}),
            ),
        )
        connection.commit()
        return _job_from_row(
            connection.execute("SELECT * FROM validation_jobs WHERE job_id = ?", (job.job_id,)).fetchone()
        )  # type: ignore[return-value]


def list_workspace_jobs(runtime_root: Path, workspace_id: str) -> list[dict[str, Any]]:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM validation_jobs
            WHERE workspace_id = ?
            ORDER BY created_at DESC, job_id DESC
            """,
            (workspace_id,),
        ).fetchall()
        return [_job_from_row(row) for row in rows if row is not None]


def get_validation_job(runtime_root: Path, job_id: str) -> dict[str, Any] | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        return _job_from_row(connection.execute("SELECT * FROM validation_jobs WHERE job_id = ?", (job_id,)).fetchone())


def count_workspace_jobs_created_since(runtime_root: Path, workspace_id: str, created_at_floor: str) -> int:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM validation_jobs
            WHERE workspace_id = ? AND created_at >= ?
            """,
            (workspace_id, created_at_floor),
        ).fetchone()
        return int(row["total"]) if row is not None else 0


def count_workspace_active_jobs(runtime_root: Path, workspace_id: str) -> int:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM validation_jobs
            WHERE workspace_id = ? AND status IN ('queued', 'running')
            """,
            (workspace_id,),
        ).fetchone()
        return int(row["total"]) if row is not None else 0


def lease_next_validation_job(runtime_root: Path) -> dict[str, Any] | None:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT *
            FROM validation_jobs
            WHERE status = 'queued'
            ORDER BY created_at, job_id
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            connection.commit()
            return None
        started_at = utc_now_iso()
        connection.execute(
            """
            UPDATE validation_jobs
            SET status = 'running', started_at = ?, retry_count = retry_count + 1
            WHERE job_id = ?
            """,
            (started_at, str(row["job_id"])),
        )
        leased = connection.execute("SELECT * FROM validation_jobs WHERE job_id = ?", (str(row["job_id"]),)).fetchone()
        connection.commit()
        return _job_from_row(leased)


def update_validation_job(
    runtime_root: Path,
    *,
    job_id: str,
    status: str,
    output_run_path: str | None = None,
    last_error: str = "",
    metadata_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with closing(_connect(runtime_db_path(runtime_root))) as connection:
        current = connection.execute("SELECT * FROM validation_jobs WHERE job_id = ?", (job_id,)).fetchone()
        if current is None:
            raise ValueError(f"Unknown validation job '{job_id}'.")
        metadata = dict(_json_loads(str(current["metadata_json"]))) if str(current["metadata_json"]) else {}
        metadata.update(metadata_updates or {})
        finished_at = utc_now_iso() if status in {"completed", "failed", "canceled"} else None
        connection.execute(
            """
            UPDATE validation_jobs
            SET status = ?,
                output_run_path = COALESCE(?, output_run_path),
                finished_at = COALESCE(?, finished_at),
                last_error = ?,
                metadata_json = ?
            WHERE job_id = ?
            """,
            (
                status,
                output_run_path,
                finished_at,
                last_error,
                _json_dumps(metadata),
                job_id,
            ),
        )
        connection.commit()
        return _job_from_row(connection.execute("SELECT * FROM validation_jobs WHERE job_id = ?", (job_id,)).fetchone())  # type: ignore[return-value]
