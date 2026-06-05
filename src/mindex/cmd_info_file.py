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


def print_info(results: list[FileInfo], fmt: str) -> None:
    """Print a list of FileInfo records in the given format.

    Args:
        results: List of FileInfo records to print.
        fmt: Output format — "json" or "text" (default: "json").
        tag: Optional tag label to include in the empty-result message.
    """
    if not results:
        if fmt == "json":
            print("[]")
        else:
            print("No records found.")
        return
    if fmt == "json":
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        for r in results:
            print("-" * 20)
            for k, v in asdict(r).items():
                print(f"{k}: {v or '-'}")
            print()
