"""Markdown Index — SQLite FTS5-based markdown indexing and search."""

from .mindex import (
    add_file,
    search,
    list_tags,
    info,
    read_file,
    delete_file,
    _normalize_tags,
    _parse_tags,
    _db,
)

__version__ = "0.1.0"
__all__ = [
    "add_file",
    "search",
    "list_tags",
    "info",
    "read_file",
    "delete_file",
    "_normalize_tags",
    "_parse_tags",
    "_db",
]
