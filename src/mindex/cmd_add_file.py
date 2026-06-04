"""Add file command: index a file into the FTS5 search index."""

import hashlib
from pathlib import Path

from mindex.db import _db


def add_file(index_dir: Path, file_path: Path, tag: str = None) -> None:
    """Add or update a file in the index."""
    content = file_path.read_text(encoding="utf-8")
    hash = hashlib.sha256(content.encode()).hexdigest()
    with _db(index_dir) as conn:
        conn.execute(
            """
            INSERT INTO docs (path, content, size, hash, tag)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                content = excluded.content,
                size = excluded.size,
                hash = excluded.hash,
                tag = excluded.tag,
                updated_at = datetime('now')
        """,
            (str(file_path.absolute()), content, len(content), hash, tag),
        )
        conn.commit()
