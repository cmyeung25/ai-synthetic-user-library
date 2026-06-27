from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from pathlib import Path
import threading
from typing import Any

from ai_validation_swarm.domain.models import PersonaSkill


METADATA_SCHEMA_VERSION = "metadata-store/v2"
METADATA_DB_FILENAME = "metadata.sqlite3"
_METADATA_WRITE_LOCK = threading.Lock()


def metadata_db_path(index_root: Path) -> Path:
    return index_root / METADATA_DB_FILENAME


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _connect(db_path: Path) -> sqlite3.Connection:
    _ensure_parent(db_path)
    connection = sqlite3.connect(str(db_path), timeout=30.0)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute("PRAGMA busy_timeout = 30000")
    _ensure_schema(connection)
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata_store_info (
            info_key TEXT PRIMARY KEY,
            info_value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS run_records (
            run_id TEXT PRIMARY KEY,
            run_kind TEXT NOT NULL,
            entrypoint TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            output_path TEXT NOT NULL,
            primary_artifact_path TEXT NOT NULL,
            brief_id TEXT NOT NULL DEFAULT '',
            persona_id TEXT NOT NULL DEFAULT '',
            research_goal TEXT NOT NULL DEFAULT '',
            interview_mode TEXT NOT NULL DEFAULT '',
            provider_name TEXT NOT NULL DEFAULT '',
            model_name TEXT NOT NULL DEFAULT '',
            selected_persona_count INTEGER NOT NULL DEFAULT 0,
            successful_response_count INTEGER,
            failed_response_count INTEGER,
            error_count INTEGER,
            request_json TEXT NOT NULL,
            result_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_run_records_kind_status_created
            ON run_records(run_kind, status, created_at);

        CREATE TABLE IF NOT EXISTS artifact_records (
            run_id TEXT NOT NULL,
            artifact_rel_path TEXT NOT NULL,
            artifact_path TEXT NOT NULL,
            artifact_type TEXT NOT NULL DEFAULT '',
            exists_on_disk INTEGER NOT NULL DEFAULT 0,
            size_bytes INTEGER,
            PRIMARY KEY (run_id, artifact_rel_path),
            FOREIGN KEY (run_id) REFERENCES run_records(run_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_artifact_records_run_id
            ON artifact_records(run_id);

        CREATE TABLE IF NOT EXISTS persona_records (
            synthetic_user_id TEXT PRIMARY KEY,
            panel_role TEXT NOT NULL DEFAULT '',
            locale_pack TEXT NOT NULL DEFAULT '',
            skill_version TEXT NOT NULL DEFAULT '',
            version_folder TEXT NOT NULL,
            profile_json_path TEXT NOT NULL,
            audit_json_path TEXT NOT NULL,
            narrative_path TEXT NOT NULL,
            artifact_root TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_persona_records_role_locale
            ON persona_records(panel_role, locale_pack, active);

        CREATE TABLE IF NOT EXISTS persona_selection_records (
            synthetic_user_id TEXT PRIMARY KEY,
            panel_role TEXT NOT NULL DEFAULT '',
            locale_pack TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL DEFAULT '',
            location_type TEXT NOT NULL DEFAULT '',
            age_band TEXT NOT NULL DEFAULT '',
            gender TEXT NOT NULL DEFAULT '',
            income_band TEXT NOT NULL DEFAULT '',
            education_band TEXT NOT NULL DEFAULT '',
            occupation_band TEXT NOT NULL DEFAULT '',
            occupation_title TEXT NOT NULL DEFAULT '',
            family_structure TEXT NOT NULL DEFAULT '',
            life_stage TEXT NOT NULL DEFAULT '',
            purchase_authority_type TEXT NOT NULL DEFAULT '',
            employment_stability TEXT NOT NULL DEFAULT '',
            workflow_maturity TEXT NOT NULL DEFAULT '',
            budget_flexibility TEXT NOT NULL DEFAULT '',
            price_sensitivity TEXT NOT NULL DEFAULT '',
            privacy_risk_tolerance TEXT NOT NULL DEFAULT '',
            privacy_concern TEXT NOT NULL DEFAULT '',
            digital_literacy_ceiling TEXT NOT NULL DEFAULT '',
            tech_savviness TEXT NOT NULL DEFAULT '',
            decision_speed TEXT NOT NULL DEFAULT '',
            trust_threshold TEXT NOT NULL DEFAULT '',
            trust_style TEXT NOT NULL DEFAULT '',
            proof_threshold TEXT NOT NULL DEFAULT '',
            cash_flow_volatility TEXT NOT NULL DEFAULT '',
            market_tags_json TEXT NOT NULL DEFAULT '[]',
            quality_score REAL,
            uniqueness_score REAL,
            active INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (synthetic_user_id) REFERENCES persona_records(synthetic_user_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_persona_selection_role_locale
            ON persona_selection_records(panel_role, locale_pack, active);

        CREATE INDEX IF NOT EXISTS idx_persona_selection_price_trust
            ON persona_selection_records(price_sensitivity, trust_style, active);

        CREATE TABLE IF NOT EXISTS persona_trait_assignments (
            synthetic_user_id TEXT NOT NULL,
            trait_key TEXT NOT NULL,
            trait_value TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            assignment_rank INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (synthetic_user_id, trait_key, trait_value),
            FOREIGN KEY (synthetic_user_id) REFERENCES persona_records(synthetic_user_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_persona_trait_lookup
            ON persona_trait_assignments(trait_key, trait_value);

        CREATE TABLE IF NOT EXISTS persona_similarity_edges (
            source_persona_id TEXT NOT NULL,
            target_persona_id TEXT NOT NULL,
            similarity_score REAL NOT NULL,
            distinctiveness_score REAL,
            similarity_dimensions_json TEXT NOT NULL DEFAULT '{}',
            high_similarity_dimensions_json TEXT NOT NULL DEFAULT '[]',
            evidence_artifact_path TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (source_persona_id, target_persona_id),
            FOREIGN KEY (source_persona_id) REFERENCES persona_records(synthetic_user_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_persona_similarity_source
            ON persona_similarity_edges(source_persona_id, similarity_score DESC);
        """
    )
    connection.execute(
        """
        INSERT INTO metadata_store_info(info_key, info_value)
        VALUES('schema_version', ?)
        ON CONFLICT(info_key) DO UPDATE SET info_value=excluded.info_value
        """,
        (METADATA_SCHEMA_VERSION,),
    )
    connection.commit()


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _quality_score_from_payload(payload: dict[str, Any] | None) -> float | None:
    if not isinstance(payload, dict):
        return None
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        return None
    overall = _optional_float(scores.get("overall"))
    if overall is not None:
        return overall
    numeric_scores = [_optional_float(value) for value in scores.values()]
    numeric_scores = [value for value in numeric_scores if value is not None]
    if not numeric_scores:
        return None
    return round(sum(numeric_scores) / len(numeric_scores), 4)


def _uniqueness_score_from_payload(payload: dict[str, Any] | None) -> float | None:
    if not isinstance(payload, dict):
        return None
    distinctiveness = _optional_float(payload.get("distinctiveness_score"))
    if distinctiveness is not None:
        return distinctiveness
    overall_similarity = _optional_float(payload.get("overall_similarity_score"))
    if overall_similarity is None:
        return None
    return round(1.0 - overall_similarity, 4)


def _trust_style(persona: PersonaSkill) -> str:
    axes = persona.profile.human_difference_axes if isinstance(persona.profile.human_difference_axes, dict) else {}
    return _text(axes.get("trust_style") or persona.seed.trust_threshold)


def _market_tags(persona: PersonaSkill) -> list[str]:
    locale_pack = _text(persona.seed.locale_pack)
    panel_role = _text(persona.seed.panel_role)
    location_type = _text(persona.seed.location_type)
    occupation_band = _text(persona.seed.occupation_band)
    life_stage = _text(persona.seed.life_stage)
    tags = [
        f"locale:{locale_pack}" if locale_pack else "",
        f"panel_role:{panel_role}" if panel_role else "",
        f"location_type:{location_type}" if location_type else "",
        f"occupation_band:{occupation_band}" if occupation_band else "",
        f"life_stage:{life_stage}" if life_stage else "",
    ]
    return sorted(tag for tag in tags if tag)


def _trait_assignment_rows(persona: PersonaSkill, updated_at: str, market_tags: list[str], trust_style: str) -> list[tuple[str, str, str, str, str, int, str]]:
    identity = persona.profile.basic_identity
    technology = persona.profile.technology_profile
    economic = persona.profile.economic_profile
    assignments: list[tuple[str, Any, str, str]] = [
        ("panel_role", persona.seed.panel_role, "seed.panel_role", "seed"),
        ("locale_pack", persona.seed.locale_pack, "seed.locale_pack", "seed"),
        ("location_type", persona.seed.location_type, "seed.location_type", "seed"),
        ("age_band", persona.seed.age_band, "seed.age_band", "seed"),
        ("occupation_band", persona.seed.occupation_band, "seed.occupation_band", "seed"),
        ("occupation_title", persona.seed.occupation_title, "seed.occupation_title", "seed"),
        ("income_band", persona.seed.income_band, "seed.income_band", "seed"),
        ("education_band", persona.seed.education_band, "seed.education_band", "seed"),
        ("purchase_authority_type", persona.seed.purchase_authority_type, "seed.purchase_authority_type", "seed"),
        ("employment_stability", persona.seed.employment_stability, "seed.employment_stability", "seed"),
        ("workflow_maturity", persona.seed.workflow_maturity, "seed.workflow_maturity", "seed"),
        ("budget_flexibility", persona.seed.budget_flexibility, "seed.budget_flexibility", "seed"),
        ("privacy_risk_tolerance", persona.seed.privacy_risk_tolerance, "seed.privacy_risk_tolerance", "seed"),
        ("digital_literacy_ceiling", persona.seed.digital_literacy_ceiling, "seed.digital_literacy_ceiling", "seed"),
        ("decision_speed", persona.seed.decision_speed, "seed.decision_speed", "seed"),
        ("trust_threshold", persona.seed.trust_threshold, "seed.trust_threshold", "seed"),
        ("proof_threshold", persona.seed.proof_threshold, "seed.proof_threshold", "seed"),
        ("cash_flow_volatility", persona.seed.cash_flow_volatility, "seed.cash_flow_volatility", "seed"),
        ("life_stage", persona.seed.life_stage, "seed.life_stage", "seed"),
        ("gender", identity.get("gender"), "basic_identity.gender", "profile"),
        ("location", identity.get("location"), "basic_identity.location", "profile"),
        ("family_structure", identity.get("family_structure"), "basic_identity.family_structure", "profile"),
        ("language", identity.get("language", []), "basic_identity.language", "profile"),
        ("tech_savviness", technology.get("tech_savviness"), "technology_profile.tech_savviness", "profile"),
        ("ai_familiarity", technology.get("ai_familiarity"), "technology_profile.ai_familiarity", "profile"),
        ("privacy_concern", technology.get("privacy_concern"), "technology_profile.privacy_concern", "profile"),
        ("price_sensitivity", economic.get("price_sensitivity"), "economic_profile.price_sensitivity", "profile"),
        ("subscription_tolerance", economic.get("subscription_tolerance"), "economic_profile.subscription_tolerance", "profile"),
        ("trust_style", trust_style, "human_difference_axes.trust_style", "derived"),
        ("market_tag", market_tags, "derived.market_tags", "derived"),
    ]

    rows: list[tuple[str, str, str, str, str, int, str]] = []
    synthetic_user_id = persona.profile.synthetic_user_id
    for trait_key, raw_value, source_path, source_kind in assignments:
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        for rank, value in enumerate(values):
            text_value = _text(value)
            if not text_value:
                continue
            rows.append(
                (
                    synthetic_user_id,
                    trait_key,
                    text_value,
                    source_path,
                    source_kind,
                    rank,
                    updated_at,
                )
            )
    return rows


def persist_run_contract_metadata(index_root: Path, contract_path: Path, contract_payload: dict[str, Any]) -> None:
    db_path = metadata_db_path(index_root)
    request = dict(contract_payload.get("request", {}))
    result = dict(contract_payload.get("result", {}))
    run_id = str(result.get("run_id") or request.get("run_id") or "")
    output_path = Path(str(result.get("output_path", contract_path.parent)))
    artifact_paths = list(result.get("artifact_paths", [])) if isinstance(result.get("artifact_paths", []), list) else []

    with _METADATA_WRITE_LOCK:
        with closing(_connect(db_path)) as connection:
            connection.execute(
                """
                INSERT INTO run_records(
                    run_id,
                    run_kind,
                    entrypoint,
                    status,
                    created_at,
                    started_at,
                    finished_at,
                    output_path,
                    primary_artifact_path,
                    brief_id,
                    persona_id,
                    research_goal,
                    interview_mode,
                    provider_name,
                    model_name,
                    selected_persona_count,
                    successful_response_count,
                    failed_response_count,
                    error_count,
                    request_json,
                    result_json
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    run_kind=excluded.run_kind,
                    entrypoint=excluded.entrypoint,
                    status=excluded.status,
                    created_at=excluded.created_at,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    output_path=excluded.output_path,
                    primary_artifact_path=excluded.primary_artifact_path,
                    brief_id=excluded.brief_id,
                    persona_id=excluded.persona_id,
                    research_goal=excluded.research_goal,
                    interview_mode=excluded.interview_mode,
                    provider_name=excluded.provider_name,
                    model_name=excluded.model_name,
                    selected_persona_count=excluded.selected_persona_count,
                    successful_response_count=excluded.successful_response_count,
                    failed_response_count=excluded.failed_response_count,
                    error_count=excluded.error_count,
                    request_json=excluded.request_json,
                    result_json=excluded.result_json
                """,
                (
                    run_id,
                    str(request.get("run_kind", "")),
                    str(request.get("entrypoint", "")),
                    str(result.get("status", "")),
                    str(request.get("created_at", "")),
                    str(result.get("started_at", "")),
                    str(result.get("finished_at", "")) or None,
                    str(output_path),
                    str(result.get("primary_artifact_path", "")),
                    str(request.get("brief_id", "")),
                    str(request.get("persona_id", "")),
                    str(request.get("research_goal", "")),
                    str(request.get("interview_mode", "")),
                    str(result.get("provider_name", "")),
                    str(result.get("model_name", "")),
                    len(list(result.get("selected_persona_ids", []))) if isinstance(result.get("selected_persona_ids", []), list) else 0,
                    result.get("successful_response_count"),
                    result.get("failed_response_count"),
                    result.get("error_count"),
                    _json_dumps(request),
                    _json_dumps(result),
                ),
            )
            connection.execute("DELETE FROM artifact_records WHERE run_id = ?", (run_id,))
            for artifact_rel_path in artifact_paths:
                artifact_path = output_path / str(artifact_rel_path)
                exists_on_disk = artifact_path.exists()
                size_bytes = artifact_path.stat().st_size if exists_on_disk else None
                connection.execute(
                    """
                    INSERT INTO artifact_records(
                        run_id,
                        artifact_rel_path,
                        artifact_path,
                        artifact_type,
                        exists_on_disk,
                        size_bytes
                    )
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        str(artifact_rel_path),
                        str(artifact_path),
                        artifact_path.suffix.lstrip("."),
                        1 if exists_on_disk else 0,
                        size_bytes,
                    ),
                )
            connection.commit()


def persist_persona_metadata(
    *,
    index_root: Path,
    persona: PersonaSkill,
    artifact_root: Path,
    profile_json_path: Path,
    audit_json_path: Path,
    narrative_path: Path,
    created_at: str,
    updated_at: str,
    active: bool = True,
    duplicate_report_payload: dict[str, Any] | None = None,
    quality_report_payload: dict[str, Any] | None = None,
) -> None:
    db_path = metadata_db_path(index_root)
    trust_style = _trust_style(persona)
    market_tags = _market_tags(persona)
    quality_score = _quality_score_from_payload(quality_report_payload)
    uniqueness_score = _uniqueness_score_from_payload(duplicate_report_payload)
    identity = persona.profile.basic_identity
    technology = persona.profile.technology_profile
    economic = persona.profile.economic_profile
    with _METADATA_WRITE_LOCK:
        with closing(_connect(db_path)) as connection:
            connection.execute(
            """
            INSERT INTO persona_records(
                synthetic_user_id,
                panel_role,
                locale_pack,
                skill_version,
                version_folder,
                profile_json_path,
                audit_json_path,
                narrative_path,
                artifact_root,
                active,
                created_at,
                updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(synthetic_user_id) DO UPDATE SET
                panel_role=excluded.panel_role,
                locale_pack=excluded.locale_pack,
                skill_version=excluded.skill_version,
                version_folder=excluded.version_folder,
                profile_json_path=excluded.profile_json_path,
                audit_json_path=excluded.audit_json_path,
                narrative_path=excluded.narrative_path,
                artifact_root=excluded.artifact_root,
                active=excluded.active,
                updated_at=excluded.updated_at
            """,
            (
                persona.profile.synthetic_user_id,
                persona.seed.panel_role,
                persona.seed.locale_pack,
                persona.skill_version,
                str(artifact_root),
                str(profile_json_path),
                str(audit_json_path),
                str(narrative_path),
                str(artifact_root),
                1 if active else 0,
                created_at,
                updated_at,
            ),
        )
            connection.execute(
            """
            INSERT INTO persona_selection_records(
                synthetic_user_id,
                panel_role,
                locale_pack,
                location,
                location_type,
                age_band,
                gender,
                income_band,
                education_band,
                occupation_band,
                occupation_title,
                family_structure,
                life_stage,
                purchase_authority_type,
                employment_stability,
                workflow_maturity,
                budget_flexibility,
                price_sensitivity,
                privacy_risk_tolerance,
                privacy_concern,
                digital_literacy_ceiling,
                tech_savviness,
                decision_speed,
                trust_threshold,
                trust_style,
                proof_threshold,
                cash_flow_volatility,
                market_tags_json,
                quality_score,
                uniqueness_score,
                active,
                updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(synthetic_user_id) DO UPDATE SET
                panel_role=excluded.panel_role,
                locale_pack=excluded.locale_pack,
                location=excluded.location,
                location_type=excluded.location_type,
                age_band=excluded.age_band,
                gender=excluded.gender,
                income_band=excluded.income_band,
                education_band=excluded.education_band,
                occupation_band=excluded.occupation_band,
                occupation_title=excluded.occupation_title,
                family_structure=excluded.family_structure,
                life_stage=excluded.life_stage,
                purchase_authority_type=excluded.purchase_authority_type,
                employment_stability=excluded.employment_stability,
                workflow_maturity=excluded.workflow_maturity,
                budget_flexibility=excluded.budget_flexibility,
                price_sensitivity=excluded.price_sensitivity,
                privacy_risk_tolerance=excluded.privacy_risk_tolerance,
                privacy_concern=excluded.privacy_concern,
                digital_literacy_ceiling=excluded.digital_literacy_ceiling,
                tech_savviness=excluded.tech_savviness,
                decision_speed=excluded.decision_speed,
                trust_threshold=excluded.trust_threshold,
                trust_style=excluded.trust_style,
                proof_threshold=excluded.proof_threshold,
                cash_flow_volatility=excluded.cash_flow_volatility,
                market_tags_json=excluded.market_tags_json,
                quality_score=excluded.quality_score,
                uniqueness_score=excluded.uniqueness_score,
                active=excluded.active,
                updated_at=excluded.updated_at
            """,
            (
                persona.profile.synthetic_user_id,
                persona.seed.panel_role,
                persona.seed.locale_pack,
                _text(identity.get("location")),
                persona.seed.location_type,
                persona.seed.age_band,
                _text(identity.get("gender")),
                persona.seed.income_band,
                persona.seed.education_band,
                persona.seed.occupation_band,
                persona.seed.occupation_title,
                _text(identity.get("family_structure")),
                persona.seed.life_stage,
                persona.seed.purchase_authority_type,
                persona.seed.employment_stability,
                persona.seed.workflow_maturity,
                persona.seed.budget_flexibility,
                _text(economic.get("price_sensitivity") or persona.seed.budget_flexibility),
                persona.seed.privacy_risk_tolerance,
                _text(technology.get("privacy_concern")),
                persona.seed.digital_literacy_ceiling,
                _text(technology.get("tech_savviness")),
                persona.seed.decision_speed,
                persona.seed.trust_threshold,
                trust_style,
                persona.seed.proof_threshold,
                persona.seed.cash_flow_volatility,
                _json_dumps(market_tags),
                quality_score,
                uniqueness_score,
                1 if active else 0,
                updated_at,
            ),
        )
            connection.execute(
                "DELETE FROM persona_trait_assignments WHERE synthetic_user_id = ?",
                (persona.profile.synthetic_user_id,),
            )
            for row in _trait_assignment_rows(persona, updated_at, market_tags, trust_style):
                connection.execute(
                    """
                    INSERT INTO persona_trait_assignments(
                        synthetic_user_id,
                        trait_key,
                        trait_value,
                        source_path,
                        source_kind,
                        assignment_rank,
                        updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
            connection.execute(
                "DELETE FROM persona_similarity_edges WHERE source_persona_id = ?",
                (persona.profile.synthetic_user_id,),
            )
            pair_reports = duplicate_report_payload.get("pair_reports", []) if isinstance(duplicate_report_payload, dict) else []
            high_similarity_dimensions = (
                duplicate_report_payload.get("high_similarity_dimensions", [])
                if isinstance(duplicate_report_payload, dict)
                else []
            )
            evidence_artifact_path = str(artifact_root / "duplicate_report.json") if duplicate_report_payload else ""
            for pair_report in pair_reports:
                if not isinstance(pair_report, dict):
                    continue
                target_persona_id = _text(pair_report.get("persona_id"))
                similarity_score = _optional_float(pair_report.get("overall_similarity_score"))
                if not target_persona_id or similarity_score is None:
                    continue
                connection.execute(
                    """
                    INSERT INTO persona_similarity_edges(
                        source_persona_id,
                        target_persona_id,
                        similarity_score,
                        distinctiveness_score,
                        similarity_dimensions_json,
                        high_similarity_dimensions_json,
                        evidence_artifact_path,
                        updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        persona.profile.synthetic_user_id,
                        target_persona_id,
                        similarity_score,
                        round(1.0 - similarity_score, 4),
                        _json_dumps(pair_report.get("dimensions", {})),
                        _json_dumps(high_similarity_dimensions),
                        evidence_artifact_path,
                        updated_at,
                    ),
                )
            connection.commit()
