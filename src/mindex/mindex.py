import argparse
from pathlib import Path

from mindex.cmd_add_file import add_file
from mindex.cmd_del_file import del_file
from mindex.cmd_file_search import file_search, print_file_search_results
from mindex.cmd_info_file import info_by_file, print_info
from mindex.cmd_lint import lint, lint_output
from mindex.cmd_read_file import read_file
from mindex.cmd_search import print_search_results, search
from mindex.db import DB_FILE

# ── CLI ────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    """Command-line interface for mindex operations."""
    parser = argparse.ArgumentParser(
        prog="mindex",
        description="SQLite FTS5-based search index",
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=Path("."),
        help=f"Directory containing the {DB_FILE} database (default: current directory)",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # add
    p_add = sub.add_parser("add", help="Add or update a file in the index")
    p_add.add_argument(
        "paths", type=str, nargs="+", help="File path(s) or glob pattern(s) to index (e.g., ~/*.md)"
    )

    # rm
    p_del = sub.add_parser("rm", help="Remove files from the index")
    p_del.add_argument(
        "paths",
        type=str,
        nargs="+",
        help='File path(s) or glob pattern(s) to remove from the index (e.g., "~/*.md")',
    )

    # ls / list
    p_info = sub.add_parser("ls", aliases=["list"], help="List indexed files")
    p_info.add_argument(
        "paths",
        nargs="*",
        default=[],
        help='File path(s) or glob pattern(s) to filter indexed files (e.g., "~/*.md")',
    )
    p_info.add_argument(
        "-f",
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    # read
    p_read = sub.add_parser("read", help="Read file content from the index in chunks")
    p_read.add_argument("path", type=Path, help="Path to the indexed file to read")
    p_read.add_argument(
        "-p",
        "--position",
        type=int,
        default=0,
        help="Starting character offset of the chunk (default: 0)",
    )
    p_read.add_argument(
        "-s",
        "--size",
        type=int,
        default=4000,
        help="Number of characters to read of the chunk (default: 4000)",
    )

    # search
    p_search = sub.add_parser("search", help="Search indexed files via FTS5")
    p_search.add_argument("query", help="Full-text search query (minimum 3 characters)")
    p_search.add_argument(
        "paths", nargs="*", default=[], help="Filter by file path(s) (wildcard, e.g. '*.md')"
    )
    p_search.add_argument("-n", "--limit", type=int, default=25, help="Max results")
    p_search.add_argument(
        "-f",
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    # file search
    p_sf = sub.add_parser("fsearch", help="Search within an indexed file")
    p_sf.add_argument("query", help="Search query")
    p_sf.add_argument("path", type=Path, help="Path to the indexed file to search")
    p_sf.add_argument("-n", "--limit", type=int, default=25, help="Max results")
    p_sf.add_argument(
        "-f",
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    # lint
    p_lint = sub.add_parser(
        "lint", help="Lint indexed files: check existence and directory membership"
    )
    p_lint.add_argument(
        "paths",
        type=str,
        nargs="*",
        default=[],
        help='Optional path or wildcard pattern(s) to filter files (e.g., "*.md" "sub/*")',
    )
    p_lint.add_argument(
        "-f",
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return

    index_dir = args.index_dir.expanduser()
    if not index_dir.exists():
        raise FileNotFoundError(f"Index directory does not exist: {index_dir}")

    if args.command == "add":
        paths = [str(Path(p).expanduser()) for p in args.paths]
        count = add_file(index_dir, paths)
        print(f"Indexed: {count} record{'s' if count != 1 else ''}")

    elif args.command == "rm":
        paths = [str(Path(p).expanduser()) for p in args.paths]
        count = del_file(index_dir, paths)
        print(
            f"Removed: {len(paths)} path{'s' if len(paths) != 1 else ''} ({count} record{'s' if count != 1 else ''})"
        )

    elif args.command == "ls" or args.command == "list":
        paths = [str(Path(p).expanduser()) for p in args.paths] if args.paths else None
        results = info_by_file(index_dir, paths)
        print_info(results, args.format)

    elif args.command == "search":
        paths = [str(Path(p).expanduser()) for p in args.paths] if args.paths else None
        results = search(index_dir, args.query, file_path=paths, limit=args.limit)
        print_search_results(results, args.format)

    elif args.command == "fsearch":
        path = str(args.path.expanduser().absolute())
        results = file_search(index_dir, path, args.query, limit=args.limit)
        print_file_search_results(results, args.format)

    elif args.command == "read":
        path = str(args.path.expanduser().absolute())
        content = read_file(index_dir, path, start=args.position, size=args.size)
        print(content)

    elif args.command == "lint":
        paths = [str(Path(p).expanduser()) for p in args.paths] if args.paths else None
        results = lint(index_dir, paths)
        lint_output(results, args.format)


if __name__ == "__main__":
    main()
