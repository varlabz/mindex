"""Database schema and connection management."""

import sqlite3
from pathlib import Path

DB_FILE = "mindex.sqlite"  # index file stored in vault directory


class _db:
    """Context-manager wrapper for sqlite3.Connection with auto-close."""

    def __init__(self, index_dir: Path, must_exist: bool = True):
        self.conn = self.get_db(index_dir, must_exist)

    def __enter__(self) -> sqlite3.Connection:
        return self.conn

    def __exit__(self, *exc) -> None:
        self.conn.close()

    @staticmethod
    def get_db(index_dir: Path, must_exist: bool = True) -> sqlite3.Connection:
        db_file = index_dir / DB_FILE
        if not db_file.exists() and must_exist:
            raise FileNotFoundError(
                f"Index database not found: {db_file}. Add files first using 'mindex add'."
            )

        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SCHEMA)
        return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,      -- store absolute path to ensure uniqueness across vault
    content TEXT NOT NULL,
    size INTEGER DEFAULT 0,
    hash TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
    content,
    content='docs',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN
    INSERT INTO docs_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN
    INSERT INTO docs_fts(docs_fts, rowid, content) VALUES ('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON docs BEGIN
    INSERT INTO docs_fts(docs_fts, rowid, content) VALUES ('delete', old.id, old.content);
    INSERT INTO docs_fts(rowid, content) VALUES (new.id, new.content);
END;
"""
