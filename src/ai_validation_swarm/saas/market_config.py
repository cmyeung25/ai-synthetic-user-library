from __future__ import annotations

from pathlib import Path

from ai_validation_swarm.saas.models import MarketDistributionConfig
from ai_validation_swarm.storage.files import read_json


def _require_object(value: object, *, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"Field '{field_name}' must be a non-empty JSON object.")
    return value


def _require_list(value: object, *, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"Field '{field_name}' must be a JSON array.")
    return value


def _validate_weight_map(weights: dict[str, object]) -> dict[str, dict[str, float]]:
    normalized: dict[str, dict[str, float]] = {}
    for dimension, raw_items in weights.items():
        item_map = _require_object(raw_items, field_name=f"weights.{dimension}")
        normalized_items: dict[str, float] = {}
        total = 0.0
        for item_key, raw_weight in item_map.items():
            if not isinstance(raw_weight, (int, float)):
                raise ValueError(f"Weight '{dimension}.{item_key}' must be numeric.")
            weight = float(raw_weight)
            if weight <= 0:
                raise ValueError(f"Weight '{dimension}.{item_key}' must be greater than 0.")
            normalized_items[str(item_key)] = weight
            total += weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Weights for dimension '{dimension}' must sum to 1.0 (+/- 0.01). Current total: {total:.4f}"
            )
        normalized[str(dimension)] = normalized_items
    return normalized


def load_market_distribution_config(path: Path) -> MarketDistributionConfig:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("Market distribution config must be a JSON object.")

    required_fields = [
        "config_version",
        "market_id",
        "display_name",
        "default_locale",
        "target_population",
        "weights",
    ]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    weights = _validate_weight_map(_require_object(payload["weights"], field_name="weights"))
    quota_rules = _require_list(payload.get("quota_rules", []), field_name="quota_rules")
    exclusion_rules = _require_list(payload.get("exclusion_rules", []), field_name="exclusion_rules")
    overlays = _require_list(payload.get("overlays", []), field_name="overlays")

    return MarketDistributionConfig(
        config_version=str(payload["config_version"]),
        market_id=str(payload["market_id"]),
        display_name=str(payload["display_name"]),
        default_locale=str(payload["default_locale"]),
        target_population=str(payload["target_population"]),
        weights=weights,
        quota_rules=[rule for rule in quota_rules if isinstance(rule, dict)],
        exclusion_rules=[rule for rule in exclusion_rules if isinstance(rule, dict)],
        overlays=[str(item) for item in overlays],
        metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
    )

