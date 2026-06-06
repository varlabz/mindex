"""Del file command: remove a file from the index."""

from pathlib import Path

from mindex.db import _db


def del_file(index_dir: Path, file_path: list[str]) -> int:
    """Remove files from the index by file path(s) or glob pattern(s)."""
    total = 0
    with _db(index_dir) as conn:
        for fp in file_path:
            cur = conn.execute("DELETE FROM docs WHERE path GLOB ?", (fp,))
            total += cur.rowcount
        conn.commit()
        return total
