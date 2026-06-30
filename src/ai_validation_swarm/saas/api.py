from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import mimetypes
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Callable
import time
from urllib.parse import parse_qs, parse_qsl, urlencode, unquote
from wsgiref.simple_server import make_server

from ai_validation_swarm.domain.models import PanelSpec
from ai_validation_swarm.saas.runtime import (
    AuthenticationError,
    AuthorizationError,
    SaasRuntime,
    ShareUnavailableError,
    ValidationJobRequest,
)


HOSTED_BROWSER_SESSION_COOKIE = "ai_validation_swarm_session"


@dataclass(slots=True)
class SaasApiDeploymentProfile:
    deployment_env: str = "local"
    public_base_url: str = ""
    secret_source: str = "local_dev"
    expected_backup_mode: str = "local_filesystem"
    allow_query_token_bootstrap: bool = True
    structured_logs: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cors_headers() -> list[tuple[str, str]]:
    return [
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Headers", "Authorization, Content-Type"),
        ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
    ]


def _json_response(
    start_response: Callable[..., Any],
    status: str,
    payload: dict[str, Any],
    *,
    extra_headers: list[tuple[str, str]] | None = None,
) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            *(extra_headers or []),
            *_cors_headers(),
        ],
    )
    return [body]


def _empty_response(
    start_response: Callable[..., Any],
    status: str = "204 No Content",
    *,
    extra_headers: list[tuple[str, str]] | None = None,
) -> list[bytes]:
    start_response(
        status,
        [
            ("Content-Length", "0"),
            *(extra_headers or []),
            *_cors_headers(),
        ],
    )
    return []


def _redirect_response(
    start_response: Callable[..., Any],
    location: str,
    status: str = "302 Found",
    *,
    extra_headers: list[tuple[str, str]] | None = None,
) -> list[bytes]:
    start_response(
        status,
        [
            ("Location", location),
            ("Content-Length", "0"),
            *(extra_headers or []),
            *_cors_headers(),
        ],
    )
    return []


def _file_response(start_response: Callable[..., Any], status: str, path: Path) -> list[bytes]:
    body = path.read_bytes()
    content_type, _ = mimetypes.guess_type(str(path))
    start_response(
        status,
        [
            ("Content-Type", content_type or "application/octet-stream"),
            ("Content-Length", str(len(body))),
            *_cors_headers(),
        ],
    )
    return [body[index : index + 65536] for index in range(0, len(body), 65536)]


def _html_response(
    start_response: Callable[..., Any],
    status: str,
    body: str,
    *,
    extra_headers: list[tuple[str, str]] | None = None,
) -> list[bytes]:
    payload = body.encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(payload))),
            *(extra_headers or []),
            *_cors_headers(),
        ],
    )
    return [payload]


def _parse_json_body(environ: dict[str, Any]) -> dict[str, Any]:
    length_raw = environ.get("CONTENT_LENGTH", "0") or "0"
    try:
        length = int(length_raw)
    except ValueError:
        length = 0
    body = environ["wsgi.input"].read(length) if length > 0 else b"{}"
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON request body must be an object.")
    return payload


def _cookie_value(environ: dict[str, Any], name: str) -> str:
    raw_cookie = str(environ.get("HTTP_COOKIE", "") or "").strip()
    if not raw_cookie:
        return ""
    cookies = SimpleCookie()
    cookies.load(raw_cookie)
    morsel = cookies.get(name)
    if morsel is None:
        return ""
    return str(morsel.value or "").strip()


def _session_cookie_headers(session_id: str, *, environ: dict[str, Any], clear: bool = False) -> list[tuple[str, str]]:
    parts = [f"{HOSTED_BROWSER_SESSION_COOKIE}={'' if clear else session_id}", "Path=/", "HttpOnly", "SameSite=Lax"]
    if clear:
        parts.append("Max-Age=0")
    else:
        parts.append("Max-Age=43200")
    if str(environ.get("wsgi.url_scheme", "")).lower() == "https":
        parts.append("Secure")
    return [("Set-Cookie", "; ".join(parts))]


def _remove_query_keys(query_string: str, *keys: str) -> str:
    if not query_string:
        return ""
    disallowed = {key for key in keys if key}
    pairs = [(key, value) for key, value in parse_qsl(query_string, keep_blank_values=True) if key not in disallowed]
    return urlencode(pairs, doseq=True)


class SaasApiApplication:
    def __init__(
        self,
        runtime: SaasRuntime,
        *,
        deployment_profile: SaasApiDeploymentProfile | None = None,
    ) -> None:
        self.runtime = runtime
        self.repo_root = Path(__file__).resolve().parents[3]
        self.deployment_profile = deployment_profile or SaasApiDeploymentProfile()

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        started_at = time.perf_counter()
        response_status = "500 Internal Server Error"

        def capture_start_response(
            status: str,
            headers: list[tuple[str, str]],
            exc_info: Any = None,
        ) -> Any:
            nonlocal response_status
            response_status = status
            return start_response(status, headers, exc_info) if exc_info is not None else start_response(status, headers)

        try:
            method = str(environ.get("REQUEST_METHOD", "GET")).upper()
            path = str(environ.get("PATH_INFO", ""))
            if method == "OPTIONS" and (
                path == "/api/v1/health"
                or path == "/api/v1/ready"
                or path == "/api/v1/service-metadata"
                or path == "/api/v1/contract-manifest"
                or path == "/api/v1/operations/summary"
                or path == "/api/v1/persona-library"
                or path == "/api/v1/public-launch-readiness"
                or path.startswith("/api/v1/validation-jobs")
                or path.startswith("/api/v1/evidence-query")
                or path.startswith("/api/v1/export-bundles")
                or path.startswith("/api/v1/share-bundles")
                or path.startswith("/api/v1/support-diagnostics")
                or path.startswith("/api/v1/support-snapshots")
                or path.startswith("/api/v1/workspace-settings")
                or path.startswith("/api/v1/audit-events")
                or path.startswith("/api/v1/workspace-billing")
                or path.startswith("/api/v1/workspace-members")
                or path.startswith("/api/v1/api-tokens")
                or path.startswith("/public/v1/share-bundles")
                or path.startswith("/api/v1/projects")
                or path.startswith("/api/v1/studies")
                or path.startswith("/api/v1/study-reports")
                or path.startswith("/api/v1/evidence-views")
                or path.startswith("/api/v1/decision-logs")
                or path == "/api/v1/session"
                or path == "/api/v1/session/logout"
                or path == "/api/v1/workspace-shell"
            ):
                return _empty_response(capture_start_response)
            if method == "GET" and path == "/api/v1/health":
                return self._get_health(capture_start_response)
            if method == "GET" and path == "/api/v1/ready":
                return self._get_readiness(capture_start_response)
            if method == "GET" and path == "/api/v1/service-metadata":
                return self._get_service_metadata(capture_start_response)
            if method == "GET" and path == "/api/v1/contract-manifest":
                return self._get_contract_manifest(capture_start_response)
            if method == "GET" and path == "/api/v1/operations/summary":
                return self._get_workspace_operations_summary(environ, capture_start_response)
            if method == "GET" and path == "/api/v1/public-launch-readiness":
                return self._get_workspace_public_launch_readiness(environ, capture_start_response)
            if method == "GET" and path.startswith("/app-static/"):
                return self._get_static_asset(path.removeprefix("/app-static/"), capture_start_response)
            if method == "GET" and self._is_hosted_workspace_route(path):
                return self._get_hosted_workspace_shell(environ, path, capture_start_response)
            if method == "GET" and self._is_hosted_frontline_route(path):
                return self._get_hosted_frontline_studio(environ, path, capture_start_response)
            if method == "GET" and path.startswith("/public/v1/share-bundles/"):
                share_key = path.rsplit("/", 1)[-1]
                return self._get_public_share_bundle(share_key, capture_start_response)
            if method == "GET" and path == "/api/v1/session":
                return self._get_session(environ, capture_start_response)
            if method == "GET" and path == "/api/v1/persona-library":
                return self._get_persona_library(environ, capture_start_response)
            if method == "POST" and path == "/api/v1/session/logout":
                return self._logout_session(environ, capture_start_response)
            if method == "GET" and path == "/api/v1/workspace-settings":
                return self._get_workspace_settings(environ, capture_start_response)
            if method == "GET" and path == "/api/v1/audit-events":
                return self._get_workspace_audit_events(environ, capture_start_response)
            if method == "POST" and path == "/api/v1/workspace-billing":
                return self._update_workspace_billing(environ, capture_start_response)
            if method == "GET" and path == "/api/v1/workspace-shell":
                return self._get_workspace_shell(environ, capture_start_response)
            if method == "POST" and path == "/api/v1/workspace-members":
                return self._upsert_workspace_member(environ, capture_start_response)
            if method == "POST" and path == "/api/v1/api-tokens":
                return self._issue_workspace_api_token(environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/api-tokens/") and path.endswith("/revoke"):
                token_id = path.removesuffix("/revoke").rsplit("/", 1)[-1]
                return self._revoke_workspace_api_token(token_id, environ, capture_start_response)
            if method == "POST" and path == "/api/v1/projects":
                return self._create_project(environ, capture_start_response)
            if method == "GET" and path == "/api/v1/projects":
                return self._list_projects(environ, capture_start_response)
            if method == "GET" and path.startswith("/api/v1/projects/"):
                project_id = path.rsplit("/", 1)[-1]
                return self._get_project(project_id, environ, capture_start_response)
            if method == "POST" and path == "/api/v1/studies":
                return self._create_study(environ, capture_start_response)
            if method == "GET" and path == "/api/v1/studies":
                return self._list_studies(environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/studies/") and path.endswith("/governed-redaction"):
                study_id = path.removesuffix("/governed-redaction").rsplit("/", 1)[-1]
                return self._update_study_governed_redaction(study_id, environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/studies/") and path.endswith("/governed-review-assignment"):
                study_id = path.removesuffix("/governed-review-assignment").rsplit("/", 1)[-1]
                return self._update_study_governed_review_assignment(study_id, environ, capture_start_response)
            if method == "GET" and path.startswith("/api/v1/studies/") and path.endswith("/activity"):
                study_id = path.removesuffix("/activity").rsplit("/", 1)[-1]
                return self._get_study_activity(study_id, environ, capture_start_response)
            if method == "GET" and path.startswith("/api/v1/studies/") and path.endswith("/frontline"):
                study_id = path.removesuffix("/frontline").rsplit("/", 1)[-1]
                return self._get_frontline_study(study_id, environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/studies/") and path.endswith("/frontline-plan-proposals"):
                study_id = path.removesuffix("/frontline-plan-proposals").rsplit("/", 1)[-1]
                return self._create_frontline_plan_proposal(study_id, environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/studies/") and path.endswith("/frontline-plan-revisions"):
                study_id = path.removesuffix("/frontline-plan-revisions").rsplit("/", 1)[-1]
                return self._confirm_frontline_plan_revision(study_id, environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/studies/") and path.endswith("/frontline-runs"):
                study_id = path.removesuffix("/frontline-runs").rsplit("/", 1)[-1]
                return self._start_frontline_research_run(study_id, environ, capture_start_response)
            if method == "GET" and path.startswith("/api/v1/studies/"):
                study_id = path.rsplit("/", 1)[-1]
                return self._get_study(study_id, environ, capture_start_response)
            if method == "POST" and path == "/api/v1/study-reports":
                return self._create_study_report(environ, capture_start_response)
            if method == "GET" and path == "/api/v1/study-reports":
                return self._list_study_reports(environ, capture_start_response)
            if method == "GET" and path.startswith("/api/v1/study-reports/"):
                study_report_id = path.rsplit("/", 1)[-1]
                return self._get_study_report(study_report_id, environ, capture_start_response)
            if method == "POST" and path == "/api/v1/evidence-views":
                return self._create_evidence_view(environ, capture_start_response)
            if method == "GET" and path == "/api/v1/evidence-views":
                return self._list_evidence_views(environ, capture_start_response)
            if method == "GET" and path.startswith("/api/v1/evidence-views/"):
                evidence_view_id = path.rsplit("/", 1)[-1]
                return self._get_evidence_view(evidence_view_id, environ, capture_start_response)
            if method == "POST" and path == "/api/v1/decision-logs":
                return self._create_decision_log(environ, capture_start_response)
            if method == "GET" and path == "/api/v1/decision-logs":
                return self._list_decision_logs(environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/decision-logs/") and path.endswith("/comments"):
                decision_log_id = path.removesuffix("/comments").rsplit("/", 1)[-1]
                return self._create_decision_comment(decision_log_id, environ, capture_start_response)
            if method == "GET" and path.startswith("/api/v1/decision-logs/") and path.endswith("/comments"):
                decision_log_id = path.removesuffix("/comments").rsplit("/", 1)[-1]
                return self._list_decision_comments(decision_log_id, environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/decision-logs/") and path.endswith("/review-assignment"):
                decision_log_id = path.removesuffix("/review-assignment").rsplit("/", 1)[-1]
                return self._update_decision_review_assignment(decision_log_id, environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/decision-logs/") and path.endswith("/review-status"):
                decision_log_id = path.removesuffix("/review-status").rsplit("/", 1)[-1]
                return self._update_decision_review_status(decision_log_id, environ, capture_start_response)
            if method == "GET" and path.startswith("/api/v1/decision-logs/"):
                decision_log_id = path.rsplit("/", 1)[-1]
                return self._get_decision_log(decision_log_id, environ, capture_start_response)
            if method == "POST" and path == "/api/v1/export-bundles":
                return self._create_export_bundle(environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/export-bundles/") and path.endswith("/mvp-promotion-request"):
                export_bundle_id = path.removesuffix("/mvp-promotion-request").rsplit("/", 1)[-1]
                return self._request_export_bundle_mvp_promotion(export_bundle_id, environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/export-bundles/") and path.endswith("/mvp-promotion-review"):
                export_bundle_id = path.removesuffix("/mvp-promotion-review").rsplit("/", 1)[-1]
                return self._review_export_bundle_mvp_promotion(export_bundle_id, environ, capture_start_response)
            if method == "GET" and path == "/api/v1/export-bundles":
                return self._list_export_bundles(environ, capture_start_response)
            if method == "GET" and path.startswith("/api/v1/export-bundles/"):
                export_bundle_id = path.rsplit("/", 1)[-1]
                return self._get_export_bundle(export_bundle_id, environ, capture_start_response)
            if method == "POST" and path == "/api/v1/share-bundles":
                return self._create_share_bundle(environ, capture_start_response)
            if method == "GET" and path == "/api/v1/share-bundles":
                return self._list_share_bundles(environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/share-bundles/") and path.endswith("/mvp-release-review-request"):
                share_bundle_id = path.removesuffix("/mvp-release-review-request").rsplit("/", 1)[-1]
                return self._request_share_bundle_mvp_release_review(share_bundle_id, environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/share-bundles/") and path.endswith("/mvp-release-review"):
                share_bundle_id = path.removesuffix("/mvp-release-review").rsplit("/", 1)[-1]
                return self._review_share_bundle_mvp_release_review(share_bundle_id, environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/share-bundles/") and path.endswith("/revoke"):
                share_bundle_id = path.removesuffix("/revoke").rsplit("/", 1)[-1]
                return self._revoke_share_bundle(share_bundle_id, environ, capture_start_response)
            if method == "GET" and path.startswith("/api/v1/share-bundles/"):
                share_bundle_id = path.rsplit("/", 1)[-1]
                return self._get_share_bundle(share_bundle_id, environ, capture_start_response)
            if method == "GET" and path == "/api/v1/support-diagnostics":
                return self._get_support_diagnostics(environ, capture_start_response)
            if method == "POST" and path == "/api/v1/support-snapshots":
                return self._create_support_snapshot(environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/support-snapshots/") and path.endswith("/handoff"):
                support_snapshot_id = path.removesuffix("/handoff").rsplit("/", 1)[-1]
                return self._update_support_snapshot_handoff(support_snapshot_id, environ, capture_start_response)
            if method == "GET" and path == "/api/v1/support-snapshots":
                return self._list_support_snapshots(environ, capture_start_response)
            if method == "GET" and path.startswith("/api/v1/support-snapshots/"):
                support_snapshot_id = path.rsplit("/", 1)[-1]
                return self._get_support_snapshot(support_snapshot_id, environ, capture_start_response)
            if method == "POST" and path == "/api/v1/validation-jobs":
                return self._submit_job(environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/validation-jobs/") and path.endswith("/cancel"):
                job_id = path.removesuffix("/cancel").rsplit("/", 1)[-1]
                return self._cancel_job(job_id, environ, capture_start_response)
            if method == "POST" and path.startswith("/api/v1/validation-jobs/") and path.endswith("/retry"):
                job_id = path.removesuffix("/retry").rsplit("/", 1)[-1]
                return self._retry_job(job_id, environ, capture_start_response)
            if method == "GET" and path == "/api/v1/validation-jobs":
                return self._list_jobs(environ, capture_start_response)
            if method == "GET" and path.startswith("/api/v1/validation-jobs/"):
                job_id = path.rsplit("/", 1)[-1]
                return self._get_job(job_id, environ, capture_start_response)
            if method == "GET" and path == "/api/v1/evidence-query":
                return self._query_evidence(environ, capture_start_response)
            return _json_response(capture_start_response, "404 Not Found", {"error": "not_found", "path": path})
        except AuthenticationError as exc:
            return _json_response(capture_start_response, "401 Unauthorized", {"error": "unauthorized", "message": str(exc)})
        except AuthorizationError as exc:
            return _json_response(capture_start_response, "403 Forbidden", {"error": "forbidden", "message": str(exc)})
        except ShareUnavailableError as exc:
            return _json_response(capture_start_response, "410 Gone", {"error": "gone", "message": str(exc)})
        except FileNotFoundError as exc:
            return _json_response(capture_start_response, "404 Not Found", {"error": "not_found", "message": str(exc)})
        except ValueError as exc:
            return _json_response(capture_start_response, "400 Bad Request", {"error": "bad_request", "message": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive fallback
            return _json_response(capture_start_response, "500 Internal Server Error", {"error": "internal_error", "message": str(exc)})
        finally:
            self._emit_request_log(
                environ,
                response_status=response_status,
                duration_ms=(time.perf_counter() - started_at) * 1000,
            )

    def _emit_request_log(
        self,
        environ: dict[str, Any],
        *,
        response_status: str,
        duration_ms: float,
    ) -> None:
        if not self.deployment_profile.structured_logs:
            return
        payload = {
            "event": "saas_api.request",
            "method": str(environ.get("REQUEST_METHOD", "GET")).upper(),
            "path": str(environ.get("PATH_INFO", "")),
            "query_string_present": bool(str(environ.get("QUERY_STRING", "")).strip()),
            "auth_kind": self._request_auth_kind(environ),
            "status": response_status.split(" ", 1)[0],
            "duration_ms": round(duration_ms, 2),
            "deployment_env": self.deployment_profile.deployment_env,
        }
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

    def _request_auth_kind(self, environ: dict[str, Any]) -> str:
        authorization = str(environ.get("HTTP_AUTHORIZATION", "")).strip()
        if authorization.startswith("Bearer "):
            return "bearer_token"
        if _cookie_value(environ, HOSTED_BROWSER_SESSION_COOKIE):
            return "browser_session"
        return "public"

    def _runtime_operations(self) -> dict[str, Any]:
        return self.runtime.describe_runtime_operations()

    def _service_metadata_payload(self) -> dict[str, Any]:
        runtime_ops = self._runtime_operations()
        return {
            "contract_version": "saas-api-service-metadata/v0-draft",
            "service": {
                "name": "ai_validation_swarm_saas_api",
                "transport": "wsgi",
                "default_api_prefix": "/api/v1",
            },
            "deployment_profile": self.deployment_profile.to_dict(),
            "auth": {
                "supported_modes": ["api_token", "browser_session"],
                "hosted_route_query_token_bootstrap": self.deployment_profile.allow_query_token_bootstrap,
            },
            "operations": {
                "health_endpoint": "/api/v1/health",
                "readiness_endpoint": "/api/v1/ready",
                "service_metadata_endpoint": "/api/v1/service-metadata",
                "contract_manifest_endpoint": "/api/v1/contract-manifest",
                "workspace_operations_summary_endpoint": "/api/v1/operations/summary",
                "workspace_public_launch_readiness_endpoint": "/api/v1/public-launch-readiness",
                "runtime_contract_version": runtime_ops["contract_version"],
            },
            "typed_contracts": {
                "frontline_studio": "/studio",
                "session": "/api/v1/session",
                "workspace_shell": "/api/v1/workspace-shell",
                "validation_jobs": "/api/v1/validation-jobs",
                "evidence_query": "/api/v1/evidence-query",
                "projects": "/api/v1/projects",
                "studies": "/api/v1/studies",
                "study_reports": "/api/v1/study-reports",
                "evidence_views": "/api/v1/evidence-views",
                "decision_logs": "/api/v1/decision-logs",
                "export_bundles": "/api/v1/export-bundles",
                "share_bundles": "/api/v1/share-bundles",
                "support_diagnostics": "/api/v1/support-diagnostics",
                "contract_manifest": "/api/v1/contract-manifest",
                "workspace_operations_summary": "/api/v1/operations/summary",
                "workspace_public_launch_readiness": "/api/v1/public-launch-readiness",
            },
            "synthetic_boundary": (
                "Service metadata and operations endpoints describe transport and deployment boundaries only; "
                "they do not widen the synthetic-evidence claim boundary."
            ),
        }

    def _contract_manifest_payload(self) -> dict[str, Any]:
        return {
            "contract_version": "saas-api-contract-manifest/v0-draft",
            "service": {
                "name": "ai_validation_swarm_saas_api",
                "transport": "wsgi",
                "default_api_prefix": "/api/v1",
            },
            "endpoints": [
                {
                    "id": "health",
                    "path": "/api/v1/health",
                    "methods": ["GET"],
                    "auth": "public",
                    "response_contract_version": "saas-api-health/v0-draft",
                    "response_root": ["status", "runtime"],
                },
                {
                    "id": "readiness",
                    "path": "/api/v1/ready",
                    "methods": ["GET"],
                    "auth": "public",
                    "response_contract_version": "saas-api-readiness/v0-draft",
                    "response_root": ["status", "checks", "runtime", "deployment_profile"],
                },
                {
                    "id": "service_metadata",
                    "path": "/api/v1/service-metadata",
                    "methods": ["GET"],
                    "auth": "public",
                    "response_contract_version": "saas-api-service-metadata/v0-draft",
                    "response_root": ["service", "operations", "typed_contracts"],
                },
                {
                    "id": "contract_manifest",
                    "path": "/api/v1/contract-manifest",
                    "methods": ["GET"],
                    "auth": "public",
                    "response_contract_version": "saas-api-contract-manifest/v0-draft",
                    "response_root": ["service", "endpoints"],
                },
                {
                    "id": "workspace_operations_summary",
                    "path": "/api/v1/operations/summary",
                    "methods": ["GET"],
                    "auth": "api_token_or_browser_session",
                    "response_contract_version": "workspace-operations-summary/v0-draft",
                    "response_root": ["worker_runtime", "evidence_review", "decision_review", "distribution", "audit", "public_launch_readiness"],
                },
                {
                    "id": "workspace_public_launch_readiness",
                    "path": "/api/v1/public-launch-readiness",
                    "methods": ["GET"],
                    "auth": "api_token_or_browser_session",
                    "response_contract_version": "workspace-public-launch-readiness/v0-draft",
                    "response_root": ["overall_status", "study_governance", "benchmark_disclosure", "distribution_readiness", "customer_claim_boundary"],
                },
                {
                    "id": "session",
                    "path": "/api/v1/session",
                    "methods": ["GET"],
                    "auth": "api_token_or_browser_session",
                    "response_root_key": "session",
                },
                {
                    "id": "persona_library",
                    "path": "/api/v1/persona-library",
                    "methods": ["GET"],
                    "auth": "api_token_or_browser_session",
                    "query_params": [
                        {"name": "panel_type", "type": "string", "required": False},
                        {"name": "sample_size", "type": "integer", "required": False},
                        {"name": "random_seed", "type": "integer", "required": False},
                        {"name": "selected_persona_id", "type": "array[string]", "required": False},
                    ],
                    "response_root_key": "persona_library",
                },
                {
                    "id": "workspace_shell",
                    "path": "/api/v1/workspace-shell",
                    "methods": ["GET"],
                    "auth": "api_token_or_browser_session",
                    "query_params": [
                        {"name": "project_id", "type": "string", "required": False},
                        {"name": "study_id", "type": "string", "required": False},
                        {"name": "job_id", "type": "string", "required": False},
                        {"name": "query_text", "type": "string", "required": False},
                        {"name": "active_family", "type": "string", "required": False},
                        {"name": "sort_by", "type": "string", "required": False},
                        {"name": "selected_result_id", "type": "string", "required": False},
                        {"name": "selected_replay_step_id", "type": "string", "required": False},
                        {"name": "selected_comparison_run_id", "type": "string", "required": False},
                    ],
                    "response_root_key": "snapshot",
                },
                {
                    "id": "validation_jobs",
                    "path": "/api/v1/validation-jobs",
                    "methods": ["GET", "POST"],
                    "auth": "api_token_or_browser_session",
                    "request_body": {
                        "brief_path": "string",
                        "persona_dir": "string",
                        "panel_spec": "object",
                        "provider_name": "string",
                        "priority": "string",
                        "max_retries": "integer",
                        "idempotency_key": "string",
                        "run_root": "string",
                        "metadata": "object",
                    },
                    "response_root_key": {"GET": "jobs", "POST": "job"},
                },
                {
                    "id": "evidence_query",
                    "path": "/api/v1/evidence-query",
                    "methods": ["GET"],
                    "auth": "api_token_or_browser_session",
                    "query_params": [
                        {"name": "run_id", "type": "string", "required": False},
                        {"name": "job_id", "type": "string", "required": False},
                        {"name": "query_text", "type": "string", "required": False},
                        {"name": "active_family", "type": "string", "required": False},
                        {"name": "sort_by", "type": "string", "required": False},
                        {"name": "selected_result_id", "type": "string", "required": False},
                        {"name": "selected_replay_step_id", "type": "string", "required": False},
                        {"name": "selected_comparison_run_id", "type": "string", "required": False},
                    ],
                    "response_root_key": "query",
                    "linked_contract_specs": ["specs/workspace_evidence_query_contract.md"],
                },
                {
                    "id": "projects",
                    "path": "/api/v1/projects",
                    "methods": ["GET", "POST"],
                    "auth": "api_token_or_browser_session",
                    "request_body": {
                        "name": "string",
                        "description": "string",
                        "slug": "string",
                        "metadata": "object",
                    },
                    "response_root_key": {"GET": "projects", "POST": "project"},
                },
                {
                    "id": "studies",
                    "path": "/api/v1/studies",
                    "methods": ["GET", "POST"],
                    "auth": "api_token_or_browser_session",
                    "query_params": [
                        {"name": "project_id", "type": "string", "required": False},
                    ],
                    "request_body": {
                        "project_id": "string",
                        "title": "string",
                        "research_intent": "string",
                        "desired_output": "string",
                        "first_task": "string",
                        "artifact_refs": "array[string]",
                        "draft_plan": "object",
                        "metadata": "object",
                    },
                    "response_root_key": {"GET": "studies", "POST": "study"},
                },
                {
                    "id": "frontline_study",
                    "path": "/api/v1/studies/{study_id}/frontline",
                    "methods": ["GET"],
                    "auth": "api_token_or_browser_session",
                    "response_root_key": "frontline_study",
                    "linked_contract_specs": ["specs/frontline_research_studio_terminology_and_data_model.md"],
                },
                {
                    "id": "frontline_plan_proposals",
                    "path": "/api/v1/studies/{study_id}/frontline-plan-proposals",
                    "methods": ["POST"],
                    "auth": "api_token_or_browser_session",
                    "request_body": {
                        "user_message": "string",
                        "target_persona": "string",
                        "target_audience": "object",
                        "persona_panel": "object",
                        "artifacts": "array[string]",
                        "study_purpose": "string",
                        "mode": "string",
                        "moderator_questions": "array[string]",
                        "metadata": "object",
                    },
                    "response_root": ["study", "plan_proposal"],
                    "linked_contract_specs": ["specs/frontline_research_studio_terminology_and_data_model.md"],
                },
                {
                    "id": "frontline_plan_revisions",
                    "path": "/api/v1/studies/{study_id}/frontline-plan-revisions",
                    "methods": ["POST"],
                    "auth": "api_token_or_browser_session",
                    "request_body": {
                        "plan_proposal_id": "string",
                        "confirmation_note": "string",
                        "metadata": "object",
                    },
                    "response_root": ["study", "plan_revision"],
                    "linked_contract_specs": ["specs/frontline_research_studio_terminology_and_data_model.md"],
                },
                {
                    "id": "frontline_runs",
                    "path": "/api/v1/studies/{study_id}/frontline-runs",
                    "methods": ["POST"],
                    "auth": "api_token_or_browser_session",
                    "request_body": {
                        "metadata": "object",
                    },
                    "response_root": ["study", "job", "research_run"],
                    "linked_contract_specs": ["specs/frontline_research_studio_terminology_and_data_model.md"],
                },
                {
                    "id": "study_reports",
                    "path": "/api/v1/study-reports",
                    "methods": ["GET", "POST"],
                    "auth": "api_token_or_browser_session",
                    "query_params": [
                        {"name": "study_id", "type": "string", "required": False},
                    ],
                    "request_body": {
                        "study_id": "string",
                        "included_run_ids": "array[string]",
                        "title": "string",
                        "status": "string",
                        "metadata": "object",
                    },
                    "response_root_key": {"GET": "study_reports", "POST": "study_report"},
                    "linked_contract_specs": ["specs/frontline_research_studio_terminology_and_data_model.md"],
                },
                {
                    "id": "study_governed_review_assignment",
                    "path": "/api/v1/studies/{study_id}/governed-review-assignment",
                    "methods": ["POST"],
                    "auth": "api_token_or_browser_session",
                    "request_body": {
                        "assignee_user_ids": "array[string]",
                        "status": "string",
                        "note": "string",
                        "metadata": "object",
                    },
                    "response_root_key": "study",
                },
                {
                    "id": "study_governed_redaction",
                    "path": "/api/v1/studies/{study_id}/governed-redaction",
                    "methods": ["POST"],
                    "auth": "api_token_or_browser_session",
                    "request_body": {
                        "status": "string",
                        "redaction_rules": "array[object]",
                        "note": "string",
                        "metadata": "object",
                    },
                    "response_root_key": "study",
                },
                {
                    "id": "evidence_views",
                    "path": "/api/v1/evidence-views",
                    "methods": ["GET", "POST"],
                    "auth": "api_token_or_browser_session",
                    "request_body": {
                        "study_id": "string",
                        "job_id": "string",
                        "title": "string",
                        "note": "string",
                        "query_text": "string",
                        "active_family": "string",
                        "sort_by": "string",
                        "selected_result_id": "string",
                        "selected_replay_step_id": "string",
                        "selected_comparison_run_id": "string",
                        "metadata": "object",
                    },
                    "response_root_key": {"GET": "evidence_views", "POST": "evidence_view"},
                },
                {
                    "id": "decision_logs",
                    "path": "/api/v1/decision-logs",
                    "methods": ["GET", "POST"],
                    "auth": "api_token_or_browser_session",
                    "request_body": {
                        "study_id": "string",
                        "title": "string",
                        "decision_summary": "string",
                        "rationale": "string",
                        "job_id": "string",
                        "evidence_view_id": "string",
                        "selected_result_id": "string",
                        "selected_comparison_run_id": "string",
                        "metadata": "object",
                    },
                    "response_root_key": {"GET": "decision_logs", "POST": "decision_log"},
                },
                {
                    "id": "decision_review_assignment",
                    "path": "/api/v1/decision-logs/{decision_log_id}/review-assignment",
                    "methods": ["POST"],
                    "auth": "api_token_or_browser_session",
                    "request_body": {
                        "assignee_user_ids": "array[string]",
                        "note": "string",
                        "metadata": "object",
                    },
                    "response_root_key": "decision_log",
                },
                {
                    "id": "export_bundles",
                    "path": "/api/v1/export-bundles",
                    "methods": ["GET", "POST"],
                    "auth": "api_token_or_browser_session",
                    "request_body": {
                        "study_id": "string",
                        "job_id": "string",
                        "title": "string",
                        "export_format": "string",
                        "artifact_ids": "array[string]",
                        "metadata": "object",
                    },
                    "response_root_key": {"GET": "export_bundles", "POST": "export_bundle"},
                },
                {
                    "id": "share_bundles",
                    "path": "/api/v1/share-bundles",
                    "methods": ["GET", "POST"],
                    "auth": "api_token_or_browser_session",
                    "query_params": [
                        {"name": "study_id", "type": "string", "required": False},
                        {"name": "export_bundle_id", "type": "string", "required": False},
                    ],
                    "request_body": {
                        "export_bundle_id": "string",
                        "title": "string",
                        "expires_in_days": "integer",
                        "partner_name": "string",
                        "partner_team_label": "string",
                        "partner_use_case": "string",
                        "support_channel": "string",
                        "review_window_days": "integer",
                        "metadata": "object",
                    },
                    "response_root_key": {"GET": "share_bundles", "POST": "share_bundle"},
                },
                {
                    "id": "support_diagnostics",
                    "path": "/api/v1/support-diagnostics",
                    "methods": ["GET"],
                    "auth": "api_token_or_browser_session",
                    "query_params": [
                        {"name": "job_id", "type": "string", "required": False},
                        {"name": "study_id", "type": "string", "required": False},
                    ],
                    "response_root_key": "support",
                },
                {
                    "id": "support_snapshot_handoff",
                    "path": "/api/v1/support-snapshots/{support_snapshot_id}/handoff",
                    "methods": ["POST"],
                    "auth": "api_token_or_browser_session",
                    "request_body": {
                        "status": "string",
                        "assigned_user_id": "string",
                        "note": "string",
                        "metadata": "object",
                    },
                    "response_root_key": "support_snapshot",
                },
            ],
            "synthetic_boundary": (
                "This manifest describes the API boundary and stable wrapper contracts. It does not widen the "
                "synthetic-evidence claim boundary."
            ),
        }

    def _readiness_payload(self) -> tuple[str, dict[str, Any]]:
        runtime_ops = self._runtime_operations()
        env_name = self.deployment_profile.deployment_env.strip().lower() or "local"
        checks: list[dict[str, Any]] = []

        def add_check(name: str, *, required: bool, passed: bool, note: str) -> None:
            checks.append(
                {
                    "name": name,
                    "required": required,
                    "status": "pass" if passed else ("fail" if required else "warn"),
                    "note": note,
                }
            )

        add_check(
            "runtime_root_access",
            required=True,
            passed=bool(runtime_ops["runtime_root_exists"]) and bool(runtime_ops["runtime_root_writable"]),
            note="Runtime root must exist and remain writable for workspace artifacts and metadata.",
        )
        add_check(
            "runtime_db_access",
            required=True,
            passed=bool(runtime_ops["runtime_db_exists"]),
            note="Runtime SQLite metadata store must be reachable before hosted wrappers or workers can operate.",
        )

        public_base_required = env_name in {"preview", "staging", "production"}
        add_check(
            "public_base_url",
            required=public_base_required,
            passed=bool(self.deployment_profile.public_base_url.strip()),
            note="Hosted environments should publish one canonical base URL for wrappers, links, and support handoff.",
        )
        hardened_secret_required = env_name in {"staging", "production"}
        secret_hardened = self.deployment_profile.secret_source.strip().lower() not in {"", "local_dev", "inline_demo_token"}
        add_check(
            "secret_source",
            required=hardened_secret_required,
            passed=secret_hardened,
            note="Production-like deployments should source auth and operator secrets from a managed environment rather than local-dev defaults.",
        )
        bootstrap_locked_down = not (
            env_name in {"staging", "production"} and self.deployment_profile.allow_query_token_bootstrap
        )
        add_check(
            "query_token_bootstrap_policy",
            required=env_name in {"staging", "production"},
            passed=bootstrap_locked_down,
            note="Query-string token bootstrap is acceptable for local MVP work but should be disabled in staging/production.",
        )
        backup_required = env_name in {"preview", "staging", "production"}
        backup_configured = self.deployment_profile.expected_backup_mode.strip().lower() not in {"", "unspecified"}
        add_check(
            "backup_expectation",
            required=backup_required,
            passed=backup_configured,
            note="Production-like deployments should declare the expected metadata/artifact backup mode explicitly.",
        )

        required_checks = [check for check in checks if check["required"]]
        ready = all(check["status"] == "pass" for check in required_checks)
        http_status = "200 OK" if ready else "503 Service Unavailable"
        payload = {
            "contract_version": "saas-api-readiness/v0-draft",
            "status": "ready" if ready else "not_ready",
            "deployment_env": env_name,
            "checks": checks,
            "runtime": runtime_ops,
            "deployment_profile": self.deployment_profile.to_dict(),
            "synthetic_boundary": runtime_ops["synthetic_boundary"],
        }
        return http_status, payload

    def _get_health(self, start_response: Callable[..., Any]) -> list[bytes]:
        runtime_ops = self._runtime_operations()
        return _json_response(
            start_response,
            "200 OK",
            {
                "contract_version": "saas-api-health/v0-draft",
                "status": "healthy",
                "service": "ai_validation_swarm_saas_api",
                "deployment_env": self.deployment_profile.deployment_env,
                "runtime": {
                    "runtime_schema_version": runtime_ops["runtime_schema_version"],
                    "workspace_count": runtime_ops["workspace_count"],
                    "job_counts": runtime_ops["job_counts"],
                },
                "synthetic_boundary": runtime_ops["synthetic_boundary"],
            },
        )

    def _get_readiness(self, start_response: Callable[..., Any]) -> list[bytes]:
        http_status, payload = self._readiness_payload()
        return _json_response(start_response, http_status, payload)

    def _get_service_metadata(self, start_response: Callable[..., Any]) -> list[bytes]:
        return _json_response(start_response, "200 OK", self._service_metadata_payload())

    def _get_contract_manifest(self, start_response: Callable[..., Any]) -> list[bytes]:
        return _json_response(start_response, "200 OK", self._contract_manifest_payload())

    def _get_workspace_operations_summary(
        self,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        operations = self.runtime.describe_workspace_operations_summary(auth)
        return _json_response(start_response, "200 OK", {"operations": operations})

    def _get_workspace_public_launch_readiness(
        self,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        launch_readiness = self.runtime.describe_workspace_public_launch_readiness(auth)
        return _json_response(start_response, "200 OK", {"launch_readiness": launch_readiness})

    def _get_static_asset(self, relative_path: str, start_response: Callable[..., Any]) -> list[bytes]:
        normalized = unquote(relative_path).lstrip("/").replace("\\", "/")
        if not normalized:
            raise FileNotFoundError("Static asset not found.")
        allowed_prefixes = ("demo/", "specs/", "frontend/")
        if not any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in allowed_prefixes):
            raise FileNotFoundError("Static asset not found.")
        asset_path = (self.repo_root / normalized).resolve()
        if not asset_path.is_file():
            raise FileNotFoundError(f"Static asset not found: {normalized}")
        try:
            asset_path.relative_to(self.repo_root)
        except ValueError as exc:
            raise FileNotFoundError("Static asset not found.") from exc
        return _file_response(start_response, "200 OK", asset_path)

    def _is_hosted_workspace_route(self, path: str) -> bool:
        normalized = path.rstrip("/")
        if normalized in ("/app/workspace", "/app/new-study"):
            return True
        prefixes = (
            "/app/projects/",
            "/app/studies/",
            "/app/evidence-views/",
            "/app/decision-logs/",
            "/app/export-bundles/",
            "/app/share-bundles/",
            "/app/support-snapshots/",
            "/app/jobs/",
        )
        return any(normalized.startswith(prefix) for prefix in prefixes)

    def _hosted_workspace_route_context(self, path: str) -> dict[str, str]:
        normalized = path.rstrip("/")
        context: dict[str, str] = {"route_path": normalized or "/app/workspace"}
        if normalized == "/app/workspace":
            context["route_kind"] = "workspace"
            return context
        if normalized == "/app/new-study":
            context["route_kind"] = "new_study"
            return context
        route_specs = (
            ("/app/projects/", "project", "project_id"),
            ("/app/studies/", "study", "study_id"),
            ("/app/evidence-views/", "evidence_view", "evidence_view_id"),
            ("/app/decision-logs/", "decision_log", "decision_log_id"),
            ("/app/export-bundles/", "export_bundle", "export_bundle_id"),
            ("/app/share-bundles/", "share_bundle", "share_bundle_id"),
            ("/app/support-snapshots/", "support_snapshot", "support_snapshot_id"),
            ("/app/jobs/", "job", "job_id"),
        )
        for prefix, route_kind, field in route_specs:
            if normalized.startswith(prefix):
                identifier = normalized.removeprefix(prefix).strip("/")
                if not identifier:
                    raise FileNotFoundError("Hosted workspace route not found.")
                context["route_kind"] = route_kind
                context[field] = identifier
                return context
        raise FileNotFoundError("Hosted workspace route not found.")

    def _render_framework_hosted_workspace_shell(self, route_context: dict[str, str]) -> str:
        html_path = self.repo_root / "frontend" / "workspace_shell_app" / "dist" / "index.html"
        html = html_path.read_text(encoding="utf-8")
        html = html.replace(
            'src="/assets/',
            'src="/app-static/frontend/workspace_shell_app/dist/assets/',
        ).replace(
            'href="/assets/',
            'href="/app-static/frontend/workspace_shell_app/dist/assets/',
        )
        injection = (
            f"<script>window.__WORKSPACE_ROUTE_CONTEXT__ = "
            f"{json.dumps(route_context, ensure_ascii=False)};</script>\n    <script type=\"module\""
        )
        return html.replace("<script type=\"module\"", injection, 1)

    def _render_hosted_workspace_shell(self, route_context: dict[str, str]) -> str:
        framework_html_path = self.repo_root / "frontend" / "workspace_shell_app" / "dist" / "index.html"
        if framework_html_path.is_file():
            return self._render_framework_hosted_workspace_shell(route_context)
        html_path = self.repo_root / "demo" / "workspace_ui_moss_stage15" / "index.html"
        html = html_path.read_text(encoding="utf-8")
        replacements = {
            "./workspace_shell_stage15_app.mjs": "/app-static/demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs",
            "../workspace_ui_design_system/": "/app-static/demo/workspace_ui_design_system/",
            "../workspace_ui_moss_stage14/": "/app-static/demo/workspace_ui_moss_stage14/",
            "../workspace_ui_shared/": "/app-static/demo/workspace_ui_shared/",
            "../../specs/": "/app-static/specs/",
        }
        for source, target in replacements.items():
            html = html.replace(source, target)
        injection = (
            f"<script>window.__WORKSPACE_ROUTE_CONTEXT__ = "
            f"{json.dumps(route_context, ensure_ascii=False)};</script>\n  <script type=\"module\">"
        )
        return html.replace("<script type=\"module\">", injection, 1)

    def _get_hosted_workspace_shell(
        self,
        environ: dict[str, Any],
        path: str,
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=True)
        bootstrap_token = str(query.get("token", [""])[0]).strip()
        if bootstrap_token:
            if not self.deployment_profile.allow_query_token_bootstrap:
                raise AuthorizationError("Query token bootstrap is disabled for this deployment profile.")
            auth = self.runtime.authenticate(bootstrap_token)
            browser_session = self.runtime.issue_browser_session(auth, source="hosted_route_query_token")
            next_query = _remove_query_keys(str(environ.get("QUERY_STRING", "")), "token")
            location = path if not next_query else f"{path}?{next_query}"
            return _redirect_response(
                start_response,
                location,
                extra_headers=_session_cookie_headers(
                    str(browser_session["session_id"]),
                    environ=environ,
                ),
            )
        self._auth(environ)
        route_context = self._hosted_workspace_route_context(path)
        html = self._render_hosted_workspace_shell(route_context)
        return _html_response(start_response, "200 OK", html)

    def _is_hosted_frontline_route(self, path: str) -> bool:
        normalized = path.rstrip("/") or "/studio"
        return normalized == "/studio" or normalized.startswith("/studio/")

    def _hosted_frontline_route_context(self, path: str) -> dict[str, str]:
        normalized = path.rstrip("/") or "/studio"
        parts = [unquote(part) for part in normalized.split("/") if part]
        if parts == ["studio"]:
            return {"route_path": normalized, "route_kind": "workspace"}
        if not parts or parts[0] != "studio":
            raise FileNotFoundError("Hosted frontline route not found.")

        context: dict[str, str] = {"route_path": normalized, "route_kind": "workspace"}
        if len(parts) == 2 and parts[1] == "projects":
            context["route_kind"] = "projects"
            return context
        if len(parts) == 3 and parts[1] == "projects" and parts[2]:
            context.update({"route_kind": "project", "project_id": parts[2]})
            return context
        if len(parts) == 3 and parts[1] == "studies" and parts[2] == "new":
            context["route_kind"] = "new_study"
            return context
        if len(parts) >= 3 and parts[1] == "studies" and parts[2]:
            study_id = parts[2]
            context["study_id"] = study_id
            if len(parts) == 3:
                context["route_kind"] = "study"
                return context
            if len(parts) == 4 and parts[3] == "setup":
                context["route_kind"] = "study_setup"
                return context
            if len(parts) == 4 and parts[3] == "runs":
                context["route_kind"] = "study_runs"
                return context
            if len(parts) == 5 and parts[3] == "runs" and parts[4]:
                context.update({"route_kind": "run", "run_id": parts[4]})
                return context
            if len(parts) == 4 and parts[3] == "evidence":
                context["route_kind"] = "study_evidence"
                return context
            if len(parts) == 5 and parts[3] == "evidence-views" and parts[4]:
                context.update({"route_kind": "evidence_view", "evidence_view_id": parts[4]})
                return context
        if len(parts) == 5 and parts[1] == "studies" and parts[2] and parts[3] == "reports" and parts[4]:
            context.update({"route_kind": "study_report", "study_report_id": parts[4]})
            return context
        if len(parts) == 5 and parts[1] == "studies" and parts[2] and parts[3] == "decisions" and parts[4]:
            context.update({"route_kind": "decision", "decision_log_id": parts[4]})
            return context
        if len(parts) == 2 and parts[1] == "share":
            context["route_kind"] = "share_collection"
            return context
        if len(parts) == 3 and parts[1] == "share" and parts[2]:
            context.update({"route_kind": "share", "share_bundle_id": parts[2]})
            return context

        raise FileNotFoundError("Hosted frontline route not found.")

    def _render_framework_hosted_frontline_studio(self, route_context: dict[str, str]) -> str:
        html_path = self.repo_root / "frontend" / "frontline_research_studio" / "dist" / "index.html"
        if not html_path.is_file():
            raise FileNotFoundError("Frontline Research Studio build is not available.")
        html = html_path.read_text(encoding="utf-8")
        html = html.replace(
            'src="/assets/',
            'src="/app-static/frontend/frontline_research_studio/dist/assets/',
        ).replace(
            'href="/assets/',
            'href="/app-static/frontend/frontline_research_studio/dist/assets/',
        )
        injection = (
            f"<script>window.__FRONTLINE_ROUTE_CONTEXT__ = "
            f"{json.dumps(route_context, ensure_ascii=False)};</script>\n    <script type=\"module\""
        )
        return html.replace("<script type=\"module\"", injection, 1)

    def _get_hosted_frontline_studio(
        self,
        environ: dict[str, Any],
        path: str,
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=True)
        bootstrap_token = str(query.get("token", [""])[0]).strip()
        if bootstrap_token:
            if not self.deployment_profile.allow_query_token_bootstrap:
                raise AuthorizationError("Query token bootstrap is disabled for this deployment profile.")
            auth = self.runtime.authenticate(bootstrap_token)
            browser_session = self.runtime.issue_browser_session(auth, source="frontline_route_query_token")
            next_query = _remove_query_keys(str(environ.get("QUERY_STRING", "")), "token")
            location = path if not next_query else f"{path}?{next_query}"
            return _redirect_response(
                start_response,
                location,
                extra_headers=_session_cookie_headers(
                    str(browser_session["session_id"]),
                    environ=environ,
                ),
            )
        self._auth(environ)
        route_context = self._hosted_frontline_route_context(path)
        html = self._render_framework_hosted_frontline_studio(route_context)
        return _html_response(start_response, "200 OK", html)

    def _auth(self, environ: dict[str, Any]):
        authorization = str(environ.get("HTTP_AUTHORIZATION", "")).strip()
        if authorization.startswith("Bearer "):
            return self.runtime.authenticate(authorization.split(" ", 1)[1])
        browser_session_id = _cookie_value(environ, HOSTED_BROWSER_SESSION_COOKIE)
        if browser_session_id:
            return self.runtime.authenticate_browser_session(browser_session_id)
        raise AuthenticationError("Missing workspace authentication.")

    def _submit_job(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        panel_payload = payload.get("panel_spec")
        if not isinstance(panel_payload, dict):
            raise ValueError("Field 'panel_spec' must be an object.")
        request = ValidationJobRequest(
            brief_path=str(payload.get("brief_path", "")),
            persona_dir=str(payload.get("persona_dir", "")),
            panel_spec=PanelSpec(**panel_payload),
            provider_name=str(payload.get("provider_name", "mock")),
            priority=str(payload.get("priority", "normal")),
            max_retries=int(payload.get("max_retries", 1)),
            idempotency_key=str(payload.get("idempotency_key", "")),
            run_root=str(payload.get("run_root", "runs")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        job = self.runtime.submit_validation_job(auth, request)
        return _json_response(start_response, "202 Accepted", {"job": job})

    def _create_project(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        project = self.runtime.create_workspace_project(
            auth,
            name=str(payload.get("name", "")),
            description=str(payload.get("description", "")),
            slug=str(payload.get("slug", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "201 Created", {"project": project})

    def _list_projects(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        projects = self.runtime.list_workspace_projects(auth)
        return _json_response(start_response, "200 OK", {"projects": projects})

    def _get_project(self, project_id: str, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        project = self.runtime.get_workspace_project(auth, project_id)
        return _json_response(start_response, "200 OK", {"project": project})

    def _create_study(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        artifact_refs = payload.get("artifact_refs", [])
        if artifact_refs is not None and not isinstance(artifact_refs, list):
            raise ValueError("Field 'artifact_refs' must be a list.")
        draft_plan = payload.get("draft_plan", {})
        if draft_plan is not None and not isinstance(draft_plan, dict):
            raise ValueError("Field 'draft_plan' must be an object.")
        study = self.runtime.create_workspace_study(
            auth,
            project_id=str(payload.get("project_id", "")),
            title=str(payload.get("title", "")),
            research_intent=str(payload.get("research_intent", "")),
            desired_output=str(payload.get("desired_output", "")),
            first_task=str(payload.get("first_task", "")),
            artifact_refs=[str(item) for item in artifact_refs] if isinstance(artifact_refs, list) else [],
            draft_plan=dict(draft_plan or {}),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "201 Created", {"study": study})

    def _list_studies(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)
        project_id = str(query.get("project_id", [""])[0])
        studies = self.runtime.list_workspace_studies(auth, project_id=project_id)
        return _json_response(start_response, "200 OK", {"studies": studies})

    def _get_study(self, study_id: str, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        study = self.runtime.get_workspace_study(auth, study_id)
        return _json_response(start_response, "200 OK", {"study": study})

    def _get_frontline_study(
        self,
        study_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        frontline = self.runtime.describe_frontline_study(auth, study_id=study_id)
        return _json_response(start_response, "200 OK", {"frontline_study": frontline})

    def _create_frontline_plan_proposal(
        self,
        study_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        artifacts = payload.get("artifacts", payload.get("artifact_refs", []))
        if artifacts is not None and not isinstance(artifacts, list):
            raise ValueError("Field 'artifacts' must be a list.")
        moderator_questions = payload.get("moderator_questions", [])
        if moderator_questions is not None and not isinstance(moderator_questions, list):
            raise ValueError("Field 'moderator_questions' must be a list.")
        target_audience = payload.get("target_audience", {})
        if target_audience is not None and not isinstance(target_audience, dict):
            raise ValueError("Field 'target_audience' must be an object.")
        persona_panel = payload.get("persona_panel", {})
        if persona_panel is not None and not isinstance(persona_panel, dict):
            raise ValueError("Field 'persona_panel' must be an object.")
        result = self.runtime.create_frontline_plan_proposal(
            auth,
            study_id=study_id,
            user_message=str(payload.get("user_message", "")),
            target_persona=str(payload.get("target_persona", "")),
            target_audience=dict(target_audience or {}),
            persona_panel=dict(persona_panel or {}),
            artifacts=[str(item) for item in artifacts] if isinstance(artifacts, list) else [],
            study_purpose=str(payload.get("study_purpose", "")),
            mode=str(payload.get("mode", "")),
            moderator_questions=[str(item) for item in moderator_questions]
            if isinstance(moderator_questions, list)
            else [],
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "201 Created", result)

    def _confirm_frontline_plan_revision(
        self,
        study_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        result = self.runtime.confirm_frontline_plan_revision(
            auth,
            study_id=study_id,
            plan_proposal_id=str(payload.get("plan_proposal_id", "")),
            confirmation_note=str(payload.get("confirmation_note", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "201 Created", result)

    def _start_frontline_research_run(
        self,
        study_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        result = self.runtime.start_frontline_research_run(
            auth,
            study_id=study_id,
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "202 Accepted", result)

    def _create_study_report(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        included_run_ids = payload.get("included_run_ids", [])
        if included_run_ids is not None and not isinstance(included_run_ids, list):
            raise ValueError("Field 'included_run_ids' must be a list.")
        study_report = self.runtime.create_workspace_study_report(
            auth,
            study_id=str(payload.get("study_id", "")),
            included_run_ids=[str(item) for item in included_run_ids] if isinstance(included_run_ids, list) else [],
            title=str(payload.get("title", "")),
            status=str(payload.get("status", "ready_for_review")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "201 Created", {"study_report": study_report})

    def _list_study_reports(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)
        study_id = str(query.get("study_id", [""])[0])
        study_reports = self.runtime.list_workspace_study_reports(auth, study_id=study_id)
        return _json_response(start_response, "200 OK", {"study_reports": study_reports})

    def _get_study_report(
        self,
        study_report_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        study_report = self.runtime.get_workspace_study_report(auth, study_report_id)
        return _json_response(start_response, "200 OK", {"study_report": study_report})

    def _update_study_governed_review_assignment(
        self,
        study_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        study = self.runtime.update_workspace_study_governed_review_assignment(
            auth,
            study_id=study_id,
            assignee_user_ids=[str(item) for item in payload.get("assignee_user_ids", [])]
            if isinstance(payload.get("assignee_user_ids"), list)
            else [],
            status=str(payload.get("status", "assigned")),
            note=str(payload.get("note", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "200 OK", {"study": study})

    def _update_study_governed_redaction(
        self,
        study_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        study = self.runtime.update_workspace_study_governed_redaction(
            auth,
            study_id=study_id,
            status=str(payload.get("status", "")),
            redaction_rules=[
                dict(item) for item in payload.get("redaction_rules", [])
                if isinstance(item, dict)
            ] if isinstance(payload.get("redaction_rules"), list) else [],
            note=str(payload.get("note", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "200 OK", {"study": study})

    def _get_study_activity(
        self,
        study_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)
        limit = int(str(query.get("limit", ["20"])[0] or "20"))
        activity = self.runtime.list_workspace_study_activity(
            auth,
            study_id=study_id,
            limit=limit,
        )
        return _json_response(start_response, "200 OK", {"study_activity": activity})

    def _create_evidence_view(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        evidence_view = self.runtime.create_workspace_evidence_view(
            auth,
            study_id=str(payload.get("study_id", "")),
            job_id=str(payload.get("job_id", "")),
            title=str(payload.get("title", "")),
            note=str(payload.get("note", "")),
            query_text=str(payload.get("query_text", "")),
            active_family=str(payload.get("active_family", "all")),
            sort_by=str(payload.get("sort_by", "relevance")),
            selected_result_id=str(payload.get("selected_result_id", "")),
            selected_replay_step_id=str(payload.get("selected_replay_step_id", "")),
            selected_comparison_run_id=str(payload.get("selected_comparison_run_id", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "201 Created", {"evidence_view": evidence_view})

    def _list_evidence_views(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)
        study_id = str(query.get("study_id", [""])[0])
        job_id = str(query.get("job_id", [""])[0])
        evidence_views = self.runtime.list_workspace_evidence_views(auth, study_id=study_id, job_id=job_id)
        return _json_response(start_response, "200 OK", {"evidence_views": evidence_views})

    def _get_evidence_view(
        self,
        evidence_view_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        evidence_view = self.runtime.get_workspace_evidence_view(auth, evidence_view_id)
        return _json_response(start_response, "200 OK", {"evidence_view": evidence_view})

    def _create_decision_log(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        decision_log = self.runtime.create_workspace_decision_log(
            auth,
            study_id=str(payload.get("study_id", "")),
            title=str(payload.get("title", "")),
            decision_summary=str(payload.get("decision_summary", "")),
            rationale=str(payload.get("rationale", "")),
            job_id=str(payload.get("job_id", "")),
            evidence_view_id=str(payload.get("evidence_view_id", "")),
            selected_result_id=str(payload.get("selected_result_id", "")),
            selected_comparison_run_id=str(payload.get("selected_comparison_run_id", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "201 Created", {"decision_log": decision_log})

    def _list_decision_logs(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)
        study_id = str(query.get("study_id", [""])[0])
        job_id = str(query.get("job_id", [""])[0])
        evidence_view_id = str(query.get("evidence_view_id", [""])[0])
        decision_logs = self.runtime.list_workspace_decision_logs(
            auth,
            study_id=study_id,
            job_id=job_id,
            evidence_view_id=evidence_view_id,
        )
        return _json_response(start_response, "200 OK", {"decision_logs": decision_logs})

    def _get_decision_log(
        self,
        decision_log_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        decision_log = self.runtime.get_workspace_decision_log(auth, decision_log_id)
        decision_comments = self.runtime.list_workspace_decision_comments(auth, decision_log_id=decision_log_id)
        return _json_response(
            start_response,
            "200 OK",
            {"decision_log": decision_log, "decision_comments": decision_comments},
        )

    def _create_decision_comment(
        self,
        decision_log_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        decision_comment = self.runtime.create_workspace_decision_comment(
            auth,
            decision_log_id=decision_log_id,
            body=str(payload.get("body", "")),
            parent_comment_id=str(payload.get("parent_comment_id", "")),
            anchor_kind=str(payload.get("anchor_kind", "general")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        decision_log = self.runtime.get_workspace_decision_log(auth, decision_log_id)
        return _json_response(
            start_response,
            "201 Created",
            {"decision_comment": decision_comment, "decision_log": decision_log},
        )

    def _list_decision_comments(
        self,
        decision_log_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        decision_comments = self.runtime.list_workspace_decision_comments(auth, decision_log_id=decision_log_id)
        decision_log = self.runtime.get_workspace_decision_log(auth, decision_log_id)
        return _json_response(
            start_response,
            "200 OK",
            {"decision_comments": decision_comments, "decision_log": decision_log},
        )

    def _update_decision_review_status(
        self,
        decision_log_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        decision_log = self.runtime.update_workspace_decision_review_status(
            auth,
            decision_log_id=decision_log_id,
            review_status=str(payload.get("review_status", "")),
            note=str(payload.get("note", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "200 OK", {"decision_log": decision_log})

    def _update_decision_review_assignment(
        self,
        decision_log_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        assignee_user_ids = payload.get("assignee_user_ids", [])
        if assignee_user_ids is not None and not isinstance(assignee_user_ids, list):
            raise ValueError("Field 'assignee_user_ids' must be a list.")
        decision_log = self.runtime.update_workspace_decision_review_assignment(
            auth,
            decision_log_id=decision_log_id,
            assignee_user_ids=[str(item) for item in assignee_user_ids] if isinstance(assignee_user_ids, list) else [],
            note=str(payload.get("note", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "200 OK", {"decision_log": decision_log})

    def _create_export_bundle(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        artifact_ids = payload.get("artifact_ids", [])
        if artifact_ids is not None and not isinstance(artifact_ids, list):
            raise ValueError("Field 'artifact_ids' must be a list.")
        export_bundle = self.runtime.create_workspace_export_bundle(
            auth,
            study_id=str(payload.get("study_id", "")),
            job_id=str(payload.get("job_id", "")),
            title=str(payload.get("title", "")),
            export_format=str(payload.get("export_format", "bundle_json")),
            artifact_ids=[str(item) for item in artifact_ids] if isinstance(artifact_ids, list) else [],
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "201 Created", {"export_bundle": export_bundle})

    def _list_export_bundles(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)
        study_id = str(query.get("study_id", [""])[0])
        job_id = str(query.get("job_id", [""])[0])
        export_bundles = self.runtime.list_workspace_export_bundles(auth, study_id=study_id, job_id=job_id)
        return _json_response(start_response, "200 OK", {"export_bundles": export_bundles})

    def _get_export_bundle(
        self,
        export_bundle_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        export_bundle = self.runtime.get_workspace_export_bundle(auth, export_bundle_id)
        return _json_response(start_response, "200 OK", {"export_bundle": export_bundle})

    def _request_export_bundle_mvp_promotion(
        self,
        export_bundle_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        export_bundle = self.runtime.request_workspace_export_bundle_mvp_promotion(
            auth,
            export_bundle_id,
            note=str(payload.get("note", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "200 OK", {"export_bundle": export_bundle})

    def _review_export_bundle_mvp_promotion(
        self,
        export_bundle_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        export_bundle = self.runtime.review_workspace_export_bundle_mvp_promotion(
            auth,
            export_bundle_id,
            decision=str(payload.get("decision", "")),
            note=str(payload.get("note", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "200 OK", {"export_bundle": export_bundle})

    def _create_share_bundle(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        expires_in_days = payload.get("expires_in_days")
        if expires_in_days is not None:
            expires_in_days = int(expires_in_days)
        share_bundle = self.runtime.create_workspace_share_bundle(
            auth,
            export_bundle_id=str(payload.get("export_bundle_id", "")),
            title=str(payload.get("title", "")),
            expires_in_days=expires_in_days,
            partner_name=str(payload.get("partner_name", "")),
            partner_team_label=str(payload.get("partner_team_label", "")),
            partner_use_case=str(payload.get("partner_use_case", "")),
            support_channel=str(payload.get("support_channel", "")),
            review_window_days=payload.get("review_window_days"),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "201 Created", {"share_bundle": share_bundle})

    def _list_share_bundles(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)
        study_id = str(query.get("study_id", [""])[0])
        export_bundle_id = str(query.get("export_bundle_id", [""])[0])
        share_bundles = self.runtime.list_workspace_share_bundles(
            auth,
            study_id=study_id,
            export_bundle_id=export_bundle_id,
        )
        return _json_response(start_response, "200 OK", {"share_bundles": share_bundles})

    def _get_share_bundle(
        self,
        share_bundle_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        share_bundle = self.runtime.get_workspace_share_bundle(auth, share_bundle_id)
        return _json_response(start_response, "200 OK", {"share_bundle": share_bundle})

    def _request_share_bundle_mvp_release_review(
        self,
        share_bundle_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        share_bundle = self.runtime.request_workspace_share_bundle_mvp_release_review(
            auth,
            share_bundle_id,
            note=str(payload.get("note", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "200 OK", {"share_bundle": share_bundle})

    def _review_share_bundle_mvp_release_review(
        self,
        share_bundle_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        share_bundle = self.runtime.review_workspace_share_bundle_mvp_release_review(
            auth,
            share_bundle_id,
            decision=str(payload.get("decision", "")),
            note=str(payload.get("note", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "200 OK", {"share_bundle": share_bundle})

    def _revoke_share_bundle(
        self,
        share_bundle_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        share_bundle = self.runtime.revoke_workspace_share_bundle(auth, share_bundle_id)
        return _json_response(start_response, "200 OK", {"share_bundle": share_bundle})

    def _get_public_share_bundle(self, share_key: str, start_response: Callable[..., Any]) -> list[bytes]:
        share_bundle = self.runtime.get_public_share_bundle(share_key)
        return _json_response(start_response, "200 OK", {"share_bundle": share_bundle})

    def _get_support_diagnostics(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)
        job_id = str(query.get("job_id", [""])[0])
        study_id = str(query.get("study_id", [""])[0])
        diagnostics = self.runtime.describe_workspace_support(auth, job_id=job_id, study_id=study_id)
        return _json_response(start_response, "200 OK", {"support": diagnostics})

    def _create_support_snapshot(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        snapshot = self.runtime.create_workspace_support_snapshot(
            auth,
            job_id=str(payload.get("job_id", "")),
            title=str(payload.get("title", "")),
            notes=str(payload.get("notes", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "201 Created", {"support_snapshot": snapshot})

    def _update_support_snapshot_handoff(
        self,
        support_snapshot_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        snapshot = self.runtime.update_workspace_support_snapshot_handoff(
            auth,
            support_snapshot_id=support_snapshot_id,
            status=str(payload.get("status", "")),
            assigned_user_id=str(payload.get("assigned_user_id", "")),
            note=str(payload.get("note", "")),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
        )
        return _json_response(start_response, "200 OK", {"support_snapshot": snapshot})

    def _list_support_snapshots(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)
        study_id = str(query.get("study_id", [""])[0])
        job_id = str(query.get("job_id", [""])[0])
        snapshots = self.runtime.list_workspace_support_snapshots(auth, study_id=study_id, job_id=job_id)
        return _json_response(start_response, "200 OK", {"support_snapshots": snapshots})

    def _get_support_snapshot(
        self,
        support_snapshot_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        snapshot = self.runtime.get_workspace_support_snapshot(auth, support_snapshot_id)
        return _json_response(start_response, "200 OK", {"support_snapshot": snapshot})

    def _get_session(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        session = self.runtime.describe_workspace_session(auth)
        return _json_response(start_response, "200 OK", {"session": session})

    def _get_persona_library(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)
        panel_type = str(query.get("panel_type", ["mainstream"])[0])
        sample_size_raw = str(query.get("sample_size", ["3"])[0])
        random_seed_raw = str(query.get("random_seed", ["17"])[0])
        selected_persona_ids = [
            value.strip()
            for raw_value in query.get("selected_persona_id", [])
            for value in str(raw_value).split(",")
            if value.strip()
        ]
        try:
            sample_size = int(sample_size_raw)
        except ValueError:
            sample_size = 3
        try:
            random_seed = int(random_seed_raw)
        except ValueError:
            random_seed = 17
        persona_library = self.runtime.describe_frontline_persona_library(
            auth,
            panel_type=panel_type,
            sample_size=sample_size,
            random_seed=random_seed,
            selected_persona_ids=selected_persona_ids,
        )
        return _json_response(start_response, "200 OK", {"persona_library": persona_library})

    def _logout_session(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        browser_session_id = _cookie_value(environ, HOSTED_BROWSER_SESSION_COOKIE)
        if browser_session_id:
            auth = self._auth(environ)
            self.runtime.revoke_browser_session(auth, browser_session_id, reason="user_logout")
        return _empty_response(
            start_response,
            extra_headers=_session_cookie_headers("", environ=environ, clear=True),
        )

    def _get_workspace_settings(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        settings = self.runtime.describe_workspace_settings(auth)
        return _json_response(start_response, "200 OK", {"workspace_settings": settings})

    def _get_workspace_audit_events(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)

        def first(name: str, default: str = "") -> str:
            values = query.get(name)
            if not values:
                return default
            return str(values[0])

        audit_history = self.runtime.list_workspace_audit_events(
            auth,
            target_type=first("target_type"),
            action_prefix=first("action_prefix"),
            limit=int(first("limit", "20")),
        )
        return _json_response(start_response, "200 OK", {"audit_history": audit_history})

    def _upsert_workspace_member(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        member = self.runtime.upsert_workspace_member(
            auth,
            user_id=str(payload.get("user_id", "")),
            role=str(payload.get("role", "")),
        )
        settings = self.runtime.describe_workspace_settings(auth)
        return _json_response(start_response, "201 Created", {"member": member, "workspace_settings": settings})

    def _update_workspace_billing(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        billing = self.runtime.update_workspace_billing(
            auth,
            plan_tier=str(payload.get("plan_tier", "")),
            billing_status=str(payload.get("billing_status", "")),
            seat_count=payload.get("seat_count"),
            renewal_at=payload.get("renewal_at"),
            daily_runs=payload.get("daily_runs"),
            max_concurrent_jobs=payload.get("max_concurrent_jobs"),
            artifact_retention_days=payload.get("artifact_retention_days"),
            note=str(payload.get("note", "")),
        )
        settings = self.runtime.describe_workspace_settings(auth)
        return _json_response(start_response, "200 OK", {"billing": billing, "workspace_settings": settings})

    def _issue_workspace_api_token(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        api_token = self.runtime.issue_workspace_api_token(auth, user_id=str(payload.get("user_id", "")))
        settings = self.runtime.describe_workspace_settings(auth)
        return _json_response(start_response, "201 Created", {"api_token": api_token, "workspace_settings": settings})

    def _revoke_workspace_api_token(
        self,
        token_id: str,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        auth = self._auth(environ)
        api_token = self.runtime.revoke_workspace_api_token(auth, token_id)
        settings = self.runtime.describe_workspace_settings(auth)
        return _json_response(start_response, "200 OK", {"api_token": api_token, "workspace_settings": settings})

    def _list_jobs(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        jobs = self.runtime.list_workspace_jobs(auth)
        return _json_response(start_response, "200 OK", {"jobs": jobs})

    def _cancel_job(self, job_id: str, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        payload = _parse_json_body(environ)
        job = self.runtime.cancel_validation_job(
            auth,
            job_id,
            reason=str(payload.get("reason", "")),
        )
        return _json_response(start_response, "200 OK", {"job": job})

    def _retry_job(self, job_id: str, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        job = self.runtime.retry_validation_job(auth, job_id)
        return _json_response(
            start_response,
            "202 Accepted",
            {
                "job": job,
                "source_job_id": job_id,
            },
        )

    def _get_workspace_shell(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)

        def first(name: str, default: str = "") -> str:
            values = query.get(name)
            if not values:
                return default
            return str(values[0])

        snapshot = self.runtime.describe_workspace_shell(
            auth,
            project_id=first("project_id"),
            study_id=first("study_id"),
            job_id=first("job_id"),
            query_text=first("query_text"),
            active_family=first("active_family", "all"),
            sort_by=first("sort_by", "relevance"),
            selected_result_id=first("selected_result_id"),
            selected_replay_step_id=first("selected_replay_step_id"),
            selected_comparison_run_id=first("selected_comparison_run_id"),
        )
        return _json_response(start_response, "200 OK", {"snapshot": snapshot})

    def _get_job(self, job_id: str, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        job = self.runtime.get_validation_job(auth, job_id)
        return _json_response(start_response, "200 OK", {"job": job})

    def _query_evidence(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=False)

        def first(name: str, default: str = "") -> str:
            values = query.get(name)
            if not values:
                return default
            return str(values[0])

        evidence_query = self.runtime.query_workspace_evidence(
            auth,
            run_id=first("run_id"),
            job_id=first("job_id"),
            query_text=first("query_text"),
            active_family=first("active_family", "all"),
            sort_by=first("sort_by", "relevance"),
            selected_result_id=first("selected_result_id"),
            selected_replay_step_id=first("selected_replay_step_id"),
            selected_comparison_run_id=first("selected_comparison_run_id"),
        )
        return _json_response(start_response, "200 OK", {"query": evidence_query})


def serve_saas_api(
    runtime_root: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8011,
    deployment_env: str = "local",
    public_base_url: str = "",
    secret_source: str = "local_dev",
    expected_backup_mode: str = "local_filesystem",
    allow_query_token_bootstrap: bool = True,
    structured_logs: bool = False,
) -> None:
    app = SaasApiApplication(
        SaasRuntime(runtime_root),
        deployment_profile=SaasApiDeploymentProfile(
            deployment_env=deployment_env,
            public_base_url=public_base_url,
            secret_source=secret_source,
            expected_backup_mode=expected_backup_mode,
            allow_query_token_bootstrap=allow_query_token_bootstrap,
            structured_logs=structured_logs,
        ),
    )
    with make_server(host, port, app) as server:
        print(f"SaaS API serving on http://{host}:{port}")
        server.serve_forever()
