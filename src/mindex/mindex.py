import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from mindex.cmd_add_file import add_file
from mindex.cmd_del_file import del_file
from mindex.cmd_file_search import file_search
from mindex.cmd_info_file import info_by_file
from mindex.cmd_lint import lint
from mindex.cmd_read_file import read_file
from mindex.cmd_search import search
from mindex.db import DB_FILE


@dataclass
class ReadResult:
    content: str
    path: str


# ── CLI ────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    """Command-line interface for mindex operations."""
    parser = argparse.ArgumentParser(
        prog="mindex",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""SQLite FTS5-based search index.

FTS5 Query Syntax:
  FTS5 uses a full-text query language for powerful text search.

  1. Simple queries:
     mindex search "python"              # Find "python" in any word
     mindex search "python" "*.py"       # Filter by file path pattern

  2. Prefix queries (words starting with a prefix):
     mindex search "pyth*"               # Matches: python, pytest, pythagorean

  3. Phrase queries (exact phrase, word order preserved):
     mindex search '"full text search"'  # Exact phrase match

  4. Boolean operators:
     mindex search 'python AND rust'     # Both terms must appear
     mindex search 'python OR rust'      # Either term may appear
     mindex search 'python NOT java'     # Must have python, must not have java
     mindex search '(python OR rust) AND cli'

  5. OR-group queries:
     mindex search '(python rust) AND cli'

  6. Column filters with paths:
      mindex search 'python' '*.py'     # Search "python" in .py files only
      mindex search '"async"' "*.rs"    # Search phrase in .rs files only

Examples:
  # Index files
  mindex add "src/**/*.py"
  mindex add "docs/*.md"

  # Basic search
  mindex search "async"
  mindex search "async" "*.py" -n 10

  # Phrase search
  mindex search '"full text"'

  # Boolean logic
  mindex search 'python AND rust'
  mindex search '(python OR rust) NOT go'

  # Prefix search
  mindex search 'pyth*'

  # List indexed files
  mindex ls
  mindex ls "*.py" -f text

  # Read a chunk of indexed content
  mindex read "src/mindex/mindex.py" -s 2000

  # File-specific search
  mindex fsearch "async" "src/mindex/mindex.py"
""",
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

    # file search
    p_sf = sub.add_parser("fsearch", help="Search within an indexed file")
    p_sf.add_argument("query", help="Search query")
    p_sf.add_argument("path", type=Path, help="Path to the indexed file to search")
    p_sf.add_argument("-n", "--limit", type=int, default=25, help="Max results")

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

    # Add --format to ALL subcommands in one place
    for p in (p_add, p_del, p_info, p_read, p_search, p_sf, p_lint):
        p.add_argument(
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
        if args.format == "json":
            print(json.dumps({"indexed": count, "paths": paths}, indent=2))
        else:
            print(f"Indexed: {count} record{'s' if count != 1 else ''}")

    elif args.command == "rm":
        paths = [str(Path(p).expanduser()) for p in args.paths]
        results = del_file(index_dir, paths)
        print_results([results], args.format)

    elif args.command == "ls" or args.command == "list":
        paths = [str(Path(p).expanduser()) for p in args.paths] if args.paths else None
        results = info_by_file(index_dir, paths)
        print_results(results, args.format)

    elif args.command == "search":
        paths = [str(Path(p).expanduser()) for p in args.paths] if args.paths else None
        results = search(index_dir, args.query, file_path=paths, limit=args.limit)
        print_results(results, args.format)

    elif args.command == "fsearch":
        path = str(args.path.expanduser().absolute())
        results = file_search(index_dir, path, args.query, limit=args.limit)
        print_results(results, args.format)

    elif args.command == "read":
        path = str(args.path.expanduser().absolute())
        results = read_file(index_dir, path, start=args.position, size=args.size)
        print_results([results], args.format)

    elif args.command == "lint":
        paths = [str(Path(p).expanduser()) for p in args.paths] if args.paths else None
        results = lint(index_dir, paths)
        print_results(results, args.format)


def print_results(results: list, fmt: str) -> None:
    """Print a list of records in the given format."""
    if not results:
        if fmt == "json":
            print("[]")
        else:
            print("No records found.")
        return
    if fmt == "json":
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        for r in results:
            print("-" * 40)
            for k, v in asdict(r).items():
                print(f"{k}: {v or '-'}")
            print()


if __name__ == "__main__":
    main()
