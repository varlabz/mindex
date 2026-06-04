"""Del file command: remove a file from the index."""

from pathlib import Path

from mindex.db import _db


def del_file(index_dir: Path, file_path: Path) -> None:
    """Remove a file from the index by file_path."""
    with _db(index_dir) as conn:
        conn.execute("DELETE FROM docs WHERE path = ?", (str(file_path.absolute()),))
        conn.commit()
