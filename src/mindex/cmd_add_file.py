"""Add file command: index files into the FTS5 search index."""

import glob
import hashlib
from dataclasses import dataclass
from pathlib import Path

from mindex.db import _db


@dataclass
class AddResult:
    path: str
    size: int


def add_file(index_dir: Path, file_path: list[str]) -> list[AddResult]:
    """Add or update file(s) in the index.

    Each item in *file_path* is treated as a glob/wildcard pattern, so each can
    match one file, many files, or none (which raises ``FileNotFoundError``).
    """
    matched: set[str] = set()
    for pattern in file_path:
        hits = glob.glob(pattern)
        # If nothing matched, try treating the path as a literal file (e.g., names
        # containing glob special characters like [ ] ?)
        if not hits:
            literal = Path(pattern)
            if literal.is_file():
                hits = [str(literal)]

        if not hits:
            raise FileNotFoundError(f"No files matched pattern: {pattern}")

        matched.update(hits)

    with _db(index_dir) as conn:
        results: list[AddResult] = []
        for fp in map(Path, matched):
            # skip hidden files (e.g., .git, .venv)
            if not fp.is_file() or fp.name.startswith("."):
                continue

            content = fp.read_text(encoding="utf-8")
            if len(content) == 0:
                continue

            # check hash to avoid re-indexing
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            before = conn.total_changes
            conn.execute(
                """
                INSERT INTO docs (path, content, size, hash)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    content = excluded.content,
                    size = excluded.size,
                    hash = excluded.hash,
                    updated_at = datetime('now')
                WHERE docs.hash IS NULL OR docs.hash != ?
            """,
                (str(fp.absolute()), content, len(content), file_hash, file_hash),
            )
            if conn.total_changes > before:
                results.append(AddResult(path=str(fp.absolute()), size=len(content)))

        conn.commit()
        return results
