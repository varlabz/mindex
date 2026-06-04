"""Add file command: index files into the FTS5 search index."""

import glob
import hashlib
from pathlib import Path

from mindex.db import _db


def add_file(index_dir: Path, file_path: str) -> int:
    """Add or update file(s) in the index.

    The *file_path* argument is treated as a glob/wildcard pattern, so it can
    match one file, many files, or none (which raises ``FileNotFoundError``).
    """
    matched = glob.glob(file_path)
    # If nothing matched, try treating the path as a literal file (e.g., names
    # containing glob special characters like [ ] ?)
    if not matched:
        literal = Path(file_path)
        if literal.is_file():
            matched = [str(literal)]

    if not matched:
        raise FileNotFoundError(f"No files matched pattern: {file_path}")

    count = 0
    with _db(index_dir) as conn:
        for fp in map(Path, matched):
            if not fp.is_file():
                continue

            content = fp.read_text(encoding="utf-8")
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            conn.execute(
                """
                INSERT INTO docs (path, content, size, hash, tag)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    content = excluded.content,
                    size = excluded.size,
                    hash = excluded.hash,
                    updated_at = datetime('now')
            """,
                (str(fp.absolute()), content, len(content), file_hash, None),
            )
            count += 1
        conn.commit()

    return count
