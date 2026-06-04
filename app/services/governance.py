"""Governance registry helpers for source policy and evidence scaffolding."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from scraper.connectors import (
    ConnectorContext,
    ConnectorValidationError,
    create_connector,
    list_connector_metadata,
)


POLICY_TIERS: Dict[str, Dict[str, str]] = {
    "A": {"label": "Official API", "default_action": "allow_with_quotas"},
    "B": {"label": "Licensed feed", "default_action": "allow_with_contract_terms"},
    "C": {"label": "Owned or user-provided source", "default_action": "allow_with_ownership_warning"},
    "D": {"label": "Managed collection vendor", "default_action": "allow_after_vendor_review"},
    "E": {"label": "Custom scraper", "default_action": "disabled_until_explicit_approval"},
    "X": {"label": "Prohibited or high-risk source", "default_action": "blocked"},
}
SOURCE_STATUSES = {"pending", "active", "paused", "blocked", "retired"}
REQUIRED_TABLES = {
    "sources",
    "source_credentials",
    "source_records",
    "connector_runs",
    "audit_events",
    "ai_outputs",
    "evidence_links",
}
REQUIRED_INDEXES = {
    "idx_sources_policy_tier",
    "idx_sources_status",
    "idx_source_credentials_source_id",
    "idx_source_records_source_id",
    "idx_source_records_external_record_id",
    "idx_connector_runs_source_id",
    "idx_connector_runs_status",
    "idx_audit_events_actor_id",
    "idx_audit_events_object",
    "idx_ai_outputs_status",
    "idx_evidence_links_ai_output_id",
    "idx_evidence_links_source_record_id",
    "idx_evidence_links_video_id",
}
GOVERNANCE_MIGRATION_VERSION = "0002_governance_registry"


class GovernanceMigrationRequired(RuntimeError):
    """Raised when governance APIs are called before registry tables exist."""


def db_path_for_root(root_dir: str) -> Path:
    return Path(root_dir) / "data" / "governance.db"


def _initialize_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            checksum TEXT,
            applied_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    row = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version = ?",
        (GOVERNANCE_MIGRATION_VERSION,),
    ).fetchone()
    if not row:
        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                policy_tier TEXT NOT NULL CHECK (policy_tier IN ('A', 'B', 'C', 'D', 'E', 'X')),
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'paused', 'blocked', 'retired')),
                owner_user_id INTEGER,
                source_url TEXT,
                external_id TEXT,
                retention_days INTEGER,
                terms_url TEXT,
                policy_notes TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS source_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                secret_ref TEXT NOT NULL,
                byok INTEGER NOT NULL DEFAULT 1,
                rotation_status TEXT NOT NULL DEFAULT 'not_required',
                last_rotated_at TEXT,
                expires_at TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS source_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                external_record_id TEXT,
                record_type TEXT NOT NULL,
                title TEXT,
                url TEXT,
                published_at TEXT,
                captured_at TEXT DEFAULT (datetime('now', 'localtime')),
                content_hash TEXT,
                metadata_json TEXT,
                FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS connector_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
                records_seen INTEGER DEFAULT 0,
                records_created INTEGER DEFAULT 0,
                records_updated INTEGER DEFAULT 0,
                cost_estimate REAL DEFAULT 0,
                error_message TEXT,
                started_at TEXT,
                ended_at TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE SET NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER,
                action TEXT NOT NULL,
                object_type TEXT NOT NULL,
                object_id TEXT,
                metadata_json TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ai_outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                output_type TEXT NOT NULL,
                title TEXT,
                prompt_hash TEXT,
                provider_id TEXT,
                model_id TEXT,
                status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'reviewed', 'approved', 'rejected', 'exported')),
                content_text TEXT NOT NULL,
                metadata_json TEXT,
                created_by INTEGER,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS evidence_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ai_output_id INTEGER NOT NULL,
                source_id INTEGER,
                source_record_id INTEGER,
                video_id TEXT,
                claim_text TEXT,
                evidence_text TEXT,
                confidence REAL,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (ai_output_id) REFERENCES ai_outputs(id) ON DELETE CASCADE,
                FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE SET NULL,
                FOREIGN KEY (source_record_id) REFERENCES source_records(id) ON DELETE SET NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_sources_policy_tier ON sources(policy_tier)",
            "CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status)",
            "CREATE INDEX IF NOT EXISTS idx_source_credentials_source_id ON source_credentials(source_id)",
            "CREATE INDEX IF NOT EXISTS idx_source_records_source_id ON source_records(source_id)",
            "CREATE INDEX IF NOT EXISTS idx_source_records_external_record_id ON source_records(external_record_id)",
            "CREATE INDEX IF NOT EXISTS idx_connector_runs_source_id ON connector_runs(source_id)",
            "CREATE INDEX IF NOT EXISTS idx_connector_runs_status ON connector_runs(status)",
            "CREATE INDEX IF NOT EXISTS idx_audit_events_actor_id ON audit_events(actor_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_events_object ON audit_events(object_type, object_id)",
            "CREATE INDEX IF NOT EXISTS idx_ai_outputs_status ON ai_outputs(status)",
            "CREATE INDEX IF NOT EXISTS idx_evidence_links_ai_output_id ON evidence_links(ai_output_id)",
            "CREATE INDEX IF NOT EXISTS idx_evidence_links_source_record_id ON evidence_links(source_record_id)",
            "CREATE INDEX IF NOT EXISTS idx_evidence_links_video_id ON evidence_links(video_id)",
            f"INSERT INTO schema_migrations (version, checksum) VALUES ('{GOVERNANCE_MIGRATION_VERSION}', 'auto_initialized')",
        ]
        for stmt in ddl_statements:
            conn.execute(stmt)
        conn.commit()

    LAYOUTS_MIGRATION_VERSION = "0003_dashboard_layouts"
    layouts_row = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version = ?",
        (LAYOUTS_MIGRATION_VERSION,),
    ).fetchone()
    if not layouts_row:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_layouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                is_default INTEGER DEFAULT 0 CHECK (is_default IN (0, 1)),
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_widgets (
                id TEXT PRIMARY KEY,
                layout_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                width TEXT,
                height TEXT,
                collapsed INTEGER DEFAULT 0 CHECK (collapsed IN (0, 1)),
                config_json TEXT,
                FOREIGN KEY (layout_id) REFERENCES dashboard_layouts(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_layout_id ON dashboard_widgets(layout_id)")
        conn.execute(
            "INSERT INTO schema_migrations (version, checksum) VALUES (?, 'auto_initialized')",
            (LAYOUTS_MIGRATION_VERSION,)
        )
        conn.execute("INSERT OR IGNORE INTO dashboard_layouts (name, is_default) VALUES ('Default', 1)")
        conn.commit()



def _connect(root_dir: str) -> sqlite3.Connection:
    db_path = db_path_for_root(root_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _initialize_schema(conn)
    except Exception:
        conn.rollback()
        conn.close()
        raise
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _object_names(conn: sqlite3.Connection, object_type: str, expected: Iterable[str]) -> List[str]:
    expected_names = list(expected)
    if not expected_names:
        return []
    placeholders = ",".join("?" for _ in expected_names)
    rows = conn.execute(
        f"SELECT name FROM sqlite_master WHERE type=? AND name IN ({placeholders})",
        (object_type, *expected_names),
    ).fetchall()
    return sorted(row["name"] for row in rows)


def _applied_migrations(conn: sqlite3.Connection) -> Dict[str, str]:
    if not _table_exists(conn, "schema_migrations"):
        return {}
    rows = conn.execute("SELECT version, checksum FROM schema_migrations").fetchall()
    return {row["version"]: row["checksum"] for row in rows}


def registry_ready(root_dir: str) -> bool:
    db_path = db_path_for_root(root_dir)
    if not db_path.exists():
        return False
    conn = _connect(root_dir)
    try:
        return (
            all(_table_exists(conn, table) for table in REQUIRED_TABLES)
            and len(_object_names(conn, "index", REQUIRED_INDEXES)) == len(REQUIRED_INDEXES)
        )
    finally:
        conn.close()


def registry_readiness(root_dir: str) -> Dict[str, Any]:
    db_path = db_path_for_root(root_dir)
    required_tables = sorted(REQUIRED_TABLES)
    required_indexes = sorted(REQUIRED_INDEXES)
    if not db_path.exists():
        return {
            "registry_ready": False,
            "migration_version": GOVERNANCE_MIGRATION_VERSION,
            "migration_applied": False,
            "database_present": False,
            "required_tables": required_tables,
            "present_tables": [],
            "missing_tables": required_tables,
            "required_indexes": required_indexes,
            "present_indexes": [],
            "missing_indexes": required_indexes,
        }

    conn = _connect(root_dir)
    try:
        present_tables = _object_names(conn, "table", required_tables)
        present_indexes = _object_names(conn, "index", required_indexes)
        missing_tables = sorted(set(required_tables) - set(present_tables))
        missing_indexes = sorted(set(required_indexes) - set(present_indexes))
        applied = _applied_migrations(conn)
        return {
            "registry_ready": not missing_tables and not missing_indexes,
            "migration_version": GOVERNANCE_MIGRATION_VERSION,
            "migration_applied": GOVERNANCE_MIGRATION_VERSION in applied,
            "database_present": True,
            "required_tables": required_tables,
            "present_tables": present_tables,
            "missing_tables": missing_tables,
            "required_indexes": required_indexes,
            "present_indexes": present_indexes,
            "missing_indexes": missing_indexes,
        }
    finally:
        conn.close()


def policy_summary(root_dir: Optional[str] = None) -> Dict[str, Any]:
    return {
        "policy_tiers": POLICY_TIERS,
        "source_statuses": sorted(SOURCE_STATUSES),
        "registry_ready": registry_ready(root_dir) if root_dir else None,
    }


def _require_registry(conn: sqlite3.Connection) -> None:
    missing = sorted(table for table in REQUIRED_TABLES if not _table_exists(conn, table))
    if missing:
        raise GovernanceMigrationRequired(
            "Governance registry migration is not applied. Missing tables: " + ", ".join(missing)
        )


def _clean_text(value: Any, max_len: int = 500) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len]


def validate_source_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    source_type = _clean_text(payload.get("type"), 80)
    name = _clean_text(payload.get("name"), 200)
    policy_tier = _clean_text(payload.get("policy_tier"), 1)
    status = _clean_text(payload.get("status"), 20) or "pending"

    if not source_type:
        raise ValueError("type is required.")
    if not name:
        raise ValueError("name is required.")
    if policy_tier not in POLICY_TIERS:
        raise ValueError("policy_tier must be one of A, B, C, D, E, X.")
    if status not in SOURCE_STATUSES:
        raise ValueError("status must be one of pending, active, paused, blocked, retired.")
    if policy_tier == "X":
        raise ValueError("Tier X sources are prohibited and cannot be registered.")

    retention_days = payload.get("retention_days")
    if retention_days in ("", None):
        retention_days = None
    elif isinstance(retention_days, bool):
        raise ValueError("retention_days must be an integer.")
    else:
        retention_days = int(retention_days)
        if retention_days < 0:
            raise ValueError("retention_days must be non-negative.")

    owner_user_id = payload.get("owner_user_id")
    if owner_user_id in ("", None):
        owner_user_id = None
    elif isinstance(owner_user_id, bool):
        raise ValueError("owner_user_id must be an integer.")
    else:
        owner_user_id = int(owner_user_id)

    return {
        "type": source_type,
        "name": name,
        "policy_tier": policy_tier,
        "status": status,
        "owner_user_id": owner_user_id,
        "source_url": _clean_text(payload.get("source_url"), 1000),
        "external_id": _clean_text(payload.get("external_id"), 250),
        "retention_days": retention_days,
        "terms_url": _clean_text(payload.get("terms_url"), 1000),
        "policy_notes": _clean_text(payload.get("policy_notes"), 2000),
    }


def _rows_to_dicts(rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(row) for row in rows]


def connector_metadata() -> Dict[str, Any]:
    """Return safe connector metadata for the Operator Runtime UI."""
    return {"connectors": list_connector_metadata()}


def list_sources(root_dir: str) -> Dict[str, Any]:
    conn = _connect(root_dir)
    try:
        _require_registry(conn)
        rows = conn.execute(
            """
            SELECT id, type, name, policy_tier, status, owner_user_id, source_url,
                   external_id, retention_days, terms_url, policy_notes, created_at, updated_at
            FROM sources
            ORDER BY id DESC
            """
        ).fetchall()
        return {"registry_ready": True, "sources": _rows_to_dicts(rows)}
    finally:
        conn.close()


def _safe_limit(limit: Any, default: int = 20, maximum: int = 100) -> int:
    try:
        clean = int(limit)
    except (TypeError, ValueError):
        return default
    return max(1, min(clean, maximum))


def list_connector_runs(root_dir: str, limit: Any = 20) -> Dict[str, Any]:
    conn = _connect(root_dir)
    try:
        _require_registry(conn)
        rows = conn.execute(
            """
            SELECT connector_runs.id, connector_runs.source_id, sources.name AS source_name,
                   connector_runs.job_type, connector_runs.status, connector_runs.records_seen,
                   connector_runs.records_created, connector_runs.records_updated,
                   connector_runs.cost_estimate, connector_runs.error_message,
                   connector_runs.started_at, connector_runs.ended_at, connector_runs.created_at
            FROM connector_runs
            LEFT JOIN sources ON sources.id = connector_runs.source_id
            ORDER BY COALESCE(connector_runs.ended_at, connector_runs.started_at, connector_runs.created_at) DESC,
                     connector_runs.id DESC
            LIMIT ?
            """,
            (_safe_limit(limit),),
        ).fetchall()
        return {"registry_ready": True, "connector_runs": _rows_to_dicts(rows)}
    finally:
        conn.close()


def list_source_records(root_dir: str, limit: Any = 20, source_id: Any = None) -> Dict[str, Any]:
    conn = _connect(root_dir)
    try:
        _require_registry(conn)
        params: List[Any] = []
        where = ""
        if source_id not in (None, ""):
            where = "WHERE source_records.source_id = ?"
            params.append(int(source_id))
        params.append(_safe_limit(limit, default=20, maximum=100))

        rows = conn.execute(
            f"""
            SELECT source_records.id, source_records.source_id,
                   sources.name AS source_name,
                   source_records.external_record_id,
                   source_records.record_type,
                   source_records.title,
                   source_records.url,
                   source_records.published_at,
                   source_records.content_hash IS NOT NULL AS has_content_hash,
                   source_records.captured_at
            FROM source_records
            LEFT JOIN sources ON sources.id = source_records.source_id
            {where}
            ORDER BY COALESCE(source_records.published_at, source_records.captured_at) DESC,
                     source_records.id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

        records = []
        for row in rows:
            record = dict(row)
            if record.get("title"):
                record["title"] = record["title"][:240]
            if record.get("url"):
                record["url"] = record["url"][:1000]
            records.append(record)

        return {"registry_ready": True, "source_records": records}
    finally:
        conn.close()


def list_audit_events(root_dir: str, limit: Any = 20) -> Dict[str, Any]:
    conn = _connect(root_dir)
    try:
        _require_registry(conn)
        rows = conn.execute(
            """
            SELECT id, actor_id, action, object_type, object_id,
                   metadata_json IS NOT NULL AS has_metadata, created_at
            FROM audit_events
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (_safe_limit(limit),),
        ).fetchall()
        return {"registry_ready": True, "audit_events": _rows_to_dicts(rows)}
    finally:
        conn.close()


def list_evidence_links(root_dir: str, limit: Any = 20) -> Dict[str, Any]:
    conn = _connect(root_dir)
    try:
        _require_registry(conn)
        rows = conn.execute(
            """
            SELECT evidence_links.id, evidence_links.ai_output_id,
                   ai_outputs.title AS ai_output_title,
                   ai_outputs.output_type AS ai_output_type,
                   ai_outputs.status AS ai_output_status,
                   evidence_links.source_id,
                   sources.name AS source_name,
                   evidence_links.source_record_id,
                   source_records.title AS source_record_title,
                   source_records.url AS source_record_url,
                   evidence_links.video_id,
                   evidence_links.claim_text AS claim_preview,
                   evidence_links.evidence_text AS evidence_preview,
                   evidence_links.confidence,
                   evidence_links.created_at
            FROM evidence_links
            LEFT JOIN ai_outputs ON ai_outputs.id = evidence_links.ai_output_id
            LEFT JOIN sources ON sources.id = evidence_links.source_id
            LEFT JOIN source_records ON source_records.id = evidence_links.source_record_id
            ORDER BY evidence_links.created_at DESC, evidence_links.id DESC
            LIMIT ?
            """,
            (_safe_limit(limit),),
        ).fetchall()

        records = []
        video_ids = [row["video_id"] for row in rows if row["video_id"]]
        video_titles = {}
        if video_ids:
            main_db_path = Path(root_dir) / "data" / "youtube_news.db"
            if main_db_path.exists():
                try:
                    main_conn = sqlite3.connect(str(main_db_path))
                    placeholders = ",".join("?" for _ in video_ids)
                    v_rows = main_conn.execute(
                        f"SELECT video_id, title FROM videos WHERE video_id IN ({placeholders})",
                        video_ids
                    ).fetchall()
                    video_titles = {r[0]: r[1] for r in v_rows}
                    main_conn.close()
                except Exception:
                    pass

        for row in rows:
            d = dict(row)
            d["video_title"] = video_titles.get(d["video_id"])
            if d.get("claim_preview"):
                d["claim_preview"] = d["claim_preview"][:240]
            if d.get("evidence_preview"):
                d["evidence_preview"] = d["evidence_preview"][:240]
            records.append(d)

        return {"registry_ready": True, "evidence_links": records}
    finally:
        conn.close()


def list_source_credential_status(root_dir: str, limit: Any = 20) -> Dict[str, Any]:
    conn = _connect(root_dir)
    try:
        _require_registry(conn)
        rows = conn.execute(
            """
            SELECT source_credentials.id, source_credentials.source_id,
                   sources.name AS source_name,
                   source_credentials.secret_ref IS NOT NULL AS has_secret_ref,
                   source_credentials.byok,
                   source_credentials.rotation_status,
                   source_credentials.last_rotated_at,
                   source_credentials.expires_at,
                   source_credentials.created_at
            FROM source_credentials
            LEFT JOIN sources ON sources.id = source_credentials.source_id
            ORDER BY source_credentials.created_at DESC, source_credentials.id DESC
            LIMIT ?
            """,
            (_safe_limit(limit),),
        ).fetchall()
        return {"registry_ready": True, "source_credentials": _rows_to_dicts(rows)}
    finally:
        conn.close()


def run_source_ingestion(root_dir: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run a connector and optionally persist normalized records.

    Dry-run is the default. `persist=true` requires a registered source_id and
    writes only to the isolated governance registry tables.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object.")

    persist = bool(payload.get("persist"))
    preview_limit = _safe_limit(payload.get("preview_limit"), default=20, maximum=100)
    context = _connector_context_from_payload(root_dir, payload, persist=persist)
    if context.policy_tier == "E" and not bool(payload.get("allow_tier_e")):
        raise ValueError("Tier E custom scraper ingestion requires allow_tier_e=true.")

    connector_kwargs = payload.get("input") or {}
    if not isinstance(connector_kwargs, dict):
        raise ValueError("input must be an object.")

    connector = create_connector(context)
    result = connector.fetch(**connector_kwargs)
    persisted = _persist_ingestion_result(root_dir, context, result) if persist else {
        "connector_run_id": None,
        "records_created": 0,
        "records_updated": 0,
    }

    return {
        "registry_ready": registry_ready(root_dir),
        "dry_run": not persist,
        "persisted": persist,
        "source": {
            "id": context.source_id,
            "type": context.source_type,
            "name": context.name,
            "policy_tier": context.policy_tier,
        },
        "summary": result.audit_summary(),
        "connector_run_id": persisted["connector_run_id"],
        "records_created": persisted["records_created"],
        "records_updated": persisted["records_updated"],
        "warnings": [warning for warning in result.warnings if warning],
        "rejected": [
            {"row_number": item.row_number, "reason": item.reason}
            for item in result.rejected[:preview_limit]
        ],
        "records": [
            _source_record_preview(record)
            for record in result.records[:preview_limit]
        ],
    }


def _connector_context_from_payload(root_dir: str, payload: Dict[str, Any], *, persist: bool) -> ConnectorContext:
    source_id = payload.get("source_id")
    if source_id not in (None, ""):
        conn = _connect(root_dir)
        try:
            _require_registry(conn)
            row = conn.execute(
                """
                SELECT id, type, name, policy_tier, source_url, external_id, status
                FROM sources
                WHERE id = ?
                """,
                (int(source_id),),
            ).fetchone()
            if not row:
                raise ValueError("source_id not found.")
            if row["status"] in {"blocked", "retired"}:
                raise ValueError("blocked or retired sources cannot be ingested.")
            return ConnectorContext(
                source_id=row["id"],
                source_type=row["type"],
                name=row["name"],
                policy_tier=row["policy_tier"],
                source_url=row["source_url"],
                external_id=row["external_id"],
            )
        finally:
            conn.close()

    if persist:
        raise ValueError("persist=true requires source_id.")

    source_payload = payload.get("source") or {}
    if not isinstance(source_payload, dict):
        raise ValueError("source must be an object.")
    source_type = _clean_text(source_payload.get("type") or payload.get("type"), 80)
    name = _clean_text(source_payload.get("name") or payload.get("name"), 200)
    policy_tier = _clean_text(source_payload.get("policy_tier") or payload.get("policy_tier"), 1) or "C"
    if not source_type:
        raise ValueError("source.type is required for dry-run ingestion.")
    if not name:
        name = f"{source_type} dry-run"
    return ConnectorContext(
        source_id=None,
        source_type=source_type,
        name=name,
        policy_tier=policy_tier,
        source_url=_clean_text(source_payload.get("source_url") or payload.get("source_url"), 1000),
        external_id=_clean_text(source_payload.get("external_id") or payload.get("external_id"), 250),
    )


def _persist_ingestion_result(root_dir: str, context: ConnectorContext, result: Any) -> Dict[str, Any]:
    if context.source_id is None:
        raise ValueError("persisted ingestion requires source_id.")

    import hashlib
    import json
    from pathlib import Path

    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    conn = _connect(root_dir)
    try:
        _require_registry(conn)
        run_cursor = conn.execute(
            """
            INSERT INTO connector_runs (
                source_id, job_type, status, records_seen, records_created,
                records_updated, cost_estimate, started_at, ended_at
            )
            VALUES (?, 'ingest', 'succeeded', ?, ?, 0, ?, ?, ?)
            """,
            (
                context.source_id,
                result.records_seen,
                len(result.records),
                result.cost_estimate,
                now,
                now,
            ),
        )

        evidence_dir = Path(root_dir) / "data" / "evidence_cache"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        for record in result.records:
            db_row = record.to_db_dict()
            
            # Extract transcript bytes if available
            transcript_bytes = None
            if context.source_type == "youtube":
                video_id = record.external_record_id
                transcripts_path = Path(root_dir) / "data" / "transcripts" / f"{video_id}.txt"
                if transcripts_path.exists():
                    try:
                        transcript_bytes = transcripts_path.read_bytes()
                    except Exception:
                        pass
                        
            # Download thumbnail bytes if available
            thumbnail_bytes = None
            if context.source_type == "youtube":
                video_id = record.external_record_id
                try:
                    import requests
                    urls = [
                        f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                        f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                    ]
                    for url in urls:
                        try:
                            response = requests.get(url, timeout=5)
                            if response.status_code == 200 and len(response.content) > 100:
                                thumbnail_bytes = response.content
                                break
                        except Exception:
                            pass
                except Exception:
                    pass

            metadata_bytes = json.dumps(record.metadata, ensure_ascii=False, sort_keys=True).encode("utf-8")
            
            # Compute SHA-256 hash of the artifacts
            h = hashlib.sha256()
            h.update(metadata_bytes)
            if transcript_bytes:
                h.update(transcript_bytes)
            if thumbnail_bytes:
                h.update(thumbnail_bytes)
            content_hash = "sha256:" + h.hexdigest()

            cursor = conn.execute(
                """
                INSERT INTO source_records (
                    source_id, external_record_id, record_type, title, url,
                    published_at, content_hash, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    db_row["source_id"],
                    db_row["external_record_id"],
                    db_row["record_type"],
                    db_row["title"],
                    db_row["url"],
                    db_row["published_at"],
                    content_hash,
                    db_row["metadata_json"],
                ),
            )
            record_id = cursor.lastrowid
            
            # Write raw files to evidence_cache
            try:
                (evidence_dir / f"source_record_{record_id}_metadata.json").write_bytes(metadata_bytes)
                if transcript_bytes:
                    (evidence_dir / f"source_record_{record_id}_transcript.txt").write_bytes(transcript_bytes)
                if thumbnail_bytes:
                    (evidence_dir / f"source_record_{record_id}_thumbnail.jpg").write_bytes(thumbnail_bytes)
            except Exception as e:
                import sys
                print(f"[Artifact Store] Failed to save evidence files for record {record_id}: {e}", file=sys.stderr)

        conn.execute(
            """
            INSERT INTO audit_events (action, object_type, object_id, metadata_json)
            VALUES ('source.ingested', 'source', ?, ?)
            """,
            (
                str(context.source_id),
                '{"note":"connector ingestion summary redacted by API"}',
            ),
        )
        conn.commit()
        return {
            "connector_run_id": run_cursor.lastrowid,
            "records_created": len(result.records),
            "records_updated": 0,
        }
    finally:
        conn.close()



def _source_record_preview(record: Any) -> Dict[str, Any]:
    return {
        "source_id": record.source_id,
        "external_record_id": record.external_record_id,
        "record_type": record.record_type,
        "title": record.title,
        "url": record.url,
        "published_at": record.published_at,
        "content_hash": record.content_hash,
        "metadata": {
            key: value
            for key, value in (record.metadata or {}).items()
            if key not in {"secret", "secret_ref", "token", "api_key"}
        },
    }


def create_source(root_dir: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    clean = validate_source_payload(payload)
    conn = _connect(root_dir)
    try:
        _require_registry(conn)
        cursor = conn.execute(
            """
            INSERT INTO sources (
                type, name, policy_tier, status, owner_user_id, source_url,
                external_id, retention_days, terms_url, policy_notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clean["type"],
                clean["name"],
                clean["policy_tier"],
                clean["status"],
                clean["owner_user_id"],
                clean["source_url"],
                clean["external_id"],
                clean["retention_days"],
                clean["terms_url"],
                clean["policy_notes"],
            ),
        )
        conn.commit()
        source_id = cursor.lastrowid

        add_audit_event(
            root_dir=root_dir,
            action="source.created",
            object_type="source",
            object_id=source_id,
            metadata={"type": clean["type"], "name": clean["name"], "policy_tier": clean["policy_tier"]},
            conn=conn
        )

        secret_value = payload.get("credentials")
        if secret_value:
            from app.services.credentials import store_credential
            store_credential(source_id, secret_value, root_dir)

        row = conn.execute(
            "SELECT * FROM sources WHERE id=?",
            (source_id,),
        ).fetchone()
        return dict(row)
    finally:
        conn.close()

def delete_source(root_dir: str, source_id: int) -> bool:
    """Delete a governed source record from database."""
    conn = _connect(root_dir)
    try:
        _require_registry(conn)
        row = conn.execute("SELECT type, name FROM sources WHERE id = ?", (source_id,)).fetchone()
        if not row:
            return False
        source_type = row["type"]
        source_name = row["name"]
        conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
        conn.commit()

        add_audit_event(
            root_dir=root_dir,
            action="source.deleted",
            object_type="source",
            object_id=source_id,
            metadata={"type": source_type, "name": source_name},
            conn=conn
        )
        return True
    finally:
        conn.close()

def add_audit_event(root_dir: str, action: str, object_type: str, object_id: Any, 
                    metadata: Optional[Dict[str, Any]] = None, actor_id: Optional[int] = None,
                    conn: Optional[sqlite3.Connection] = None) -> None:
    """Insert a new record into audit_events in governance.db."""
    import json
    metadata_json = json.dumps(metadata) if metadata else None
    
    should_close = False
    if conn is None:
        conn = _connect(root_dir)
        should_close = True
        
    try:
        conn.execute(
            """
            INSERT INTO audit_events (actor_id, action, object_type, object_id, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (actor_id, action, object_type, str(object_id) if object_id is not None else None, metadata_json)
        )
        conn.commit()
    except Exception as e:
        import sys
        print(f"[add_audit_event] failed: {e}", file=sys.stderr)
    finally:
        if should_close:
            conn.close()

def purge_expired_data(root_dir: str) -> Dict[str, Any]:
    """Auto-purge expired raw files and source_records based on policy retention_days."""
    conn = _connect(root_dir)
    try:
        _require_registry(conn)
        # Fetch sources with configured retention
        sources_rows = conn.execute(
            "SELECT id, name, retention_days FROM sources WHERE retention_days IS NOT NULL"
        ).fetchall()
        
        purged_records_count = 0
        purged_files_count = 0
        
        from pathlib import Path
        evidence_dir = Path(root_dir) / "data" / "evidence_cache"
        
        for src in sources_rows:
            source_id = src["id"]
            retention_days = src["retention_days"]
            
            # Find expired records
            expired_rows = conn.execute(
                """
                SELECT id FROM source_records 
                WHERE source_id = ? AND datetime(captured_at) < datetime('now', ?)
                """,
                (source_id, f"-{retention_days} days")
            ).fetchall()
            
            expired_ids = [r["id"] for r in expired_rows]
            if not expired_ids:
                continue
                
            # Delete files first
            for r_id in expired_ids:
                for suffix in ("_metadata.json", "_transcript.txt", "_thumbnail.jpg"):
                    file_path = evidence_dir / f"source_record_{r_id}{suffix}"
                    if file_path.exists():
                        try:
                            file_path.unlink()
                            purged_files_count += 1
                        except Exception:
                            pass
                            
            # Delete database records (foreign key cascade deletes evidence links, etc.)
            placeholders = ",".join("?" for _ in expired_ids)
            conn.execute(
                f"DELETE FROM source_records WHERE id IN ({placeholders})",
                expired_ids
            )
            purged_records_count += len(expired_ids)
            
            add_audit_event(
                root_dir=root_dir,
                action="source.purged",
                object_type="source",
                object_id=source_id,
                metadata={"purged_records": len(expired_ids), "purged_files": purged_files_count},
                conn=conn
            )
            
        conn.commit()
        return {
            "purged_records": purged_records_count,
            "purged_files": purged_files_count
        }
    finally:
        conn.close()


def validate_watcher_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate scheduled watcher payload against configuration boundaries.
    
    Raises:
        ValueError: if payload has invalid fields or parameters out of bounds.
    """
    if not isinstance(payload, dict):
        raise ValueError("Watcher configuration payload must be a dictionary.")
        
    watcher_id = _clean_text(payload.get("id"), 80)
    if not watcher_id:
        raise ValueError("Watcher 'id' is required.")
        
    source_id_val = payload.get("source_id")
    if source_id_val in (None, ""):
        raise ValueError("Watcher 'source_id' is required.")
    try:
        source_id = int(source_id_val)
        if source_id <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        raise ValueError("Watcher 'source_id' must be a positive integer.")
        
    name = _clean_text(payload.get("name"), 200)
    if not name:
        raise ValueError("Watcher 'name' is required.")
        
    interval_val = payload.get("interval_minutes")
    if interval_val in (None, ""):
        raise ValueError("Watcher 'interval_minutes' is required.")
    try:
        interval_minutes = int(interval_val)
        if interval_minutes < 15:
            raise ValueError("Watcher 'interval_minutes' must be at least 15 minutes to prevent rate limit overheating.")
    except (TypeError, ValueError) as e:
        if "must be at least 15 minutes" in str(e):
            raise
        raise ValueError("Watcher 'interval_minutes' must be a valid integer.")
        
    enabled = bool(payload.get("enabled", False))
    
    max_runs_val = payload.get("max_runs_per_day")
    if max_runs_val in (None, ""):
        max_runs_per_day = 24
    else:
        try:
            max_runs_per_day = int(max_runs_val)
            if max_runs_per_day <= 0 or max_runs_per_day > 96:
                raise ValueError()
        except (TypeError, ValueError):
            raise ValueError("Watcher 'max_runs_per_day' must be an integer between 1 and 96.")
            
    cost_limit_val = payload.get("cost_limit_usd")
    if cost_limit_val in (None, ""):
        cost_limit_usd = 1.0
    else:
        try:
            cost_limit_usd = float(cost_limit_val)
            if cost_limit_usd < 0.0 or cost_limit_usd > 10.0:
                raise ValueError()
        except (TypeError, ValueError):
            raise ValueError("Watcher 'cost_limit_usd' must be a float between 0.0 and 10.0.")
            
    return {
        "id": watcher_id,
        "source_id": source_id,
        "name": name,
        "interval_minutes": interval_minutes,
        "enabled": enabled,
        "max_runs_per_day": max_runs_per_day,
        "cost_limit_usd": cost_limit_usd
    }


def execute_watchers(root_dir: str) -> Dict[str, Any]:
    """Load, validate, and execute all enabled scheduled watchers.
    
    Logs connector_runs and audit_events for each enabled watcher.
    """
    import json
    config_path = Path(root_dir) / "configs" / "watchers.config.json"
    if not config_path.exists():
        return {"ran_watchers": [], "total_run": 0, "warning": "Config file not found."}
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse watchers config JSON: {e}")
        
    watchers = data.get("watchers")
    if not isinstance(watchers, list):
        raise ValueError("watchers config must contain a list of watchers.")
        
    ran_watchers = []
    
    conn = _connect(root_dir)
    try:
        _require_registry(conn)
        now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        
        for w in watchers:
            if not isinstance(w, dict):
                continue
            if not bool(w.get("enabled", False)):
                continue
                
            # Validate configuration boundaries
            clean = validate_watcher_config(w)
            
            # Log run in connector_runs
            conn.execute(
                """
                INSERT INTO connector_runs (
                    source_id, job_type, status, records_seen, records_created,
                    records_updated, cost_estimate, started_at, ended_at
                )
                VALUES (?, 'watcher', 'succeeded', 0, 0, 0, 0.0, ?, ?)
                """,
                (clean["source_id"], now, now)
            )
            
            # Log audit event
            add_audit_event(
                root_dir=root_dir,
                action="watcher.run",
                object_type="watcher",
                object_id=clean["id"],
                metadata={
                    "source_id": clean["source_id"],
                    "max_runs_per_day": clean["max_runs_per_day"],
                    "cost_limit_usd": clean["cost_limit_usd"]
                },
                conn=conn
            )
            
            ran_watchers.append(clean["id"])
            
        conn.commit()
    finally:
        conn.close()
        
    return {
        "ran_watchers": ran_watchers,
        "total_run": len(ran_watchers)
    }





