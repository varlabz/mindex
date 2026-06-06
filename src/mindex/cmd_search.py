"""Search command: FTS5-based search across indexed files with optional path filtering."""

from dataclasses import dataclass
from pathlib import Path

from mindex.db import _db


@dataclass
class SearchResult:
    path: str
    snippet: str
    updated_at: str


def search(
    index_dir: Path, query: str, file_path: list[str] | None, limit: int
) -> list[SearchResult]:
    """Search indexed files using FTS5 full-text search.

    Runs an FTS5 MATCH query against the index, optionally restricting results
    to files matching one or more glob-style path patterns. Results are ordered
    by relevance (BM25).

    Args:
        index_dir: Path to the index directory containing the SQLite database.
        query: FTS5 search query string. Must be at least 3 characters after stripping.
        file_path: Optional list of glob patterns to filter by file path
            (e.g. ["*.md", "docs/*"]). When None, searches all indexed files.
        limit: Maximum number of search results to return.

    Returns:
        list[SearchResult] with matching file paths, content snippets, and timestamps.

    Raises:
        ValueError: If query is empty/whitespace or shorter than 3 characters.
    """
    stripped = query.strip()
    if not stripped:
        raise ValueError("Query cannot be empty or whitespace only")

    if len(stripped) < 3:
        raise ValueError(
            f"Query too short ({len(stripped)} chars). Minimum query length is 3 characters."
        )

    with _db(index_dir) as conn:
        sql = """
            SELECT d.path,
                   snippet(docs_fts, 0, '', '', '...', 64) as snippet,
                   d.updated_at
            FROM docs_fts
            JOIN docs d ON docs_fts.rowid = d.id
            WHERE docs_fts MATCH ?
        """
        fts_query = query
        params: list = [fts_query]

        if file_path:
            clauses = []
            for fp in file_path:
                clauses.append("path GLOB ?")
                params.append(fp)
            sql += " AND (" + " OR ".join(clauses) + ")"

        sql += " ORDER BY bm25(docs_fts) "
        sql += " LIMIT ? "
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [SearchResult(**row) for row in rows]
