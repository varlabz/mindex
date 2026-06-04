"""Read command: retrieve stored file content from the index."""

from pathlib import Path

from mindex.db import _db


def read_file(index_dir: Path, file_path: Path, start: int, size: int) -> str:
    """Read file content from the index with optional pagination.

    Args:
        index_dir: Path to the index directory.
        file_path: Path to the indexed file.
        start: Starting character offset (default: 0).
        size: Number of characters to read. None means read entire file.

    Returns:
        The file content as a string.

    Raises:
        FileNotFoundError: If the file is not found in the index.
    """
    with _db(index_dir) as conn:
        row = conn.execute(
            "SELECT content FROM docs WHERE path = ?",
            (str(file_path.absolute()),),
        ).fetchone()

        if not row:
            raise FileNotFoundError(f"File not indexed: {file_path}")

        content = row["content"]
        end = start + size if size is not None else None
        return content[start:end]
