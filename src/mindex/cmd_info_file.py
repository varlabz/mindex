"""Info command: show metadata about indexed files."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from mindex.db import _db


@dataclass
class FileInfo:
    path: str
    size: int
    updated_at: str


def info_by_file(index_dir: Path, file_path: str) -> list[FileInfo]:
    """Return basic info about indexed file(s).

    Args:
        index_dir: Path to the index directory.
        file: Optional path or wildcard pattern to match indexed files.
                   If None, returns all indexed files.
                   Supports glob-style wildcards (e.g. "*.md", "docs/*").

    Returns:
        list[FileInfo] of matching records.

    Raises:
        FileNotFoundError: If file_path is provided but no records match.
    """
    with _db(index_dir) as conn:
        rows = conn.execute(
            "SELECT path, size, updated_at FROM docs WHERE path GLOB ?", (file_path,)
        ).fetchall()
        result = [FileInfo(**row) for row in rows]
        return result
