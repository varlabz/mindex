#!/usr/bin/env python3
"""
Markdown Index — MD files as source of truth, SQLite FTS5 for search.

Features:
  - Add one markdown file at a time
  - Search with ranked results (BM25 via FTS5, includes tags)
  - Tag-based filtering and management
  - File change detection (hash-based, incremental)
  - Single SQLite database, zero external dependencies
"""

import sqlite3
import hashlib
import os
import argparse
import json
from pathlib import Path

DB_FILE = ".mindex.sqlite"  # index file stored in vault directory


class _db:
    """Context-manager wrapper for sqlite3.Connection with auto-close."""

    def __init__(self, index_dir: str | Path):
        self.conn = self.get_db(index_dir)

    def __enter__(self) -> sqlite3.Connection:
        return self.conn

    def __exit__(self, *exc) -> None:
        self.conn.close()

    @staticmethod
    def get_db(index_dir: str | Path) -> sqlite3.Connection:
        index_path = Path(index_dir)
        index_path.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(os.path.join(index_dir, DB_FILE))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SCHEMA)
        return conn


# ── Database Setup ────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
    id INTEGER PRIMARY KEY,             -- Row identifier
    path TEXT UNIQUE NOT NULL,          -- Relative file path in the workspace
    source TEXT,                        -- Original source URL or reference (defaults to path)
    title TEXT NOT NULL,                -- Document title extracted from markdown heading
    content TEXT NOT NULL,              -- Full document content (with tags for FTS)
    summary TEXT NOT NULL,              -- Short summary extracted from first paragraphs
    size INTEGER DEFAULT 0,             -- File size in characters
    hash TEXT,                          -- SHA-256 file content hash for change detection
    created_at TEXT DEFAULT (datetime('now')),  -- Timestamp of record creation
    updated_at TEXT DEFAULT (datetime('now'))   -- Timestamp of last update
);

CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
    title, content, summary,
    content='docs', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN
    INSERT INTO docs_fts(rowid, title, content, summary)
        VALUES (new.id, new.title, new.content, new.summary);
END;

CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN
    INSERT INTO docs_fts(docs_fts, rowid, title, content, summary)
        VALUES ('delete', old.id, old.title, old.content, old.summary);
END;

CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON docs BEGIN
    INSERT INTO docs_fts(docs_fts, rowid, title, content, summary)
        VALUES ('delete', old.id, old.title, old.content, old.summary);
    INSERT INTO docs_fts(rowid, title, content, summary)
        VALUES (new.id, new.title, new.content, new.summary);
END;

CREATE TABLE IF NOT EXISTS tags (
    doc_id INTEGER NOT NULL REFERENCES docs(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (doc_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
CREATE INDEX IF NOT EXISTS idx_tags_doc ON tags(doc_id);
"""

# ── Add / Index Files ─────────────────────────────────────────────


def add_file(
    file_path: Path,
    index_path: Path,
    tags: list[str] | None = None,
    title: str | None = None,
    summary: str | None = None,
    source: str | None = None,
):
    """Add or update a single markdown file in the index."""

    def file_hash(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]

    abs_path = str(file_path.absolute())
    with _db(index_path) as conn:
        h = file_hash(file_path)

        # Skip unchanged files unless custom title/summary/tags provided
        existing = conn.execute("SELECT id, hash FROM docs WHERE path = ?", (abs_path,)).fetchone()
        if existing and existing["hash"] == h and not title and not summary and not tags:
            # print(f"Unchanged, skipped: {abs_path}")
            return

        content = file_path.read_text(encoding="utf-8")
        size = len(content)
        if not existing:
            conn.execute(
                """INSERT INTO docs (path, title, content, summary, size, source, hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (abs_path, title, content, summary, size, source or abs_path, h),
            )
            doc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        else:
            doc_id = existing["id"]
            conn.execute(
                """UPDATE docs SET title=?, content=?, summary=?, size=?, source=?, hash=?,
                   updated_at=datetime('now') WHERE path=?""",
                (title, content, summary, size, source or abs_path, h, abs_path),
            )

        for tag in _normalize_tags(tags) if tags else []:
            conn.execute(
                """INSERT OR IGNORE INTO tags (doc_id, tag) VALUES (?, ?)""", (doc_id, tag)
            )

        conn.commit()
        # print(f"  ✓ Indexed: {action} {abs_path}")


# ── Search ────────────────────────────────────────────────────────


def search(
    query: str,
    index_path: Path,
    limit: int = 10,
    file_path: Path | None = None,
    tags: list[str] | None = None,
) -> list[dict]:
    """Search indexed markdown files with FTS5 ranking (includes tags).

    If file_path is provided, only search within that file.
    If tags is provided, only search in files that have all the given tags.
    Tag filtering is case-insensitive.
    Returns list of dicts with keys: path, title, snippet, tags
    """
    with _db(index_path) as conn:
        # Check if index is empty
        count = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
        if count == 0:
            raise ValueError("Index is empty. Add files first.")

        # if have file and tags throw error because they serve different purposes
        # and combining them doesn't make sense
        if file_path and tags:
            raise ValueError(
                "Cannot use both --file and --tags filters in the same search command."
            )

        sql = """
            SELECT d.id, d.path, d.source, d.title,
                   snippet(docs_fts, -1, '\n', '', '...', 100) AS snippet,
                   d.summary, d.size, d.updated_at,
                   bm25(docs_fts) AS relevance,
                   (
                       SELECT GROUP_CONCAT(tag, ', ')
                       FROM tags
                       WHERE doc_id = d.id
                   ) AS tags
            FROM docs_fts f
            JOIN docs d ON d.id = f.rowid
            WHERE docs_fts MATCH ?
        """

        params: list = [query]

        # Add file filter if specified
        if file_path:
            abs_path = str(file_path.absolute())
            sql += " AND d.path = ?"
            params.append(abs_path)

        # Add tag filter if specified (case-insensitive)
        if tags:
            placeholders = ",".join("?" * len(tags))
            tag_filter = (
                f" AND d.id IN (SELECT doc_id FROM tags WHERE LOWER(tag) "
                f"IN ({placeholders}) GROUP BY doc_id "
                f"HAVING COUNT(DISTINCT tag) = ?)"
            )
            sql += tag_filter
            params.extend([t.lower() for t in tags])
            params.append(len(tags))

        sql += " ORDER BY relevance LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [
            {
                "path": str(r["path"]),
                "source": str(r["source"]),
                "title": str(r["title"]),
                "updated_at": str(r["updated_at"]),
                "snippet": str(r["snippet"]),
                "total_size": str(r["size"]),
                "relevance": r["relevance"],
                "tags": r["tags"].split(", ") if r["tags"] else [],
            }
            for r in rows
        ]


# ── Tags ──────────────────────────────────────────────────────────


def list_tags(index_path: Path) -> set[str]:
    """List all unique tag names."""
    with _db(index_path) as conn:
        rows = conn.execute("""
            SELECT DISTINCT t.tag
            FROM tags t
            ORDER BY t.tag
        """).fetchall()

        return {r["tag"] for r in rows}


def info(file_path: Path, index_path: Path) -> dict:
    """Return details about an indexed file as a dict."""
    abs_path = str(file_path)
    with _db(index_path) as conn:
        doc = conn.execute("SELECT * FROM docs WHERE path = ?", (abs_path,)).fetchone()

        if not doc:
            raise ValueError(f"  ✗ File not indexed: {file_path}")

        tags = [
            r["tag"]
            for r in conn.execute("SELECT tag FROM tags WHERE doc_id = ?", (doc["id"],)).fetchall()
        ]

        return {
            "path": doc["path"],
            "source": doc["source"],
            "title": doc["title"],
            "summary": doc["summary"],
            "total_size": doc["size"],
            "tags": tags,
        }


def read_file(file_path: Path, index_path: Path, position: int = 0, size: int | None = None) -> str:
    """Read file content from position with optional size limit."""
    abs_path = str(file_path)
    with _db(index_path) as conn:
        doc = conn.execute("SELECT content FROM docs WHERE path = ?", (abs_path,)).fetchone()
        if not doc:
            raise ValueError(f"File not indexed: {file_path}")

        content = str(doc["content"])
        return content[position : position + size] if size else content[position:]


def delete_file(file_path: Path, index_path: Path):
    """Delete a file from the index."""
    abs_path = str(file_path)
    with _db(index_path) as conn:
        doc = conn.execute("SELECT id, title FROM docs WHERE path = ?", (abs_path,)).fetchone()

        if not doc:
            raise ValueError(f"  ✗ File not indexed: {file_path}")

        conn.execute("DELETE FROM docs WHERE id = ?", (doc["id"],))
        conn.commit()


# ── CLI ───────────────────────────────────────────────────────────


def _resolve_file(file: str) -> Path:
    """Resolve a file argument to absolute Path. Try as-is first, then from current directory."""
    path = Path(file)
    # Try the path as given
    if path.exists():
        return path.resolve()

    raise ValueError(f"Not found: {file}")


def _format_search_results_text(rows: list[dict]) -> str:
    """Format search results as indented key-value text."""
    output = ""
    for r in rows:
        for key, value in r.items():
            if key == "tags":
                if value:
                    output += f"{key}: {', '.join(value)}\n"
            else:
                output += f"{key}: {value}\n"
        output += "\n"
        output += "-" * 20 + "\n"
    return output


def _format_search_results_json(rows: list[dict]) -> str:
    """Format search results as JSON."""
    return json.dumps(rows, indent=2)


def _normalize_tags(tags: list[str]) -> list[str]:
    """Normalize a list of tags: strip, lowercase, deduplicate."""
    seen: set[str] = set()
    result: list[str] = []
    for t in tags:
        t = t.strip().lower()
        if t and t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _parse_tags(tags: list[str] | None) -> list[str] | None:
    """Parse and normalize tags from command line arguments (space or comma separated)."""
    if not tags:
        return None
    tag_list = [x.strip() for t in tags for x in t.replace(",", " ").split() if x.strip()]
    return _normalize_tags(tag_list)


def main():
    parser = argparse.ArgumentParser(
        description="Markdown Wiki Indexer — MD files + SQLite FTS5 search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mindex.py add articles/sqlite.md --title "SQLite FTS5" --summary "Indexing guide"
  mindex.py --index ~/my-wiki add articles/notes.md --title "Notes" --summary "Quick notes"
  mindex.py add articles/notes.md --title "Notes" --summary "Quick notes" --tags ai sqlite
  mindex.py add articles/notes.md --title "Notes" --summary "Quick notes" --source "https://example.com/original"
  mindex.py search "sqlite fts5"
  mindex.py search "agent memory" --limit 20
  mindex.py search "agent memory" --file articles/notes.md
  mindex.py search "agent memory" --json
  mindex.py tags
  mindex.py info articles/notes.md
  mindex.py info articles/notes.md --json
  mindex.py rm articles/notes.md
        """,
    )

    # Top-level --index option
    parser.add_argument(
        "--index",
        "-i",
        required=True,
        help="Index directory (default: current dir)",
    )

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # add
    p_add = sub.add_parser("add", help="Add markdown file to index")
    p_add.add_argument("file", help="Markdown file to add. ")
    p_add.add_argument(
        "--tags", "-t", nargs="+", help="Tags to assign to the file (space or comma separated)"
    )
    p_add.add_argument("--title", "-T", help="Custom title for the file (required)")
    p_add.add_argument("--summary", "-S", help="Custom summary text (required)")
    p_add.add_argument("--source", "-s", help="Source URL or reference (default: full file path)")

    # search
    p_search = sub.add_parser("search", help="Search indexed files")
    p_search.add_argument("query", help="Search query (FTS5 syntax)")
    p_search.add_argument("--limit", "-l", type=int, default=10, help="Max results")
    search_filter = p_search.add_mutually_exclusive_group()
    search_filter.add_argument("--file", "--path", help="Restrict search to a specific file")
    search_filter.add_argument(
        "--tags",
        "-t",
        nargs="+",
        help="Filter by tags (space or comma separated)",
    )
    p_search.add_argument("--text", action="store_true", help="Output as text instead of JSON")

    # tags
    sub.add_parser("tags", help="List all tags")

    # info
    p_info = sub.add_parser("info", help="Show file details")
    p_info.add_argument("file", help="Markdown file path")
    p_info.add_argument("--text", action="store_true", help="Output as text instead of JSON")

    # read
    p_read = sub.add_parser("read", help="Show file content from position")
    p_read.add_argument("file", help="Markdown file path")
    p_read.add_argument("--position", "-p", type=int, default=0, help="Start position (default: 0)")
    p_read.add_argument("--size", "-s", type=int, help="Number of characters to show")

    # rm/delete
    p_rm = sub.add_parser("rm", aliases=["delete"], help="Remove file from index")
    p_rm.add_argument("file", help="Markdown file path to remove")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # can use ~index_dir to specify different directory for index file
    index_path = Path(os.path.expanduser(args.index))
    if not index_path.exists():
        raise ValueError(f"Index directory does not exist: {index_path}")

    cmd = args.command

    if cmd == "add":
        file_path = _resolve_file(args.file)
        add_file(
            file_path,
            index_path=index_path,
            tags=_parse_tags(args.tags),
            title=args.title,
            summary=args.summary,
            source=args.source,
        )

    elif cmd in ["rm", "delete"]:
        file_path = _resolve_file(args.file)
        delete_file(file_path, index_path=index_path)

    elif cmd == "search":
        file_arg = _resolve_file(args.file) if args.file else None
        tag_list = _parse_tags(args.tags)
        results = search(
            args.query,
            index_path=index_path,
            limit=args.limit,
            file_path=file_arg,
            tags=tag_list,
        )
        output = (
            _format_search_results_text(results)
            if args.text
            else _format_search_results_json(results)
        )
        print(output)

    elif cmd == "tags":
        print("\n".join(list_tags(index_path=index_path)))

    elif cmd == "read":
        file_path = _resolve_file(args.file)
        content = read_file(
            file_path, index_path=index_path, position=args.position, size=args.size
        )
        print(content)

    elif cmd == "info":
        file_path = _resolve_file(args.file)
        obj = info(file_path, index_path=index_path)
        if args.text:
            print("\n")
            print(f"    File: {obj['path']}")
            print(f"  Source: {obj['source']}")
            print(f"   Title: {obj['title']}")
            print(f" Summary: {obj['summary']}")
            print(f"    Size: {obj['total_size']} characters")
            print(f"    Tags: {', '.join(obj['tags']) if obj['tags'] else '—'}\n")
        else:
            print(json.dumps(obj, indent=2))


if __name__ == "__main__":
    main()
