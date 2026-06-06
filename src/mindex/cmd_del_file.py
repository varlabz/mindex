"""Del file command: remove a file from the index."""

from dataclasses import dataclass
from pathlib import Path

from mindex.db import _db


@dataclass
class DelResult:
    paths: list[str]


def del_file(index_dir: Path, file_path: list[str]) -> DelResult:
    """Remove files from the index by file path(s) or glob pattern(s)."""
    if not file_path:
        raise ValueError("file_path must not be empty")

    with _db(index_dir) as conn:
        sql = "DELETE FROM docs WHERE " + " OR ".join("path GLOB ?" for _ in file_path)
        sql += " RETURNING path"
        rows = conn.execute(sql, file_path).fetchall()
        conn.commit()
        return DelResult([row["path"] for row in rows])
