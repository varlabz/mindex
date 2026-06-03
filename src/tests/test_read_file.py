"""Tests for read_file function."""

from pathlib import Path

import pytest

from mindex.mindex import _db, add_file, read_file


@pytest.fixture
def index_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for the index."""
    return tmp_path


@pytest.fixture
def indexed_file(index_dir: Path) -> Path:
    """Create and index a test file."""
    file_path = index_dir / "test.md"
    file_path.write_text(
        "# Title\n\nThis is the first paragraph.\n\nThis is the second paragraph.",
        encoding="utf-8",
    )
    add_file(index_dir, file_path)
    return file_path


class TestReadFilePositive:
    """Positive test cases for read_file."""

    def test_read_full_file(self, index_dir: Path, indexed_file: Path):
        """Test reading the entire file content."""
        content = read_file(index_dir, indexed_file)
        expected = "# Title\n\nThis is the first paragraph.\n\nThis is the second paragraph."
        assert content == expected

    def test_read_with_start_zero(self, index_dir: Path, indexed_file: Path):
        """Test reading from the beginning of the file."""
        content = read_file(index_dir, indexed_file, start=0)
        expected = "# Title\n\nThis is the first paragraph.\n\nThis is the second paragraph."
        assert content == expected

    def test_read_with_start_offset(self, index_dir: Path, indexed_file: Path):
        """Test reading from a character offset."""
        content = read_file(index_dir, indexed_file, start=9)
        # "# Title\n\n" is 9 chars, so start=9 skips to "This is..."
        assert content == "This is the first paragraph.\n\nThis is the second paragraph."

    def test_read_with_size(self, index_dir: Path, indexed_file: Path):
        """Test reading a specific number of characters."""
        content = read_file(index_dir, indexed_file, start=0, size=5)
        assert content == "# Tit"

    def test_read_with_start_and_size(self, index_dir: Path, indexed_file: Path):
        """Test reading with both start offset and size."""
        # "# Title\n\n" is 9 chars, so start=9, size=5 gives "This "
        content = read_file(index_dir, indexed_file, start=9, size=5)
        assert content == "This "

    def test_read_partial_last_chars(self, index_dir: Path, indexed_file: Path):
        """Test reading near the end of the file."""
        full = "# Title\n\nThis is the first paragraph.\n\nThis is the second paragraph."
        # Read last 10 chars
        content = read_file(index_dir, indexed_file, start=len(full) - 10)
        assert content == "paragraph."

    def test_read_beyond_end(self, index_dir: Path, indexed_file: Path):
        """Test reading past the end of the file returns what's available."""
        content = read_file(index_dir, indexed_file, start=9999, size=10)
        assert content == ""

    def test_read_size_larger_than_remaining(self, index_dir: Path, indexed_file: Path):
        """Test reading a size larger than remaining content."""
        # "# Title\n\n" is 9 chars, so start=9 leaves from "This is..."
        content = read_file(index_dir, indexed_file, start=9, size=9999)
        expected = "This is the first paragraph.\n\nThis is the second paragraph."
        assert content == expected

    def test_read_empty_file(self, index_dir: Path):
        """Test reading an empty file."""
        file_path = index_dir / "empty.md"
        file_path.write_text("", encoding="utf-8")
        add_file(index_dir, file_path)

        content = read_file(index_dir, file_path)
        assert content == ""

    def test_read_unicode_file(self, index_dir: Path):
        """Test reading a file with unicode content."""
        file_path = index_dir / "unicode.md"
        file_path.write_text("こんにちは世界 🌍 café", encoding="utf-8")
        add_file(index_dir, file_path)

        content = read_file(index_dir, file_path)
        assert content == "こんにちは世界 🌍 café"

    def test_read_unicode_with_offset(self, index_dir: Path):
        """Test reading unicode content with offset."""
        file_path = index_dir / "unicode.md"
        file_path.write_text("こんにちは世界", encoding="utf-8")
        add_file(index_dir, file_path)

        # Python strings are character-based, not byte-based
        # "こんにちは世界" is 7 characters
        content = read_file(index_dir, file_path, start=3, size=1)
        assert content == "ち"

    def test_read_preserves_newlines(self, index_dir: Path, indexed_file: Path):
        """Test that newlines are preserved in read output."""
        content = read_file(index_dir, indexed_file, start=0, size=20)
        assert "\n" in content

    def test_read_multiple_times(self, index_dir: Path, indexed_file: Path):
        """Test reading the same file multiple times returns consistent results."""
        content1 = read_file(index_dir, indexed_file)
        content2 = read_file(index_dir, indexed_file)
        assert content1 == content2


class TestReadFileNegative:
    """Negative test cases for read_file."""

    def test_read_unindexed_file_raises(self, index_dir: Path):
        """Test that reading an unindexed file raises FileNotFoundError."""
        file_path = index_dir / "not_indexed.md"
        file_path.write_text("some content", encoding="utf-8")

        with pytest.raises(FileNotFoundError, match="not indexed"):
            read_file(index_dir, file_path)

    def test_read_deleted_file_raises(self, index_dir: Path, indexed_file: Path):
        """Test that reading a deleted file raises FileNotFoundError."""
        from mindex.mindex import del_file

        del_file(index_dir, indexed_file)

        with pytest.raises(FileNotFoundError, match="not indexed"):
            read_file(index_dir, indexed_file)

    def test_read_nonexistent_path(self, index_dir: Path):
        """Test reading with a path that was never created."""
        file_path = index_dir / "does_not_exist.md"

        with pytest.raises(FileNotFoundError, match="not indexed"):
            read_file(index_dir, file_path)


class TestReadFileEdgeCases:
    """Edge case tests for read_file."""

    def test_read_start_negative(self, index_dir: Path, indexed_file: Path):
        """Test reading with negative start offset."""
        content = read_file(index_dir, indexed_file, start=-5)
        # Python slicing handles negative indices naturally
        assert len(content) > 0

    def test_read_size_zero(self, index_dir: Path, indexed_file: Path):
        """Test reading with size=0 returns empty string."""
        content = read_file(index_dir, indexed_file, start=0, size=0)
        assert content == ""

    def test_read_large_file(self, index_dir: Path):
        """Test reading a large file."""
        file_path = index_dir / "large.md"
        large_content = "x" * 1_000_000
        file_path.write_text(large_content, encoding="utf-8")
        add_file(index_dir, file_path)

        content = read_file(index_dir, file_path)
        assert content == large_content

    def test_read_large_file_with_pagination(self, index_dir: Path):
        """Test reading a large file with pagination."""
        file_path = index_dir / "large.md"
        large_content = "chunkA" * 100_000 + "chunkB" * 100_000
        file_path.write_text(large_content, encoding="utf-8")
        add_file(index_dir, file_path)

        # Read first 100 chars (all chunkA)
        chunk1 = read_file(index_dir, file_path, start=0, size=100)
        # Read from the middle where chunkB starts
        chunk2 = read_file(index_dir, file_path, start=200_000 - 100, size=100)

        assert len(chunk1) == 100
        assert len(chunk2) == 100
        assert chunk1 != chunk2

    def test_read_with_spaces_in_filename(self, index_dir: Path):
        """Test reading a file with spaces in its name."""
        file_path = index_dir / "my file name.md"
        file_path.write_text("content with spaces", encoding="utf-8")
        add_file(index_dir, file_path)

        content = read_file(index_dir, file_path)
        assert content == "content with spaces"

    def test_read_with_newlines_in_content(self, index_dir: Path):
        """Test reading content with many newlines."""
        file_path = index_dir / "newlines.md"
        file_path.write_text("\n\n\n\n", encoding="utf-8")
        add_file(index_dir, file_path)

        content = read_file(index_dir, file_path)
        assert content == "\n\n\n\n"

    def test_read_with_mixed_line_endings(self, index_dir: Path):
        """Test reading content with mixed line endings (LF and CRLF)."""
        file_path = index_dir / "mixed.md"
        file_path.write_text("line1\r\nline2\nline3\r\n", encoding="utf-8")
        add_file(index_dir, file_path)

        content = read_file(index_dir, file_path)
        assert "line1" in content
        assert "line2" in content
        assert "line3" in content
