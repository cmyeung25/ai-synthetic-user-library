from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import utc_now_iso
from ai_validation_swarm.saas.models import BillingAccount, TenantWorkspace, ValidationJob, WorkspaceMember


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
        connection.execute("DELETE FROM workspace_members WHERE workspace_id = ?", (workspace.workspace_id,))
        for member in workspace.members:
            connection.execute(
                """
                INSERT INTO workspace_members(workspace_id, user_id, role, joined_at)
                VALUES(?, ?, ?, ?)
                """,
                (workspace.workspace_id, member.user_id, member.role, member.joined_at),
            )
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
