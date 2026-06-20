from __future__ import annotations

from ai_validation_swarm.providers.base import BaseProvider
from ai_validation_swarm.providers.mock import MockProvider


def build_provider(name: str) -> BaseProvider:
    provider_name = name.strip().lower()
    if provider_name == "mock":
        return MockProvider()
    raise ValueError(f"Unsupported provider '{name}'. Only 'mock' is implemented in this POC.")
