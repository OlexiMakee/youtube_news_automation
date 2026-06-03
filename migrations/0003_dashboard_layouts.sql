CREATE TABLE IF NOT EXISTS dashboard_layouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    is_default INTEGER DEFAULT 0 CHECK (is_default IN (0, 1)),
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS dashboard_widgets (
    id TEXT PRIMARY KEY,
    layout_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    width TEXT,
    height TEXT,
    collapsed INTEGER DEFAULT 0 CHECK (collapsed IN (0, 1)),
    config_json TEXT,
    FOREIGN KEY (layout_id) REFERENCES dashboard_layouts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_layout_id ON dashboard_widgets(layout_id);
