"""Lint command: check indexed files for existence."""

from dataclasses import dataclass
from pathlib import Path

from mindex.db import _db


@dataclass
class LintInfo:
    path: str
    status: str


def lint(index_dir: Path, file_path: list[str] | None = None, fix: bool = False) -> list[LintInfo]:
    """Check whether indexed files still exist on disk.

    Queries the index for all (or filtered) file paths and checks each one
    against the filesystem. Returns a status of ``"OK"`` for files that exist
    and ``"missing"`` for files that have been deleted or moved.

    Args:
        index_dir: Path to the index directory containing the SQLite database.
        file_path: Optional list of glob-style wildcard patterns to filter which
            indexed files are checked. If None, all indexed files are linted.

    Returns:
        list[LintInfo] with ``path`` and ``status`` (``"OK"`` or ``"missing"``).
    """
    with _db(index_dir) as conn:
        sql = "SELECT path FROM docs"
        params: list[str] = []

        if file_path:
            clauses = []
            for fd in file_path:
                clauses.append("path GLOB ?")
                params.append(fd)
            sql += " WHERE " + " OR ".join(clauses)

        rows = conn.execute(sql, params).fetchall()

    results = []
    for row in rows:
        fp = Path(row["path"])
        status = "OK" if fp.is_file() else "missing"
        results.append(LintInfo(path=str(fp), status=status))

    if fix:
        with _db(index_dir) as conn:
            for result in results:
                if result.status == "missing":
                    # delete the missing file from the index
                    conn.execute("DELETE FROM docs WHERE path = ?", (result.path,))
            conn.commit()

    return results
