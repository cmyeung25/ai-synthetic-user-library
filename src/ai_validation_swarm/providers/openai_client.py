from __future__ import annotations

import json
import os
import subprocess
import base64
import http.client
import mimetypes
import re
import shutil
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse


class OpenAIProviderError(RuntimeError):
    pass


@dataclass(slots=True)
class OpenAIProviderConfig:
    api_key: str
    model: str = "gpt-5.4"
    profile: str = "chatgpt-5.4-high"
    provider_name: str = "openai"
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
    agnes_enable_thinking: bool = False
    agnes_transport_retries: int = 0
    agnes_transport_retry_backoff_seconds: int = 2


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


def _first_env_value(*names: str) -> tuple[str, str]:
    for name in names:
        if not name:
            continue
        value = os.getenv(name, "").strip()
        if value:
            return value, name
    return "", ""


def _env_value(default: str, *names: str) -> str:
    value, _ = _first_env_value(*names)
    return value or default


def _normalize_provider_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "openai"


def _derive_provider_name_from_api_base(api_base: str) -> str:
    hostname = urlparse(api_base).hostname or ""
    normalized_host = hostname.strip().lower()
    if not normalized_host:
        return "openai"
    if normalized_host == "api.openai.com":
        return "openai"
    if "agnes" in normalized_host:
        return "agnes"
    return "openai-compatible"


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
        "provider_name": getattr(config, "provider_name", "openai"),
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
        "codex_cli_output_mode": getattr(config, "codex_cli_output_mode", "auto"),
        "agnes_enable_thinking": getattr(config, "agnes_enable_thinking", False),
        "agnes_transport_retries": getattr(config, "agnes_transport_retries", 0),
        "agnes_transport_retry_backoff_seconds": getattr(config, "agnes_transport_retry_backoff_seconds", 2),
        "has_token": bool(config.api_key),
        "token_claim_keys": sorted(claims.keys()),
        "scopes": normalized_scopes,
        "has_api_responses_write_scope": "api.responses.write" in normalized_scopes,
        "expires_at_epoch": claims.get("exp"),
        "issued_at_epoch": claims.get("iat"),
        "subject": claims.get("sub"),
    }


def load_openai_provider_config(
    *,
    prefer_codex_auth: bool = False,
    force_transport: str | None = None,
    timeout_default: int | None = None,
    force_provider_name: str | None = None,
    force_api_key_env: str | None = None,
    default_model: str | None = None,
    default_profile: str | None = None,
    default_api_base: str | None = None,
) -> OpenAIProviderConfig:
    auth_source = ""
    codex_auth_file = ""
    api_key = ""
    auth_path_raw = os.getenv("AI_VALIDATION_CODEX_AUTH_FILE", "").strip()
    auth_path = Path(auth_path_raw) if auth_path_raw else None
    configured_provider_name = _env_value("", "AI_VALIDATION_LLM_PROVIDER", "AI_VALIDATION_OPENAI_PROVIDER")
    configured_api_base = _env_value(
        default_api_base or "https://api.openai.com/v1",
        "AI_VALIDATION_LLM_BASE_URL",
        "AI_VALIDATION_OPENAI_BASE_URL",
    )
    provider_name = _normalize_provider_name(force_provider_name or configured_provider_name or _derive_provider_name_from_api_base(configured_api_base))
    primary_api_key_env = force_api_key_env or ""
    primary_api_key_label = primary_api_key_env or "OPENAI_API_KEY"
    api_key_env_names = tuple(
        name
        for name in (
            primary_api_key_env,
            "AI_VALIDATION_LLM_API_KEY",
            "AI_VALIDATION_OPENAI_API_KEY",
            "OPENAI_API_KEY",
            "CODEX_API_KEY",
        )
        if name
    )

    if prefer_codex_auth:
        api_key = load_codex_access_token(auth_path)
        if api_key:
            codex_auth_path = auth_path or _default_codex_auth_path()
            codex_auth_file = str(codex_auth_path)
            auth_source = f"codex_auth_file:{codex_auth_path}"
        else:
            api_key, api_key_env_name = _first_env_value(*api_key_env_names)
            if api_key:
                auth_source = f"fallback_api_key_env:{api_key_env_name}"
    else:
        api_key, api_key_env_name = _first_env_value(*api_key_env_names)
        if api_key:
            auth_source = f"api_key_env:{api_key_env_name}"
        elif "CODEX_API_KEY" not in api_key_env_names:
            api_key, api_key_env_name = _first_env_value("CODEX_API_KEY")
            if api_key:
                auth_source = f"api_key_env:{api_key_env_name}"
        if not api_key:
            api_key = load_codex_access_token(auth_path)
            if api_key:
                codex_auth_path = auth_path or _default_codex_auth_path()
                codex_auth_file = str(codex_auth_path)
                auth_source = f"codex_auth_file:{codex_auth_path}"

    if not api_key:
        raise OpenAIProviderError(
            f"LLM credentials are missing for provider '{provider_name}'. "
            f"Set {primary_api_key_label}, AI_VALIDATION_LLM_API_KEY, OPENAI_API_KEY, or CODEX_API_KEY, "
            "or sign in through Codex so C:\\Users\\user\\.codex\\auth.json exposes a ChatGPT access token."
        )

    default_transport = "node_https" if os.name == "nt" else "python_urllib"
    if auth_source.startswith("codex_auth_file:"):
        default_transport = "codex_cli"
    resolved_transport = force_transport or _env_value(default_transport, "AI_VALIDATION_LLM_TRANSPORT", "AI_VALIDATION_OPENAI_TRANSPORT")
    codex_home_mode_default = "global" if resolved_transport == "codex_cli" else "local"
    codex_home_mode = os.getenv("AI_VALIDATION_CODEX_HOME_MODE", codex_home_mode_default).strip().lower() or codex_home_mode_default
    if codex_home_mode not in {"global", "local"}:
        codex_home_mode = codex_home_mode_default
    codex_home_path = os.getenv("AI_VALIDATION_CODEX_HOME", "").strip() or os.getenv("CODEX_HOME", "").strip()
    resolved_timeout_default = timeout_default
    if resolved_timeout_default is None:
        resolved_timeout_default = 240 if resolved_transport == "codex_cli" else 120
    return OpenAIProviderConfig(
        api_key=api_key,
        model=_env_value(default_model or "gpt-5.4", "AI_VALIDATION_LLM_MODEL", "AI_VALIDATION_OPENAI_MODEL"),
        profile=_env_value(default_profile or "chatgpt-5.4-high", "AI_VALIDATION_LLM_PROFILE", "AI_VALIDATION_OPENAI_PROFILE"),
        provider_name=provider_name,
        model_reasoning_effort=_env_value("high", "AI_VALIDATION_LLM_REASONING_EFFORT", "AI_VALIDATION_OPENAI_REASONING_EFFORT"),
        api_base=configured_api_base,
        timeout_seconds=int(_env_value(str(resolved_timeout_default), "AI_VALIDATION_LLM_TIMEOUT_SECONDS", "AI_VALIDATION_OPENAI_TIMEOUT_SECONDS")),
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
        agnes_enable_thinking=_env_flag(
            "AI_VALIDATION_AGNES_ENABLE_THINKING",
            provider_name == "agnes",
        ),
        agnes_transport_retries=int(
            os.getenv(
                "AI_VALIDATION_AGNES_TRANSPORT_RETRIES",
                "2" if provider_name == "agnes" and resolved_transport in {"python_urllib", "node_https", "powershell_webrequest"} else "0",
            )
        ),
        agnes_transport_retry_backoff_seconds=int(
            os.getenv(
                "AI_VALIDATION_AGNES_TRANSPORT_RETRY_BACKOFF_SECONDS",
                "2",
            )
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
    missing: list[str] = []
    for key in required:
        if not isinstance(key, str):
            continue
        if key not in payload:
            missing.append(key)
    if not missing:
        return True
    # Some Codex CLI turns return a valid flat persona payload without the
    # outer "sections" wrapper, while still including the other required
    # top-level contract keys. Let the persona-layer normalizer handle it.
    if missing == ["sections"]:
        other_required = [key for key in required if isinstance(key, str) and key != "sections"]
        if all(key in payload for key in other_required) and any(key not in set(other_required) for key in payload):
            return True
    return False


def _estimate_token_count(text: str) -> int:
    candidate = text.strip()
    if not candidate:
        return 0
    return max(1, len(candidate) // 4)


def _normalize_usage_payload(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    normalized: dict[str, Any] = {}
    for key in (
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "reasoning_tokens",
        "cached_tokens",
    ):
        value = payload.get(key)
        if isinstance(value, int):
            normalized[key] = value
    if normalized:
        normalized["source"] = "api"
        return normalized
    return None


def _find_usage_in_jsonish(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        direct = _normalize_usage_payload(payload.get("usage"))
        if direct is not None:
            return direct
        direct = _normalize_usage_payload(payload)
        if direct is not None:
            return direct
        for value in payload.values():
            nested = _find_usage_in_jsonish(value)
            if nested is not None:
                return nested
    elif isinstance(payload, list):
        for item in payload:
            nested = _find_usage_in_jsonish(item)
            if nested is not None:
                return nested
    return None


def extract_usage_from_jsonl_output(text: str) -> dict[str, Any] | None:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = _find_usage_in_jsonish(payload)
        if usage is not None:
            usage["source"] = "codex_jsonl"
            return usage
    return None


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


def extract_chat_completion_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list):
        return ""
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            collected: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    collected.append(text.strip())
            if collected:
                return "\n".join(collected).strip()
    return ""


def image_file_to_data_url(path: str | Path) -> str:
    file_path = Path(path)
    try:
        raw = file_path.read_bytes()
    except OSError as exc:
        raise OpenAIProviderError(f"Image stimulus file could not be read: {file_path}") from exc
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type or not mime_type.startswith("image/"):
        raise OpenAIProviderError(
            f"Unsupported image stimulus file type for '{file_path}'. Use a standard image extension such as .png, .jpg, or .webp."
        )
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _input_items_are_text_only(input_items: list[dict[str, Any]]) -> bool:
    for item in input_items:
        if not isinstance(item, dict):
            return False
        content_items = item.get("content")
        if not isinstance(content_items, list):
            return False
        for content_item in content_items:
            if not isinstance(content_item, dict):
                return False
            if content_item.get("type") != "input_text":
                return False
            if not isinstance(content_item.get("text"), str):
                return False
    return True


def _text_prompt_from_input_items(input_items: list[dict[str, Any]], role: str) -> str:
    collected: list[str] = []
    for item in input_items:
        if not isinstance(item, dict) or item.get("role") != role:
            continue
        content_items = item.get("content")
        if not isinstance(content_items, list):
            continue
        for content_item in content_items:
            if not isinstance(content_item, dict):
                continue
            text = content_item.get("text")
            if content_item.get("type") == "input_text" and isinstance(text, str) and text.strip():
                collected.append(text.strip())
    return "\n\n".join(collected).strip()


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
    def __init__(self, config: OpenAIProviderConfig, debug_writer: Callable[[str], None] | None = None) -> None:
        self.config = config
        self.last_transport_metadata: dict[str, Any] = {}
        self.debug_writer = debug_writer

    def _debug(self, message: str) -> None:
        if self.debug_writer is not None:
            self.debug_writer(message)

    def _debug_block(self, label: str, text: str) -> None:
        if self.debug_writer is None:
            return
        self.debug_writer(f"[llm] {label} >>>")
        self.debug_writer(text)
        self.debug_writer(f"[llm] {label} <<<")

    def _maybe_attach_agnes_chat_template_kwargs(self, body: dict[str, Any]) -> dict[str, Any]:
        if self.config.provider_name != "agnes" or not self.config.agnes_enable_thinking:
            return body
        enriched = dict(body)
        existing = enriched.get("chat_template_kwargs")
        if isinstance(existing, dict):
            kwargs = dict(existing)
        else:
            kwargs = {}
        kwargs["enable_thinking"] = True
        enriched["chat_template_kwargs"] = kwargs
        return enriched

    def _supports_agnes_transport_retry(self) -> bool:
        return (
            self.config.provider_name == "agnes"
            and self.config.transport in {"python_urllib", "node_https", "powershell_webrequest"}
        )

    def _is_retryable_agnes_transport_failure(self, error: OpenAIProviderError) -> bool:
        normalized = str(error).strip().lower()
        retryable_fragments = (
            "socket hang up",
            "remote end closed connection without response",
            "connection was closed unexpectedly",
            "connection reset",
            "connection aborted",
            "econnreset",
            "econnaborted",
            "etimedout",
            "timed out",
            "timeout",
            "temporarily unavailable",
            "service unavailable",
            "bad gateway",
            "gateway timeout",
            "rate limit",
            "http 429",
            "http 500",
            "http 502",
            "http 503",
            "http 504",
        )
        return any(fragment in normalized for fragment in retryable_fragments)

    def _agnes_transport_retry_delay(self, attempt_index: int) -> int:
        base_delay = max(0, int(self.config.agnes_transport_retry_backoff_seconds))
        if base_delay <= 0:
            return 0
        return base_delay * (2 ** attempt_index)

    def _run_with_agnes_transport_retry(
        self,
        *,
        operation: str,
        request: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        attempts = max(1, int(self.config.agnes_transport_retries) + 1) if self._supports_agnes_transport_retry() else 1
        for attempt_index in range(attempts):
            try:
                return request()
            except OpenAIProviderError as exc:
                remaining_attempts = attempts - attempt_index - 1
                retryable = self._is_retryable_agnes_transport_failure(exc)
                self._debug(
                    f"[llm] agnes_transport_failure operation={operation} attempt={attempt_index + 1}/{attempts} "
                    f"retryable={retryable} error={exc}"
                )
                if remaining_attempts <= 0 or not retryable:
                    raise
                delay_seconds = self._agnes_transport_retry_delay(attempt_index)
                self._debug(
                    f"[llm] agnes_transport_retry operation={operation} remaining_attempts={remaining_attempts} "
                    f"backoff_seconds={delay_seconds}"
                )
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
        raise OpenAIProviderError(f"Agnes transport retry loop exhausted without a result for operation '{operation}'.")

    def _create_responses_payload_via_transport(self, body: dict[str, Any]) -> dict[str, Any]:
        if self.config.transport == "node_https":
            return self._create_response_via_node(body)
        if self.config.transport == "powershell_webrequest":
            return self._create_response_via_powershell(body)
        return self._create_response_via_python(body)

    def _create_chat_completion_payload_via_transport(self, body: dict[str, Any]) -> dict[str, Any]:
        if self.config.transport == "node_https":
            return self._create_chat_completion_via_node(body)
        if self.config.transport == "powershell_webrequest":
            return self._create_chat_completion_via_powershell(body)
        return self._create_chat_completion_via_python(body)

    def create_json_response_from_input_items(
        self,
        *,
        input_items: list[dict[str, Any]],
        output_schema: dict[str, Any] | None = None,
        codex_session_id: str | None = None,
        persist_codex_session: bool = False,
        use_transport_output_schema: bool = True,
    ) -> dict[str, Any]:
        self.last_transport_metadata = {}
        self._debug(
            f"[llm] create_json_response_from_input_items transport={self.config.transport} model={self.config.model} "
            f"reasoning={self.config.model_reasoning_effort} persist_session={persist_codex_session}"
        )
        if self.config.transport in {"codex_cli", "codex_sdk_node"}:
            if not _input_items_are_text_only(input_items):
                raise OpenAIProviderError(
                    "Multimodal inputs are not supported for codex transports. "
                    "Use python_urllib, node_https, or powershell_webrequest with a direct API key for image stimulus review."
                )
            system_prompt = _text_prompt_from_input_items(input_items, "system")
            user_prompt = _text_prompt_from_input_items(input_items, "user")
            return self.create_json_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=output_schema,
                codex_session_id=codex_session_id,
                persist_codex_session=persist_codex_session,
                use_transport_output_schema=use_transport_output_schema,
            )

        body = {
            "model": self.config.model,
            "input": input_items,
        }
        body = self._maybe_attach_agnes_chat_template_kwargs(body)
        try:
            payload = self._run_with_agnes_transport_retry(
                operation="responses",
                request=lambda: self._create_responses_payload_via_transport(body),
            )
        except OpenAIProviderError as exc:
            if not _input_items_are_text_only(input_items) or not self._should_use_chat_completions_fallback(exc):
                raise
            self._debug(
                f"[llm] responses_api_failed provider={self.config.provider_name} transport={self.config.transport} "
                f"error={exc}; retrying via chat_completions"
            )
            payload = self._create_response_via_chat_completions(
                system_prompt=_text_prompt_from_input_items(input_items, "system"),
                user_prompt=_text_prompt_from_input_items(input_items, "user"),
            )
        usage = _find_usage_in_jsonish(payload)
        if usage is not None:
            self.last_transport_metadata["usage"] = usage
            self._debug(f"[llm] usage {json.dumps(usage, ensure_ascii=False)}")

        output_text = extract_output_text(payload)
        if not output_text and self.last_transport_metadata.get("fallback_transport") == "chat_completions":
            output_text = extract_chat_completion_text(payload)
        return extract_json_object(output_text)

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
        if self.config.transport == "codex_cli":
            self.last_transport_metadata = {}
            self._debug(
                f"[llm] create_json_response transport={self.config.transport} model={self.config.model} "
                f"reasoning={self.config.model_reasoning_effort} persist_session={persist_codex_session}"
            )
            return self._create_response_via_codex_cli(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=output_schema or {"type": "object"},
                codex_session_id=codex_session_id,
                persist_session=persist_codex_session,
            )
        if self.config.transport == "codex_sdk_node":
            self.last_transport_metadata = {}
            self._debug(
                f"[llm] create_json_response transport={self.config.transport} model={self.config.model} "
                f"reasoning={self.config.model_reasoning_effort} persist_session={persist_codex_session}"
            )
            return self._create_response_via_codex_sdk(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=(output_schema or {"type": "object"}) if use_transport_output_schema else None,
            )
        return self.create_json_response_from_input_items(
            input_items=[
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            output_schema=output_schema,
            codex_session_id=codex_session_id,
            persist_codex_session=persist_codex_session,
            use_transport_output_schema=use_transport_output_schema,
        )

    def create_text_response(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        codex_session_id: str | None = None,
        persist_codex_session: bool = False,
    ) -> str:
        self.last_transport_metadata = {}
        self._debug(
            f"[llm] create_text_response transport={self.config.transport} model={self.config.model} "
            f"reasoning={self.config.model_reasoning_effort} persist_session={persist_codex_session}"
        )
        if self.config.transport in {"codex_cli", "codex_sdk_node"}:
            raise OpenAIProviderError("Text responses are not supported for codex transports.")
        body = {
            "model": self.config.model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
        }
        body = self._maybe_attach_agnes_chat_template_kwargs(body)
        del codex_session_id, persist_codex_session
        try:
            payload = self._run_with_agnes_transport_retry(
                operation="responses_text",
                request=lambda: self._create_responses_payload_via_transport(body),
            )
        except OpenAIProviderError as exc:
            if not self._should_use_chat_completions_fallback(exc):
                raise
            self._debug(
                f"[llm] responses_api_failed provider={self.config.provider_name} transport={self.config.transport} "
                f"error={exc}; retrying via chat_completions"
            )
            payload = self._create_response_via_chat_completions(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        usage = _find_usage_in_jsonish(payload)
        if usage is not None:
            self.last_transport_metadata["usage"] = usage
            self._debug(f"[llm] usage {json.dumps(usage, ensure_ascii=False)}")

        output_text = extract_output_text(payload)
        if not output_text and self.last_transport_metadata.get("fallback_transport") == "chat_completions":
            output_text = extract_chat_completion_text(payload)
        text = output_text.strip()
        if not text:
            raise OpenAIProviderError("Model returned empty text when plain text was expected.")
        self.last_transport_metadata["response_format"] = "text"
        self._debug_block("text_response", text)
        return text

    def _should_use_chat_completions_fallback(self, exc: OpenAIProviderError) -> bool:
        if self.config.provider_name != "agnes":
            return False
        if self.config.transport not in {"python_urllib", "node_https", "powershell_webrequest"}:
            return False
        message = str(exc).lower()
        return any(
            fragment in message
            for fragment in (
                "socket hang up",
                "remote end closed connection without response",
                "request failed",
                "response body was not a json object",
                "connection was closed unexpectedly",
            )
        )

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
            self._debug(
                f"[llm] codex_cli workspace_root={workspace_root} codex_home={codex_home} "
                f"timeout={self.config.timeout_seconds}s output_mode={self.config.codex_cli_output_mode}"
            )
            self._debug_block("system_prompt", system_prompt)
            self._debug_block("user_prompt", user_prompt)
            last_error: OpenAIProviderError | None = None
            for strategy in _codex_cli_strategies(self.config, persist_session):
                self._debug(f"[llm] codex_cli strategy={strategy} persist_session={persist_session}")
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
                self._debug_block("wrapped_prompt", wrapped_prompt)

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
                self._debug_block(
                    "output_schema",
                    json.dumps(transport_schema, ensure_ascii=False, indent=2),
                )

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
                self._debug(f"[llm] codex_cli command={' '.join(command[:-1])}")

                attempts = max(1, int(self.config.codex_cli_retries) + 1)
                failure_details = ""
                stdout = ""
                completed: subprocess.CompletedProcess[str] | None = None
                for attempt_index in range(attempts):
                    self._debug(
                        f"[llm] codex_cli subprocess_start strategy={strategy} attempt={attempt_index + 1}/{attempts}"
                    )
                    started_at = time.perf_counter()
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
                        self._debug(
                            f"[llm] codex_cli timeout strategy={strategy} attempt={attempt_index + 1}/{attempts} "
                            f"after={int(exc.timeout)}s"
                        )
                        raise OpenAIProviderError(
                            f"Codex CLI transport timed out after {int(exc.timeout)} seconds. "
                            "Try reducing prompt size, lowering workers, or increasing AI_VALIDATION_OPENAI_TIMEOUT_SECONDS."
                        ) from exc
                    except OSError as exc:
                        self._debug(f"[llm] codex_cli start_error strategy={strategy} error={exc}")
                        raise OpenAIProviderError(f"Codex CLI transport failed to start: {exc}") from exc

                    elapsed = time.perf_counter() - started_at
                    stdout = completed.stdout.strip()
                    stderr = completed.stderr.strip()
                    self._debug(
                        f"[llm] codex_cli subprocess_exit strategy={strategy} attempt={attempt_index + 1}/{attempts} "
                        f"returncode={completed.returncode} elapsed={elapsed:.1f}s"
                    )
                    if stdout:
                        self._debug_block("codex_cli.stdout", stdout)
                        usage = extract_usage_from_jsonl_output(stdout)
                        if usage is not None:
                            self.last_transport_metadata["usage"] = usage
                            self._debug(f"[llm] usage {json.dumps(usage, ensure_ascii=False)}")
                    if stderr:
                        self._debug_block("codex_cli.stderr", stderr)
                    if completed.returncode == 0:
                        break

                    failure_details = summarize_codex_failure(stdout, stderr)
                    self._debug(
                        f"[llm] codex_cli retryable_failure strategy={strategy} details={failure_details}"
                    )
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
                    self._debug(f"[llm] codex_cli missing_output_file strategy={strategy} path={output_path}")
                    last_error = OpenAIProviderError(
                        "Codex CLI transport completed without writing the final message file."
                    )
                    continue

                try:
                    raw_output_text = output_path.read_text(encoding="utf-8")
                    if "usage" not in self.last_transport_metadata:
                        estimated_usage = {
                            "input_tokens_estimated": _estimate_token_count(wrapped_prompt),
                            "output_tokens_estimated": _estimate_token_count(raw_output_text),
                            "total_tokens_estimated": _estimate_token_count(wrapped_prompt) + _estimate_token_count(raw_output_text),
                            "source": "estimated_from_text",
                        }
                        self.last_transport_metadata["usage"] = estimated_usage
                        self._debug(f"[llm] usage {json.dumps(estimated_usage, ensure_ascii=False)}")
                    self._debug_block("codex_cli.output_file", raw_output_text)
                    output_payload = extract_json_object(raw_output_text)
                    if persist_session:
                        resolved_session_id = extract_codex_session_id(stdout) or (codex_session_id or "")
                        if not resolved_session_id:
                            raise OpenAIProviderError("Codex CLI persistent transport completed without a thread id.")
                        self.last_transport_metadata["codex_session_id"] = resolved_session_id
                        self._debug(f"[llm] codex_cli persist_success session_id={resolved_session_id}")
                        return output_payload
                    if strategy == "direct":
                        if set(output_payload.keys()) == {"json_payload_b64"}:
                            decoded_payload = decode_codex_json_payload(str(output_payload.get("json_payload_b64", "")).strip())
                            if not payload_satisfies_required_keys(decoded_payload, output_schema):
                                raise OpenAIProviderError(
                                    "Codex CLI direct strategy returned JSON but it did not satisfy the required top-level output keys."
                                )
                            self._debug_block(
                                "codex_cli.decoded_payload",
                                json.dumps(decoded_payload, ensure_ascii=False, indent=2),
                            )
                            return decoded_payload
                        payload_text = str(output_payload.get("json_payload", "")).strip()
                        self._debug_block("codex_cli.json_payload_text", payload_text)
                        decoded_payload = extract_json_object(payload_text)
                        if not payload_satisfies_required_keys(decoded_payload, output_schema):
                            raise OpenAIProviderError(
                                "Codex CLI direct strategy returned JSON but it did not satisfy the required top-level output keys."
                            )
                        self._debug_block(
                            "codex_cli.decoded_payload",
                            json.dumps(decoded_payload, ensure_ascii=False, indent=2),
                        )
                        return decoded_payload
                    payload_b64 = str(output_payload.get("json_payload_b64", "")).strip()
                    self._debug_block("codex_cli.json_payload_b64", payload_b64)
                    decoded_payload = decode_codex_json_payload(payload_b64)
                    if not payload_satisfies_required_keys(decoded_payload, output_schema):
                        raise OpenAIProviderError(
                            "Codex CLI wrapper strategy returned JSON but it did not satisfy the required top-level output keys."
                        )
                    self._debug_block(
                        "codex_cli.decoded_payload",
                        json.dumps(decoded_payload, ensure_ascii=False, indent=2),
                    )
                    return decoded_payload
                except OpenAIProviderError as exc:
                    self._debug(f"[llm] codex_cli decode_error strategy={strategy} error={exc}")
                    last_error = exc
                    continue

            if last_error is not None:
                self._debug(f"[llm] codex_cli final_error error={last_error}")
                raise last_error
            self._debug("[llm] codex_cli final_error no usable JSON payload")
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
        except (http.client.HTTPException, ConnectionError, OSError) as exc:
            raise OpenAIProviderError(f"OpenAI Responses API request failed: {exc}") from exc

    def _create_response_via_chat_completions(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        body = self._maybe_attach_agnes_chat_template_kwargs(body)
        if self.config.provider_name != "agnes":
            body["response_format"] = {"type": "json_object"}
        payload = self._run_with_agnes_transport_retry(
            operation="chat_completions",
            request=lambda: self._create_chat_completion_payload_via_transport(body),
        )
        self.last_transport_metadata["fallback_transport"] = "chat_completions"
        return payload

    def _create_chat_completion_via_python(self, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url=f"{self.config.api_base.rstrip('/')}/chat/completions",
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
            raise OpenAIProviderError(f"OpenAI Chat Completions API request failed: HTTP {exc.code} {details}") from exc
        except urllib.error.URLError as exc:
            raise OpenAIProviderError(f"OpenAI Chat Completions API request failed: {exc.reason}") from exc
        except (http.client.HTTPException, ConnectionError, OSError) as exc:
            raise OpenAIProviderError(f"OpenAI Chat Completions API request failed: {exc}") from exc

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

    def _create_response_via_powershell(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._invoke_via_powershell(
            url=f"{self.config.api_base.rstrip('/')}/responses",
            body=body,
            error_prefix="OpenAI Responses API request failed via powershell transport",
        )

    def _create_chat_completion_via_node(self, body: dict[str, Any]) -> dict[str, Any]:
        helper_path = Path(__file__).with_name("openai_transport_node.mjs")
        helper_input = {
            "url": f"{self.config.api_base.rstrip('/')}/chat/completions",
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
            raise OpenAIProviderError(f"OpenAI Chat Completions API request failed via node transport: {details}")

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise OpenAIProviderError(f"Node transport returned invalid JSON: {stdout[:300]}") from exc

        if not isinstance(payload, dict):
            raise OpenAIProviderError("Node transport returned a non-object payload.")

        if payload.get("ok") is not True:
            status = payload.get("status", "unknown")
            details = payload.get("body", "")
            raise OpenAIProviderError(f"OpenAI Chat Completions API request failed: HTTP {status} {details}")

        response_body = payload.get("response")
        if not isinstance(response_body, dict):
            raise OpenAIProviderError("Node transport response body was not a JSON object.")
        return response_body

    def _create_chat_completion_via_powershell(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._invoke_via_powershell(
            url=f"{self.config.api_base.rstrip('/')}/chat/completions",
            body=body,
            error_prefix="OpenAI Chat Completions API request failed via powershell transport",
        )

    def _invoke_via_powershell(self, *, url: str, body: dict[str, Any], error_prefix: str) -> dict[str, Any]:
        workspace_root = Path(self.config.workspace_root or os.getcwd())
        tmp_root = workspace_root / ".tmp"
        tmp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="ps-http-", dir=tmp_root) as temp_dir:
            body_path = Path(temp_dir) / "body.json"
            body_path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            script = "\n".join(
                [
                    "$ErrorActionPreference = 'Stop'",
                    f"$url = '{url}'",
                    f"$apiKey = '{self.config.api_key}'",
                    f"$bodyPath = '{str(body_path)}'",
                    "$headers = @{ Authorization = \"Bearer $apiKey\"; 'Content-Type' = 'application/json' }",
                    "$body = [System.IO.File]::ReadAllText($bodyPath, [System.Text.Encoding]::UTF8)",
                    "try {",
                    "  $response = Invoke-WebRequest -Uri $url -Headers $headers -Method Post -Body $body -UseBasicParsing -TimeoutSec 240",
                    "  $content = $response.Content",
                    "  try { $parsed = $content | ConvertFrom-Json } catch { $parsed = $null }",
                    "  $result = @{ ok = $true; status = [int]$response.StatusCode; response = $parsed; body = $content }",
                    "  $result | ConvertTo-Json -Depth 100 -Compress",
                    "} catch {",
                    "  $httpResponse = $_.Exception.Response",
                    "  if ($httpResponse) {",
                    "    $stream = $httpResponse.GetResponseStream()",
                    "    $reader = New-Object System.IO.StreamReader($stream)",
                    "    $errorBody = $reader.ReadToEnd()",
                    "    $statusCode = [int]$httpResponse.StatusCode",
                    "  } else {",
                    "    $errorBody = $_.Exception.Message",
                    "    $statusCode = 0",
                    "  }",
                    "  $result = @{ ok = $false; status = $statusCode; response = $null; body = $errorBody }",
                    "  $result | ConvertTo-Json -Depth 100 -Compress",
                    "  exit 1",
                    "}",
                ]
            )
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.config.timeout_seconds + 120,
                check=False,
            )
            stdout = completed.stdout.strip()
            stderr = completed.stderr.strip()
            raw = stdout or stderr
            if not raw:
                raise OpenAIProviderError(f"{error_prefix}: empty powershell response")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                snippet = raw[:500]
                raise OpenAIProviderError(f"{error_prefix}: invalid JSON wrapper {snippet}") from exc
            if not isinstance(payload, dict):
                raise OpenAIProviderError(f"{error_prefix}: non-object wrapper payload")
            if payload.get("ok") is not True:
                status = payload.get("status", "unknown")
                details = payload.get("body", "")
                raise OpenAIProviderError(f"{error_prefix}: HTTP {status} {details}")
            response_body = payload.get("response")
            if not isinstance(response_body, dict):
                raise OpenAIProviderError(f"{error_prefix}: response body was not a JSON object")
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
        command = ["node", "--use-system-ca", str(helper_path)]
        self._debug(f"[llm] codex_sdk subprocess_start command={' '.join(command)}")
        started_at = time.perf_counter()
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []

        def drain_stdout() -> None:
            assert process.stdout is not None
            for line in process.stdout:
                stdout_parts.append(line)

        def drain_stderr() -> None:
            assert process.stderr is not None
            for line in process.stderr:
                stderr_parts.append(line)
                self._debug(f"[llm] codex_sdk event {line.rstrip()}")

        stdout_thread = threading.Thread(target=drain_stdout, daemon=True)
        stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        assert process.stdin is not None
        process.stdin.write(json.dumps(helper_input, ensure_ascii=False))
        process.stdin.close()
        deadline = time.monotonic() + self.config.timeout_seconds + 15
        next_heartbeat = time.monotonic() + 15
        while process.poll() is None:
            now = time.monotonic()
            if now >= deadline:
                process.kill()
                process.wait()
                raise OpenAIProviderError(
                    f"Codex SDK transport timed out after {self.config.timeout_seconds + 15} seconds."
                )
            if now >= next_heartbeat:
                self._debug(
                    f"[llm] codex_sdk heartbeat elapsed={time.perf_counter() - started_at:.1f}s"
                )
                next_heartbeat = now + 15
            time.sleep(0.2)
        stdout_thread.join(timeout=2)
        stderr_thread.join(timeout=2)
        stdout = "".join(stdout_parts).strip()
        stderr = "".join(stderr_parts).strip()
        self._debug(
            f"[llm] codex_sdk subprocess_exit returncode={process.returncode} "
            f"elapsed={time.perf_counter() - started_at:.1f}s"
        )
        if process.returncode != 0:
            details = stderr or stdout or "unknown codex sdk transport error"
            raise OpenAIProviderError(f"Codex SDK transport failed: {details}")

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise OpenAIProviderError(f"Codex SDK transport returned invalid JSON: {stdout[:300]}") from exc

        if not isinstance(payload, dict):
            raise OpenAIProviderError("Codex SDK transport returned a non-object payload.")
        usage = _normalize_usage_payload(payload.get("usage"))
        if usage is not None:
            usage["source"] = "codex_sdk"
            self.last_transport_metadata["usage"] = usage
            self._debug(f"[llm] usage {json.dumps(usage, ensure_ascii=False)}")
        self.last_transport_metadata["sdk_module_path"] = str(payload.get("sdk_module_path", ""))
        final_response = str(payload.get("final_response", "")).strip()
        self._debug_block("codex_sdk.final_response", final_response)
        return extract_json_object(final_response)
