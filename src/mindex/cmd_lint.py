"""Lint command: check indexed files for existence."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from mindex.db import _db


@dataclass
class LintInfo:
    path: str
    status: str


def lint(index_dir: Path, file_path: list[str] | None = None) -> list[LintInfo]:
    """Lint indexed files: check if they exist on disk.

    Args:
        index_dir: Path to the index directory.
        file_path: Optional list of path or wildcard patterns to filter files by.
            Supports glob-style wildcards (e.g. "*.md", "sub/*").
            Only files matching at least one pattern are returned.

    Returns:
        List of LintInfo records with 'path' and 'status'.
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

    return results


def lint_output(results: list[LintInfo], fmt: str) -> None:
    """Print lint results in the specified format.

    Args:
        results: List of LintInfo records.
        fmt: Output format ('json' or 'text').
    """
    if not results:
        print("No indexed files.")
        return
    if fmt == "json":
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        for r in results:
            print("-" * 20)
            for k, v in asdict(r).items():
                print(f"{k}: {v or '-'}")
            print()
