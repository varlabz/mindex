#!/usr/bin/env python3
"""
Tests for mindex tag functionality.
Covers positive and negative test cases for list_tags, add_file with tags,
and tag normalization.
"""

import pytest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from mindex import add_file, list_tags, info, _normalize_tags, _db


@pytest.fixture
def temp_index_dir():
    """Create a temporary directory for test index."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestNormalizeTagsPositive:
    """Positive tests for _normalize_tags."""

    def test_normalize_lowercase(self):
        """Tags should be lowercased."""
        result = _normalize_tags(["Python", "SQLITE", "Testing"])
        assert result == ["python", "sqlite", "testing"]

    def test_normalize_strip_whitespace(self):
        """Tags should be stripped of leading/trailing whitespace."""
        result = _normalize_tags(["  python  ", " sqlite ", "testing"])
        assert result == ["python", "sqlite", "testing"]

    def test_normalize_deduplicate(self):
        """Duplicate tags should be removed."""
        result = _normalize_tags(["python", "Python", "PYTHON"])
        assert result == ["python"]

    def test_normalize_empty_strings_removed(self):
        """Empty and whitespace-only tags should be removed."""
        result = _normalize_tags(["python", "", "  ", "sqlite"])
        assert result == ["python", "sqlite"]

    def test_normalize_preserves_order(self):
        """Tag order should be preserved (first occurrence)."""
        result = _normalize_tags(["zebra", "apple", "mango"])
        assert result == ["zebra", "apple", "mango"]

    def test_normalize_empty_list(self):
        """Empty list should return empty list."""
        result = _normalize_tags([])
        assert result == []


class TestNormalizeTagsNegative:
    """Negative tests for _normalize_tags."""

    def test_normalize_does_not_modify_internal_spaces(self):
        """Internal spaces are preserved (not stripped)."""
        result = _normalize_tags(["machine learning"])
        assert result == ["machine learning"]

    def test_normalize_does_not_add_tags(self):
        """No tags should be added beyond what was provided."""
        result = _normalize_tags(["python"])
        assert len(result) == 1
        assert "python" in result


class TestAddFileTagsPositive:
    """Positive tests for adding files with tags."""

    def test_add_file_with_single_tag(self, temp_index_dir):
        """Adding a file with one tag should store the tag."""
        index_path = Path(temp_index_dir)
        test_file = Path(temp_index_dir) / "test.md"
        test_file.write_text("# Test\nContent.")

        add_file(test_file, index_path, title="Test", summary="Summary", tags=["python"])

        with _db(index_path) as conn:
            doc = conn.execute("SELECT id FROM docs WHERE path = ?", (str(test_file),)).fetchone()
            tags = [r["tag"] for r in conn.execute(
                "SELECT tag FROM tags WHERE doc_id = ?", (doc["id"],)
            ).fetchall()]
        assert tags == ["python"]

    def test_add_file_with_multiple_tags(self, temp_index_dir):
        """Adding a file with multiple tags should store all tags."""
        index_path = Path(temp_index_dir)
        test_file = Path(temp_index_dir) / "test.md"
        test_file.write_text("# Test\nContent.")

        add_file(test_file, index_path, title="Test", summary="Summary", tags=["python", "sqlite", "testing"])

        with _db(index_path) as conn:
            doc = conn.execute("SELECT id FROM docs WHERE path = ?", (str(test_file),)).fetchone()
            tags = sorted([r["tag"] for r in conn.execute(
                "SELECT tag FROM tags WHERE doc_id = ?", (doc["id"],)
            ).fetchall()])
        assert tags == ["python", "sqlite", "testing"]

    def test_add_file_duplicate_tags_not_stored(self, temp_index_dir):
        """Duplicate tags should not be stored multiple times."""
        index_path = Path(temp_index_dir)
        test_file = Path(temp_index_dir) / "test.md"
        test_file.write_text("# Test\nContent.")

        add_file(test_file, index_path, title="Test", summary="Summary", tags=["python", "python"])

        with _db(index_path) as conn:
            doc = conn.execute("SELECT id FROM docs WHERE path = ?", (str(test_file),)).fetchone()
            tags = [r["tag"] for r in conn.execute(
                "SELECT tag FROM tags WHERE doc_id = ?", (doc["id"],)
            ).fetchall()]
        assert len(tags) == 1

    def test_add_file_no_tags(self, temp_index_dir):
        """Adding a file without tags should succeed with no tags stored."""
        index_path = Path(temp_index_dir)
        test_file = Path(temp_index_dir) / "test.md"
        test_file.write_text("# Test\nContent.")

        add_file(test_file, index_path, title="Test", summary="Summary")

        with _db(index_path) as conn:
            doc = conn.execute("SELECT id FROM docs WHERE path = ?", (str(test_file),)).fetchone()
            tags = conn.execute(
                "SELECT tag FROM tags WHERE doc_id = ?", (doc["id"],)
            ).fetchall()
        assert len(tags) == 0

    def test_add_file_with_empty_tag_list(self, temp_index_dir):
        """Adding a file with an empty tag list should succeed."""
        index_path = Path(temp_index_dir)
        test_file = Path(temp_index_dir) / "test.md"
        test_file.write_text("# Test\nContent.")

        add_file(test_file, index_path, title="Test", summary="Summary", tags=[])

        with _db(index_path) as conn:
            doc = conn.execute("SELECT id FROM docs WHERE path = ?", (str(test_file),)).fetchone()
            tags = conn.execute(
                "SELECT tag FROM tags WHERE doc_id = ?", (doc["id"],)
            ).fetchall()
        assert len(tags) == 0


class TestAddFileTagsNegative:
    """Negative tests for adding files with tags."""

    def test_add_file_tags_none_is_safe(self, temp_index_dir):
        """Passing tags=None should not raise an error."""
        index_path = Path(temp_index_dir)
        test_file = Path(temp_index_dir) / "test.md"
        test_file.write_text("# Test\nContent.")

        add_file(test_file, index_path, title="Test", summary="Summary", tags=None)

        with _db(index_path) as conn:
            doc = conn.execute("SELECT id FROM docs WHERE path = ?", (str(test_file),)).fetchone()
            tags = conn.execute(
                "SELECT tag FROM tags WHERE doc_id = ?", (doc["id"],)
            ).fetchall()
        assert len(tags) == 0


class TestListTagsPositive:
    """Positive tests for list_tags."""

    def test_list_tags_returns_all_unique_tags(self, temp_index_dir):
        """list_tags should return all unique tags across files."""
        index_path = Path(temp_index_dir)

        f1 = Path(temp_index_dir) / "file1.md"
        f1.write_text("# File 1\nContent.")
        add_file(f1, index_path, title="File 1", summary="S1", tags=["python", "ai"])

        f2 = Path(temp_index_dir) / "file2.md"
        f2.write_text("# File 2\nContent.")
        add_file(f2, index_path, title="File 2", summary="S2", tags=["sqlite", "ai"])

        tags = list_tags(index_path)
        assert tags == {"ai", "python", "sqlite"}

    def test_list_tags_empty_index(self, temp_index_dir):
        """list_tags on an empty index should return empty set."""
        index_path = Path(temp_index_dir)
        tags = list_tags(index_path)
        assert tags == set()

    def test_list_tags_ordered(self, temp_index_dir):
        """Tags should be returned in alphabetical order (as a set, order doesn't matter)."""
        index_path = Path(temp_index_dir)
        test_file = Path(temp_index_dir) / "test.md"
        test_file.write_text("# Test\nContent.")

        add_file(test_file, index_path, title="Test", summary="Summary", tags=["zebra", "apple", "mango"])

        tags = list_tags(index_path)
        assert tags == {"zebra", "apple", "mango"}


class TestListTagsNegative:
    """Negative tests for list_tags."""

class TestInfoTagsPositive:
    """Positive tests for info() with tags."""

    def test_info_returns_tags(self, temp_index_dir):
        """info() should include tags in the returned dict."""
        index_path = Path(temp_index_dir)
        test_file = Path(temp_index_dir) / "test.md"
        test_file.write_text("# Test\nContent.")

        add_file(test_file, index_path, title="Test", summary="Summary", tags=["python", "sqlite"])

        obj = info(test_file, index_path)
        assert "tags" in obj
        assert sorted(obj["tags"]) == ["python", "sqlite"]

    def test_info_returns_empty_tags_list(self, temp_index_dir):
        """info() should return empty list for file with no tags."""
        index_path = Path(temp_index_dir)
        test_file = Path(temp_index_dir) / "test.md"
        test_file.write_text("# Test\nContent.")

        add_file(test_file, index_path, title="Test", summary="Summary")

        obj = info(test_file, index_path)
        assert obj["tags"] == []


class TestInfoTagsNegative:
    """Negative tests for info() with tags."""

    def test_info_raises_for_unindexed_file(self, temp_index_dir):
        """info() should raise ValueError for a file not in the index."""
        index_path = Path(temp_index_dir)
        test_file = Path(temp_index_dir) / "missing.md"
        test_file.write_text("# Missing\nNot indexed.")

        with pytest.raises(ValueError, match="not indexed"):
            info(test_file, index_path)
