BEGIN TRANSACTION;

CREATE TABLE git_credentials_new (
    credential_id TEXT PRIMARY KEY,
    repository_slug TEXT NOT NULL,
    environment_name TEXT NOT NULL,
    public_key_fingerprint TEXT NOT NULL,
    permissions TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_verified_at TEXT,
    status TEXT NOT NULL
);

INSERT INTO git_credentials_new (
    credential_id,
    repository_slug,
    environment_name,
    public_key_fingerprint,
    permissions,
    created_at,
    last_verified_at,
    status
)
SELECT
    credential_id,
    repository_slug,
    environment_name,
    public_key_fingerprint,
    permissions,
    created_at,
    last_verified_at,
    status
FROM git_credentials;

DROP TABLE git_credentials;
ALTER TABLE git_credentials_new RENAME TO git_credentials;

COMMIT;
