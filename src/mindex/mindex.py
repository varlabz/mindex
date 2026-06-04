import argparse
import json
from dataclasses import asdict
from pathlib import Path

from mindex.cmd_add_file import add_file
from mindex.cmd_del_file import del_file
from mindex.cmd_info_file import info_by_file, info_by_tag, print_info
from mindex.cmd_lint import lint, lint_fix, lint_output
from mindex.cmd_read_file import read_file
from mindex.cmd_search import search
from mindex.cmd_search_file import search_file

# ── CLI ────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    """Command-line interface for mindex operations."""
    parser = argparse.ArgumentParser(
        prog="mindex",
        description="SQLite FTS5-based wiki search index",
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=Path("."),
        help="Index directory containing mindex.sqlite (default: current directory)",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # add
    p_add = sub.add_parser("add", help="Add or update a file in the index")
    p_add.add_argument("file", type=str, help="Path to the file to index. Can use wildcard (e.g. \"~/*.md\")")
    p_add.add_argument("-t", "--tag", default=None, help="Optional tag for the file")

    # rm
    p_del = sub.add_parser("rm", help="Remove a file from the index")
    p_del.add_argument("file", type=str, help="Path to the file to remove (e.g. \"~/name*/*.md\")")

    # search
    p_search = sub.add_parser("search", help="Search indexed files via FTS5")
    p_search.add_argument("query", help="Search query (min 3 chars)")
    p_search.add_argument("-t", "--tag", default=None, help="Filter by tag")
    p_search.add_argument("-n", "--limit", type=int, default=10, help="Max results")
    p_search.add_argument(
        "-f",
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    # info
    p_info = sub.add_parser("info", help="Show info about an indexed file or list files by tag")
    p_info.add_argument(
        "file",
        type=str,
        nargs="?",
        default=None,
        help='Filename patter to the indexed file (e.g. "~/name*/*.md")',
    )
    p_info.add_argument(
        "-t",
        "--tag",
        default=None,
        help="Show all records with this tag (file argument is not required)",
    )
    p_info.add_argument(
        "-f",
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    # read
    p_read = sub.add_parser("read", help="Read file content from the index")
    p_read.add_argument("file", type=Path, help="Path to the indexed file to read")
    p_read.add_argument(
        "-p", "--position", type=int, default=0, help="Starting character offset (default: 0)"
    )
    p_read.add_argument(
        "-s",
        "--size",
        type=int,
        default=4000,
        help="Number of characters to read (default: 4000 chars)",
    )

    # lint
    p_lint = sub.add_parser(
        "lint", help="Lint indexed files: check existence and directory membership"
    )
    p_lint.add_argument(
        "file_dir",
        type=Path,
        nargs="?",
        default=None,
        help="Optional directory to verify files belong to",
    )
    p_lint.add_argument(
        "-f",
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    p_lint.add_argument(
        "--fix",
        action="store_true",
        default=False,
        help="Delete records for files that no longer exist on disk",
    )

    # file
    p_sf = sub.add_parser("file", help="Search within a specific indexed file")
    p_sf.add_argument("file", type=Path, help="Path to the indexed file to search")
    p_sf.add_argument("query", help="Search query")
    p_sf.add_argument("-n", "--limit", type=int, default=10, help="Max results")
    p_sf.add_argument(
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

    # Expand ~ in index_dir to home directory
    index_dir = args.index_dir.expanduser()
    if not index_dir.exists():
        raise FileNotFoundError(f"Index directory does not exist: {index_dir}")

    if args.command == "add":
        file = str(Path(args.file).expanduser().absolute())
        count = add_file(index_dir, file, tag=args.tag)
        print(f"Indexed: {args.file} ({count} record{'s' if count != 1 else ''})")

    elif args.command == "rm":
        file = str(Path(args.file).expanduser().absolute())
        try:
            count = del_file(index_dir, file)
            print(f"Removed: {args.file} ({count} record{'s' if count != 1 else ''})")
        except FileNotFoundError:
            print(f"Not found: {args.file}")

    elif args.command == "info":
        if args.tag and args.file:
            raise ValueError("Error: cannot use both 'file' and '--tag' at the same time")

        if args.tag:
            results = info_by_tag(index_dir, args.tag)
            print_info(results, args.format, tag=args.tag)
        else:
            file = str(Path(args.file).expanduser().absolute()) if args.file else None
            results = info_by_file(index_dir, file)
            print_info(results, args.format)

    elif args.command == "search":
        results = search(index_dir, args.query, tag=args.tag, limit=args.limit)
        if not results:
            print("No results.")
            return
        if args.format == "json":
            print(json.dumps([asdict(r) for r in results], indent=2))
        else:
            for r in results:
                print(f"{r.path}\t{r.tag or ''}\t{r.snippet}")

    elif args.command == "file":
        results = search_file(index_dir, args.file.expanduser(), args.query, limit=args.limit)
        if not results:
            print("No results.")
            return
        if args.format == "json":
            print(json.dumps([asdict(r) for r in results], indent=2))
        else:
            for r in results:
                print(r.snippet)

    elif args.command == "read":
        content = read_file(index_dir, args.file.expanduser(), start=args.position, size=args.size)
        print(content)

    elif args.command == "lint":
        file_dir = args.file_dir.expanduser() if args.file_dir else None
        if args.fix:
            lint_fix(index_dir, file_dir)
        else:
            results = lint(index_dir, file_dir)
            lint_output(results, args.format)


if __name__ == "__main__":
    main()
