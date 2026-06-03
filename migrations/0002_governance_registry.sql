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
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (owner_user_id) REFERENCES users(id)
);

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
);

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
);

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
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id INTEGER,
    action TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id TEXT,
    metadata_json TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (actor_id) REFERENCES users(id)
);

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
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

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
    FOREIGN KEY (source_record_id) REFERENCES source_records(id) ON DELETE SET NULL,
    FOREIGN KEY (video_id) REFERENCES videos(video_id)
);

CREATE INDEX IF NOT EXISTS idx_sources_policy_tier ON sources(policy_tier);
CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);
CREATE INDEX IF NOT EXISTS idx_source_credentials_source_id ON source_credentials(source_id);
CREATE INDEX IF NOT EXISTS idx_source_records_source_id ON source_records(source_id);
CREATE INDEX IF NOT EXISTS idx_source_records_external_record_id ON source_records(external_record_id);
CREATE INDEX IF NOT EXISTS idx_connector_runs_source_id ON connector_runs(source_id);
CREATE INDEX IF NOT EXISTS idx_connector_runs_status ON connector_runs(status);
CREATE INDEX IF NOT EXISTS idx_audit_events_actor_id ON audit_events(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_object ON audit_events(object_type, object_id);
CREATE INDEX IF NOT EXISTS idx_ai_outputs_status ON ai_outputs(status);
CREATE INDEX IF NOT EXISTS idx_evidence_links_ai_output_id ON evidence_links(ai_output_id);
CREATE INDEX IF NOT EXISTS idx_evidence_links_source_record_id ON evidence_links(source_record_id);
CREATE INDEX IF NOT EXISTS idx_evidence_links_video_id ON evidence_links(video_id);
