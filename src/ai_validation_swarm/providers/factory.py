from __future__ import annotations

from collections.abc import Callable

from ai_validation_swarm.providers.base import BaseProvider
from ai_validation_swarm.providers.mock import MockProvider
from ai_validation_swarm.providers.openai_client import OpenAIResponsesClient, load_openai_provider_config
from ai_validation_swarm.providers.openai_validation import OpenAIValidationProvider


def _build_openai_client_for_provider(provider_name: str) -> OpenAIResponsesClient:
    if provider_name == "codex":
        config = load_openai_provider_config(
            prefer_codex_auth=True,
            force_transport="codex_cli",
            force_provider_name="codex",
            timeout_default=240,
        )
    elif provider_name == "codex-sdk":
        config = load_openai_provider_config(
            prefer_codex_auth=True,
            force_transport="codex_sdk_node",
            force_provider_name="codex",
            timeout_default=240,
        )
    elif provider_name == "agnes":
        config = load_openai_provider_config(force_provider_name="agnes")
    else:
        config = load_openai_provider_config(force_provider_name="openai")
    return OpenAIResponsesClient(config)


def build_provider(
    name: str,
    *,
    client_builder: Callable[[str], OpenAIResponsesClient] | None = None,
) -> BaseProvider:
    provider_name = name.strip().lower()
    if provider_name == "mock":
        return MockProvider()
    if provider_name in {"openai", "agnes", "codex", "codex-sdk"}:
        builder = client_builder or _build_openai_client_for_provider
        return OpenAIValidationProvider(builder(provider_name), provider_name=provider_name)
    raise ValueError(
        f"Unsupported provider '{name}'. Supported providers: mock, openai, agnes, codex, codex-sdk."
    )
