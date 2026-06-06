"""Read command: retrieve stored file content from the index."""

from dataclasses import dataclass
from pathlib import Path

from mindex.db import _db


@dataclass
class ReadResult:
    content: str
    position: int
    size: int


def read_file(index_dir: Path, file_path: str, start: int, size: int) -> ReadResult:
    """Read file content from the index with optional pagination.

    Retrieves stored content of an indexed file, optionally returning only a
    character slice defined by *start* and *size*.

    Args:
        index_dir: Path to the index directory containing the SQLite database.
        file_path: Exact path of the indexed file to read.
        start: Starting character offset (0-based).
        size: Number of characters to read. Pass ``0`` to read the entire file.

    Returns:
        ReadResult containing the content slice, the start offset, and total file size.

    Raises:
        FileNotFoundError: If *file_path* is not found in the index.
    """
    with _db(index_dir) as conn:
        row = conn.execute(
            "SELECT content FROM docs WHERE path = ?",
            (file_path,),
        ).fetchone()

        if not row:
            raise FileNotFoundError(f"File not indexed: {file_path}")

        content = row["content"]
        end = start + size if size is not None else None
        cnt = content[start:end]
        return ReadResult(cnt, start, len(content))
