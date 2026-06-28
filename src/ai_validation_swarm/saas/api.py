from __future__ import annotations

import json
import mimetypes
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Callable
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
    def __init__(self, runtime: SaasRuntime) -> None:
        self.runtime = runtime
        self.repo_root = Path(__file__).resolve().parents[3]

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        try:
            method = str(environ.get("REQUEST_METHOD", "GET")).upper()
            path = str(environ.get("PATH_INFO", ""))
            if method == "OPTIONS" and (
                path.startswith("/api/v1/validation-jobs")
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
                or path.startswith("/api/v1/evidence-views")
                or path.startswith("/api/v1/decision-logs")
                or path == "/api/v1/session"
                or path == "/api/v1/session/logout"
                or path == "/api/v1/workspace-shell"
            ):
                return _empty_response(start_response)
            if method == "GET" and path.startswith("/app-static/"):
                return self._get_static_asset(path.removeprefix("/app-static/"), start_response)
            if method == "GET" and self._is_hosted_workspace_route(path):
                return self._get_hosted_workspace_shell(environ, path, start_response)
            if method == "GET" and path.startswith("/public/v1/share-bundles/"):
                share_key = path.rsplit("/", 1)[-1]
                return self._get_public_share_bundle(share_key, start_response)
            if method == "GET" and path == "/api/v1/session":
                return self._get_session(environ, start_response)
            if method == "POST" and path == "/api/v1/session/logout":
                return self._logout_session(environ, start_response)
            if method == "GET" and path == "/api/v1/workspace-settings":
                return self._get_workspace_settings(environ, start_response)
            if method == "GET" and path == "/api/v1/audit-events":
                return self._get_workspace_audit_events(environ, start_response)
            if method == "POST" and path == "/api/v1/workspace-billing":
                return self._update_workspace_billing(environ, start_response)
            if method == "GET" and path == "/api/v1/workspace-shell":
                return self._get_workspace_shell(environ, start_response)
            if method == "POST" and path == "/api/v1/workspace-members":
                return self._upsert_workspace_member(environ, start_response)
            if method == "POST" and path == "/api/v1/api-tokens":
                return self._issue_workspace_api_token(environ, start_response)
            if method == "POST" and path.startswith("/api/v1/api-tokens/") and path.endswith("/revoke"):
                token_id = path.removesuffix("/revoke").rsplit("/", 1)[-1]
                return self._revoke_workspace_api_token(token_id, environ, start_response)
            if method == "POST" and path == "/api/v1/projects":
                return self._create_project(environ, start_response)
            if method == "GET" and path == "/api/v1/projects":
                return self._list_projects(environ, start_response)
            if method == "GET" and path.startswith("/api/v1/projects/"):
                project_id = path.rsplit("/", 1)[-1]
                return self._get_project(project_id, environ, start_response)
            if method == "POST" and path == "/api/v1/studies":
                return self._create_study(environ, start_response)
            if method == "GET" and path == "/api/v1/studies":
                return self._list_studies(environ, start_response)
            if method == "GET" and path.startswith("/api/v1/studies/") and path.endswith("/activity"):
                study_id = path.removesuffix("/activity").rsplit("/", 1)[-1]
                return self._get_study_activity(study_id, environ, start_response)
            if method == "GET" and path.startswith("/api/v1/studies/"):
                study_id = path.rsplit("/", 1)[-1]
                return self._get_study(study_id, environ, start_response)
            if method == "POST" and path == "/api/v1/evidence-views":
                return self._create_evidence_view(environ, start_response)
            if method == "GET" and path == "/api/v1/evidence-views":
                return self._list_evidence_views(environ, start_response)
            if method == "GET" and path.startswith("/api/v1/evidence-views/"):
                evidence_view_id = path.rsplit("/", 1)[-1]
                return self._get_evidence_view(evidence_view_id, environ, start_response)
            if method == "POST" and path == "/api/v1/decision-logs":
                return self._create_decision_log(environ, start_response)
            if method == "GET" and path == "/api/v1/decision-logs":
                return self._list_decision_logs(environ, start_response)
            if method == "POST" and path.startswith("/api/v1/decision-logs/") and path.endswith("/comments"):
                decision_log_id = path.removesuffix("/comments").rsplit("/", 1)[-1]
                return self._create_decision_comment(decision_log_id, environ, start_response)
            if method == "GET" and path.startswith("/api/v1/decision-logs/") and path.endswith("/comments"):
                decision_log_id = path.removesuffix("/comments").rsplit("/", 1)[-1]
                return self._list_decision_comments(decision_log_id, environ, start_response)
            if method == "POST" and path.startswith("/api/v1/decision-logs/") and path.endswith("/review-status"):
                decision_log_id = path.removesuffix("/review-status").rsplit("/", 1)[-1]
                return self._update_decision_review_status(decision_log_id, environ, start_response)
            if method == "GET" and path.startswith("/api/v1/decision-logs/"):
                decision_log_id = path.rsplit("/", 1)[-1]
                return self._get_decision_log(decision_log_id, environ, start_response)
            if method == "POST" and path == "/api/v1/export-bundles":
                return self._create_export_bundle(environ, start_response)
            if method == "GET" and path == "/api/v1/export-bundles":
                return self._list_export_bundles(environ, start_response)
            if method == "GET" and path.startswith("/api/v1/export-bundles/"):
                export_bundle_id = path.rsplit("/", 1)[-1]
                return self._get_export_bundle(export_bundle_id, environ, start_response)
            if method == "POST" and path == "/api/v1/share-bundles":
                return self._create_share_bundle(environ, start_response)
            if method == "GET" and path == "/api/v1/share-bundles":
                return self._list_share_bundles(environ, start_response)
            if method == "POST" and path.startswith("/api/v1/share-bundles/") and path.endswith("/revoke"):
                share_bundle_id = path.removesuffix("/revoke").rsplit("/", 1)[-1]
                return self._revoke_share_bundle(share_bundle_id, environ, start_response)
            if method == "GET" and path.startswith("/api/v1/share-bundles/"):
                share_bundle_id = path.rsplit("/", 1)[-1]
                return self._get_share_bundle(share_bundle_id, environ, start_response)
            if method == "GET" and path == "/api/v1/support-diagnostics":
                return self._get_support_diagnostics(environ, start_response)
            if method == "POST" and path == "/api/v1/support-snapshots":
                return self._create_support_snapshot(environ, start_response)
            if method == "GET" and path == "/api/v1/support-snapshots":
                return self._list_support_snapshots(environ, start_response)
            if method == "GET" and path.startswith("/api/v1/support-snapshots/"):
                support_snapshot_id = path.rsplit("/", 1)[-1]
                return self._get_support_snapshot(support_snapshot_id, environ, start_response)
            if method == "POST" and path == "/api/v1/validation-jobs":
                return self._submit_job(environ, start_response)
            if method == "POST" and path.startswith("/api/v1/validation-jobs/") and path.endswith("/cancel"):
                job_id = path.removesuffix("/cancel").rsplit("/", 1)[-1]
                return self._cancel_job(job_id, environ, start_response)
            if method == "POST" and path.startswith("/api/v1/validation-jobs/") and path.endswith("/retry"):
                job_id = path.removesuffix("/retry").rsplit("/", 1)[-1]
                return self._retry_job(job_id, environ, start_response)
            if method == "GET" and path == "/api/v1/validation-jobs":
                return self._list_jobs(environ, start_response)
            if method == "GET" and path.startswith("/api/v1/validation-jobs/"):
                job_id = path.rsplit("/", 1)[-1]
                return self._get_job(job_id, environ, start_response)
            if method == "GET" and path == "/api/v1/evidence-query":
                return self._query_evidence(environ, start_response)
            return _json_response(start_response, "404 Not Found", {"error": "not_found", "path": path})
        except AuthenticationError as exc:
            return _json_response(start_response, "401 Unauthorized", {"error": "unauthorized", "message": str(exc)})
        except AuthorizationError as exc:
            return _json_response(start_response, "403 Forbidden", {"error": "forbidden", "message": str(exc)})
        except ShareUnavailableError as exc:
            return _json_response(start_response, "410 Gone", {"error": "gone", "message": str(exc)})
        except FileNotFoundError as exc:
            return _json_response(start_response, "404 Not Found", {"error": "not_found", "message": str(exc)})
        except ValueError as exc:
            return _json_response(start_response, "400 Bad Request", {"error": "bad_request", "message": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive fallback
            return _json_response(start_response, "500 Internal Server Error", {"error": "internal_error", "message": str(exc)})

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
        diagnostics = self.runtime.describe_workspace_support(auth, job_id=job_id)
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


def serve_saas_api(runtime_root: Path, *, host: str = "127.0.0.1", port: int = 8011) -> None:
    app = SaasApiApplication(SaasRuntime(runtime_root))
    with make_server(host, port, app) as server:
        print(f"SaaS API serving on http://{host}:{port}")
        server.serve_forever()
