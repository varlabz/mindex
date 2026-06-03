import argparse
import hashlib
import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

DB_FILE = "mindex.sqlite"  # index file stored in vault directory


class _db:
    """Context-manager wrapper for sqlite3.Connection with auto-close."""

    def __init__(self, index_dir: Path):
        self.conn = self.get_db(index_dir)

    def __enter__(self) -> sqlite3.Connection:
        return self.conn

    def __exit__(self, *exc) -> None:
        self.conn.close()

    @staticmethod
    def get_db(index_dir: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(os.path.join(index_dir, DB_FILE))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SCHEMA)
        return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,      -- store absolute path to ensure uniqueness across vault
    content TEXT NOT NULL,
    size INTEGER DEFAULT 0,
    hash TEXT,
    tag TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
    content,
    content='docs',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN
    INSERT INTO docs_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN
    INSERT INTO docs_fts(docs_fts, rowid, content) VALUES ('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON docs BEGIN
    INSERT INTO docs_fts(docs_fts, rowid, content) VALUES ('delete', old.id, old.content);
    INSERT INTO docs_fts(rowid, content) VALUES (new.id, new.content);
END;
"""


def add_file(index_dir: Path, file_path: Path, tag: str = None) -> None:
    """Add or update a file in the index."""
    content = file_path.read_text(encoding="utf-8")
    hash = hashlib.sha256(content.encode()).hexdigest()

    with _db(index_dir) as conn:
        conn.execute(
            """
            INSERT INTO docs (path, content, size, hash, tag)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                content = excluded.content,
                size = excluded.size,
                hash = excluded.hash,
                tag = excluded.tag,
                updated_at = datetime('now')
        """,
            (str(file_path.absolute()), content, len(content), hash, tag),
        )
        conn.commit()


def del_file(index_dir: Path, file_path: Path) -> None:
    """Remove a file from the index by file_path."""
    with _db(index_dir) as conn:
        conn.execute("DELETE FROM docs WHERE path = ?", (str(file_path.absolute()),))
        conn.commit()


@dataclass
class SearchResult:
    path: str
    snippet: str
    tag: str
    updated_at: str


def _escape_fts5(query: str) -> str:
    """Escape a user query for safe use as a literal FTS5 phrase match.

    Wraps the query in double quotes so FTS5 treats it as a literal phrase.
    Embedded double quotes are escaped by doubling ("").
    """
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


def search(index_dir: Path, query: str, tag: str = None, limit: int = 10) -> list[SearchResult]:
    """Search using FTS5, optionally filtering by tag in tag1 field."""
    stripped = query.strip()
    if not stripped:
        raise ValueError("Query cannot be empty or whitespace only")

    if len(stripped) < 3:
        raise ValueError(
            f"Query too short ({len(stripped)} chars). Minimum query length is 3 characters."
        )

    with _db(index_dir) as conn:
        sql = f"""
            SELECT d.path,
                   snippet(docs_fts, 0, '', '', '...', 64) as snippet,
                   d.tag, d.updated_at
            FROM docs_fts
            JOIN docs d ON docs_fts.rowid = d.id
            WHERE docs_fts MATCH ? {" AND d.tag = ?" if tag else ""}
            ORDER BY bm25(docs_fts)
            LIMIT ?
        """
        fts_query = _escape_fts5(stripped)
        if tag:
            rows = conn.execute(sql, (fts_query, tag, limit)).fetchall()
        else:
            rows = conn.execute(sql, (fts_query, limit)).fetchall()

        return [SearchResult(**row) for row in rows]


@dataclass
class FileSearchResult:
    snippet: str
    position: int


MARK_START = "|$d%T&#-s|"
MARK_END = "|$d%T&#-e|"
PAD = 40


def _extract_snippets(highlighted: str, limit: int) -> list[FileSearchResult]:
    """Extract matching snippets from highlighted text by scanning for MARK_START/MARK_END pairs."""
    marker_overhead = len(MARK_START) + len(MARK_END)
    results = []
    search_start = 0
    while len(results) < limit:
        pos = highlighted.find(MARK_START, search_start)
        if pos == -1:
            break
        end_pos = highlighted.find(MARK_END, pos + len(MARK_START))
        if end_pos == -1:
            break
        term_end = end_pos + len(MARK_END)

        # Compute real position: each earlier complete match adds marker_overhead bytes
        real_pos = pos - len(results) * marker_overhead

        # Extract context window (~40 chars each side) from highlighted text
        ctx_start = max(0, pos - PAD)
        ctx_end = min(len(highlighted), term_end + PAD)
        snippet = highlighted[ctx_start:ctx_end]

        # Strip FTS5 highlight markers from the snippet
        snippet = snippet.replace(MARK_START, "").replace(MARK_END, "")

        results.append(FileSearchResult(snippet=snippet, position=real_pos))
        search_start = term_end

    return results


def read_file(index_dir: Path, file_path: Path, start: int = 0, size: int = None) -> str:
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


def search_file(
    index_dir: Path, file_path: Path, query: str, limit: int = 10
) -> list[FileSearchResult]:
    """Search within a specific file and return multiple matching snippets.

    Uses FTS5's highlight() to wrap matched terms with custom markers.
    Extracts context windows by scanning for markers in the highlighted text,
    avoiding byte-offset mismatches caused by marker insertion.
    """
    fts_query = _escape_fts5(query)
    with _db(index_dir) as conn:
        row = conn.execute(
            f"""SELECT highlight(docs_fts, 0, '{MARK_START}', '{MARK_END}') AS h
            FROM docs_fts
            JOIN docs d ON docs_fts.rowid = d.id
            WHERE docs_fts MATCH ? AND d.path = ?
            """,
            (fts_query, str(file_path.absolute())),
        ).fetchone()
        if not row or not row["h"]:
            return []

        return _extract_snippets(row["h"], limit)


# ── CLI ────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    """Command-line interface for mindex operations."""
    parser = argparse.ArgumentParser(
        prog="mindex",
        description="SQLite FTS5-based wiki search index",
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=Path("."),
        help="Index directory containing mindex.sqlite (default: current directory)",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # add
    p_add = sub.add_parser("add", help="Add or update a file in the index")
    p_add.add_argument("file", type=Path, help="Path to the file to index")
    p_add.add_argument("-t", "--tag", default=None, help="Optional tag for the file")

    # rm
    p_del = sub.add_parser("rm", help="Remove a file from the index")
    p_del.add_argument("file", type=Path, help="Path to the file to remove")

    # search
    p_search = sub.add_parser("search", help="Search indexed files via FTS5")
    p_search.add_argument("query", help="Search query (min 3 chars)")
    p_search.add_argument("-t", "--tag", default=None, help="Filter by tag")
    p_search.add_argument("-n", "--limit", type=int, default=10, help="Max results")
    p_search.add_argument(
        "-f",
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    # read
    p_read = sub.add_parser("read", help="Read file content from the index")
    p_read.add_argument("file", type=Path, help="Path to the indexed file to read")
    p_read.add_argument("-p", "--position", type=int, default=0, help="Starting character offset (default: 0)")
    p_read.add_argument("-s", "--size", type=int, default=4000, help="Number of characters to read (default: 4000 chars)")

    # file
    p_sf = sub.add_parser("file", help="Search within a specific indexed file")
    p_sf.add_argument("file", type=Path, help="Path to the indexed file to search")
    p_sf.add_argument("query", help="Search query")
    p_sf.add_argument("-n", "--limit", type=int, default=10, help="Max results")
    p_sf.add_argument(
        "-f",
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return

    # Expand ~ in index_dir to home directory
    index_dir = args.index_dir.expanduser()
    if not index_dir.exists():
        raise ValueError(f"Index directory does not exist: {index_dir}")

    if args.command == "add":
        add_file(index_dir, args.file.expanduser(), tag=args.tag)
        print(f"Indexed: {args.file}")

    elif args.command == "rm":
        del_file(index_dir, args.file.expanduser())
        print(f"Removed: {args.file}")

    elif args.command == "search":
        results = search(index_dir, args.query, tag=args.tag, limit=args.limit)
        if not results:
            print("No results.")
            return
        if args.format == "json":
            print(json.dumps([asdict(r) for r in results], indent=2))
        else:
            for r in results:
                print(f"{r.path}\t{r.tag or ''}\t{r.snippet}")

    elif args.command == "file":
        results = search_file(index_dir, args.file.expanduser(), args.query, limit=args.limit)
        if not results:
            print("No results.")
            return
        if args.format == "json":
            print(json.dumps([asdict(r) for r in results], indent=2))
        else:
            for r in results:
                print(r.snippet)

    elif args.command == "read":
        content = read_file(index_dir, args.file.expanduser(), start=args.position, size=args.size)
        print(content)


if __name__ == "__main__":
    main()
