"""Del file command: remove a file from the index."""

import glob
from pathlib import Path

from mindex.db import _db


def del_file(index_dir: Path, file_path: str) -> int:
    """Remove a file from the index by file_path."""
    matched = glob.glob(str(file_path))
    # If nothing matched, try treating the path as a literal file (e.g., names
    # containing glob special characters like [ ] ?)
    if not matched:
        literal = Path(file_path)
        if literal.is_file():
            matched = [str(literal)]

    if not matched:
        raise FileNotFoundError(f"No files matched pattern: {file_path}")

    total = 0
    with _db(index_dir) as conn:
        for fp in map(Path, matched):
            if not fp.is_file():
                continue

            cur = conn.execute("DELETE FROM docs WHERE path = ?", (str(fp.absolute()),))
            conn.commit()
            total += cur.rowcount

    return total