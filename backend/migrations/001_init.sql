CREATE TABLE IF NOT EXISTS transfer_records (
    transfer_id TEXT PRIMARY KEY,
    direction TEXT NOT NULL,
    node_id TEXT NOT NULL,
    source TEXT NOT NULL,
    destination TEXT NOT NULL,
    status TEXT NOT NULL,
    file_count INTEGER NOT NULL DEFAULT 0,
    total_bytes INTEGER NOT NULL DEFAULT 0,
    transferred_bytes INTEGER NOT NULL DEFAULT 0,
    manifest_sha256 TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error_code TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS host_keys (
    target_id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    port INTEGER NOT NULL,
    algorithm TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    approved_at TEXT NOT NULL,
    approved_by TEXT NOT NULL,
    changed_at TEXT,
    note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS git_credentials (
    credential_id TEXT PRIMARY KEY,
    repository_slug TEXT NOT NULL,
    environment_name TEXT NOT NULL,
    public_key_fingerprint TEXT NOT NULL,
    permissions TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_verified_at TEXT,
    status TEXT NOT NULL,
    remote_path TEXT NOT NULL
);
