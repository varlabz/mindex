"""Lint command: check indexed files for existence."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from mindex.db import _db


@dataclass
class LintInfo:
    path: str
    status: str


def lint(index_dir: Path, file_dir: Path | None = None) -> list[LintInfo]:
    """Lint indexed files: check if they exist on disk.

    Args:
        index_dir: Path to the index directory.
        file_dir: Optional directory to filter files by. Only files whose path
            starts with this directory are returned.

    Returns:
        List of LintInfo records with 'path' and 'status'.
    """
    prefix = str((file_dir / "").absolute()) if file_dir is not None else None
    with _db(index_dir) as conn:
        if prefix:
            rows = conn.execute(
                "SELECT path FROM docs WHERE SUBSTR(path, 1, LENGTH(?)) = ?",
                (prefix, prefix),
            ).fetchall()
        else:
            rows = conn.execute("SELECT path FROM docs").fetchall()

    results = []
    for row in rows:
        file_path = Path(row["path"])
        status = "OK" if file_path.is_file() else "missing"
        results.append(LintInfo(path=str(file_path), status=status))

    return results


def lint_fix(index_dir: Path, file_dir: Path | None = None) -> None:
    """Delete indexed records whose files no longer exist on disk.

    Args:
        index_dir: Path to the index directory.
        file_dir: Optional directory to filter records by. Only records whose
            path starts with this directory are considered for deletion.
    """
    prefix = str((file_dir / "").absolute()) if file_dir is not None else None
    deleted = 0
    with _db(index_dir) as conn:
        if prefix:
            rows = conn.execute(
                "SELECT path FROM docs WHERE SUBSTR(path, 1, LENGTH(?)) = ?",
                (prefix, prefix),
            ).fetchall()
        else:
            rows = conn.execute("SELECT path FROM docs").fetchall()
        for row in rows:
            file_path = Path(row["path"])
            if not file_path.is_file():
                conn.execute("DELETE FROM docs WHERE path = ?", (str(file_path.absolute()),))
                deleted += 1
        conn.commit()
    if deleted:
        print(f"Deleted {deleted} missing record(s).")
    else:
        print("No missing records to delete.")


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
