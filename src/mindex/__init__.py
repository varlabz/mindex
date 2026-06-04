"""Markdown Index — SQLite FTS5-based markdown indexing and search."""

from .cmd_add_file import add_file
from .cmd_del_file import del_file
from .cmd_info_file import FileInfo, info_by_file
from .cmd_read_file import read_file
from .cmd_search import search
from .cmd_file_search import FileSearchResult, file_search
from .db import _db

__version__ = "0.1.0"
__all__ = [
    "add_file",
    "del_file",
    "info_by_file",
    "read_file",
    "search",
    "file_search",
    "FileInfo",
    "FileSearchResult",
    "_db",
]
