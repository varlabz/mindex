"""Tests for info function."""

from pathlib import Path

import pytest

from mindex.mindex import add_file, FileInfo, info, info_by_tag


@pytest.fixture
def index_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for the index."""
    return tmp_path


@pytest.fixture
def indexed_file(index_dir: Path) -> Path:
    """Create and index a test file."""
    file_path = index_dir / "test.md"
    file_path.write_text("# Title\n\nSome content here.", encoding="utf-8")
    add_file(index_dir, file_path)
    return file_path


@pytest.fixture
def indexed_file_with_tag(index_dir: Path) -> Path:
    """Create and index a test file with a tag."""
    file_path = index_dir / "tagged.md"
    file_path.write_text("Tagged content.", encoding="utf-8")
    add_file(index_dir, file_path, tag="article")
    return file_path


class TestInfoPositive:
    """Positive test cases for info."""

    def test_info_returns_file_info(self, index_dir: Path, indexed_file: Path):
        """Test that info returns a FileInfo object with correct fields."""
        fi = info(index_dir, indexed_file)
        assert isinstance(fi, FileInfo)
        assert fi.path == str(indexed_file.absolute())
        assert fi.size > 0
        assert fi.updated_at is not None
        assert isinstance(fi.updated_at, str)

    def test_info_returns_size_correctly(self, index_dir: Path, indexed_file: Path):
        """Test that info returns the correct file size."""
        content = indexed_file.read_text(encoding="utf-8")
        fi = info(index_dir, indexed_file)
        assert fi.size == len(content)

    def test_info_returns_none_tag_when_not_set(self, index_dir: Path, indexed_file: Path):
        """Test that info returns None for tag when no tag was set."""
        fi = info(index_dir, indexed_file)
        assert fi.tag is None

    def test_info_returns_tag_when_set(self, index_dir: Path, indexed_file_with_tag: Path):
        """Test that info returns the correct tag."""
        fi = info(index_dir, indexed_file_with_tag)
        assert fi.tag == "article"

    def test_info_returns_absolute_path(self, index_dir: Path, indexed_file: Path):
        """Test that info returns the absolute path."""
        fi = info(index_dir, indexed_file)
        assert fi.path.startswith("/")

    def test_info_empty_file(self, index_dir: Path):
        """Test info on an empty indexed file."""
        file_path = index_dir / "empty.md"
        file_path.write_text("", encoding="utf-8")
        add_file(index_dir, file_path)
        fi = info(index_dir, file_path)
        assert fi.size == 0

    def test_info_large_file(self, index_dir: Path):
        """Test info on a large indexed file."""
        file_path = index_dir / "large.md"
        content = "x" * 100_000
        file_path.write_text(content, encoding="utf-8")
        add_file(index_dir, file_path)
        fi = info(index_dir, file_path)
        assert fi.size == 100_000


class TestInfoNegative:
    """Negative test cases for info."""

    def test_info_file_not_indexed(self, index_dir: Path):
        """Test that info raises FileNotFoundError for non-indexed files."""
        file_path = index_dir / "nonexistent.md"
        with pytest.raises(FileNotFoundError, match="File not indexed"):
            info(index_dir, file_path)

    def test_info_file_exists_but_not_indexed(self, index_dir: Path):
        """Test that info raises FileNotFoundError for files that exist on disk but are not indexed."""
        file_path = index_dir / "not_indexed.md"
        file_path.write_text("I exist but am not indexed.", encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="File not indexed"):
            info(index_dir, file_path)


class TestInfoEdgeCases:
    """Edge cases for info."""

    def test_info_file_with_special_chars_in_name(self, index_dir: Path):
        """Test info on a file with special characters in the name."""
        file_path = index_dir / "test-file_v2.0 (draft).md"
        file_path.write_text("Special name content.", encoding="utf-8")
        add_file(index_dir, file_path)
        fi = info(index_dir, file_path)
        assert fi.size == len("Special name content.")

    def test_info_file_with_unicode_content(self, index_dir: Path):
        """Test info on a file with unicode content."""
        file_path = index_dir / "unicode.md"
        content = "こんにちは世界 🌍"
        file_path.write_text(content, encoding="utf-8")
        add_file(index_dir, file_path)
        fi = info(index_dir, file_path)
        assert fi.size == len(content)


class TestInfoByTagPositive:
    """Positive test cases for info_by_tag."""

    def test_info_by_tag_returns_matching_records(self, index_dir: Path, indexed_file_with_tag: Path):
        """Test that info_by_tag returns records with the specified tag."""
        results = info_by_tag(index_dir, "article")
        assert len(results) == 1
        assert results[0].tag == "article"

    def test_info_by_tag_returns_multiple_records(self, index_dir: Path, indexed_file_with_tag: Path):
        """Test that info_by_tag returns all records with the same tag."""
        for i in range(3):
            file_path = index_dir / f"tagged_{i}.md"
            file_path.write_text(f"Content {i}", encoding="utf-8")
            add_file(index_dir, file_path, tag="article")
        results = info_by_tag(index_dir, "article")
        assert len(results) == 4  # 1 from fixture + 3 added

    def test_info_by_tag_returns_correct_paths(self, index_dir: Path):
        """Test that info_by_tag returns correct file paths."""
        file_path = index_dir / "path_test.md"
        file_path.write_text("Path test content.", encoding="utf-8")
        add_file(index_dir, file_path, tag="test")
        results = info_by_tag(index_dir, "test")
        assert len(results) == 1
        assert results[0].path == str(file_path.absolute())

    def test_info_by_tag_returns_correct_size(self, index_dir: Path):
        """Test that info_by_tag returns correct file sizes."""
        file_path = index_dir / "size_test.md"
        content = "Size test content."
        file_path.write_text(content, encoding="utf-8")
        add_file(index_dir, file_path, tag="test")
        results = info_by_tag(index_dir, "test")
        assert len(results) == 1
        assert results[0].size == len(content)


class TestInfoByTagNegative:
    """Negative test cases for info_by_tag."""

    def test_info_by_tag_no_matching_records(self, index_dir: Path):
        """Test that info_by_tag returns empty list for non-existent tag."""
        results = info_by_tag(index_dir, "nonexistent")
        assert results == []

    def test_info_by_tag_empty_tag(self, index_dir: Path):
        """Test that info_by_tag returns empty list for empty tag string."""
        results = info_by_tag(index_dir, "")
        assert results == []


class TestInfoByTagEdgeCases:
    """Edge cases for info_by_tag."""

    def test_info_by_tag_special_chars_in_tag(self, index_dir: Path):
        """Test info_by_tag with special characters in tag."""
        file_path = index_dir / "special_tag.md"
        file_path.write_text("Special tag content.", encoding="utf-8")
        add_file(index_dir, file_path, tag="test/v2.0 (draft)")
        results = info_by_tag(index_dir, "test/v2.0 (draft)")
        assert len(results) == 1

    def test_info_by_tag_unicode_tag(self, index_dir: Path):
        """Test info_by_tag with unicode tag."""
        file_path = index_dir / "unicode_tag.md"
        file_path.write_text("Unicode tag content.", encoding="utf-8")
        add_file(index_dir, file_path, tag="日本語")
        results = info_by_tag(index_dir, "日本語")
        assert len(results) == 1

    def test_info_after_update(self, index_dir: Path):
        """Test that info reflects updated content size after re-indexing."""
        file_path = index_dir / "update.md"
        file_path.write_text("Short.", encoding="utf-8")
        add_file(index_dir, file_path)
        fi1 = info(index_dir, file_path)

        file_path.write_text("This is much longer content now.", encoding="utf-8")
        add_file(index_dir, file_path)
        fi2 = info(index_dir, file_path)

        assert fi2.size > fi1.size
        assert fi2.size == len("This is much longer content now.")
