from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import settings


MIGRATIONS_DIR = Path(__file__).with_name("migrations")


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    target = db_path or settings.database_path
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db(db_path: Path | None = None):
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> None:
    target = db_path or settings.database_path
    target.parent.mkdir(parents=True, exist_ok=True)
    with get_db(target) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )
        for migration_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = int(migration_path.stem.split("_", 1)[0])
            row = conn.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (version,)).fetchone()
            if row:
                continue
            conn.executescript(migration_path.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, datetime('now'))",
                (version,),
            )
