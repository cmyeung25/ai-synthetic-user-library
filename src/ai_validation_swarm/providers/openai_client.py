from __future__ import annotations

import json
import os
import subprocess
import base64
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class OpenAIProviderError(RuntimeError):
    pass


@dataclass(slots=True)
class OpenAIProviderConfig:
    api_key: str
    model: str = "gpt-5.4"
    profile: str = "chatgpt-5.4-high"
    model_reasoning_effort: str = "high"
    api_base: str = "https://api.openai.com/v1"
    timeout_seconds: int = 120
    auth_source: str = "unknown"
    transport: str = "python_urllib"
    workspace_root: str = ""
    codex_auth_file: str = ""
    codex_home_mode: str = "global"
    codex_home_path: str = ""
    codex_ignore_user_config: bool = True
    codex_ignore_rules: bool = True
    codex_cli_path: str = ""
    codex_sdk_module_path: str = ""
    codex_cli_retries: int = 0
    codex_cli_retry_backoff_seconds: int = 5
    codex_cli_output_mode: str = "auto"


def _default_codex_home_path(auth_path: Path | None = None) -> Path:
    if auth_path is not None:
        resolved = Path(auth_path)
        if resolved.name.lower() == "auth.json":
            return resolved.parent
        return resolved
    home = os.getenv("USERPROFILE", "").strip() or os.getenv("HOME", "").strip()
    if home:
        return Path(home) / ".codex"
    return Path(".codex")


def _default_codex_auth_path() -> Path:
    return _default_codex_home_path() / "auth.json"


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _env_choice(name: str, default: str, allowed: set[str]) -> str:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    return normalized if normalized in allowed else default


def load_codex_access_token(auth_path: Path | None = None) -> str:
    path = auth_path or _default_codex_auth_path()
    if not path.exists():
        return ""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""

    if payload.get("auth_mode") != "chatgpt":
        return ""
    tokens = payload.get("tokens", {})
    if not isinstance(tokens, dict):
        return ""
    access_token = tokens.get("access_token", "")
    return access_token.strip() if isinstance(access_token, str) else ""


def decode_jwt_claims(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    padded = payload + "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        claims = json.loads(decoded)
    except Exception:
        return {}
    return claims if isinstance(claims, dict) else {}


def inspect_openai_auth(config: OpenAIProviderConfig) -> dict[str, Any]:
    claims = decode_jwt_claims(config.api_key)
    scopes = claims.get("scp", [])
    normalized_scopes = [scope for scope in scopes if isinstance(scope, str)] if isinstance(scopes, list) else []
    return {
        "auth_source": config.auth_source,
        "transport": config.transport,
        "model": config.model,
        "profile": config.profile,
        "model_reasoning_effort": config.model_reasoning_effort,
        "timeout_seconds": config.timeout_seconds,
        "codex_home_mode": config.codex_home_mode,
        "codex_home_path": config.codex_home_path,
        "codex_ignore_user_config": config.codex_ignore_user_config,
        "codex_ignore_rules": config.codex_ignore_rules,
        "codex_cli_retries": config.codex_cli_retries,
        "codex_cli_retry_backoff_seconds": config.codex_cli_retry_backoff_seconds,
        "codex_cli_output_mode": config.codex_cli_output_mode,
        "has_token": bool(config.api_key),
        "token_claim_keys": sorted(claims.keys()),
        "scopes": normalized_scopes,
        "has_api_responses_write_scope": "api.responses.write" in normalized_scopes,
        "expires_at_epoch": claims.get("exp"),
        "issued_at_epoch": claims.get("iat"),
        "subject": claims.get("sub"),
    }


def load_openai_provider_config(*, prefer_codex_auth: bool = False, force_transport: str | None = None) -> OpenAIProviderConfig:
    auth_source = ""
    codex_auth_file = ""
    api_key = ""
    auth_path_raw = os.getenv("AI_VALIDATION_CODEX_AUTH_FILE", "").strip()
    auth_path = Path(auth_path_raw) if auth_path_raw else None

    if prefer_codex_auth:
        api_key = load_codex_access_token(auth_path)
        if api_key:
            codex_auth_path = auth_path or _default_codex_auth_path()
            codex_auth_file = str(codex_auth_path)
            auth_source = f"codex_auth_file:{codex_auth_path}"
        else:
            api_key = os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("CODEX_API_KEY", "").strip()
            if api_key:
                auth_source = "fallback_api_key_env"
    else:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if api_key:
            auth_source = "openai_api_key_env"
        else:
            api_key = os.getenv("CODEX_API_KEY", "").strip()
            if api_key:
                auth_source = "codex_api_key_env"
            else:
                api_key = load_codex_access_token(auth_path)
                if api_key:
                    codex_auth_path = auth_path or _default_codex_auth_path()
                    codex_auth_file = str(codex_auth_path)
                    auth_source = f"codex_auth_file:{codex_auth_path}"

    if not api_key:
        raise OpenAIProviderError(
            "OpenAI credentials are missing. Set OPENAI_API_KEY, or provide a compatible CODEX_API_KEY, or sign in through Codex so C:\\Users\\user\\.codex\\auth.json exposes a ChatGPT access token."
        )

    default_transport = "node_https" if os.name == "nt" else "python_urllib"
    if auth_source.startswith("codex_auth_file:"):
        default_transport = "codex_cli"
    resolved_transport = force_transport or os.getenv("AI_VALIDATION_OPENAI_TRANSPORT", default_transport)
    codex_home_mode_default = "global" if resolved_transport == "codex_cli" else "local"
    codex_home_mode = os.getenv("AI_VALIDATION_CODEX_HOME_MODE", codex_home_mode_default).strip().lower() or codex_home_mode_default
    if codex_home_mode not in {"global", "local"}:
        codex_home_mode = codex_home_mode_default
    codex_home_path = os.getenv("AI_VALIDATION_CODEX_HOME", "").strip() or os.getenv("CODEX_HOME", "").strip()
    timeout_default = "240" if resolved_transport == "codex_cli" else "120"
    return OpenAIProviderConfig(
        api_key=api_key,
        model=os.getenv("AI_VALIDATION_OPENAI_MODEL", "gpt-5.4"),
        profile=os.getenv("AI_VALIDATION_OPENAI_PROFILE", "chatgpt-5.4-high"),
        model_reasoning_effort=os.getenv("AI_VALIDATION_OPENAI_REASONING_EFFORT", "high"),
        api_base=os.getenv("AI_VALIDATION_OPENAI_BASE_URL", "https://api.openai.com/v1"),
        timeout_seconds=int(os.getenv("AI_VALIDATION_OPENAI_TIMEOUT_SECONDS", timeout_default)),
        auth_source=auth_source or "unknown",
        transport=resolved_transport,
        workspace_root=os.getenv("AI_VALIDATION_WORKSPACE_ROOT", os.getcwd()),
        codex_auth_file=codex_auth_file,
        codex_home_mode=codex_home_mode,
        codex_home_path=codex_home_path,
        codex_ignore_user_config=_env_flag("AI_VALIDATION_CODEX_IGNORE_USER_CONFIG", resolved_transport == "codex_cli"),
        codex_ignore_rules=_env_flag("AI_VALIDATION_CODEX_IGNORE_RULES", resolved_transport == "codex_cli"),
        codex_cli_path=os.getenv("AI_VALIDATION_CODEX_CLI_PATH", "").strip(),
        codex_sdk_module_path=os.getenv("AI_VALIDATION_CODEX_SDK_MODULE", "").strip(),
        codex_cli_retries=int(os.getenv("AI_VALIDATION_CODEX_CLI_RETRIES", "2" if resolved_transport == "codex_cli" else "0")),
        codex_cli_retry_backoff_seconds=int(os.getenv("AI_VALIDATION_CODEX_CLI_RETRY_BACKOFF_SECONDS", "5")),
        codex_cli_output_mode=_env_choice(
            "AI_VALIDATION_CODEX_CLI_OUTPUT_MODE",
            "auto",
            {"auto", "direct", "wrapper"},
        ),
    )


def _build_local_codex_config(workspace_root: str, model: str, reasoning_effort: str) -> str:
    project_key = str(workspace_root or "").lower()
    escaped_root = str(workspace_root or "").replace("\\", "\\\\")
    return "\n".join(
        [
            f'model = "{model}"',
            f'model_reasoning_effort = "{reasoning_effort}"',
            'approval_policy = "never"',
            'sandbox_mode = "workspace-write"',
            "",
            "[windows]",
            'sandbox = "elevated"',
            "",
            f"[projects.'{project_key}']",
            'trust_level = "trusted"',
            "",
            "[sandbox_workspace_write]",
            "network_access = true",
            f"writable_roots = ['{escaped_root}']",
            "",
        ]
    )


def ensure_local_codex_home(config: OpenAIProviderConfig) -> Path:
    workspace_root = Path(config.workspace_root or os.getcwd())
    local_home = workspace_root / ".codex-cli-home"
    local_home.mkdir(parents=True, exist_ok=True)

    source_auth = Path(config.codex_auth_file) if config.codex_auth_file else _default_codex_auth_path()
    if not source_auth.exists():
        raise OpenAIProviderError(f"Codex auth file not found: {source_auth}")

    target_auth = local_home / "auth.json"
    if source_auth.resolve() != target_auth.resolve():
        shutil.copyfile(source_auth, target_auth)
    (local_home / "config.toml").write_text(
        _build_local_codex_config(
            str(workspace_root),
            config.model,
            config.model_reasoning_effort,
        ),
        encoding="utf-8",
    )
    return local_home


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def resolve_codex_home(config: OpenAIProviderConfig) -> Path:
    if config.codex_home_mode == "local":
        return ensure_local_codex_home(config)
    candidate: Path
    if config.codex_home_path:
        candidate = Path(config.codex_home_path)
    elif config.codex_auth_file:
        candidate = _default_codex_home_path(Path(config.codex_auth_file))
    else:
        candidate = _default_codex_home_path()
    workspace_root = Path(config.workspace_root or os.getcwd())
    if _path_is_within(candidate, workspace_root):
        return candidate
    return ensure_local_codex_home(config)


def resolve_codex_cli_path(config: OpenAIProviderConfig) -> str:
    if config.codex_cli_path:
        return config.codex_cli_path

    if os.name == "nt":
        local_appdata = os.getenv("LOCALAPPDATA", "").strip()
        if local_appdata:
            bin_root = Path(local_appdata) / "OpenAI" / "Codex" / "bin"
            candidates = sorted(
                bin_root.glob("*/codex.exe"),
                key=lambda entry: entry.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                return str(candidates[0])

    which_path = shutil.which("codex")
    if which_path:
        return which_path

    return "codex"


def summarize_codex_failure(stdout: str, stderr: str) -> str:
    combined_lines = [
        line.strip()
        for line in f"{stdout}\n{stderr}".splitlines()
        if line.strip() and not line.lstrip().startswith("<")
    ]
    priority_fragments = [
        "unexpected status 403",
        "failed to connect to websocket",
        "backend-api/codex/responses",
        "backend-api/codex/models",
        "failed to refresh available models",
    ]

    selected: list[str] = []
    for fragment in priority_fragments:
        for line in combined_lines:
            if fragment in line.lower() and line not in selected:
                selected.append(line)
                break

    if selected:
        return " | ".join(selected[:4])

    if not combined_lines:
        return "unknown codex exec error"

    return " | ".join(combined_lines[-6:])


def codex_exec_timeout_seconds(config: OpenAIProviderConfig) -> int:
    return max(1, int(config.timeout_seconds)) + 30


def is_retryable_codex_failure(details: str) -> bool:
    normalized = details.lower()
    retryable_fragments = (
        "failed to refresh available models",
        "stream disconnected before completion",
        "backend-api/codex/models",
    )
    return any(fragment in normalized for fragment in retryable_fragments)


CODEX_JSON_WRAPPER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["json_payload_b64"],
    "properties": {
        "json_payload_b64": {"type": "string"},
    },
}


CODEX_JSON_TEXT_WRAPPER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["json_payload"],
    "properties": {
        "json_payload": {"type": "string"},
    },
}


def extract_json_object(raw_text: str) -> dict[str, Any]:
    candidate = raw_text.strip()
    if not candidate:
        raise OpenAIProviderError("Model returned empty text when JSON was expected.")

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise OpenAIProviderError("Model did not return a valid JSON object.") from None
        try:
            payload = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise OpenAIProviderError(f"Model did not return a valid JSON object: {exc}") from exc

    if not isinstance(payload, dict):
        raise OpenAIProviderError("Model returned JSON, but it was not an object.")
    return payload


def payload_satisfies_required_keys(payload: dict[str, Any], schema: dict[str, Any] | None) -> bool:
    if not schema or not isinstance(schema, dict):
        return True
    required = schema.get("required")
    if not isinstance(required, list) or not required:
        return True
    for key in required:
        if not isinstance(key, str) or key not in payload:
            return False
    return True


def extract_output_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    output_items = payload.get("output")
    if not isinstance(output_items, list):
        return ""

    collected: list[str] = []
    for output_item in output_items:
        if not isinstance(output_item, dict):
            continue
        content_items = output_item.get("content")
        if not isinstance(content_items, list):
            continue
        for content_item in content_items:
            if not isinstance(content_item, dict):
                continue
            if content_item.get("type") == "output_text":
                text = content_item.get("text")
                if isinstance(text, str) and text.strip():
                    collected.append(text.strip())
    return "\n".join(collected).strip()


def decode_codex_json_payload(payload_b64: str) -> dict[str, Any]:
    candidate = "".join(payload_b64.split()).strip()
    if not candidate:
        raise OpenAIProviderError("Codex CLI transport completed without a json_payload_b64 wrapper field.")

    # Some model turns return the requested JSON directly despite the wrapper instruction.
    if candidate.startswith("{"):
        return extract_json_object(candidate)

    padded = candidate + "=" * (-len(candidate) % 4)
    decoders = (base64.b64decode, base64.urlsafe_b64decode)
    for decoder in decoders:
        try:
            decoded = decoder(padded.encode("ascii")).decode("utf-8")
            return extract_json_object(decoded)
        except Exception:
            continue
    raise OpenAIProviderError("Codex CLI transport returned an invalid base64 payload wrapper.")


def _codex_cli_strategies(config: OpenAIProviderConfig, persist_session: bool) -> tuple[str, ...]:
    if persist_session:
        return ("direct",)
    mode = (config.codex_cli_output_mode or "auto").strip().lower()
    if mode == "direct":
        return ("direct",)
    if mode == "wrapper":
        return ("wrapper",)
    return ("direct", "wrapper")


def extract_codex_session_id(jsonl_output: str) -> str:
    for line in jsonl_output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == "thread.started":
            thread_id = event.get("thread_id")
            if isinstance(thread_id, str) and thread_id.strip():
                return thread_id.strip()
    return ""


class OpenAIResponsesClient:
    def __init__(self, config: OpenAIProviderConfig) -> None:
        self.config = config
        self.last_transport_metadata: dict[str, Any] = {}

    def create_json_response(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any] | None = None,
        codex_session_id: str | None = None,
        persist_codex_session: bool = False,
        use_transport_output_schema: bool = True,
    ) -> dict[str, Any]:
        self.last_transport_metadata = {}
        body = {
            "model": self.config.model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
        }
        if self.config.transport == "codex_cli":
            return self._create_response_via_codex_cli(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=output_schema or {"type": "object"},
                codex_session_id=codex_session_id,
                persist_session=persist_codex_session,
            )
        if self.config.transport == "codex_sdk_node":
            return self._create_response_via_codex_sdk(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=(output_schema or {"type": "object"}) if use_transport_output_schema else None,
            )
        if self.config.transport == "node_https":
            payload = self._create_response_via_node(body)
        else:
            payload = self._create_response_via_python(body)

        output_text = extract_output_text(payload)
        return extract_json_object(output_text)

    def _create_response_via_codex_cli(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
        codex_session_id: str | None = None,
        persist_session: bool = False,
    ) -> dict[str, Any]:
        workspace_root = Path(self.config.workspace_root or os.getcwd())
        tmp_root = workspace_root / ".tmp"
        tmp_root.mkdir(parents=True, exist_ok=True)
        codex_home = resolve_codex_home(self.config)
        codex_cli_path = resolve_codex_cli_path(self.config)

        with tempfile.TemporaryDirectory(prefix="codex-cli-", dir=tmp_root) as temp_dir:
            env = os.environ.copy()
            env["CODEX_HOME"] = str(codex_home)
            last_error: OpenAIProviderError | None = None
            for strategy in _codex_cli_strategies(self.config, persist_session):
                transport_requirements = (
                    [
                        "Transport requirement:",
                        "Return the requested JSON object directly and match the provided output schema.",
                        "Do not include markdown fences.",
                    ]
                    if persist_session
                    else [
                        "Transport requirement:",
                        "Your final response must be a JSON object with exactly one key named json_payload.",
                        "The value of json_payload must be a valid JSON string whose decoded contents are the requested JSON object.",
                        "Do not include markdown fences.",
                    ]
                    if strategy == "direct"
                    else [
                        "Transport requirement:",
                        "Your final response must be a JSON object with exactly one key named json_payload_b64.",
                        "The value of json_payload_b64 must be a standard base64-encoded UTF-8 JSON object representing the requested result.",
                        "Encode the final JSON bytes directly to base64 with no line breaks.",
                        "Do not include markdown fences.",
                    ]
                )
                wrapped_prompt = "\n".join(
                    [system_prompt.strip(), "", user_prompt.strip(), "", *transport_requirements]
                ).strip()

                schema_path = Path(temp_dir) / f"schema-{strategy}.json"
                output_path = Path(temp_dir) / f"output-{strategy}.json"
                transport_schema = (
                    output_schema
                    if persist_session
                    else CODEX_JSON_TEXT_WRAPPER_SCHEMA
                    if strategy == "direct"
                    else CODEX_JSON_WRAPPER_SCHEMA
                )
                schema_path.write_text(json.dumps(transport_schema, ensure_ascii=False), encoding="utf-8")

                command = [codex_cli_path, "exec"]
                if codex_session_id:
                    command.append("resume")
                command.extend([
                    "--skip-git-repo-check",
                    "-m", self.config.model,
                    "-c",
                    f'model_reasoning_effort="{self.config.model_reasoning_effort}"',
                    "-c",
                    'approval_policy="never"',
                ])
                if not codex_session_id:
                    command.extend([
                        "-C", str(workspace_root),
                        "-c", "sandbox_workspace_write.network_access=true",
                        "-s", "workspace-write",
                    ])
                if not persist_session:
                    command.append("--ephemeral")
                if persist_session:
                    command.append("--json")
                command.extend([
                    "--output-schema",
                    str(schema_path),
                    "-o",
                    str(output_path),
                ])
                if self.config.codex_ignore_user_config:
                    command.append("--ignore-user-config")
                if self.config.codex_ignore_rules:
                    command.append("--ignore-rules")
                if codex_session_id:
                    command.append(codex_session_id)
                command.append(wrapped_prompt)

                attempts = max(1, int(self.config.codex_cli_retries) + 1)
                failure_details = ""
                stdout = ""
                completed: subprocess.CompletedProcess[str] | None = None
                for attempt_index in range(attempts):
                    try:
                        completed = subprocess.run(
                            command,
                            stdin=subprocess.DEVNULL,
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            timeout=codex_exec_timeout_seconds(self.config),
                            check=False,
                            env=env,
                        )
                    except subprocess.TimeoutExpired as exc:
                        raise OpenAIProviderError(
                            f"Codex CLI transport timed out after {int(exc.timeout)} seconds. "
                            "Try reducing prompt size, lowering workers, or increasing AI_VALIDATION_OPENAI_TIMEOUT_SECONDS."
                        ) from exc
                    except OSError as exc:
                        raise OpenAIProviderError(f"Codex CLI transport failed to start: {exc}") from exc

                    stdout = completed.stdout.strip()
                    stderr = completed.stderr.strip()
                    if completed.returncode == 0:
                        break

                    failure_details = summarize_codex_failure(stdout, stderr)
                    remaining_attempts = attempts - attempt_index - 1
                    if remaining_attempts <= 0 or not is_retryable_codex_failure(failure_details):
                        last_error = OpenAIProviderError(f"Codex CLI transport failed: {failure_details}")
                        completed = None
                        break
                    time.sleep(max(0, int(self.config.codex_cli_retry_backoff_seconds)))
                else:  # pragma: no cover
                    last_error = OpenAIProviderError(
                        f"Codex CLI transport failed: {failure_details or 'unknown codex exec error'}"
                    )

                if completed is None:
                    continue
                if not output_path.exists():
                    last_error = OpenAIProviderError(
                        "Codex CLI transport completed without writing the final message file."
                    )
                    continue

                try:
                    output_payload = extract_json_object(output_path.read_text(encoding="utf-8"))
                    if persist_session:
                        resolved_session_id = extract_codex_session_id(stdout) or (codex_session_id or "")
                        if not resolved_session_id:
                            raise OpenAIProviderError("Codex CLI persistent transport completed without a thread id.")
                        self.last_transport_metadata["codex_session_id"] = resolved_session_id
                        return output_payload
                    if strategy == "direct":
                        if set(output_payload.keys()) == {"json_payload_b64"}:
                            decoded_payload = decode_codex_json_payload(str(output_payload.get("json_payload_b64", "")).strip())
                            if not payload_satisfies_required_keys(decoded_payload, output_schema):
                                raise OpenAIProviderError(
                                    "Codex CLI direct strategy returned JSON but it did not satisfy the required top-level output keys."
                                )
                            return decoded_payload
                        payload_text = str(output_payload.get("json_payload", "")).strip()
                        decoded_payload = extract_json_object(payload_text)
                        if not payload_satisfies_required_keys(decoded_payload, output_schema):
                            raise OpenAIProviderError(
                                "Codex CLI direct strategy returned JSON but it did not satisfy the required top-level output keys."
                            )
                        return decoded_payload
                    payload_b64 = str(output_payload.get("json_payload_b64", "")).strip()
                    decoded_payload = decode_codex_json_payload(payload_b64)
                    if not payload_satisfies_required_keys(decoded_payload, output_schema):
                        raise OpenAIProviderError(
                            "Codex CLI wrapper strategy returned JSON but it did not satisfy the required top-level output keys."
                        )
                    return decoded_payload
                except OpenAIProviderError as exc:
                    last_error = exc
                    continue

            if last_error is not None:
                raise last_error
            raise OpenAIProviderError("Codex CLI transport failed without producing a usable JSON payload.")

    def _create_response_via_python(self, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url=f"{self.config.api_base.rstrip('/')}/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise OpenAIProviderError(f"OpenAI Responses API request failed: HTTP {exc.code} {details}") from exc
        except urllib.error.URLError as exc:
            raise OpenAIProviderError(f"OpenAI Responses API request failed: {exc.reason}") from exc

    def _create_response_via_node(self, body: dict[str, Any]) -> dict[str, Any]:
        helper_path = Path(__file__).with_name("openai_transport_node.mjs")
        helper_input = {
            "url": f"{self.config.api_base.rstrip('/')}/responses",
            "api_key": self.config.api_key,
            "timeout_seconds": self.config.timeout_seconds,
            "body": body,
        }
        completed = subprocess.run(
            ["node", "--use-system-ca", str(helper_path)],
            input=json.dumps(helper_input),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=self.config.timeout_seconds + 5,
            check=False,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            details = stderr or stdout or "unknown node transport error"
            raise OpenAIProviderError(f"OpenAI Responses API request failed via node transport: {details}")

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise OpenAIProviderError(f"Node transport returned invalid JSON: {stdout[:300]}") from exc

        if not isinstance(payload, dict):
            raise OpenAIProviderError("Node transport returned a non-object payload.")

        if payload.get("ok") is not True:
            status = payload.get("status", "unknown")
            details = payload.get("body", "")
            raise OpenAIProviderError(f"OpenAI Responses API request failed: HTTP {status} {details}")

        response_body = payload.get("response")
        if not isinstance(response_body, dict):
            raise OpenAIProviderError("Node transport response body was not a JSON object.")
        return response_body

    def _create_response_via_codex_sdk(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any] | None,
    ) -> dict[str, Any]:
        helper_path = Path(__file__).with_name("codex_sdk_transport_node.mjs")
        helper_input = {
            "workspace": self.config.workspace_root or os.getcwd(),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "output_schema": output_schema,
            "model": self.config.model,
            "model_reasoning_effort": self.config.model_reasoning_effort,
            "codex_auth_file": self.config.codex_auth_file,
            "codex_sdk_module_path": self.config.codex_sdk_module_path,
        }
        completed = subprocess.run(
            ["node", "--use-system-ca", str(helper_path)],
            input=json.dumps(helper_input, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=self.config.timeout_seconds + 15,
            check=False,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            details = stderr or stdout or "unknown codex sdk transport error"
            raise OpenAIProviderError(f"Codex SDK transport failed: {details}")

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise OpenAIProviderError(f"Codex SDK transport returned invalid JSON: {stdout[:300]}") from exc

        if not isinstance(payload, dict):
            raise OpenAIProviderError("Codex SDK transport returned a non-object payload.")
        final_response = str(payload.get("final_response", "")).strip()
        return extract_json_object(final_response)
