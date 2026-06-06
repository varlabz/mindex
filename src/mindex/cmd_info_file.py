"""Info command: show metadata about indexed files."""

from dataclasses import dataclass
from pathlib import Path

from mindex.db import _db


@dataclass
class FileInfo:
    path: str
    size: int
    updated_at: str


def info_by_file(index_dir: Path, file_path: list[str] | None) -> list[FileInfo]:
    """Return metadata about indexed file(s).

    Args:
        index_dir: Path to the index directory containing the SQLite database.
        file_path: Optional list of glob-style wildcard patterns to filter indexed files.
            If None, returns info for all indexed files.
            Examples: ``["*.md"]``, ``["docs/*", "src/*.py"]``.

    Returns:
        list[FileInfo] with path, size, and last-updated timestamp for each match.
    """
    with _db(index_dir) as conn:
        sql = "SELECT path, size, updated_at FROM docs"
        params: list[str] = []
        if file_path:
            clauses = ["path GLOB ?"] * len(file_path)
            params.extend(file_path)
            sql += " WHERE " + " OR ".join(clauses)

        return [FileInfo(**row) for row in conn.execute(sql, params).fetchall()]
