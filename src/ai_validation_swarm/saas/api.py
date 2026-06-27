from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from ai_validation_swarm.domain.models import PanelSpec
from ai_validation_swarm.saas.runtime import AuthenticationError, AuthorizationError, SaasRuntime, ValidationJobRequest


def _cors_headers() -> list[tuple[str, str]]:
    return [
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Headers", "Authorization, Content-Type"),
        ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
    ]


def _json_response(start_response: Callable[..., Any], status: str, payload: dict[str, Any]) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            *_cors_headers(),
        ],
    )
    return [body]


def _empty_response(start_response: Callable[..., Any], status: str = "204 No Content") -> list[bytes]:
    start_response(
        status,
        [
            ("Content-Length", "0"),
            *_cors_headers(),
        ],
    )
    return []


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


class SaasApiApplication:
    def __init__(self, runtime: SaasRuntime) -> None:
        self.runtime = runtime

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        try:
            method = str(environ.get("REQUEST_METHOD", "GET")).upper()
            path = str(environ.get("PATH_INFO", ""))
            if method == "OPTIONS" and (
                path.startswith("/api/v1/validation-jobs") or path.startswith("/api/v1/evidence-query") or path == "/api/v1/session" or path == "/api/v1/workspace-shell"
            ):
                return _empty_response(start_response)
            if method == "GET" and path == "/api/v1/session":
                return self._get_session(environ, start_response)
            if method == "GET" and path == "/api/v1/workspace-shell":
                return self._get_workspace_shell(environ, start_response)
            if method == "POST" and path == "/api/v1/validation-jobs":
                return self._submit_job(environ, start_response)
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
        except FileNotFoundError as exc:
            return _json_response(start_response, "404 Not Found", {"error": "not_found", "message": str(exc)})
        except ValueError as exc:
            return _json_response(start_response, "400 Bad Request", {"error": "bad_request", "message": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive fallback
            return _json_response(start_response, "500 Internal Server Error", {"error": "internal_error", "message": str(exc)})

    def _auth(self, environ: dict[str, Any]):
        authorization = str(environ.get("HTTP_AUTHORIZATION", "")).strip()
        if not authorization.startswith("Bearer "):
            raise AuthenticationError("Missing Bearer token.")
        return self.runtime.authenticate(authorization.split(" ", 1)[1])

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

    def _get_session(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        session = self.runtime.describe_workspace_session(auth)
        return _json_response(start_response, "200 OK", {"session": session})

    def _list_jobs(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        auth = self._auth(environ)
        jobs = self.runtime.list_workspace_jobs(auth)
        return _json_response(start_response, "200 OK", {"jobs": jobs})

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
            job_id=first("job_id"),
            query_text=first("query_text"),
            active_family=first("active_family", "all"),
            sort_by=first("sort_by", "relevance"),
            selected_result_id=first("selected_result_id"),
            selected_replay_step_id=first("selected_replay_step_id"),
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
        )
        return _json_response(start_response, "200 OK", {"query": evidence_query})


def serve_saas_api(runtime_root: Path, *, host: str = "127.0.0.1", port: int = 8011) -> None:
    app = SaasApiApplication(SaasRuntime(runtime_root))
    with make_server(host, port, app) as server:
        print(f"SaaS API serving on http://{host}:{port}")
        server.serve_forever()
