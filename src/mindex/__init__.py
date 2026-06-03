"""Markdown Index — SQLite FTS5-based markdown indexing and search."""

from .mindex import (
    add_file,
    del_file,
    search,
    search_file,
    _db,
)

__version__ = "0.1.0"
__all__ = [
    "add_file",
    "del_file",
    "search",
    "search_file",
    "_db",
]
