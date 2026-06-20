from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

RULE_OWNED_PROFILE_TARGETS = {
    "basic_identity",
    "audit_evidence_layer",
    "generation_status",
}


@dataclass(frozen=True, slots=True)
class PersonaSectionSpec:
    name: str
    targets: tuple[str, ...]
    prompt_version: str
    owner: str = "llm"
    required: bool = True
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PersonaSectionRegistry:
    def __init__(self, sections: Iterable[PersonaSectionSpec] = ()) -> None:
        self._sections: dict[str, PersonaSectionSpec] = {}
        for section in sections:
            self.register(section)

    def register(self, section: PersonaSectionSpec) -> None:
        if section.name in self._sections:
            raise ValueError(f"Persona section already registered: {section.name}")
        if section.owner not in {"llm", "rules", "renderer"}:
            raise ValueError(f"Unsupported section owner: {section.owner}")
        if not section.targets:
            raise ValueError(f"Persona section must define at least one target: {section.name}")
        forbidden = sorted(target for target in section.targets if target in RULE_OWNED_PROFILE_TARGETS)
        if forbidden:
            raise ValueError(
                f"Persona section '{section.name}' targets rule-owned profile fields: {', '.join(forbidden)}"
            )
        self._sections[section.name] = section

    def get(self, name: str) -> PersonaSectionSpec:
        try:
            return self._sections[name]
        except KeyError as exc:
            raise KeyError(f"Unknown persona section: {name}") from exc

    def enabled(self, names: Iterable[str] | None = None) -> list[PersonaSectionSpec]:
        if names is None:
            return list(self._sections.values())
        requested = list(dict.fromkeys(names))
        return [self.get(name) for name in requested]

    def manifest(self, names: Iterable[str] | None = None) -> list[dict[str, Any]]:
        return [section.to_dict() for section in self.enabled(names)]

    def resolve_generation_sections(self, optional_names: Iterable[str] | None = None) -> list[PersonaSectionSpec]:
        requested = set(optional_names or ())
        for name in requested:
            self.get(name)
        return [
            section
            for section in self._sections.values()
            if section.required or section.name in requested
        ]


CORE_SECTIONS = (
    PersonaSectionSpec(
        name="childhood_environment",
        targets=("childhood_environment",),
        prompt_version="childhood-environment/v3_2.md",
        description="Ordinary childhood context, caregiver dynamics, early lessons, and bounded links to adult judgment.",
    ),
    PersonaSectionSpec(
        name="biography",
        targets=("canonical_biography", "life_story"),
        prompt_version="persona-biography/v3_2.md",
        description="Life arc, decade scenes, current identity, and product-relevant memories.",
    ),
    PersonaSectionSpec(
        name="behaviour_and_decisions",
        targets=(
            "personality_belief",
            "values",
            "behavior_profile",
            "problem_context",
            "workflow_adoption_model",
            "product_reaction_rules",
            "contradiction_map",
            "deep_research_notes",
            "panel_role_profile",
        ),
        prompt_version="persona-synthesis/v3_2.md",
        description="Motivation, tensions, adoption, objections, and founder-misread risks.",
    ),
    PersonaSectionSpec(
        name="economics_and_pricing",
        targets=("economic_profile", "pricing_logic", "spending_and_leisure_patterns"),
        prompt_version="persona-economics/v3_2.md",
        description="Contextual spending, authority, pricing, and category-specific trade-offs.",
    ),
    PersonaSectionSpec(
        name="technology_and_products",
        targets=(
            "technology_profile",
            "domain_fit",
            "cross_domain_product_reaction_model",
            "product_discovery_paths",
        ),
        prompt_version="persona-products/v3_2.md",
        description="Technology exposure, discovery, domain fit, and cross-domain reactions.",
    ),
    PersonaSectionSpec(
        name="local_grounding",
        targets=("local_grounding_layer", "cultural_texture"),
        prompt_version="local-grounding/v3_2.md",
        description="Local scenes and market context that affect product behaviour without stereotyping.",
    ),
    PersonaSectionSpec(
        name="sensitive_scenarios",
        targets=(
            "sensitive_reality_layer",
            "identity_and_inclusion_reaction",
            "sensitive_scenario_reactions",
            "sensitive_scenario_salience",
            "identity_language",
        ),
        prompt_version="sensitive-scenarios/v3_2.md",
        description="Contextual privacy, identity, family, workplace, finance, and wellbeing reactions.",
    ),
    PersonaSectionSpec(
        name="voiceprint",
        targets=("persona_voiceprint", "objection_language_style"),
        prompt_version="persona-voiceprint/v3_2.md",
        description="Individual speech, disagreement, polite interest, and payment-intent language.",
    ),
)


LIFESTYLE_HOBBIES_SECTION = PersonaSectionSpec(
    name="lifestyle_and_hobbies",
    targets=(
        "interests_and_hobbies",
        "media_and_content_diet",
        "daily_micro_behaviours",
        "social_circle_and_communities",
        "taste_and_aesthetic_preferences",
        "personal_environment",
        "emotional_regulation_style",
        "hidden_habits",
        "identity_symbols",
    ),
    prompt_version="lifestyle-hobbies/v3_2.md",
    description="Interests and ordinary-life details whose effects are connected to product behaviour.",
)


def build_default_v3_2_registry() -> PersonaSectionRegistry:
    return PersonaSectionRegistry((*CORE_SECTIONS, LIFESTYLE_HOBBIES_SECTION))


DEFAULT_V3_2_REGISTRY = build_default_v3_2_registry()
