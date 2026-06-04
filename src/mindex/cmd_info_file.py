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
    tag: str


def info_by_file(index_dir: Path, file: str | None = None) -> list[FileInfo]:
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
        if file is not None:
            file = str(file)
            # relative wildcards should match stored absolute paths
            if not file.startswith("/"):
                file = "*/" + file
        else:
            file = "*"
        rows = conn.execute(
            "SELECT path, size, updated_at, tag FROM docs WHERE path GLOB ?",
            (file, )
        ).fetchall()
        result = [FileInfo(**row) for row in rows]
        if not result and file != "*":
            raise FileNotFoundError("No indexed files matched the given pattern.")
        return result

def info_by_tag(index_dir: Path, tag: str) -> list[FileInfo]:
    """Return info for all indexed files with the given tag.

    Args:
        index_dir: Path to the index directory.
        tag: Tag to filter by.

    Returns:
        List of FileInfo records matching the tag.
    """
    with _db(index_dir) as conn:
        rows = conn.execute(
            "SELECT path, size, updated_at, tag FROM docs WHERE tag = ?",
            (tag,),
        ).fetchall()

        return [FileInfo(**row) for row in rows]


def print_info(results: list[FileInfo], fmt: str = "json", tag: str = None) -> None:
    """Print a list of FileInfo records in the given format.

    Args:
        results: List of FileInfo records to print.
        fmt: Output format — "json" or "text" (default: "json").
        tag: Optional tag label to include in the empty-result message.
    """
    if not results:
        if tag is not None:
            print(f"No records found with tag: {tag}")
        elif fmt == "json":
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
