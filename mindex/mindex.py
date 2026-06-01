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
import sys
from pathlib import Path

DB_PATH = "mindex.sqlite"       # index file stored in vault directory

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


class _db:
    """Context-manager wrapper for sqlite3.Connection with auto-close."""
    def __init__(self, index_dir: str = "."):
        self.conn = self.get_db(index_dir)
    def __enter__(self) -> sqlite3.Connection:
        return self.conn
    def __exit__(self, *exc) -> None:
        self.conn.close()

    @staticmethod
    def get_db(index_dir: str = ".") -> sqlite3.Connection:
        index_path = Path(index_dir)
        index_path.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(os.path.join(index_dir, DB_PATH))
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
    word_count INTEGER DEFAULT 0,       -- Number of words in the document
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

def add_file(file_path: Path, index_path: Path, tags: list[str] | None = None, title: str | None = None, summary: str | None = None, source: str | None = None):
    """Add or update a single markdown file in the index."""

    def file_hash(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]

    abs_path = str(file_path.absolute())
    with _db(index_path) as conn:
        h = file_hash(file_path)

        # Skip unchanged files unless custom title/summary/tags provided
        existing = conn.execute(
            "SELECT id, hash FROM docs WHERE path = ?", (abs_path,)
        ).fetchone()
        if existing and existing["hash"] == h and not title and not summary and not tags:
            print(f"  ✓ Unchanged, skipped: {abs_path}")
            return

        content = file_path.read_text(encoding="utf-8")
        wc = len(content.split())
        if not existing:
            conn.execute(
                """INSERT INTO docs (path, title, content, summary, word_count, source, hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (abs_path, title, content, summary, wc, source or abs_path, h)
            )
            doc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            action = "new"
        else:
            doc_id = existing["id"]
            conn.execute(
                """UPDATE docs SET title=?, content=?, summary=?, word_count=?, source=?, hash=?,
                   updated_at=datetime('now') WHERE path=?""",
                (title, content, summary, wc, source or abs_path, h, abs_path)
            )
            action = "updated"

        # Add & normalize tags
        tag_list = _normalize_tags(tags or [])
        for tag in tag_list:
            conn.execute(
                """INSERT OR IGNORE INTO tags (doc_id, tag) VALUES (?, ?)""",
                (doc_id, tag)
            )

        conn.commit()
        print(f"  ✓ Indexed: {action} {abs_path}")


# ── Search ────────────────────────────────────────────────────────

def search(query: str, index_path: Path, limit: int = 10, file_path: Path | None = None) -> list[sqlite3.Row] | None:
    """Search indexed markdown files with FTS5 ranking (includes tags).
    
    If file_path is provided, only search within that file.
    """
    with _db(index_path) as conn:
        # Check if index is empty
        count = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
        if count == 0: raise ValueError("Index is empty. Add files first.")

        sql = """
            SELECT d.id, d.path, d.title,
                   snippet(docs_fts, -1, '', '', '...', 100) AS snippet,   
                   d.summary, d.word_count, d.updated_at,
                   bm25(docs_fts) AS relevance
            FROM docs_fts f
            JOIN docs d ON d.id = f.rowid
            WHERE docs_fts MATCH ?
        """
        
        params = [query]
        
        # Add file filter if specified
        if file_path:
            abs_path = str(file_path.absolute())
            sql += " AND d.path = ?"
            params.append(abs_path)
        
        sql += " ORDER BY relevance LIMIT ?"
        params.append(limit)

        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError as e:
            print(f"  ✗ Search error: {e}", file=sys.stderr)
            print("     Try quoting your query or simplifying it.", file=sys.stderr)
            return

        return rows


# ── Tags ──────────────────────────────────────────────────────────

def manage_tags(file_path: Path, index_path: Path, add_tags: list[str] | None = None,
                remove_tags: list[str] | None = None):
    """Add or remove tags from a file."""
    abs_path = str(file_path)
    with _db(index_path) as conn:
        doc = conn.execute("SELECT id, content FROM docs WHERE path = ?", (abs_path,)).fetchone()

        if not doc:
            print(f"  ✗ File not indexed: {file_path}", file=sys.stderr)
            print(f"     Run: python md-index.py add {file_path}", file=sys.stderr)
            return

        doc_id = doc["id"]

        if add_tags:
            normalized = _normalize_tags(add_tags)
            for tag in normalized:
                conn.execute(
                    """INSERT OR IGNORE INTO tags (doc_id, tag) VALUES (?, ?)""",
                    (doc_id, tag)
                )
            print(f"  ✓ Added tags to {abs_path}: {', '.join(normalized)}")

        if remove_tags:
            normalized = _normalize_tags(remove_tags)
            for tag in normalized:
                conn.execute(
                    "DELETE FROM tags WHERE doc_id = ? AND tag = ?",
                    (doc_id, tag)
                )
            print(f"  ✓ Removed tags from {abs_path}: {', '.join(normalized)}")

        # Rebuild searchable content with current tags
        all_tags = [r["tag"] for r in conn.execute(
            "SELECT tag FROM tags WHERE doc_id = ?", (doc_id,)
        ).fetchall()]
        if all_tags:
            conn.execute(
                "UPDATE docs SET content = ?, updated_at = datetime('now') WHERE id = ?",
                (_build_searchable_content(doc["content"], all_tags), doc_id)
            )

        conn.commit()


def list_tags(index_path: Path = Path(".")):
    """List all tags and their document counts."""
    with _db(index_path) as conn:
        rows = conn.execute("""
            SELECT t.tag, COUNT(t.doc_id) AS count
            FROM tags t
            GROUP BY t.tag
            ORDER BY count DESC, t.tag
        """).fetchall()

        if not rows:
            print("  ✗ No tags found. Add tags with:", file=sys.stderr)
            print(f"     python md-index.py tags --add <file.md> tag1,tag2", file=sys.stderr)
            return

        print(f"\n  Tags ({len(rows)} total):\n")
        for r in rows:
            print(f"  • {r['tag']:<25} ({r['count']} doc{'s' if r['count'] != 1 else ''})")
        print()


def list_docs(tag: str | None = None, sort: str = "updated", show_tags: bool = False, index_path: Path = Path(".")):
    """List all indexed documents, optionally filtered by tag."""
    with _db(index_path) as conn:
        base = """
            SELECT d.path, d.title, d.word_count, d.updated_at,
                   GROUP_CONCAT(t.tag, ', ') AS tags
            FROM docs d
            LEFT JOIN tags t ON t.doc_id = d.id
        """

        conditions = []
        params = []

        if tag:
            conditions.append("d.id IN (SELECT doc_id FROM tags WHERE tag = ?)")
            params.append(tag)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        sort_col = "updated_at" if sort == "updated" else "title"
        sql = f"{base}{where} GROUP BY d.id ORDER BY {sort_col} DESC"

        rows = conn.execute(sql, params).fetchall()

        if not rows:
            print("  ✗ No documents found.", file=sys.stderr)
            return

        print(f"\n  Documents ({len(rows)} total)")
        if tag:
            print(f"  Tag filter: {tag}")
        print(f"  {'='*70}\n")

        for r in rows:
            tag_str = r['tags'] or "—"
            if show_tags and tag_str != "—":
                print(f"  • {r['title']:<35} ({r['word_count']} words)")
                print(f"    Path:   {r['path']}")
                print(f"    Updated:{r['updated_at']}")
                print(f"    Tags:   {tag_str}")
                print(f"  {'─'*70}")
            else:
                print(f"  • {r['title']:<40} [{tag_str}]")
                print(f"    {r['path']}  ({r['word_count']} words, {r['updated_at']})")

        print()


def info(file_path: Path, index_path: Path) -> dict:
    """Return details about an indexed file as a dict."""
    abs_path = str(file_path)
    with _db(index_path) as conn:
        doc = conn.execute("SELECT * FROM docs WHERE path = ?", (abs_path,)).fetchone()

        if not doc: raise ValueError(f"  ✗ File not indexed: {file_path}")

        tags = [r["tag"] for r in conn.execute(
            "SELECT tag FROM tags WHERE doc_id = ?", (doc["id"],)
        ).fetchall()]

        return {
            "path": doc["path"],
            "source": doc["source"],
            "title": doc["title"],
            "summary": doc["summary"],
            "size": doc["word_count"],
            "tags": tags,
        }


def delete_file(file_path: Path, index_path: Path):
    """Delete a file from the index."""
    abs_path = str(file_path)
    with _db(index_path) as conn:
        doc = conn.execute("SELECT id, title FROM docs WHERE path = ?", (abs_path,)).fetchone()
        
        if not doc: raise ValueError(f"  ✗ File not indexed: {file_path}")
        
        conn.execute("DELETE FROM docs WHERE id = ?", (doc["id"],))
        conn.commit()
        print(f"  ✓ Deleted: {doc['title']} ({abs_path})")


# ── CLI ───────────────────────────────────────────────────────────

def _resolve_file(file: str) -> Path:
    """Resolve a file argument to absolute Path. Try as-is first, then from current directory."""
    path = Path(file)
    # Try the path as given
    if path.exists(): return path.resolve()
  
    raise ValueError(f"Not found: {file}")

def _format_search_results_text(rows: list[sqlite3.Row]) -> str:
    """Format search results as plain text."""
    if not rows:
        print("  ✗ No results", file=sys.stderr)
        return ""
    output = f"\n  Results ({len(rows)} found):\n"
    for i, r in enumerate(rows, 1):
        output += f"  {i}. Path: {r['path']}\n     Title: {r['title']}\n     Snippet: {r['snippet']}\n\n"
    return output


def _format_search_results_json(rows: list[sqlite3.Row]) -> str:
    """Format search results as JSON."""
    return json.dumps([{"path": r["path"], "title": r["title"], "snippet": r["snippet"]} for r in rows], indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Markdown Wiki Indexer — MD files + SQLite FTS5 search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mindex.py add articles/sqlite.md --title "SQLite FTS5" --summary "Indexing guide"
  mindex.py --index_dir ~/my-wiki add articles/notes.md --title "Notes" --summary "Quick notes"
  mindex.py add articles/notes.md --title "Notes" --summary "Quick notes" --tags ai sqlite
  mindex.py add articles/notes.md --title "Notes" --summary "Quick notes" --source "https://example.com/original"
  mindex.py search "sqlite fts5"
  mindex.py search "agent memory" --limit 20
  mindex.py tags --add articles/notes.md ai,sqlite
  mindex.py tags --remove articles/notes.md draft
  mindex.py tags --list
  mindex.py list
  mindex.py list --tag ai
  mindex.py list --tags
  mindex.py info articles/notes.md
  mindex.py rebuild
        """
    )

    # Top-level --index option
    parser.add_argument("--index_dir", "-i", default=".", help="Index directory (default: current dir)")

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # add
    p_add = sub.add_parser("add", help="Add markdown file to index")
    p_add.add_argument("file", help="Markdown file to add. ")
    p_add.add_argument("--tags", "-t", nargs="+", help="Tags to assign to the file (space or comma separated)")
    p_add.add_argument("--title", "-T", required=True, help="Custom title for the file (required)")
    p_add.add_argument("--summary", "-S", required=True, help="Custom summary text (required)")
    p_add.add_argument("--source", "-s", help="Source URL or reference (default: full file path)")

    # search
    p_search = sub.add_parser("search", help="Search indexed files")
    p_search.add_argument("query", help="Search query (FTS5 syntax)")
    p_search.add_argument("--limit", "-l", type=int, default=10, help="Max results")
    p_search.add_argument("--file", "--path", help="Restrict search to a specific file")
    p_search_fmt = p_search.add_mutually_exclusive_group()
    p_search_fmt.add_argument("--json", action="store_true", help="Output as JSON")
    p_search_fmt.add_argument("--text", action="store_true", help="Output as text")

    # tags
    p_tags = sub.add_parser("tags", help="Manage tags")
    p_tags.add_argument("--add", nargs=2, metavar=("FILE", "TAGS"), help="Add tags to file")
    p_tags.add_argument("--remove", nargs=2, metavar=("FILE", "TAGS"), help="Remove tags from file")
    p_tags.add_argument("--list", "-l", action="store_true", help="List all tags")

    # list
    p_list = sub.add_parser("list", help="List indexed documents")
    p_list.add_argument("--tag", "-t", help="Filter by tag")
    p_list.add_argument("--sort", "-s", choices=["updated", "title"], default="updated")
    p_list.add_argument("--tags", action="store_true", help="Show tags for each document")

    # info
    p_info = sub.add_parser("info", help="Show file details")
    p_info.add_argument("file", help="Markdown file path")
    p_info_fmt = p_info.add_mutually_exclusive_group()
    p_info_fmt.add_argument("--json", action="store_true", help="Output as JSON")
    p_info_fmt.add_argument("--text", action="store_true", help="Output as text")

    # rm/delete
    p_rm = sub.add_parser("rm", aliases=["delete"], help="Remove file from index")
    p_rm.add_argument("file", help="Markdown file path to remove")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    index_path = Path(os.path.abspath(args.index_dir))
    if not index_path.exists(): index_path.mkdir(parents=True)
    cmd = args.command

    if cmd == "add":
        file_path = _resolve_file(args.file)
        tag_list = [x.strip() for t in args.tags or [] for x in t.split(",") if x.strip()]
        normalized_tags = _normalize_tags(tag_list)
        add_file(file_path, index_path=index_path, tags=normalized_tags, title=args.title, summary=args.summary, source=args.source)

    elif cmd in ["rm", "delete"]:
        file_path = _resolve_file(args.file)
        delete_file(file_path, index_path=index_path)

    elif cmd == "search":
        file_arg = _resolve_file(args.file) if args.file else None
        results = search(args.query, index_path=index_path, limit=args.limit, file_path=file_arg)
        if results:
            output = _format_search_results_json(results) if args.json else _format_search_results_text(results)
            if output:
                print(output)
        else:
            print(f"  ✗ No results for: {args.query}", file=sys.stderr)

    elif cmd == "tags":
        if args.list:
            list_tags(index_path=index_path)
        elif args.add:
            file_path = _resolve_file(args.add[0])
            tag_list = [x.strip() for t in args.tags or [] for x in t.split(",") if x.strip()]
            normalized_tags = _normalize_tags(tag_list)
            manage_tags(file_path, index_path=index_path, add_tags=normalized_tags)
        elif args.remove:
            file_path = _resolve_file(args.remove[0])
            tag_list = [x.strip() for t in args.tags or [] for x in t.split(",") if x.strip()]
            normalized_tags = _normalize_tags(tag_list)
            manage_tags(file_path, index_path=index_path, remove_tags=normalized_tags)
        else:
            list_tags(index_path=index_path)

    elif cmd == "list":
        list_docs(args.tag, args.sort, show_tags=args.tags, index_path=index_path)

    elif cmd == "info":
        file_path = _resolve_file(args.file)
        obj = info(file_path, index_path=index_path)
        if args.json:
            print(json.dumps(obj, indent=2))
        else:
            print(f"\n  File: {obj['path']}")
            print(f"  Source: {obj['source']}")
            print(f"  Title: {obj['title']}")
            print(f"  Summary: {obj['summary']}")
            print(f"  Size: {obj['size']} words")
            print(f"  Tags: {', '.join(obj['tags']) if obj['tags'] else '—'}\n")


if __name__ == "__main__":
    main()
