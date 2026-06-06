"""File-level search: FTS5 highlight-based search within a single indexed file."""

from dataclasses import dataclass
from pathlib import Path

from mindex.db import _db


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


def file_search(
    index_dir: Path, file_path: str, query: str, limit: int = 10
) -> list[FileSearchResult]:
    """Search within a single indexed file using FTS5 and return matching snippets.

    Runs an FTS5 MATCH query restricted to one specific file path. Uses FTS5's
    ``highlight()`` function to locate matches, then extracts context windows
    around each match separated by custom markers to avoid byte-offset mismatches.

    Args:
        index_dir: Path to the index directory containing the SQLite database.
        file_path: Exact path of the indexed file to search within.
        query: FTS5 search query string.
        limit: Maximum number of snippets to return (default: 10).

    Returns:
        list[FileSearchResult] with snippet text and character position for each match.
        Returns an empty list if no matches are found.
    """
    with _db(index_dir) as conn:
        row = conn.execute(
            f"""SELECT highlight(docs_fts, 0, '{MARK_START}', '{MARK_END}') AS h
            FROM docs_fts
            JOIN docs d ON docs_fts.rowid = d.id
            WHERE docs_fts MATCH ? AND d.path = ?
            """,
            (
                query,
                file_path,
            ),
        ).fetchone()
        if not row or not row["h"]:
            return []

        return _extract_snippets(row["h"], limit)
