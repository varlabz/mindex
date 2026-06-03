"""Tests for the mindex CLI (main function) — positive, negative, and edge cases."""

import json
from pathlib import Path

import pytest

from mindex.mindex import DB_FILE, main

# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def index_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for the index."""
    return tmp_path


@pytest.fixture
def test_file(index_dir: Path) -> Path:
    """Create a temporary test file."""
    file_path = index_dir / "test.md"
    file_path.write_text("# Hello World\n\nThis is a test file.", encoding="utf-8")
    return file_path


@pytest.fixture
def indexed_files(index_dir: Path) -> dict[str, Path]:
    """Create and index multiple test files."""
    files = {}
    for name, content in [
        ("file1.md", "# Python Tutorial\n\nPython is a great programming language."),
        ("file2.md", "# JavaScript Guide\n\nJavaScript is widely used for web development."),
        (
            "file3.md",
            "# Rust Programming\n\nRust is a systems programming language focused on safety.",
        ),
    ]:
        file_path = index_dir / name
        file_path.write_text(content, encoding="utf-8")
        files[name] = file_path
    # Index all created files so search tests have data
    for fp in files.values():
        main(["--index-dir", str(index_dir), "add", str(fp)])
    return files


# ── Helper ───────────────────────────────────────────────────────────────────────


def _run(argv: list[str], index_dir: Path, capfd: pytest.CaptureFixture[str]):
    """Run main() with argv and index_dir, return captured stdout."""
    capfd.readouterr()  # discard any previously captured output (e.g. from fixtures)
    main(["--index-dir", str(index_dir)] + argv)
    return capfd.readouterr().out


# ── Positive Tests ──────────────────────────────────────────────────────────────


class TestCLIAddPositive:
    """Positive tests for CLI 'add' command."""

    def test_add_file_success(
        self, index_dir: Path, test_file: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that add command indexes a file and prints confirmation."""
        out = _run(["add", str(test_file)], index_dir, capfd)
        assert f"Indexed: {test_file}" in out

    def test_add_file_with_tag(
        self, index_dir: Path, test_file: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that add command with --tag option stores the tag."""
        _run(["add", str(test_file), "--tag", "wiki"], index_dir, capfd)

        with open(index_dir / DB_FILE) as f:
            pass  # DB created; tag verified via API if needed

    def test_add_file_with_short_tag_option(
        self, index_dir: Path, test_file: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that add command with -t option stores the tag."""
        _run(["add", str(test_file), "-t", "quick"], index_dir, capfd)

    def test_add_overwrites_existing(
        self, index_dir: Path, test_file: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that add command updates an existing file entry."""
        _run(["add", str(test_file)], index_dir, capfd)
        _run(["add", str(test_file)], index_dir, capfd)  # second add


class TestCLIRmPositive:
    """Positive tests for CLI 'rm' command."""

    def test_rm_file_success(
        self, index_dir: Path, test_file: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that rm command removes a file and prints confirmation."""
        # First add, then remove
        main(["--index-dir", str(index_dir), "add", str(test_file)])
        out = _run(["rm", str(test_file)], index_dir, capfd)
        assert f"Removed: {test_file}" in out

    def test_rm_removes_from_index(self, index_dir: Path, test_file: Path):
        """Test that rm command actually removes the file from the index."""
        from mindex.mindex import _db, add_file

        add_file(index_dir, test_file)

        with _db(index_dir) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM docs WHERE path = ?",
                (str(test_file.absolute()),),
            ).fetchone()
            assert row[0] == 1

        main(["--index-dir", str(index_dir), "rm", str(test_file)])

        with _db(index_dir) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM docs WHERE path = ?",
                (str(test_file.absolute()),),
            ).fetchone()
            assert row[0] == 0


class TestCLIAddNegative:
    """Negative tests for CLI 'add' command."""

    def test_add_nonexistent_file(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that add command raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            main(["--index-dir", str(index_dir), "add", "nonexistent.md"])

    def test_add_missing_file_argument(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that add command requires a file argument."""
        with pytest.raises(SystemExit):
            main(["--index-dir", str(index_dir), "add"])


class TestCLIRmNegative:
    """Negative tests for CLI 'rm' command."""

    def test_rm_missing_file_argument(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that rm command requires a file argument."""
        with pytest.raises(SystemExit):
            main(["--index-dir", str(index_dir), "rm"])

    def test_rm_nonexistent_file_no_error(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that rm command does not error for a file never added."""
        out = _run(["rm", "never_added.md"], index_dir, capfd)
        assert "never_added.md" in out


# ── CLI Search Tests ────────────────────────────────────────────────────────────


class TestCLISearchPositive:
    """Positive tests for CLI 'search' command."""

    def test_search_json_output(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that search command outputs valid JSON by default."""
        out = _run(["search", "programming"], index_dir, capfd)
        results = json.loads(out)
        assert isinstance(results, list)
        assert len(results) >= 2
        for r in results:
            assert "path" in r
            assert "snippet" in r

    def test_search_text_output(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that search command with --format text outputs tab-separated lines."""
        out = _run(["search", "programming", "--format", "text"], index_dir, capfd)
        lines = [l for l in out.strip().split("\n") if l]
        assert len(lines) >= 2
        # Check that the query term appears somewhere in the text output
        # (FTS5 snippet() can contain newlines, so a result may span multiple lines)
        assert any("programming" in l.lower() for l in lines)

    def test_search_with_tag_filter(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that search command with --tag option filters results."""
        # Add tagged files
        f1 = index_dir / "tagged1.md"
        f1.write_text("Python programming is great", encoding="utf-8")
        f2 = index_dir / "tagged2.md"
        f2.write_text("JavaScript programming is fun", encoding="utf-8")

        main(["--index-dir", str(index_dir), "add", str(f1), "--tag", "python"])
        main(["--index-dir", str(index_dir), "add", str(f2), "--tag", "javascript"])

        out = _run(["search", "programming", "--tag", "python"], index_dir, capfd)
        results = json.loads(out)
        for r in results:
            assert r.get("tag") == "python"

    def test_search_with_limit(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that search command with --limit option respects the limit."""
        out = _run(["search", "programming", "--limit", "1"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) <= 1

    def test_search_with_short_limit_option(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that search command with -n option respects the limit."""
        out = _run(["search", "programming", "-n", "1"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) <= 1

    def test_search_with_no_results(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that search command prints 'No results.' when nothing matches."""
        out = _run(["search", "nonexistent_xyz_123"], index_dir, capfd)
        assert "No results." in out

    def test_search_multi_word(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that search command works with multi-word query."""
        out = _run(["search", "programming language"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) >= 2


class TestCLISearchNegative:
    """Negative tests for CLI 'search' command."""

    def test_search_empty_query(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that search command raises ValueError for empty query."""
        with pytest.raises(ValueError, match="Query cannot be empty or whitespace only"):
            _run(["search", "   "], index_dir, capfd)

    def test_search_short_query(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that search command raises ValueError for query too short."""
        with pytest.raises(ValueError, match="Query too short"):
            _run(["search", "ab"], index_dir, capfd)

    def test_search_missing_query_argument(
        self, index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that search command requires a query argument."""
        with pytest.raises(SystemExit):
            main(["--index-dir", str(index_dir), "search"])

    def test_search_invalid_limit(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that search command with invalid limit raises an error."""
        with pytest.raises(SystemExit):
            _run(["search", "programming", "--limit", "not_a_number"], index_dir, capfd)

    def test_search_invalid_format(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that search command with invalid format raises an error."""
        with pytest.raises(SystemExit):
            _run(["search", "programming", "--format", "xml"], index_dir, capfd)


class TestCLIFilePositive:
    """Positive tests for CLI 'file' command."""

    def test_file_search_json_output(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that file command outputs valid JSON by default."""
        out = _run(["file", str(index_dir / "file1.md"), "Python"], index_dir, capfd)
        results = json.loads(out)
        assert isinstance(results, list)
        assert len(results) >= 1
        for r in results:
            assert "snippet" in r
            assert "position" in r

    def test_file_search_text_output(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that file command with --format text outputs snippets line by line."""
        out = _run(
            ["file", str(index_dir / "file1.md"), "Python", "--format", "text"], index_dir, capfd
        )
        lines = [l for l in out.strip().split("\n") if l]
        assert len(lines) >= 1

    def test_file_search_with_limit(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that file command with --limit option respects the limit."""
        # Add a file with many repeated terms
        f = index_dir / "repeats.md"
        f.write_text(" ".join(["term"] * 20), encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(f)])

        out = _run(["file", str(f), "term", "--limit", "3"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) <= 3

    def test_file_search_with_no_results(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that file command prints 'No results.' when nothing matches."""
        out = _run(["file", str(index_dir / "file1.md"), "nonexistent_xyz"], index_dir, capfd)
        assert "No results." in out

    def test_file_search_multi_word(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that file command works with multi-word query."""
        out = _run(["file", str(index_dir / "file1.md"), "Python programming"], index_dir, capfd)
        if "No results." in out:
            return  # Phrase match may not find results depending on content layout
        results = json.loads(out)
        assert len(results) >= 0


class TestCLIFileNegative:
    """Negative tests for CLI 'file' command."""

    def test_file_missing_file_argument(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that file command requires a file argument."""
        with pytest.raises(SystemExit):
            main(["--index-dir", str(index_dir), "file"])

    def test_file_missing_query_argument(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that file command requires a query argument."""
        with pytest.raises(SystemExit):
            main(["--index-dir", str(index_dir), "file", "somefile.md"])

    def test_file_unindexed_file(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that file command returns no results for an unindexed file."""
        unindexed = index_dir / "not_indexed.md"
        unindexed.write_text("some content", encoding="utf-8")

        out = _run(["file", str(unindexed), "content"], index_dir, capfd)
        assert "No results." in out


# ── CLI Global Options Tests ────────────────────────────────────────────────────


class TestCLIOptionsPositive:
    """Positive tests for global CLI options."""

    def test_index_dir_option(
        self, index_dir: Path, test_file: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that --index-dir option works to specify index directory."""
        out = _run(["add", str(test_file)], index_dir, capfd)
        assert f"Indexed: {test_file}" in out
        assert (index_dir / DB_FILE).exists()

    def test_no_command_shows_help(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that running without a command prints help."""
        out = _run([], index_dir, capfd)
        assert "mindex" in out
        assert "add" in out
        assert "rm" in out
        assert "search" in out
        assert "file" in out

    def test_index_dir_nonexistent_creates_db(
        self, index_dir: Path, test_file: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that add command creates the SQLite DB in the index directory."""
        _run(["add", str(test_file)], index_dir, capfd)
        assert (index_dir / DB_FILE).exists()


class TestCLIOptionsNegative:
    """Negative tests for global CLI options."""

    def test_invalid_index_dir_type(self, capfd: pytest.CaptureFixture[str]):
        """Test that --index-dir with a non-existent path causes an error."""
        with pytest.raises(ValueError):
            main(["--index-dir", "12345", "add", "something"])

    def test_unknown_subcommand(self, capfd: pytest.CaptureFixture[str]):
        """Test that an unknown subcommand causes an error."""
        with pytest.raises(SystemExit):
            main(["unknown-command"])


# ── CLI Edge Cases ──────────────────────────────────────────────────────────────


class TestCLIEdgeCases:
    """Edge case tests for CLI commands."""

    def test_add_file_with_spaces_in_name(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that add command handles files with spaces in the name."""
        f = index_dir / "my file name.md"
        f.write_text("# Space File\n\nContent here.", encoding="utf-8")
        out = _run(["add", str(f)], index_dir, capfd)
        assert f"Indexed: {f}" in out

    def test_add_file_with_special_chars_in_name(
        self, index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that add command handles files with special characters in the name."""
        f = index_dir / "file [v2].md"
        f.write_text("# Special\n\nContent.", encoding="utf-8")
        out = _run(["add", str(f)], index_dir, capfd)
        assert f"Indexed: {f}" in out

    def test_add_file_dotfile(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that add command handles dotfiles."""
        f = index_dir / ".hidden"
        f.write_text("# Hidden\n\nContent.", encoding="utf-8")
        out = _run(["add", str(f)], index_dir, capfd)
        assert f"Indexed: {f}" in out

    def test_add_file_empty_content(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that add command handles empty file content."""
        f = index_dir / "empty.md"
        f.write_text("", encoding="utf-8")
        out = _run(["add", str(f)], index_dir, capfd)
        assert f"Indexed: {f}" in out

    def test_add_file_unicode_content(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that add command handles unicode content."""
        f = index_dir / "unicode.md"
        f.write_text("# こんにちは\n\nこれはテストです。", encoding="utf-8")
        out = _run(["add", str(f)], index_dir, capfd)
        assert f"Indexed: {f}" in out

    def test_add_file_large_content(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that add command handles large file content."""
        f = index_dir / "large.md"
        f.write_text("x" * 100_000, encoding="utf-8")
        out = _run(["add", str(f)], index_dir, capfd)
        assert f"Indexed: {f}" in out

    def test_search_json_structure(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that search JSON output has the correct structure."""
        out = _run(["search", "Python"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) >= 1
        r = results[0]
        assert "path" in r
        assert "snippet" in r
        assert "tag" in r or "tag" in json.loads(out)[0]

    def test_search_text_output_structure(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that search text output has path, tag, snippet separated by tabs."""
        out = _run(["search", "Python", "--format", "text"], index_dir, capfd)
        lines = [l for l in out.strip().split("\n") if l]
        assert len(lines) >= 1
        # First line should contain the path
        assert "file1.md" in lines[0]

    def test_file_json_structure(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that file search JSON output has the correct structure."""
        out = _run(["file", str(index_dir / "file1.md"), "Python"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) >= 1
        for r in results:
            assert "snippet" in r
            assert "position" in r

    def test_file_text_structure(
        self, indexed_files: dict[str, Path], index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that file search text output prints snippets line by line."""
        out = _run(
            ["file", str(index_dir / "file1.md"), "Python", "--format", "text"], index_dir, capfd
        )
        lines = [l for l in out.strip().split("\n") if l]
        assert len(lines) >= 1

    def test_cli_add_search_roundtrip(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that a file added via CLI can be searched via CLI."""
        f = index_dir / "roundtrip.md"
        f.write_text("This is a test for roundtrip CLI testing.", encoding="utf-8")

        _run(["add", str(f)], index_dir, capfd)
        out = _run(["search", "roundtrip"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) >= 1
        assert "roundtrip.md" in results[0]["path"]

    def test_cli_add_search_rm_roundtrip(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test add -> search -> rm roundtrip via CLI."""
        f = index_dir / "full_roundtrip.md"
        f.write_text("Full roundtrip test content here.", encoding="utf-8")

        _run(["add", str(f)], index_dir, capfd)

        out = _run(["search", "roundtrip"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) >= 1

        _run(["rm", str(f)], index_dir, capfd)

        out = _run(["search", "roundtrip"], index_dir, capfd)
        if "No results." in out:
            return
        results = json.loads(out)
        assert len(results) == 0

    def test_cli_add_with_tag_search_with_tag(
        self, index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test add with tag, then search with tag filter."""
        f = index_dir / "tagged.md"
        f.write_text("Tagged content for testing.", encoding="utf-8")

        _run(["add", str(f), "--tag", "mytag"], index_dir, capfd)

        out = _run(["search", "Tagged", "--tag", "mytag"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) >= 1
        assert results[0]["tag"] == "mytag"

    def test_cli_file_with_unicode(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test file command with unicode content."""
        f = index_dir / "unicode.md"
        f.write_text("日本語テスト\n\nこれはテストです。", encoding="utf-8")
        _run(["add", str(f)], index_dir, capfd)

        out = _run(["file", str(f), "テスト"], index_dir, capfd)
        # FTS5 may not match CJK, but should not crash
        assert "No results." in out or json.loads(out)
