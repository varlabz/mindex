"""Markdown Index - SQLite FTS5-based markdown indexing and search."""

from .mindex import (
    add_file,
    search,
    manage_tags,
    list_tags,
    list_docs,
    info,
    delete_file,
)

__version__ = "0.1.0"
__all__ = [
    "add_file",
    "search",
    "manage_tags",
    "list_tags",
    "list_docs",
    "info",
    "delete_file",
]
