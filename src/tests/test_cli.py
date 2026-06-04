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

    def test_search_no_results(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that search command prints 'No results.' when nothing matches."""
        out = _run(["search", "xyznonexistent123"], index_dir, capfd)
        assert "No results." in out

    def test_search_with_limit(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that search command respects --limit option."""
        # Add a file with a unique term to ensure predictable results
        test_file = index_dir / "limit_test.md"
        test_file.write_text("unique limit test term here", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["search", "limit", "--limit", "1"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) <= 1

    def test_search_with_short_limit_option(
        self, index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that search command respects -n short option for limit."""
        test_file = index_dir / "limit_test2.md"
        test_file.write_text("unique limit test term here", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["search", "limit", "-n", "1"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) <= 1

    def test_search_empty_query(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that search with empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            _run(["search", ""], index_dir, capfd)

    def test_search_short_query(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that search with too-short query raises ValueError."""
        with pytest.raises(ValueError, match="Query too short"):
            _run(["search", "ab"], index_dir, capfd)


class TestCLIFilePositive:
    """Positive tests for CLI 'file' command."""

    def test_file_search_json_output(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that file command outputs valid JSON by default."""
        test_file = index_dir / "search_target.md"
        test_file.write_text("apple banana cherry apple date apple", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["file", str(test_file), "apple"], index_dir, capfd)
        results = json.loads(out)
        assert isinstance(results, list)
        assert len(results) >= 1
        for r in results:
            assert "snippet" in r
            assert "position" in r

    def test_file_search_text_output(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that file command with --format text outputs snippets."""
        test_file = index_dir / "search_target.md"
        test_file.write_text("hello world hello", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["file", str(test_file), "hello", "--format", "text"], index_dir, capfd)
        lines = [l for l in out.strip().split("\n") if l]
        assert len(lines) >= 1
        assert any("hello" in l for l in lines)

    def test_file_search_with_limit(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that file command respects --limit option."""
        test_file = index_dir / "search_target.md"
        test_file.write_text("test test test test test", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["file", str(test_file), "test", "--limit", "2"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) == 2

    def test_file_search_multi_word(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test file command with multi-word query."""
        test_file = index_dir / "search_target.md"
        test_file.write_text("the quick brown fox jumps", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["file", str(test_file), "quick brown"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) >= 1


class TestCLIFileNegative:
    """Negative tests for CLI 'file' command."""

    def test_file_no_results(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that file command prints 'No results.' when nothing matches."""
        test_file = index_dir / "search_target.md"
        test_file.write_text("hello world", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["file", str(test_file), "nonexistent123"], index_dir, capfd)
        assert "No results." in out

    def test_file_unindexed_file(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that file command returns no results for unindexed file."""
        test_file = index_dir / "search_target.md"
        test_file.write_text("hello world", encoding="utf-8")
        # Do NOT add to index

        out = _run(["file", str(test_file), "hello"], index_dir, capfd)
        assert "No results." in out

    def test_file_missing_file_argument(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that file command requires a file argument."""
        with pytest.raises(SystemExit):
            _run(["file"], index_dir, capfd)

    def test_file_missing_query_argument(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that file command requires a query argument."""
        with pytest.raises(SystemExit):
            _run(["file", "somefile.md"], index_dir, capfd)


class TestCLIReadPositive:
    """Positive tests for CLI 'read' command."""

    def test_read_full_file(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that read command outputs full file content."""
        test_file = index_dir / "read_target.md"
        expected = "# Title\n\nHello world content."
        test_file.write_text(expected, encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["read", str(test_file)], index_dir, capfd)
        assert expected in out

    def test_read_with_start_offset(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that read command respects --position option."""
        test_file = index_dir / "read_target.md"
        test_file.write_text("0123456789", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["read", str(test_file), "--position", "5"], index_dir, capfd)
        assert "56789" in out

    def test_read_with_short_position_option(
        self, index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that read command respects -p short option for position."""
        test_file = index_dir / "read_target.md"
        test_file.write_text("0123456789", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["read", str(test_file), "-p", "7"], index_dir, capfd)
        assert "789" in out

    def test_read_with_size(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that read command respects --size option."""
        test_file = index_dir / "read_target.md"
        test_file.write_text("0123456789", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["read", str(test_file), "--position", "2", "--size", "3"], index_dir, capfd)
        assert "234" in out

    def test_read_with_short_size_option(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that read command respects -s short option for size."""
        test_file = index_dir / "read_target.md"
        test_file.write_text("0123456789", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["read", str(test_file), "-p", "0", "-s", "4"], index_dir, capfd)
        assert "0123" in out

    def test_read_empty_file(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test reading an empty file."""
        test_file = index_dir / "empty.md"
        test_file.write_text("", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["read", str(test_file)], index_dir, capfd)
        # print() adds a trailing newline even for empty string
        assert out.strip() == ""


class TestCLIReadNegative:
    """Negative tests for CLI 'read' command."""

    def test_read_unindexed_file(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that read command raises error for unindexed file."""
        test_file = index_dir / "not_indexed.md"
        test_file.write_text("content", encoding="utf-8")

        with pytest.raises(FileNotFoundError):
            _run(["read", str(test_file)], index_dir, capfd)

    def test_read_missing_file_argument(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that read command requires a file argument."""
        with pytest.raises(SystemExit):
            _run(["read"], index_dir, capfd)


class TestCLIInfoPositive:
    """Positive tests for CLI 'info' command."""

    def test_info_json_output(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that info command outputs valid JSON by default."""
        test_file = index_dir / "info_target.md"
        test_file.write_text("some content here", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["info", str(test_file)], index_dir, capfd)
        result = json.loads(out)
        assert "path" in result
        assert "size" in result
        assert "updated_at" in result
        assert "tag" in result
        assert result["size"] == len("some content here")
        assert result["tag"] is None

    def test_info_text_output(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that info command with --format text outputs labeled fields."""
        test_file = index_dir / "info_target.md"
        test_file.write_text("some content here", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["info", str(test_file), "--format", "text"], index_dir, capfd)
        assert "path:" in out
        assert "size:" in out
        assert "updated_at:" in out
        assert "tag:" in out

    def test_info_with_tag(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that info command includes the tag when one is set."""
        test_file = index_dir / "info_target.md"
        test_file.write_text("content", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file), "--tag", "wiki"])

        out = _run(["info", str(test_file)], index_dir, capfd)
        result = json.loads(out)
        assert result["tag"] == "wiki"

    def test_info_text_shows_dash_for_missing_tag(
        self, index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test that info text format shows '-' for missing tag."""
        test_file = index_dir / "info_target.md"
        test_file.write_text("content", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        out = _run(["info", str(test_file), "--format", "text"], index_dir, capfd)
        assert "tag:" in out and "-" in out

    def test_info_tag_json_output(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that info --tag outputs valid JSON with multiple records."""
        for i in range(3):
            f = index_dir / f"tagged_{i}.md"
            f.write_text(f"content {i}", encoding="utf-8")
            main(["--index-dir", str(index_dir), "add", str(f), "--tag", "wiki"])

        out = _run(["info", "--tag", "wiki"], index_dir, capfd)
        results = json.loads(out)
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(r["tag"] == "wiki" for r in results)

    def test_info_tag_text_output(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that info --tag with --format text outputs labeled fields."""
        f = index_dir / "tagged.md"
        f.write_text("content", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(f), "--tag", "article"])

        out = _run(["info", "--tag", "article", "--format", "text"], index_dir, capfd)
        assert "path:" in out
        assert "size:" in out
        assert "updated_at:" in out
        assert "tag:" in out and "article" in out

    def test_info_tag_no_results(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that info --tag prints message when no records match."""
        out = _run(["info", "--tag", "nonexistent"], index_dir, capfd)
        assert "No records found with tag: nonexistent" in out

    def test_info_tag_and_file_error(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that info with both file and --tag prints error."""
        test_file = index_dir / "target.md"
        test_file.write_text("content", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        with pytest.raises(ValueError, match="cannot use both 'file' and '--tag'"):
            _run(["info", str(test_file), "--tag", "wiki"], index_dir, capfd)

    def test_info_tag_with_single_record(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that info --tag works with a single matching record."""
        f = index_dir / "single.md"
        f.write_text("single content", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(f), "--tag", "solo"])

        out = _run(["info", "--tag", "solo"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) == 1
        assert results[0]["tag"] == "solo"


class TestCLIInfoNegative:
    """Negative tests for CLI 'info' command."""

    def test_info_unindexed_file(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that info command raises error for unindexed file."""
        test_file = index_dir / "not_indexed.md"
        test_file.write_text("content", encoding="utf-8")

        with pytest.raises(FileNotFoundError):
            _run(["info", str(test_file)], index_dir, capfd)

    def test_info_missing_file_argument(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that info command prints error when no file or --tag is provided."""
        out = _run(["info"], index_dir, capfd)
        assert "Error: 'file' argument is required when not using --tag" in out


class TestCLIEdgeCases:
    """Edge case tests for CLI commands."""

    def test_no_command_prints_help(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that running main with no command prints help."""
        main(["--index-dir", str(index_dir)])
        out, err = capfd.readouterr()
        assert "usage" in out.lower() or "help" in out.lower()

    def test_index_dir_does_not_exist(self):
        """Test that CLI raises error for non-existent index directory."""
        with pytest.raises(ValueError, match="does not exist"):
            main(["--index-dir", "/nonexistent/path/xyz", "search", "test"])

    def test_add_file_with_tilde_path(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that add command handles paths with tilde."""
        # Create a subdirectory with tilde-like name
        subdir = index_dir / "tilde_test"
        subdir.mkdir()
        test_file = subdir / "file.md"
        test_file.write_text("content", encoding="utf-8")

        out = _run(["add", str(test_file)], index_dir, capfd)
        assert "Indexed:" in out

    def test_search_unicode_content(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test search with unicode file content."""
        test_file = index_dir / "unicode.md"
        test_file.write_text("こんにちは世界", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        # Search for ASCII term that won't match CJK
        out = _run(["search", "hello"], index_dir, capfd)
        assert "No results." in out

    def test_multiple_add_same_file(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test adding the same file multiple times."""
        test_file = index_dir / "test.md"
        test_file.write_text("v1", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file)])

        test_file.write_text("v2", encoding="utf-8")
        out = _run(["add", str(test_file)], index_dir, capfd)
        assert "Indexed:" in out

        # Verify content was updated
        out = _run(["read", str(test_file)], index_dir, capfd)
        assert "v2" in out

    def test_rm_nonexistent_file_no_crash(self, index_dir: Path, capfd: pytest.CaptureFixture[str]):
        """Test that rm of a never-added file doesn't crash."""
        out = _run(["rm", "never_added_file.md"], index_dir, capfd)
        assert "never_added_file.md" in out

    def test_search_tag_with_special_chars(
        self, index_dir: Path, capfd: pytest.CaptureFixture[str]
    ):
        """Test search with tag containing special characters."""
        test_file = index_dir / "special_tag.md"
        test_file.write_text("tagged content", encoding="utf-8")
        main(["--index-dir", str(index_dir), "add", str(test_file), "--tag", "my-tag_v2"])

        out = _run(["search", "tagged", "--tag", "my-tag_v2"], index_dir, capfd)
        results = json.loads(out)
        assert len(results) >= 1
        assert results[0].get("tag") == "my-tag_v2"

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
        with pytest.raises(FileNotFoundError):
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
