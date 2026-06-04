"""Markdown Index — SQLite FTS5-based markdown indexing and search."""

from .cmd_add_file import add_file
from .cmd_del_file import del_file
from .cmd_info import FileInfo, info, info_by_tag
from .cmd_read_file import read_file
from .cmd_search import search
from .cmd_search_file import FileSearchResult, search_file
from .db import _db

__version__ = "0.1.0"
__all__ = [
    "add_file",
    "del_file",
    "info",
    "info_by_tag",
    "read_file",
    "search",
    "search_file",
    "FileInfo",
    "FileSearchResult",
    "_db",
]
