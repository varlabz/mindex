"""Search command: FTS5-based search across indexed files."""

from dataclasses import dataclass
from pathlib import Path

from mindex.db import _db


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
