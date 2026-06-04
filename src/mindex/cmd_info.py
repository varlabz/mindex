"""Info command: show metadata about indexed files."""

from dataclasses import dataclass
from pathlib import Path


from mindex.db import _db


@dataclass
class FileInfo:
    path: str
    size: int
    updated_at: str
    tag: str


def info_by_file(index_dir: Path, file_path: Path) -> FileInfo:
    """Return basic info about an indexed file record.

    Args:
        index_dir: Path to the index directory.
        file_path: Path to the indexed file.

    Returns:
        FileInfo with path, size, updated_at, and tag.

    Raises:
        FileNotFoundError: If the file is not found in the index.
    """
    with _db(index_dir) as conn:
        row = conn.execute(
            "SELECT path, size, updated_at, tag FROM docs WHERE path = ?",
            (str(file_path.absolute()),),
        ).fetchone()

        if not row:
            raise FileNotFoundError(f"File not indexed: {file_path}")

        return FileInfo(**row)


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
