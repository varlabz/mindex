"""Search command: FTS5-based search across indexed files with optional path filtering."""

from dataclasses import dataclass
from pathlib import Path

from mindex.db import _db


@dataclass
class SearchResult:
    path: str
    snippet: str
    updated_at: str


@dataclass
class SearchResponse:
    results: list[SearchResult]
    results_count: int
    total: int


def search(index_dir: Path, query: str, file_path: list[str] | None, limit: int) -> SearchResponse:
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
        SearchResponse with matching file paths, content snippets,
        timestamps, and total match count.

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
        fts_query = query
        params: list = [fts_query]

        # Build WHERE clause (shared between count and fetch queries)
        where = "WHERE docs_fts MATCH ?"
        if file_path:
            clauses = []
            for fp in file_path:
                clauses.append("path GLOB ?")
                params.append(fp)
            where += " AND (" + " OR ".join(clauses) + ")"

        # 1. Count total matches (no LIMIT)
        count_sql = f"""
            SELECT COUNT(*)
            FROM docs_fts
            JOIN docs d ON docs_fts.rowid = d.id
            {where}"""
        total = conn.execute(count_sql, params).fetchone()[0]

        # 2. Fetch limited results
        sql = f"""
            SELECT d.path,
                   snippet(docs_fts, 0, '', '', '...', 64) as snippet,
                   d.updated_at
            FROM docs_fts
            JOIN docs d ON docs_fts.rowid = d.id
            {where}
            ORDER BY bm25(docs_fts)
            LIMIT ?
        """
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return SearchResponse(
            results=[SearchResult(**row) for row in rows],
            results_count=len(rows),
            total=total,
        )
