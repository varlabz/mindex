#!/usr/bin/env python3
"""
Tests for tag filtering in search function.

Run with: pytest tests/test_tag_filtering.py -v
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from mindex import add_file, search, _parse_tags, _normalize_tags


@pytest.fixture
def temp_index_dir():
    """Create a temporary directory for test index."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_markdown_files():
    """Create temporary markdown files for testing."""
    temp_dir = tempfile.mkdtemp()
    
    file1 = Path(temp_dir) / "python.md"
    file1.write_text("# Python Guide\nPython programming language guide.")
    
    file2 = Path(temp_dir) / "sqlite.md"
    file2.write_text("# SQLite Database\nSQLite database and full-text search.")
    
    file3 = Path(temp_dir) / "tutorial.md"
    file3.write_text("# Tutorial\nPython and SQLite tutorial for beginners.")
    
    yield temp_dir, file1, file2, file3
    shutil.rmtree(temp_dir)


class TestSearchWithTagFiltering:
    """Test search function with tag filtering."""

    def test_search_single_tag(self, temp_index_dir, temp_markdown_files):
        """Test searching with a single tag filter."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        # Add files with different tags
        add_file(file1, index_path, title="Python Guide", summary="Python guide", tags=["python", "programming"])
        add_file(file2, index_path, title="SQLite Database", summary="Database", tags=["sqlite", "database"])
        add_file(file3, index_path, title="Tutorial", summary="Tutorial", tags=["python", "sqlite", "tutorial"])
        
        # Search with single tag
        results = search("guide", index_path, tags=["python"])
        
        assert len(results) == 1
        assert results[0]["title"] == "Python Guide"
        assert "python" in results[0]["tags"]

    def test_search_multiple_tags_and_condition(self, temp_index_dir, temp_markdown_files):
        """Test searching with multiple tags (AND condition - must have all tags)."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        add_file(file1, index_path, title="Python Guide", summary="Python guide", tags=["python", "programming"])
        add_file(file2, index_path, title="SQLite Database", summary="Database", tags=["sqlite", "database"])
        add_file(file3, index_path, title="Tutorial", summary="Tutorial", tags=["python", "sqlite", "tutorial"])
        
        # Search with multiple tags - only file3 has both python AND sqlite
        results = search("tutorial", index_path, tags=["python", "sqlite"])
        
        assert len(results) == 1
        assert results[0]["title"] == "Tutorial"
        assert "python" in results[0]["tags"]
        assert "sqlite" in results[0]["tags"]

    def test_search_no_matching_tags(self, temp_index_dir, temp_markdown_files):
        """Test searching with tags that don't match any documents."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        add_file(file1, index_path, title="Python Guide", summary="Python guide", tags=["python"])
        add_file(file2, index_path, title="SQLite Database", summary="Database", tags=["sqlite"])
        
        # Search with non-existent tag
        results = search("guide", index_path, tags=["nonexistent"])
        
        assert len(results) == 0

    def test_search_without_tag_filter(self, temp_index_dir, temp_markdown_files):
        """Test that search without tags returns all matching documents."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        add_file(file1, index_path, title="Python Guide", summary="Python guide", tags=["python"])
        add_file(file2, index_path, title="SQLite Guide", summary="SQLite guide", tags=["sqlite"])
        
        # Search without tag filter
        results = search("guide", index_path)
        
        assert len(results) == 2

    def test_search_tag_filter_case_insensitive(self, temp_index_dir, temp_markdown_files):
        """Test that tag filtering is case-insensitive."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        # Tags are normalized to lowercase when stored
        add_file(file1, index_path, title="Python Guide", summary="Guide", tags=["python", "Programming"])
        
        # Search with uppercase tag - should work due to case-insensitive search
        results = search("guide", index_path, tags=["PROGRAMMING"])
        
        assert len(results) == 1
        assert results[0]["title"] == "Python Guide"
        # Verify tag was normalized to lowercase in storage
        assert "programming" in results[0]["tags"]


class TestTagParsingHelpers:
    """Test helper functions for tag parsing."""

    def test_normalize_tags_lowercase(self):
        """Test that tags are normalized to lowercase."""
        tags = ["Python", "SQLITE", "Tutorial"]
        result = _normalize_tags(tags)
        assert result == ["python", "sqlite", "tutorial"]

    def test_normalize_tags_strip_whitespace(self):
        """Test that whitespace is stripped from tags."""
        tags = ["  python  ", " sqlite", "tutorial "]
        result = _normalize_tags(tags)
        assert result == ["python", "sqlite", "tutorial"]

    def test_normalize_tags_deduplicate(self):
        """Test that duplicate tags are removed."""
        tags = ["python", "sqlite", "python", "tutorial", "sqlite"]
        result = _normalize_tags(tags)
        assert result == ["python", "sqlite", "tutorial"]

    def test_parse_tags_comma_separated(self):
        """Test parsing comma-separated tags."""
        tags = ["python,sqlite,tutorial"]
        result = _parse_tags(tags)
        assert result == ["python", "sqlite", "tutorial"]

    def test_parse_tags_space_separated(self):
        """Test parsing space-separated tags."""
        tags = ["python sqlite tutorial"]
        result = _parse_tags(tags)
        assert result == ["python", "sqlite", "tutorial"]

    def test_parse_tags_mixed_separators(self):
        """Test parsing tags with mixed comma and space separators."""
        tags = ["python,sqlite", "tutorial database"]
        result = _parse_tags(tags)
        assert result == ["python", "sqlite", "tutorial", "database"]

    def test_parse_tags_none(self):
        """Test that None input returns None."""
        result = _parse_tags(None)
        assert result is None

    def test_parse_tags_empty_list(self):
        """Test that empty list returns None."""
        result = _parse_tags([])
        assert result is None

    def test_parse_tags_with_extra_whitespace(self):
        """Test parsing tags with extra whitespace."""
        tags = ["  python  ,  sqlite  ", "  tutorial  "]
        result = _parse_tags(tags)
        assert result == ["python", "sqlite", "tutorial"]

    def test_parse_tags_deduplication(self):
        """Test that parsed tags are deduplicated and normalized."""
        tags = ["Python,python", "PYTHON sqlite"]
        result = _parse_tags(tags)
        assert result == ["python", "sqlite"]
