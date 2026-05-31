CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,
    tag TEXT,
    google_id TEXT,
    avatar_url TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS user_invites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    tag TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    used_at TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS system_metrics (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cpu_percent REAL,
    ram_mb_used REAL,
    disk_io_mb REAL,
    http_sessions_active INTEGER
);

CREATE TABLE IF NOT EXISTS agent_feedback_memory (
    id INTEGER PRIMARY KEY,
    prompt_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    model_id TEXT,
    provider_id TEXT,
    feedback_type TEXT,
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leaked_quota_errors (
    id INTEGER PRIMARY KEY,
    error_string TEXT,
    provider_id TEXT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    intercepted_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_user_invites_email ON user_invites(email);
CREATE INDEX IF NOT EXISTS idx_user_invites_token ON user_invites(token);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_agent_feedback_memory_provider_id ON agent_feedback_memory(provider_id);
CREATE INDEX IF NOT EXISTS idx_agent_feedback_memory_model_id ON agent_feedback_memory(model_id);
CREATE INDEX IF NOT EXISTS idx_leaked_quota_errors_provider_id ON leaked_quota_errors(provider_id);
